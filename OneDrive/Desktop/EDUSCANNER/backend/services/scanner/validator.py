"""
ScanValidator

Responsabilidade única: decidir se a imagem recebida é utilizável antes
de tentarmos ler qualquer bolha, e produzir uma mensagem clara e não
técnica para o professor quando não for (Seção 14 e 31).
"""

from typing import Optional, Tuple
import cv2
import numpy as np

MIN_BRIGHTNESS = 35.0
MIN_SHARPNESS = 35.0
MIN_CARD_AREA_RATIO = 0.15


class ScanValidator:
    def validate_readability(self, image: Optional[np.ndarray]) -> Tuple[bool, str]:
        if image is None:
            return False, "Não foi possível abrir a imagem. Tente novamente."

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        brightness = float(np.mean(gray))
        if brightness < MIN_BRIGHTNESS:
            return False, "Imagem muito escura. Tente novamente com mais luz."

        sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())
        if sharpness < MIN_SHARPNESS:
            return False, "Imagem muito borrada. Segure o celular firme e tente novamente."

        return True, ""

    def validate_card_found(self, corners, image_shape) -> Tuple[bool, str]:
        if corners is None:
            return False, "Cartão não encontrado. Posicione o cartão inteiro dentro da câmera, sobre um fundo liso."

        h, w = image_shape[:2]
        area = cv2.contourArea(corners.astype(np.float32))
        image_area = float(h * w)
        if area < MIN_CARD_AREA_RATIO * image_area:
            return False, "O cartão parece cortado ou muito distante. Aproxime a câmera e enquadre o cartão inteiro."

        return True, ""
