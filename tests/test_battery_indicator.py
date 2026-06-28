"""Phase 13 — Battery Indicator Icon: contract tests for draw_battery_indicator().

These tests MUST fail (RED) until Task 2 lands draw_battery_indicator() and the
two threshold constants (BATTERY_LOW_THRESHOLD, BATTERY_FLAT_THRESHOLD) in app.py.

Contract:
  - battery_pct > 20 -> no-op (byte-identical image)
  - 5 < battery_pct <= 20 -> partial-fill battery icon drawn
  - battery_pct <= 5 -> empty battery outline drawn (no fill bar)
  - flat state has fewer non-white pixels than low state (fill bar absent)
  - position_str is honored (different positions -> different images)
"""
import inspect

from PIL import Image

from app import BATTERY_FLAT_THRESHOLD, BATTERY_LOW_THRESHOLD, draw_battery_indicator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_POSITION = 'topRight'
_DEFAULT_COLOR = (255, 255, 255, 255)
_DEFAULT_FONT_SIZE = 26
_DEFAULT_ROTATION = 0


def _fresh_white():
    """Return a pristine 1200x1600 white RGB image."""
    return Image.new('RGB', (1200, 1600), (255, 255, 255))


def _nonwhite(img):
    """Count pixels that are not pure white (255, 255, 255)."""
    return sum(1 for px in img.getdata() if px != (255, 255, 255))


def _draw(img, pct, position_str=_DEFAULT_POSITION):
    draw_battery_indicator(
        img,
        battery_pct=pct,
        position_str=position_str,
        rotation=_DEFAULT_ROTATION,
        font_size=_DEFAULT_FONT_SIZE,
        color=_DEFAULT_COLOR,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_thresholds_are_constants():
    """BATIND-02: threshold constants exist with correct values."""
    assert BATTERY_LOW_THRESHOLD == 20
    assert BATTERY_FLAT_THRESHOLD == 5


def test_signature():
    """D-18: function parameter names must match the contract exactly."""
    params = list(inspect.signature(draw_battery_indicator).parameters)
    assert params == ['output_img', 'battery_pct', 'position_str', 'rotation', 'font_size', 'color']


def test_above_threshold_is_noop():
    """BATIND-03 / D-19: battery_pct > 20 leaves the image byte-identical."""
    img_a = Image.new('RGB', (1200, 1600), (255, 255, 255))
    img_b = Image.new('RGB', (1200, 1600), (255, 255, 255))
    _draw(img_b, pct=50)
    assert img_a.tobytes() == img_b.tobytes(), (
        "Image should be unchanged when battery_pct > BATTERY_LOW_THRESHOLD"
    )


def test_at_threshold_boundary_low_draws():
    """battery_pct == 20 is inclusive low boundary -> icon must appear (non-white pixels)."""
    img = _fresh_white()
    _draw(img, pct=20)
    assert _nonwhite(img) > 0, "battery_pct=20 (inclusive boundary) must draw the icon"


def test_low_state_draws_partial_fill():
    """BATIND-01: battery_pct=10 produces non-white pixels (icon + fill bar present)."""
    img = _fresh_white()
    _draw(img, pct=10)
    assert _nonwhite(img) > 0, "battery_pct=10 must draw a partial-fill icon"


def test_flat_state_draws_empty_outline():
    """BATIND-01: battery_pct=3 produces non-white pixels (outline present, even without fill)."""
    img = _fresh_white()
    _draw(img, pct=3)
    assert _nonwhite(img) > 0, "battery_pct=3 must draw an empty battery outline"


def test_flat_has_fewer_nonwhite_than_low():
    """D-02: flat state (no fill bar) has strictly fewer non-white pixels than low state."""
    img_low = _fresh_white()
    img_flat = _fresh_white()
    _draw(img_low, pct=10)   # low: outline + partial fill
    _draw(img_flat, pct=3)   # flat: outline only (no fill)
    count_low = _nonwhite(img_low)
    count_flat = _nonwhite(img_flat)
    assert count_flat < count_low, (
        f"Flat state ({count_flat} non-white px) must be < low state ({count_low} non-white px)"
    )


def test_position_differs():
    """D-08/D-11: different position_str values must produce visually different images."""
    img_tl = _fresh_white()
    img_br = _fresh_white()
    _draw(img_tl, pct=10, position_str='topLeft')
    _draw(img_br, pct=10, position_str='bottomRight')
    assert img_tl.tobytes() != img_br.tobytes(), (
        "topLeft and bottomRight positions must produce different images"
    )


def test_at_flat_threshold_boundary_draws():
    """battery_pct == 5 is the flat boundary -> empty outline drawn (non-white pixels present)."""
    img = _fresh_white()
    _draw(img, pct=5)
    assert _nonwhite(img) > 0, "battery_pct=5 (flat boundary) must draw the empty outline"


def test_zero_pct_draws_empty_outline():
    """battery_pct=0 is still within the draw range -> outline rendered."""
    img = _fresh_white()
    # Note: D-07 says last_battery_voltage == 0 suppresses drawing in the pipeline,
    # but draw_battery_indicator() itself is called with an explicit pct value.
    # The function draws for pct=0 (<= FLAT_THRESHOLD) unless guarded by caller.
    # The plan specifies the guard is battery_pct > BATTERY_LOW_THRESHOLD -> return.
    # pct=0 is <= 5, so outline is drawn.
    _draw(img, pct=0)
    assert _nonwhite(img) > 0, "battery_pct=0 (within draw range) must draw the empty outline"
