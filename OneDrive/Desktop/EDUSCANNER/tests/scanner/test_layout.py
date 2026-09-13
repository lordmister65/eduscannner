from backend.services.scanner.layout import build_layout, grid_dimensions, OPTIONS


def test_grid_dimensions_for_valid_blocks():
    assert grid_dimensions(20) == (2, 10)
    assert grid_dimensions(30) == (2, 15)
    assert grid_dimensions(45) == (3, 15)


def test_layout_has_one_entry_per_question():
    for question_count in (20, 30, 45):
        layout = build_layout(question_count)
        assert set(layout.bubble_positions_mm.keys()) == set(range(1, question_count + 1))
        assert set(layout.label_positions_mm.keys()) == set(range(1, question_count + 1))


def test_each_question_has_all_five_options():
    layout = build_layout(30)
    for opts in layout.bubble_positions_mm.values():
        assert set(opts.keys()) == set(OPTIONS)


def test_bubble_positions_stay_inside_content_box():
    from backend.services.scanner.layout import CONTENT_W_MM, CONTENT_H_MM

    layout = build_layout(45)
    for opts in layout.bubble_positions_mm.values():
        for x, y in opts.values():
            assert 0 <= x <= CONTENT_W_MM
            assert 0 <= y <= CONTENT_H_MM


def test_pixel_conversion_preserves_aspect_ratio():
    from backend.services.scanner.layout import CONTENT_W_MM, CONTENT_H_MM

    layout = build_layout(30)
    _, radius_px, canon_h = layout.bubble_positions_px(canon_w=950)
    assert radius_px > 0
    assert abs(canon_h / 950 - CONTENT_H_MM / CONTENT_W_MM) < 0.01


def test_layout_is_deterministic():
    """A mesma geometria precisa ser reproduzida sempre — é a âncora
    compartilhada entre o PDF impresso e a leitura do scanner."""
    a = build_layout(30)
    b = build_layout(30)
    assert a.bubble_positions_mm == b.bubble_positions_mm
