"""
ColorDetector

Responsabilidade única: transformar uma imagem BGR em uma máscara binária
das regiões vermelhas (bolhas marcadas), usando HSV — não escala de
cinza — para ser resistente a iluminação, sombra e variações de câmera
(Seção 12).
"""

import cv2
import numpy as np


class ColorDetector:
    # Duas faixas porque o vermelho "cruza" o 0/180 no espaço de matiz do HSV.
    LOWER_RED_1 = (0, 90, 60)
    UPPER_RED_1 = (10, 255, 255)
    LOWER_RED_2 = (170, 90, 60)
    UPPER_RED_2 = (180, 255, 255)

    def red_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        mask_a = cv2.inRange(hsv, np.array(self.LOWER_RED_1), np.array(self.UPPER_RED_1))
        mask_b = cv2.inRange(hsv, np.array(self.LOWER_RED_2), np.array(self.UPPER_RED_2))
        mask = cv2.bitwise_or(mask_a, mask_b)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask
