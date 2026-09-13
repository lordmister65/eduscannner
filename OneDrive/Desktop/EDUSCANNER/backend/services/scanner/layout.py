"""
Geometria do cartão-resposta.

Este módulo é a ÚNICA fonte de verdade sobre onde cada bolha fica no
cartão. Ele é usado tanto para:

    1. desenhar o cartão-resposta em PDF (para impressão);
    2. localizar as bolhas na imagem já corrigida (para leitura OMR).

Trabalhamos em milímetros dentro de uma "caixa de conteúdo" (a área
delimitada pela borda preta grossa que é impressa no cartão). Essa
borda é o que o CardDetector localiza na foto e usa para corrigir a
perspectiva, então a caixa de conteúdo em mm mapeia 1:1 para a imagem
corrigida (canônica), o que elimina a dependência do tamanho físico da
foto (Seção 13 do briefing).
"""

from dataclasses import dataclass
from typing import Dict, Tuple

# Página A4 em milímetros
PAGE_W_MM = 210.0
PAGE_H_MM = 297.0

# Espessura/posição da borda impressa (usada pelo CardDetector como âncora)
BORDER_MARGIN_MM = 10.0
BORDER_STROKE_MM = 2.6

# Caixa de conteúdo = área interna da borda
CONTENT_W_MM = PAGE_W_MM - 2 * BORDER_MARGIN_MM
CONTENT_H_MM = PAGE_H_MM - 2 * BORDER_MARGIN_MM

# Cabeçalho (nome do aluno, turma, ID, nome do cartão) — não é lido pelo OMR
HEADER_H_MM = 40.0

# Grade de questões
GRID_TOP_MM = HEADER_H_MM + 5.0
GRID_BOTTOM_MARGIN_MM = 7.0
LABEL_W_MM = 14.0
LABEL_GAP_MM = 4.0
BUBBLE_RADIUS_MM = 2.4

OPTIONS = ("A", "B", "C", "D", "E")


def grid_dimensions(question_count: int) -> Tuple[int, int]:
    """Define colunas x linhas para o bloco. Blocos válidos: 20, 30, 45."""
    if question_count <= 0:
        raise ValueError("question_count deve ser positivo")
    columns = 3 if question_count >= 45 else 2
    if question_count % columns != 0:
        # fallback genérico e determinístico para blocos não previstos
        columns = 1
        while question_count % columns == 0 and question_count // columns > 15:
            columns += 1
    rows = question_count // columns
    return columns, rows


@dataclass(frozen=True)
class CardLayout:
    question_count: int
    columns: int
    rows: int
    # posições em mm, relativas à caixa de conteúdo (origem = canto sup. esq.)
    bubble_positions_mm: Dict[int, Dict[str, Tuple[float, float]]]
    label_positions_mm: Dict[int, Tuple[float, float]]

    def bubble_positions_px(self, canon_w: int) -> Tuple[Dict[int, Dict[str, Tuple[float, float]]], float, int]:
        """Converte para pixels em uma imagem canônica de largura canon_w
        (altura derivada automaticamente para preservar a proporção)."""
        scale = canon_w / CONTENT_W_MM
        canon_h = round(canon_w * CONTENT_H_MM / CONTENT_W_MM)
        positions_px = {
            q: {opt: (x * scale, y * scale) for opt, (x, y) in opts.items()}
            for q, opts in self.bubble_positions_mm.items()
        }
        radius_px = BUBBLE_RADIUS_MM * scale
        return positions_px, radius_px, canon_h


def build_layout(question_count: int) -> CardLayout:
    columns, rows = grid_dimensions(question_count)
    grid_h_mm = CONTENT_H_MM - GRID_TOP_MM - GRID_BOTTOM_MARGIN_MM
    col_w_mm = CONTENT_W_MM / columns
    row_h_mm = grid_h_mm / rows

    bubble_positions: Dict[int, Dict[str, Tuple[float, float]]] = {}
    label_positions: Dict[int, Tuple[float, float]] = {}

    usable_w_mm = col_w_mm - LABEL_W_MM - LABEL_GAP_MM
    spacing_mm = usable_w_mm / len(OPTIONS)

    q = 1
    for c in range(columns):
        col_x0 = c * col_w_mm
        for r in range(rows):
            row_y0 = GRID_TOP_MM + r * row_h_mm
            cy = row_y0 + row_h_mm / 2
            label_positions[q] = (col_x0 + LABEL_W_MM * 0.5, cy)
            opts: Dict[str, Tuple[float, float]] = {}
            for i, letter in enumerate(OPTIONS):
                cx = col_x0 + LABEL_W_MM + LABEL_GAP_MM + spacing_mm * (i + 0.5)
                opts[letter] = (cx, cy)
            bubble_positions[q] = opts
            q += 1

    return CardLayout(
        question_count=question_count,
        columns=columns,
        rows=rows,
        bubble_positions_mm=bubble_positions,
        label_positions_mm=label_positions,
    )
