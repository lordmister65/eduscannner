"""
QuestionAnalyzer

Responsabilidade única: dado o fill ratio de cada alternativa (A-E) de
uma questão, decidir o status da questão:

    - "OK"    -> uma alternativa claramente marcada
    - "BLANK" -> nenhuma alternativa atingiu o mínimo (Seção 17)
    - "MULT"  -> duas ou mais alternativas claramente marcadas (Seção 16)

Esta classe NÃO compara com o gabarito — isso é responsabilidade da
correção (Seção 19), feita depois, fora do módulo de scanner.
"""

from dataclasses import dataclass
from typing import Dict, Optional

# fração mínima de vermelho dentro do círculo para considerar "marcada"
MARK_THRESHOLD = 0.35


@dataclass(frozen=True)
class QuestionReading:
    number: int
    status: str  # "OK" | "BLANK" | "MULT"
    answer: Optional[str]
    confidence: float
    ratios: Dict[str, float]


class QuestionAnalyzer:
    def __init__(self, mark_threshold: float = MARK_THRESHOLD):
        self.mark_threshold = mark_threshold

    def analyze(self, number: int, ratios: Dict[str, float]) -> QuestionReading:
        marked = {opt: r for opt, r in ratios.items() if r >= self.mark_threshold}

        if len(marked) == 0:
            return QuestionReading(number, "BLANK", None, 0.0, ratios)

        if len(marked) >= 2:
            return QuestionReading(number, "MULT", None, 0.0, ratios)

        answer, ratio = next(iter(marked.items()))
        others = sorted((r for opt, r in ratios.items() if opt != answer), reverse=True)
        second = others[0] if others else 0.0
        # confiança combina o quão preenchida está a bolha e a margem
        # em relação à segunda alternativa mais marcada
        confidence = round(min(1.0, (ratio * 0.6) + ((ratio - second) * 0.4)), 3)
        return QuestionReading(number, "OK", answer, max(0.0, confidence), ratios)
