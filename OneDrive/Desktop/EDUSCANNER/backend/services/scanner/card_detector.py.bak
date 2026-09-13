"""
CardDetector

Detecta o quadrilatero correspondente ao cartao-resposta.

Estrategias:
1. Contornos/quadrilateros.
2. Fallback por linhas de Hough quando a borda do cartao nao fecha
   em um contorno unico.

O detector nao conhece questoes, bolhas ou banco de dados.
"""

from typing import Optional
import math

import cv2
import numpy as np


ABSOLUTE_DARK_LIMIT = 115


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Ordena 4 pontos como topo-esq, topo-dir, baixo-dir, baixo-esq."""
    pts = pts.reshape(4, 2).astype(np.float32)

    ordered = np.zeros((4, 2), dtype=np.float32)

    s = pts.sum(axis=1)
    ordered[0] = pts[np.argmin(s)]
    ordered[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1).reshape(-1)
    ordered[1] = pts[np.argmin(diff)]
    ordered[3] = pts[np.argmax(diff)]

    return ordered


def _angle_difference(a: float, b: float) -> float:
    """Diferenca angular considerando que linhas paralelas sao equivalentes."""
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


class CardDetector:
    """Localiza o cartao-resposta em uma imagem."""

    def __init__(
        self,
        min_area_ratio: float = 0.12,
        dark_limit: int = ABSOLUTE_DARK_LIMIT,
    ):
        self.min_area_ratio = min_area_ratio
        self.dark_limit = dark_limit

    def find_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        if image is None or image.size == 0:
            return None

        h, w = image.shape[:2]
        image_area = float(h * w)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # ---------------------------------------------------------
        # ESTRATEGIA 1: CONTORNOS
        # ---------------------------------------------------------
        candidates = self._collect_candidates(blurred, image_area)

        scored = []

        for area, approx in candidates:
            if not self._is_reasonable_quad(approx, w, h, area):
                continue

            darkness = self._perimeter_darkness(gray, approx)

            if darkness is not None and darkness < self.dark_limit:
                scored.append((darkness, area, approx))

        if scored:
            # Primeiro privilegia uma borda realmente escura.
            scored.sort(key=lambda item: (item[0], -item[1]))

            best = scored[0][2].astype(np.float32)
            best = self._refine_corners(gray, best)

            if self._is_reasonable_quad(
                best,
                w,
                h,
                cv2.contourArea(best),
            ):
                return _order_corners(best)

        # ---------------------------------------------------------
        # ESTRATEGIA 2: LINHAS DE HOUGH
        # ---------------------------------------------------------
        hough = self._find_by_hough(gray)

        if hough is not None:
            return hough

        return None

    # =============================================================
    # CONTORNOS
    # =============================================================

    def _collect_candidates(
        self,
        gray_blurred: np.ndarray,
        image_area: float,
    ):
        edges = cv2.Canny(gray_blurred, 40, 120)

        # Mantemos a dilatacao pequena para nao transformar
        # varias estruturas da folha em um unico contorno falso.
        edges = cv2.dilate(
            edges,
            np.ones((5, 5), np.uint8),
            iterations=1,
        )

        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates = []

        for cnt in contours:
            area = cv2.contourArea(cnt)

            if area < self.min_area_ratio * image_area:
                continue

            peri = cv2.arcLength(cnt, True)

            if peri <= 0:
                continue

            approx = cv2.approxPolyDP(
                cnt,
                0.02 * peri,
                True,
            )

            if len(approx) != 4:
                continue

            if not cv2.isContourConvex(approx):
                continue

            candidates.append((area, approx))

        return candidates

    def _is_reasonable_quad(
        self,
        approx: np.ndarray,
        width: int,
        height: int,
        area: float,
    ) -> bool:
        if approx is None:
            return False

        pts = approx.reshape(4, 2).astype(np.float32)

        if len(pts) != 4:
            return False

        image_area = float(width * height)

        if area < self.min_area_ratio * image_area:
            return False

        # Evita falsos positivos que sao praticamente
        # o limite da propria imagem.
        border_tolerance = max(
            5,
            int(round(0.015 * min(width, height))),
        )

        touching_border = 0

        for x, y in pts:
            if (
                x <= border_tolerance
                or x >= width - 1 - border_tolerance
                or y <= border_tolerance
                or y >= height - 1 - border_tolerance
            ):
                touching_border += 1

        # Um cartao pode encostar em 1 ou 2 bordas da foto.
        # 3+ normalmente indica que estamos detectando
        # uma regiao formada pelo proprio limite da imagem.
        if touching_border >= 3:
            return False

        # Todos os lados precisam ter comprimento razoavel.
        ordered = _order_corners(pts)

        sides = []

        for i in range(4):
            p1 = ordered[i]
            p2 = ordered[(i + 1) % 4]
            sides.append(float(np.linalg.norm(p2 - p1)))

        minimum_side = 0.05 * min(width, height)

        if min(sides) < minimum_side:
            return False

        return True

    def _perimeter_darkness(
        self,
        gray: np.ndarray,
        approx: np.ndarray,
    ):
        h, w = gray.shape[:2]

        mask = np.zeros(
            (h, w),
            dtype=np.uint8,
        )

        thickness = max(
            3,
            int(round(0.01 * max(h, w))),
        )

        cv2.polylines(
            mask,
            [approx.astype(np.int32)],
            True,
            255,
            thickness,
        )

        sampled = gray[mask > 0]

        if sampled.size < 20:
            return None

        return float(np.mean(sampled))

    def _refine_corners(
        self,
        gray: np.ndarray,
        pts: np.ndarray,
    ) -> np.ndarray:
        """Refina os cantos usando cornerSubPix."""
        pts = pts.reshape(-1, 1, 2).astype(np.float32)

        criteria = (
            cv2.TERM_CRITERIA_EPS
            + cv2.TERM_CRITERIA_MAX_ITER,
            40,
            0.001,
        )

        try:
            refined = cv2.cornerSubPix(
                gray,
                pts,
                (11, 11),
                (-1, -1),
                criteria,
            )

            return refined.reshape(-1, 2)

        except cv2.error:
            return pts.reshape(-1, 2)

    # =============================================================
    # HOUGH
    # =============================================================

    def _find_by_hough(
        self,
        gray: np.ndarray,
    ) -> Optional[np.ndarray]:
        """
        Procura duas linhas aproximadamente paralelas em uma direcao
        e duas em uma direcao perpendicular.

        Isso funciona especialmente bem quando a borda impressa
        do cartao nao forma um unico contorno fechado.
        """

        h, w = gray.shape[:2]
        minimum_dimension = min(h, w)

        blurred = cv2.GaussianBlur(
            gray,
            (5, 5),
            0,
        )

        edges = cv2.Canny(
            blurred,
            30,
            100,
        )

        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180.0,
            threshold=80,
            minLineLength=int(0.35 * minimum_dimension),
            maxLineGap=40,
        )

        if lines is None:
            return None

        segments = []
        histogram = np.zeros(36, dtype=np.float64)

        for line in lines[:, 0]:
            x1, y1, x2, y2 = map(float, line)

            length = math.hypot(
                x2 - x1,
                y2 - y1,
            )

            if length < 0.35 * minimum_dimension:
                continue

            angle = (
                math.degrees(
                    math.atan2(
                        y2 - y1,
                        x2 - x1,
                    )
                )
                % 180.0
            )

            bucket = int(angle // 5) % 36
            histogram[bucket] += length

            segments.append(
                (
                    length,
                    angle,
                    np.array(
                        [x1, y1, x2, y2],
                        dtype=np.float32,
                    ),
                )
            )

        if not segments:
            return None

        # Orientacao dominante da folha/cartao.
        dominant_angle = (
            float(np.argmax(histogram)) * 5.0
            + 2.5
        ) % 180.0

        pair_a = self._select_parallel_pair(
            segments,
            dominant_angle,
            minimum_dimension,
        )

        pair_b = self._select_parallel_pair(
            segments,
            (dominant_angle + 90.0) % 180.0,
            minimum_dimension,
        )

        if pair_a is None or pair_b is None:
            return None

        points = []

        for line_a in pair_a[1:]:
            for line_b in pair_b[1:]:
                point = self._line_intersection(
                    line_a,
                    line_b,
                )

                if point is None:
                    return None

                points.append(point)

        if len(points) != 4:
            return None

        points = np.asarray(
            points,
            dtype=np.float32,
        )

        if not np.all(np.isfinite(points)):
            return None

        points = _order_corners(points)

        area = float(
            abs(cv2.contourArea(points))
        )

        if area < 0.75 * self.min_area_ratio * h * w:
            return None

        # Permite uma pequena extrapolacao causada pela interseccao
        # das linhas, mas rejeita uma deteccao muito fora da foto.
        margin = max(
            8,
            int(0.03 * minimum_dimension),
        )

        if (
            np.any(points[:, 0] < -margin)
            or np.any(points[:, 0] > w - 1 + margin)
            or np.any(points[:, 1] < -margin)
            or np.any(points[:, 1] > h - 1 + margin)
        ):
            return None

        # Traz de volta para a imagem.
        points[:, 0] = np.clip(
            points[:, 0],
            0,
            w - 1,
        )

        points[:, 1] = np.clip(
            points[:, 1],
            0,
            h - 1,
        )

        return points.astype(np.float32)

    def _select_parallel_pair(
        self,
        segments,
        target_angle: float,
        minimum_dimension: int,
    ):
        """
        Escolhe duas linhas aproximadamente paralelas.

        O criterio privilegia:
        - grande separacao entre as linhas;
        - linhas longas;
        - orientacao semelhante.
        """

        family = []

        for segment in segments:
            length, angle, coords = segment

            if (
                _angle_difference(angle, target_angle)
                <= 10.0
            ):
                family.append(segment)

        if len(family) < 2:
            return None

        converted = []

        for length, angle, coords in family:
            x1, y1, x2, y2 = coords

            p1 = np.array(
                [x1, y1],
                dtype=np.float32,
            )

            p2 = np.array(
                [x2, y2],
                dtype=np.float32,
            )

            direction = p2 - p1
            norm = float(np.linalg.norm(direction))

            if norm <= 1e-6:
                continue

            direction /= norm

            normal = np.array(
                [-direction[1], direction[0]],
                dtype=np.float32,
            )

            offset = float(
                np.dot(normal, p1)
            )

            converted.append(
                (
                    normal,
                    offset,
                    float(length),
                )
            )

        best = None

        for i in range(len(converted)):
            for j in range(i + 1, len(converted)):
                n1, c1, length1 = converted[i]
                n2, c2, length2 = converted[j]

                parallel = abs(
                    float(np.dot(n1, n2))
                )

                if parallel < 0.97:
                    continue

                if float(np.dot(n1, n2)) < 0:
                    n2 = -n2
                    c2 = -c2

                separation = abs(c1 - c2)

                if separation < 0.25 * minimum_dimension:
                    continue

                score = (
                    separation
                    * min(length1, length2)
                )

                if best is None or score > best[0]:
                    best = (
                        score,
                        (
                            n1,
                            c1,
                            length1,
                        ),
                        (
                            n2,
                            c2,
                            length2,
                        ),
                    )

        return best

    @staticmethod
    def _line_intersection(
        line_a,
        line_b,
    ) -> Optional[np.ndarray]:
        n1, c1, _ = line_a
        n2, c2, _ = line_b

        matrix = np.vstack(
            [n1, n2]
        )

        determinant = float(
            np.linalg.det(matrix)
        )

        if abs(determinant) < 1e-6:
            return None

        point = np.linalg.solve(
            matrix,
            np.array(
                [c1, c2],
                dtype=np.float32,
            ),
        )

        return point.astype(np.float32)
