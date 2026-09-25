import cv2
import numpy as np

from app.scanner import X_REL, Y_REL, scan_card


BLOCKS = [(28, 424, 250, 996), (258, 424, 476, 996), (484, 424, 712, 992)]


def make_card():
    img = np.full((1024, 768, 3), 245, np.uint8)
    # Simplified representation of the new CEPI-JBR card.
    cv2.rectangle(img, (20, 18), (742, 1005), (35, 35, 35), 3)
    for x1, y1, x2, y2 in BLOCKS:
        cv2.rectangle(img, (x1, y1), (x2, y2), (50, 50, 50), 2)
        for yr in Y_REL:
            y = int(y1 + float(yr) * (y2 - y1 - 1))
            for xr in X_REL:
                x = int(x1 + float(xr) * (x2 - x1 - 1))
                cv2.circle(img, (x, y), 10, (80, 80, 80), 2)

    # Deterministic marks: Q1=C, Q16=A, Q31=E; Q19 has two marks.
    marks = [
        (0, 0, 2, (20, 20, 20)),
        (1, 0, 0, (20, 20, 20)),
        (2, 0, 4, (20, 20, 20)),
        (1, 3, 1, (20, 20, 20)),
        (1, 3, 2, (20, 20, 20)),
    ]
    for bi, row, col, color in marks:
        x1, y1, x2, y2 = BLOCKS[bi]
        x = int(x1 + float(X_REL[col]) * (x2 - x1 - 1))
        y = int(y1 + float(Y_REL[row]) * (y2 - y1 - 1))
        cv2.circle(img, (x, y), 9, color, -1)
    return img


def test_new_template_reads_expected_marks():
    img = make_card()
    ok, enc = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    result = scan_card(enc.tobytes())
    qs = {q['number']: q for q in result['questions']}
    assert len(result['questions']) == 45
    assert qs[1]['answer'] == 'C'
    assert qs[16]['answer'] == 'A'
    assert qs[31]['answer'] == 'E'
    assert qs[19]['status'] == 'MULT'


def test_new_template_accepts_red_marks():
    img = make_card()
    x1, y1, x2, y2 = BLOCKS[2]
    x = int(x1 + float(X_REL[1]) * (x2 - x1 - 1))
    y = int(y1 + float(Y_REL[4]) * (y2 - y1 - 1))
    cv2.circle(img, (x, y), 9, (20, 20, 180), -1)  # B in red ink
    ok, enc = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    result = scan_card(enc.tobytes())
    qs = {q['number']: q for q in result['questions']}
    assert qs[35]['answer'] == 'B'
