"""
PerspectiveCorrector

Responsabilidade única: dado os quatro cantos do cartão na foto original,
corrigir a perspectiva e devolver uma imagem "canônica" de tamanho fixo.

É essa etapa que resolve a Seção 13 (cartões de tamanhos diferentes,
distância, rotação, perspectiva): depois dela, coordenadas normalizadas
do layout do cartão mapeiam diretamente para pixels, não importa como a
foto original foi tirada.
"""

import cv2
import numpy as np


class PerspectiveCorrector:
    def warp(self, image: np.ndarray, corners: np.ndarray, canon_w: int, canon_h: int) -> np.ndarray:
        dst = np.array(
            [[0, 0], [canon_w - 1, 0], [canon_w - 1, canon_h - 1], [0, canon_h - 1]],
            dtype=np.float32,
        )
        matrix = cv2.getPerspectiveTransform(corners.astype(np.float32), dst)
        return cv2.warpPerspective(image, matrix, (canon_w, canon_h))
