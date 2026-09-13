"""
Gera o cartão-resposta em PDF para impressão (Seção 10).

Regra visual obrigatória:
    QUESTÃO (número) = AZUL
    BOLHAS (A-E)     = VERMELHO

As posições vêm de backend.services.scanner.layout, a MESMA geometria
usada pelo módulo de scanner para localizar as bolhas na leitura — ou
seja, o cartão impresso e o cartão lido nunca podem "dessincronizar".
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from backend.services.scanner.layout import (
    build_layout,
    BORDER_MARGIN_MM,
    BORDER_STROKE_MM,
    CONTENT_H_MM,
    HEADER_H_MM,
    BUBBLE_RADIUS_MM,
    OPTIONS,
)

COLOR_BLUE = (0.05, 0.24, 0.85)   # questão
COLOR_RED = (0.86, 0.08, 0.08)    # bolha
COLOR_BORDER = (0, 0, 0)


def _to_page_xy(x_mm: float, y_mm: float) -> tuple:
    """Converte (x,y) relativos à caixa de conteúdo (origem topo-esquerda)
    para coordenadas de página do reportlab (origem embaixo-esquerda)."""
    page_x = (BORDER_MARGIN_MM + x_mm) * mm
    page_y = (297.0 - BORDER_MARGIN_MM - y_mm) * mm
    return page_x, page_y


def build_answer_card_pdf(card, teacher_name: str = "") -> BytesIO:
    layout = build_layout(card.question_count)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"EDUSCANNER - {card.name}")

    # Borda (âncora usada pelo CardDetector na leitura)
    c.setStrokeColorRGB(*COLOR_BORDER)
    c.setLineWidth(BORDER_STROKE_MM * mm)
    border_x = BORDER_MARGIN_MM * mm
    border_y = (297.0 - BORDER_MARGIN_MM - CONTENT_H_MM) * mm
    c.rect(border_x, border_y, (210.0 - 2 * BORDER_MARGIN_MM) * mm, CONTENT_H_MM * mm, stroke=1, fill=0)

    # Cabeçalho
    hx, _ = _to_page_xy(0, 0)
    top_y = (297.0 - BORDER_MARGIN_MM - 8) * mm
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(hx + 2 * mm, top_y, "EDUSCANNER")
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.45, 0.55)
    c.drawString(hx + 2 * mm, top_y - 4.5 * mm, "Cartão-resposta — preencha as bolhas de vermelho")

    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.drawString(hx + 2 * mm, top_y - 12 * mm, card.name)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.4, 0.45, 0.55)
    c.drawString(hx + 2 * mm, top_y - 17 * mm, f"Bloco {card.block} · {card.question_count} questões")

    field_y = top_y - 25 * mm
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.2, 0.25, 0.32)
    for label, x_offset, width_mm in (
        ("Nome do aluno", 0, 95),
        ("ID / Número", 100, 40),
        ("Turma", 145, 45),
    ):
        c.drawString(hx + x_offset * mm, field_y, label)
        c.setLineWidth(0.4)
        c.line(hx + x_offset * mm, field_y - 2 * mm, hx + (x_offset + width_mm) * mm, field_y - 2 * mm)

    # Questões e bolhas
    c.setFont("Helvetica-Bold", 8.5)
    for q, (lx, ly) in layout.label_positions_mm.items():
        px, py = _to_page_xy(lx, ly)
        c.setFillColorRGB(*COLOR_BLUE)
        c.drawCentredString(px, py - 2.6, str(q))

    c.setLineWidth(0.9 * mm)
    for q, opts in layout.bubble_positions_mm.items():
        for letter in OPTIONS:
            bx, by = opts[letter]
            px, py = _to_page_xy(bx, by)
            c.setStrokeColorRGB(*COLOR_RED)
            c.setFillColorRGB(1, 1, 1)
            c.circle(px, py, BUBBLE_RADIUS_MM * mm, stroke=1, fill=1)
            c.setFont("Helvetica", 6.5)
            c.setFillColorRGB(*COLOR_RED)
            c.drawCentredString(px, py - 2.1, letter)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
