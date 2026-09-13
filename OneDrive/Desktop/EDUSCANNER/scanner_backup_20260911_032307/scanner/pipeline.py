"""
Pipeline do Scanner (Seção 14):

    imagem
      -> pré-processamento / validação
      -> detecção do cartão (4 cantos)
      -> correção de perspectiva
      -> normalização (imagem canônica)
      -> detecção das regiões vermelhas
      -> leitura das bolhas
      -> resultado por questão

Este módulo apenas ORQUESTRA os componentes abaixo — cada um deles é
testável isoladamente e não conhece o restante do sistema (banco,
API, interface). Ele não sabe nada sobre o gabarito: só devolve o que
foi lido na imagem.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import cv2
import numpy as np

from backend.services.scanner.card_detector import CardDetector
from backend.services.scanner.perspective import PerspectiveCorrector
from backend.services.scanner.color_detector import ColorDetector
from backend.services.scanner.bubble_reader import BubbleDetector, BubbleReader
from backend.services.scanner.question_analyzer import QuestionAnalyzer
from backend.services.scanner.validator import ScanValidator
from backend.services.scanner.layout import build_layout

CANON_WIDTH_PX = 950


@dataclass
class OMRQuestion:
    number: int
    answer: Optional[str]
    confidence: float
    ratios: Dict[str, float]
    status: str = "OK"  # "OK" | "BLANK" | "MULT"


@dataclass
class OMRResult:
    questions: List[OMRQuestion] = field(default_factory=list)
    debug_message: str = ""
    ok: bool = True


class ScanPipeline:
    def __init__(self) -> None:
        self.card_detector = CardDetector()
        self.perspective = PerspectiveCorrector()
        self.color_detector = ColorDetector()
        self.question_analyzer = QuestionAnalyzer()
        self.validator = ScanValidator()

    def run(self, image_bytes: bytes, question_count: int) -> OMRResult:
        array = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            return OMRResult([], "Não foi possível abrir a imagem. Tente novamente.", ok=False)

        # Redimensiona ANTES de qualquer outra etapa. Fotos de celular
        # costumam vir em 3000-4000px de lado; processar tudo nesse
        # tamanho é desnecessário (a leitura final usa uma imagem
        # canônica bem menor de qualquer forma) e caro — em especial o
        # cálculo de nitidez/brilho da validação, que antes rodava
        # sobre a imagem inteira. Redimensionar primeiro corta esse
        # custo proporcionalmente ao quadrado da escala (Seção 33).
        image = self._resize_for_processing(image, max_side=1600)

        ok, message = self.validator.validate_readability(image)
        if not ok:
            return OMRResult([], message, ok=False)

        corners = self.card_detector.find_corners(image)
        ok, message = self.validator.validate_card_found(corners, image.shape)
        if not ok:
            return OMRResult([], message, ok=False)

        layout = build_layout(question_count)
        detector = BubbleDetector(layout, canon_w=CANON_WIDTH_PX)
        canonical = self.perspective.warp(image, corners, detector.canon_w, detector.canon_h)

        red_mask = self.color_detector.red_mask(canonical)
        reader = BubbleReader(red_mask, detector.radius_px)

        questions: List[OMRQuestion] = []
        blanks = mults = 0
        for q in range(1, question_count + 1):
            ratios = reader.read_question(detector, q)
            reading = self.question_analyzer.analyze(q, ratios)
            if reading.status == "BLANK":
                blanks += 1
            elif reading.status == "MULT":
                mults += 1
            questions.append(
                OMRQuestion(
                    number=reading.number,
                    answer=reading.answer,
                    confidence=reading.confidence,
                    ratios=reading.ratios,
                    status=reading.status,
                )
            )

        message = f"Leitura concluída: {question_count - blanks - mults} identificadas"
        if blanks:
            message += f", {blanks} em branco"
        if mults:
            message += f", {mults} com múltiplas marcações"
        message += "."

        return OMRResult(questions, message, ok=True)

    @staticmethod
    def _resize_for_processing(image: np.ndarray, max_side: int) -> np.ndarray:
        h, w = image.shape[:2]
        scale = min(1.0, max_side / max(h, w))
        if scale >= 1.0:
            return image
        # INTER_AREA dá melhor qualidade para reduzir imagens, mas
        # INTER_LINEAR é bem mais rápido e, nesta escala, indistinguível
        # para o que o pipeline precisa (detectar bordas e cor, não
        # detalhe fino) — a leitura final acontece na imagem canônica
        # normalizada, não nesta.
        return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)


_pipeline = ScanPipeline()


def analyze_image(image_bytes: bytes, question_count: int) -> OMRResult:
    """Ponto de entrada usado pelas rotas da API (mantém compatibilidade)."""
    return _pipeline.run(image_bytes, question_count)
