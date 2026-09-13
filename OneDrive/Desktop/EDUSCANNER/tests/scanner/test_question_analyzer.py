from backend.services.scanner.question_analyzer import QuestionAnalyzer


def test_blank_when_nothing_marked():
    analyzer = QuestionAnalyzer()
    reading = analyzer.analyze(1, {"A": 0.0, "B": 0.05, "C": 0.1, "D": 0.0, "E": 0.02})
    assert reading.status == "BLANK"
    assert reading.answer is None


def test_ok_when_single_bubble_clearly_marked():
    analyzer = QuestionAnalyzer()
    reading = analyzer.analyze(2, {"A": 0.02, "B": 0.9, "C": 0.05, "D": 0.0, "E": 0.03})
    assert reading.status == "OK"
    assert reading.answer == "B"
    assert reading.confidence > 0.5


def test_mult_when_two_bubbles_clearly_marked():
    analyzer = QuestionAnalyzer()
    reading = analyzer.analyze(3, {"A": 0.8, "B": 0.0, "C": 0.75, "D": 0.0, "E": 0.0})
    assert reading.status == "MULT"
    assert reading.answer is None


def test_mult_never_guesses_an_answer_even_with_a_leader():
    """Seção 16: não tentar adivinhar qual seria a resposta correta."""
    analyzer = QuestionAnalyzer()
    reading = analyzer.analyze(4, {"A": 0.95, "B": 0.4, "C": 0.0, "D": 0.0, "E": 0.0})
    assert reading.status == "MULT"
    assert reading.answer is None


def test_threshold_is_configurable():
    analyzer = QuestionAnalyzer(mark_threshold=0.5)
    reading = analyzer.analyze(5, {"A": 0.4, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0})
    assert reading.status == "BLANK"
