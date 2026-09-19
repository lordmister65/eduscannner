from __future__ import annotations

import cv2
import numpy as np

# Perfil calibrado para o cartão EDUSCANNER físico de 40 questões enviado pelo usuário.
# A normalização usa um retângulo interno estável do próprio formulário.
WARP_W = 1000
WARP_H = 1325

# Centros das alternativas após a normalização.
X_CENTERS = np.array([143, 219, 294, 370, 445, 642, 717, 792, 867, 942], dtype=np.float32)
Y_CENTERS = np.linspace(421, 1205, 20, dtype=np.float32)
LETTERS = "ABCDE"


class ScanError(Exception):
    pass


def _order_points(points: np.ndarray) -> np.ndarray:
    points = points.astype(np.float32)
    s = points.sum(axis=1)
    d = np.diff(points, axis=1).reshape(-1)
    return np.array(
        [
            points[np.argmin(s)],
            points[np.argmin(d)],
            points[np.argmax(s)],
            points[np.argmax(d)],
        ],
        dtype=np.float32,
    )


def _find_reference_rectangle(image: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Localiza o retângulo impresso usado como referência geométrica.

    Em vez de tentar adivinhar a folha inteira, usamos um retângulo interno do
    formulário, que se mostrou mais estável nas fotos reais.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        11,
    )
    binary = cv2.dilate(
        binary,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, float, np.ndarray, float, float]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if not (0.25 * h * w < area < 0.90 * h * w):
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4:
            continue

        ordered = _order_points(approx.reshape(4, 2))
        top = np.linalg.norm(ordered[1] - ordered[0])
        bottom = np.linalg.norm(ordered[2] - ordered[3])
        left = np.linalg.norm(ordered[3] - ordered[0])
        right = np.linalg.norm(ordered[2] - ordered[1])
        width = (top + bottom) / 2.0
        height = (left + right) / 2.0
        if height <= 1:
            continue

        ratio = width / height
        area_ratio = area / float(h * w)

        # O retângulo de referência fica perto de 0,755 após projeção frontal.
        if 0.72 < ratio < 0.90:
            candidates.append((abs(ratio - 0.755), -area, ordered, ratio, area_ratio))

    if not candidates:
        raise ScanError(
            "Não consegui localizar o cartão. Fotografe a folha inteira, sobre uma superfície plana e com boa luz."
        )

    candidates.sort(key=lambda item: (item[0], item[1]))
    _, _, ordered, ratio, area_ratio = candidates[0]

    # Preferimos rejeitar uma foto ruim a gerar leitura incorreta.
    if area_ratio < 0.43:
        raise ScanError("O cartão está muito longe. Aproxime a câmera e tente novamente.")
    if not (0.72 < ratio < 0.775):
        raise ScanError("A foto está muito inclinada. Tire a foto mais de cima, deixando a folha mais reta.")

    return ordered, ratio, area_ratio


def _warp(image: np.ndarray) -> tuple[np.ndarray, dict]:
    points, ratio, area_ratio = _find_reference_rectangle(image)
    target = np.array(
        [[0, 0], [WARP_W - 1, 0], [WARP_W - 1, WARP_H - 1], [0, WARP_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(points, target)
    warped = cv2.warpPerspective(image, matrix, (WARP_W, WARP_H))
    return warped, {"ratio": float(ratio), "area_ratio": float(area_ratio)}


def _bubble_score(gray: np.ndarray, hsv: np.ndarray, x: float, y: float, radius: int = 9) -> float:
    """Compara o centro da bolha com o fundo local.

    Isso aceita marcações pretas, azuis e vermelhas e reduz o efeito de sombras.
    """
    h, w = gray.shape
    yy, xx = np.ogrid[:h, :w]
    distance2 = (xx - x) ** 2 + (yy - y) ** 2
    inside = distance2 <= radius * radius
    background = (distance2 <= (2.4 * radius) ** 2) & (distance2 >= (1.6 * radius) ** 2)

    center_gray = float(np.mean(gray[inside]))
    local_gray = float(np.median(gray[background]))
    center_saturation = float(np.mean(hsv[:, :, 1][inside]))

    contrast = max(0.0, (local_gray - center_gray) / 255.0)
    color_bonus = 0.30 * (center_saturation / 255.0)
    return contrast + color_bonus


def scan_card(image_bytes: bytes) -> dict:
    raw = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ScanError("Imagem inválida.")

    # Evita imagens minúsculas/compressão excessiva.
    if min(image.shape[:2]) < 700:
        raise ScanError("A foto está com resolução muito baixa. Tire outra foto mais próxima.")

    warped, geometry = _warp(image)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)

    scores = []
    for q_index in range(40):
        side = 0 if q_index < 20 else 1
        row = q_index % 20
        row_scores = [
            _bubble_score(gray, hsv, float(X_CENTERS[side * 5 + option]), float(Y_CENTERS[row]))
            for option in range(5)
        ]
        scores.append(row_scores)

    scores_np = np.asarray(scores, dtype=np.float32)
    flattened = scores_np.reshape(-1)
    baseline = float(np.median(flattened))
    mad = float(np.median(np.abs(flattened - baseline)))
    threshold = min(0.20, max(0.08, baseline + 5.0 * mad))

    questions = []
    for number, row_scores in enumerate(scores_np, start=1):
        order = np.argsort(row_scores)[::-1]
        best_idx = int(order[0])
        second_idx = int(order[1])
        best = float(row_scores[best_idx])
        second = float(row_scores[second_idx])

        # Duas marcações: anula a questão.
        # A segunda marca pode ser um pouco mais fraca, por isso há uma regra relativa.
        multiple = best > threshold and second > max(0.11, 0.55 * best)

        if multiple:
            status = "MULT"
            answer = None
        elif best > threshold:
            status = "OK"
            answer = LETTERS[best_idx]
        else:
            status = "BLANK"
            answer = None

        questions.append(
            {
                "number": number,
                "status": status,
                "answer": answer,
                "scores": [round(float(v), 3) for v in row_scores],
            }
        )

    return {
        "questions": questions,
        "threshold": round(threshold, 3),
        "geometry": geometry,
    }
