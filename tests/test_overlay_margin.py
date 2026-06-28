"""Tests for Phase 11: Overlay Margin (MARGIN-01, MARGIN-02).

These tests target the extended POSITIONS lambdas and draw_date_overlay() signature.
They MUST fail (RED) until Plan 11-01 lands — that is the TDD contract.

MARGIN-01: POSITIONS lambdas accept (w, h, tw, th, p, mh, mv) and compute
           margin-aware x/y for all 9 positions.
MARGIN-02: draw_date_overlay() has margin_h=0 and margin_v=0 defaults, and
           zero-margin output matches omitted-margin output byte-for-byte.
"""

import inspect

from PIL import Image

from app import POSITIONS, draw_date_overlay

# Fixed test dimensions per MARGIN-01 spec
W, H, TW, TH, P, MH, MV = 1200, 1600, 100, 40, 6, 80, 50


def test_positions_edge_corners_apply_both_margins():
    """MARGIN-01: Corner positions incorporate both mh and mv into x/y."""
    assert POSITIONS['topLeft'](W, H, TW, TH, P, MH, MV) == (P + MH, P + MV)  # (86, 56)
    assert POSITIONS['topLeft'](W, H, TW, TH, P, MH, MV) == (86, 56)

    assert POSITIONS['topRight'](W, H, TW, TH, P, MH, MV) == (W - TW - P - MH, P + MV)  # (1014, 56)
    assert POSITIONS['topRight'](W, H, TW, TH, P, MH, MV) == (1014, 56)

    assert POSITIONS['bottomLeft'](W, H, TW, TH, P, MH, MV) == (P + MH, H - TH - P - MV)  # (86, 1504)
    assert POSITIONS['bottomLeft'](W, H, TW, TH, P, MH, MV) == (86, 1504)

    assert POSITIONS['bottomRight'](W, H, TW, TH, P, MH, MV) == (W - TW - P - MH, H - TH - P - MV)  # (1014, 1504)
    assert POSITIONS['bottomRight'](W, H, TW, TH, P, MH, MV) == (1014, 1504)


def test_positions_axis_center_apply_single_axis():
    """MARGIN-01: Axis-center positions use only the relevant margin axis."""
    # topCenter and bottomCenter: apply mv only, ignore mh; x is geometric center
    assert POSITIONS['topCenter'](W, H, TW, TH, P, MH, MV) == ((W - TW) // 2, P + MV)  # (550, 56)
    assert POSITIONS['topCenter'](W, H, TW, TH, P, MH, MV) == (550, 56)

    assert POSITIONS['bottomCenter'](W, H, TW, TH, P, MH, MV) == ((W - TW) // 2, H - TH - P - MV)  # (550, 1504)
    assert POSITIONS['bottomCenter'](W, H, TW, TH, P, MH, MV) == (550, 1504)

    # centerLeft and centerRight: apply mh only, ignore mv; y is geometric center
    assert POSITIONS['centerLeft'](W, H, TW, TH, P, MH, MV) == (P + MH, (H - TH) // 2)  # (86, 780)
    assert POSITIONS['centerLeft'](W, H, TW, TH, P, MH, MV) == (86, 780)

    assert POSITIONS['centerRight'](W, H, TW, TH, P, MH, MV) == (W - TW - P - MH, (H - TH) // 2)  # (1014, 780)
    assert POSITIONS['centerRight'](W, H, TW, TH, P, MH, MV) == (1014, 780)


def test_positions_center_ignores_margins():
    """MARGIN-01: center position ignores both mh and mv — geometric center unchanged."""
    assert POSITIONS['center'](W, H, TW, TH, P, MH, MV) == ((W - TW) // 2, (H - TH) // 2)  # (550, 780)
    assert POSITIONS['center'](W, H, TW, TH, P, MH, MV) == (550, 780)


def test_draw_overlay_signature_defaults():
    """MARGIN-02: draw_date_overlay() has margin_h=0 and margin_v=0 in its signature."""
    params = inspect.signature(draw_date_overlay).parameters
    assert 'margin_h' in params, "draw_date_overlay missing margin_h parameter"
    assert 'margin_v' in params, "draw_date_overlay missing margin_v parameter"
    assert params['margin_h'].default == 0, f"margin_h default should be 0, got {params['margin_h'].default}"
    assert params['margin_v'].default == 0, f"margin_v default should be 0, got {params['margin_v'].default}"


def test_draw_overlay_zero_margin_matches_omitted(dejavu_or_default_font):
    """MARGIN-02: Passing margin_h=0, margin_v=0 produces byte-identical output to omitting them."""
    img_a = Image.new('RGB', (1200, 1600), (255, 255, 255))
    img_b = Image.new('RGB', (1200, 1600), (255, 255, 255))

    draw_date_overlay(img_a, '05.01.2022', dejavu_or_default_font, 'bottomRight', padding=6)
    draw_date_overlay(img_b, '05.01.2022', dejavu_or_default_font, 'bottomRight', padding=6, margin_h=0, margin_v=0)

    assert list(img_a.getdata()) == list(img_b.getdata()), (
        "Zero-margin output does not match omitted-margin output — backward compat broken"
    )
