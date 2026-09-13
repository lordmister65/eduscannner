"""
BubbleDetector + BubbleReader

BubbleDetector: sabe ONDE cada bolha está na imagem canônica (usa o
CardLayout — não adivinha nada, as posições vêm do mesmo gerador que
desenha o cartão para impressão).

BubbleReader: sabe LER o quanto de vermelho existe dentro de cada bolha
e devolve um "fill ratio" (0..1) por alternativa.

Nenhum dos dois conhece regras de correção/negócio (Seção 28).
"""

from typing import Dict, Tuple
import cv2
import numpy as np

from backend.services.scanner.layout import CardLayout, OPTIONS


class BubbleDetector:
    def __init__(self, layout: CardLayout, canon_w: int = 950):
        self.layout = layout
        self.positions_px, self.radius_px, self.canon_h = layout.bubble_positions_px(canon_w)
        self.canon_w = canon_w

    def bubble_center(self, question: int, option: str) -> Tuple[float, float]:
        return self.positions_px[question][option]


class BubbleReader:
    """Mede a fração de pixels vermelhos dentro do círculo de cada bolha."""

    def __init__(self, red_mask: np.ndarray, radius_px: float):
        self.red_mask = red_mask
        self.radius = max(3, int(round(radius_px)))
        # template circular reutilizado para todas as bolhas
        side = self.radius * 2 + 1
        template = np.zeros((side, side), dtype=np.uint8)
        cv2.circle(template, (self.radius, self.radius), self.radius, 255, -1)
        self._circle_template = template
        self._circle_area = int(cv2.countNonZero(template))

    def fill_ratio(self, center_x: float, center_y: float) -> float:
        h, w = self.red_mask.shape[:2]
        cx, cy = int(round(center_x)), int(round(center_y))
        r = self.radius
        x0, y0 = cx - r, cy - r
        x1, y1 = cx + r + 1, cy + r + 1

        if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            return 0.0

        roi = self.red_mask[y0:y1, x0:x1]
        if roi.shape != self._circle_template.shape:
            return 0.0

        masked = cv2.bitwise_and(roi, self._circle_template)
        filled = int(cv2.countNonZero(masked))
        return filled / self._circle_area if self._circle_area else 0.0

    def read_question(self, detector: BubbleDetector, question: int) -> Dict[str, float]:
        ratios = {}
        for option in OPTIONS:
            cx, cy = detector.bubble_center(question, option)
            ratios[option] = self.fill_ratio(cx, cy)
        return ratios
