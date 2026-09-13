"""
Teste de integração do pipeline de scanner.

Como não temos fotos reais de cartões neste ambiente, este teste
DESENHA um cartão sintético usando a mesma geometria de
backend.services.scanner.layout (a mesma fonte de verdade usada para
gerar o PDF), aplica uma distorção de perspectiva/rotação/iluminação
para simular uma foto tirada com o celular, e então roda o pipeline
completo (backend.services.scanner.analyze_image) para conferir se as
respostas marcadas são lidas corretamente.

Isso cobre a Seção 32 (testes de detecção de bolhas vermelhas, cartões
em diferentes ângulos/perspectiva, condições de iluminação).
"""

import random

import cv2
import numpy as np
import pytest

from backend.services.scanner.layout import (
    build_layout,
    BORDER_MARGIN_MM,
    BORDER_STROKE_MM,
    PAGE_W_MM,
    PAGE_H_MM,
    BUBBLE_RADIUS_MM,
    OPTIONS,
)
from backend.services.scanner import analyze_image


def render_synthetic_card(
    question_count,
    chosen_answers,
    px_per_mm=6,
    rotate_deg=6,
    perspective_jitter=25,
    brightness=1.0,
    noise=False,
    seed=42,
):
    """Desenha um cartão-resposta sintético e simula uma foto tirada em
    ângulo, com fundo, rotação, perspectiva e iluminação variáveis."""
    page_w = int(PAGE_W_MM * px_per_mm)
    page_h = int(PAGE_H_MM * px_per_mm)
    img = np.full((page_h, page_w, 3), 255, dtype=np.uint8)

    bx0 = int(BORDER_MARGIN_MM * px_per_mm)
    by0 = int(BORDER_MARGIN_MM * px_per_mm)
    bx1 = int((PAGE_W_MM - BORDER_MARGIN_MM) * px_per_mm)
    by1 = int((PAGE_H_MM - BORDER_MARGIN_MM) * px_per_mm)
    cv2.rectangle(img, (bx0, by0), (bx1, by1), (0, 0, 0), int(BORDER_STROKE_MM * px_per_mm))

    layout = build_layout(question_count)
    radius_px = int(BUBBLE_RADIUS_MM * px_per_mm)
    for q, opts in layout.bubble_positions_mm.items():
        chosen = chosen_answers.get(q)
        fill_letters = set(OPTIONS[:2]) if chosen == "MULT" else ({chosen} if chosen else set())
        for letter in OPTIONS:
            mx, my = opts[letter]
            cx = bx0 + int(mx * px_per_mm)
            cy = by0 + int(my * px_per_mm)
            cv2.circle(img, (cx, cy), radius_px, (30, 20, 200), 2)
            if letter in fill_letters:
                cv2.circle(img, (cx, cy), radius_px - 1, (20, 15, 190), -1)

    canvas_w, canvas_h = page_w + 400, page_h + 400
    canvas = np.full((canvas_h, canvas_w, 3), 90, dtype=np.uint8)
    ox, oy = 200, 200
    canvas[oy:oy + page_h, ox:ox + page_w] = img

    src = np.float32([[0, 0], [canvas_w, 0], [canvas_w, canvas_h], [0, canvas_h]])
    rnd = random.Random(seed)
    jitter = lambda: rnd.uniform(-perspective_jitter, perspective_jitter)
    dst = np.float32([
        [jitter(), jitter()],
        [canvas_w + jitter(), jitter()],
        [canvas_w + jitter(), canvas_h + jitter()],
        [jitter(), canvas_h + jitter()],
    ])
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(canvas, matrix, (canvas_w, canvas_h), borderValue=(90, 90, 90))

    center = (canvas_w // 2, canvas_h // 2)
    rot_matrix = cv2.getRotationMatrix2D(center, rotate_deg, 1.0)
    rotated = cv2.warpAffine(warped, rot_matrix, (canvas_w, canvas_h), borderValue=(90, 90, 90))

    if brightness != 1.0:
        rotated = np.clip(rotated.astype(np.float32) * brightness, 0, 255).astype(np.uint8)
    if noise:
        n = np.random.default_rng(seed).normal(0, 8, rotated.shape)
        rotated = np.clip(rotated.astype(np.int16) + n.astype(np.int16), 0, 255).astype(np.uint8)

    ok, buf = cv2.imencode(".jpg", rotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    assert ok
    return buf.tobytes()


def _accuracy(question_count, answers, **distortion):
    img_bytes = render_synthetic_card(question_count, answers, **distortion)
    result = analyze_image(img_bytes, question_count)
    assert result.ok, result.debug_message
    correct = 0
    for reading in result.questions:
        expected = answers.get(reading.number)
        if expected == "MULT":
            correct += reading.status == "MULT"
        elif expected is None:
            correct += reading.status == "BLANK"
        else:
            correct += reading.status == "OK" and reading.answer == expected
    return correct / question_count


@pytest.mark.parametrize("question_count", [20, 30, 45])
def test_reads_all_blocks_correctly_under_mild_distortion(question_count):
    answers = {q: OPTIONS[(q * 3 + 1) % 5] for q in range(1, question_count + 1)}
    accuracy = _accuracy(question_count, answers, rotate_deg=5, perspective_jitter=20)
    assert accuracy == 1.0


def test_detects_blank_and_multi_mark_questions():
    question_count = 30
    answers = {q: OPTIONS[(q * 7) % 5] for q in range(1, question_count + 1)}
    answers[5] = None
    answers[12] = "MULT"
    accuracy = _accuracy(question_count, answers, rotate_deg=7, perspective_jitter=30)
    assert accuracy == 1.0


@pytest.mark.parametrize("rotate_deg,jitter", [(15, 50), (-20, 60), (0, 0)])
def test_tolerates_rotation_and_perspective(rotate_deg, jitter):
    """Seção 13: cartões fotografados em ângulos e distâncias diferentes
    continuam sendo lidos corretamente."""
    question_count = 30
    answers = {q: OPTIONS[(q * 3 + 1) % 5] for q in range(1, question_count + 1)}
    accuracy = _accuracy(question_count, answers, rotate_deg=rotate_deg, perspective_jitter=jitter)
    assert accuracy == 1.0


@pytest.mark.parametrize("brightness", [1.0, 0.7, 0.5, 0.35])
def test_tolerates_different_lighting_conditions(brightness):
    """Seção 12: resistente a iluminação diferente."""
    question_count = 30
    answers = {q: OPTIONS[(q * 3 + 1) % 5] for q in range(1, question_count + 1)}
    accuracy = _accuracy(question_count, answers, rotate_deg=6, perspective_jitter=25, brightness=brightness)
    assert accuracy == 1.0


def test_tolerates_camera_noise():
    question_count = 30
    answers = {q: OPTIONS[(q * 3 + 1) % 5] for q in range(1, question_count + 1)}
    accuracy = _accuracy(question_count, answers, rotate_deg=6, perspective_jitter=25, noise=True)
    assert accuracy == 1.0


def test_rejects_image_with_no_card():
    blank_photo = np.full((800, 600, 3), 90, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", blank_photo)
    result = analyze_image(buf.tobytes(), 30)
    assert result.ok is False
    # uma imagem completamente uniforme é rejeitada de qualquer forma —
    # seja por não haver cartão, seja por parecer borrada (sem nenhuma
    # aresta), mas NUNCA deve prosseguir para leitura de bolhas.
    assert result.questions == []


def test_rejects_photo_without_any_card_border():
    """Uma foto nítida e bem iluminada, mas sem nenhum cartão nela —
    deve ser rejeitada explicitamente por 'cartão não encontrado', não
    silenciosamente processada."""
    rng = np.random.default_rng(7)
    noisy_scene = rng.integers(60, 200, size=(900, 700, 3), dtype=np.uint8)
    cv2.rectangle(noisy_scene, (50, 50), (650, 850), (200, 180, 150), 4)  # objeto qualquer, não preto
    ok, buf = cv2.imencode(".jpg", noisy_scene)
    result = analyze_image(buf.tobytes(), 30)
    assert result.ok is False
    assert result.questions == []
    assert "cartão" in result.debug_message.lower() or "não encontrado" in result.debug_message.lower() or "borrada" in result.debug_message.lower()


def test_rejects_completely_dark_image():
    dark_photo = np.full((800, 600, 3), 5, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", dark_photo)
    result = analyze_image(buf.tobytes(), 30)
    assert result.ok is False
    assert "escura" in result.debug_message.lower()
