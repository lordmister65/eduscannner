"""
CardDetector

Responsabilidade única: encontrar, em uma foto qualquer (ângulo,
distância, iluminação, tamanho variados), o quadrilátero correspondente
à borda impressa do cartão-resposta e devolver os quatro cantos.

Não sabe nada sobre bolhas, questões ou banco de dados (Seção 28).

Ponto importante: a aresta de maior contraste em uma foto normalmente
é o limite do PAPEL (branco) contra o fundo da mesa — não a borda
impressa do cartão. Por isso não basta pegar "o maior quadrilátero":
cada candidato é verificado quanto à sua escuridão ABSOLUTA (não
relativa) ao longo do próprio traço, usando a imagem em escala de
cinza original. Só a borda realmente impressa em preto passa nesse
filtro.
"""

from typing import Optional
import cv2
import numpy as np

# Pixels com este nível de cinza ou mais escuros são considerados
# "tinta preta"; qualquer coisa mais clara (papel, fundo, sombra leve)
# não conta, mesmo que seja uma aresta de alto contraste.
ABSOLUTE_DARK_LIMIT = 115


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Ordena 4 pontos como [topo-esq, topo-dir, baixo-dir, baixo-esq]."""
    pts = pts.reshape(4, 2)
    ordered = np.zeros((4, 2), dtype=np.float32)

    s = pts.sum(axis=1)
    ordered[0] = pts[np.argmin(s)]  # topo-esquerda: menor soma x+y
    ordered[2] = pts[np.argmax(s)]  # baixo-direita: maior soma x+y

    diff = np.diff(pts, axis=1).reshape(-1)
    ordered[1] = pts[np.argmin(diff)]  # topo-direita: menor (y - x)
    ordered[3] = pts[np.argmax(diff)]  # baixo-esquerda: maior (y - x)

    return ordered


class CardDetector:
    """Localiza o cartão (borda impressa) em uma imagem."""

    def __init__(self, min_area_ratio: float = 0.12, dark_limit: int = ABSOLUTE_DARK_LIMIT):
        # área mínima do quadrilátero encontrado em relação à área total
        # da imagem: evita confundir objetos pequenos com o cartão.
        self.min_area_ratio = min_area_ratio
        self.dark_limit = dark_limit

    def find_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        h, w = image.shape[:2]
        image_area = float(h * w)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        candidates = self._collect_candidates(blurred, image_area)
        if not candidates:
            return None

        # Entre os candidatos, mantém só os cujo traço é REALMENTE preto
        # (não apenas "mais escuro que a vizinhança") e, entre esses,
        # escolhe o mais escuro — não o maior. A borda de maior área em
        # uma foto costuma ser o limite do PAPEL contra o fundo, que
        # também pode parecer "escuro o bastante" sob luz fraca; mas a
        # tinta preta impressa é sempre substancialmente mais escura que
        # qualquer fundo, então a escuridão (não a área) é o critério
        # confiável para distinguir as duas.
        scored = []
        for area, approx in candidates:
            darkness = self._perimeter_darkness(blurred, approx)
            if darkness is not None and darkness < self.dark_limit:
                scored.append((darkness, area, approx))
        if not scored:
            return None

        scored.sort(key=lambda item: item[0])
        best = scored[0][2].astype(np.float32)
        best = self._refine_corners(gray, best)
        return _order_corners(best)

    def _refine_corners(self, gray: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Refina os 4 cantos com precisão sub-pixel (cv2.cornerSubPix).
        approxPolyDP entrega cantos com erro de vários pixels, o que é
        suficiente para desalinhar a leitura das bolhas em uma grade
        densa; o refinamento sub-pixel reduz esse erro de forma
        consistente, quaisquer que sejam as condições de iluminação."""
        pts = pts.reshape(-1, 1, 2).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
        try:
            refined = cv2.cornerSubPix(gray, pts, (11, 11), (-1, -1), criteria)
            return refined.reshape(-1, 2)
        except cv2.error:
            return pts.reshape(-1, 2)

    def _collect_candidates(self, gray_blurred: np.ndarray, image_area: float):
        """Gera candidatos a quadrilátero a partir de bordas de contraste
        (Canny). Não filtra por cor ainda — isso é feito depois, com a
        verificação de escuridão absoluta, que é a parte que realmente
        distingue a borda impressa do limite do papel."""
        edges = cv2.Canny(gray_blurred, 40, 120)
        edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area_ratio * image_area:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                candidates.append((area, approx))
        return candidates

    def _perimeter_darkness(self, gray: np.ndarray, approx: np.ndarray):
        """Devolve a intensidade média (0-255) dos pixels em cima do
        próprio traço do candidato, amostrados na imagem em escala de
        cinza ORIGINAL — não apenas uma transição de contraste local."""
        h, w = gray.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        thickness = max(3, int(round(0.01 * max(h, w))))
        cv2.polylines(mask, [approx.astype(np.int32)], True, 255, thickness)

        sampled = gray[mask > 0]
        if sampled.size < 20:
            return None
        return float(np.mean(sampled))
