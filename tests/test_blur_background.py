# -*- coding: utf-8 -*-
"""
Contract tests for blurred background in fit mode (BG-01 through BG-06).
Phase 9: Blurred background behind image when using fit-width or fit-height modes.

All tests in this file that check blur behavior (BG-02, BG-04, BG-05, BG-06)
are expected to FAIL (RED) until cpy_fallback.load_scaled() is updated in Plan 02.
"""

from PIL import Image

from cpy_fallback import load_scaled

EPD_W = 1200
EPD_H = 1600

# --- Helpers ---


def make_colored_image(width, height, color=(200, 100, 50)):
    """Return a solid-color RGB PIL Image."""
    img = Image.new('RGB', (width, height), color)
    return img


# --- BG-01: fit mode always returns exact display dimensions ---


def test_fit_output_dimensions_portrait():
    """BG-01a: fit mode with portrait image returns (1200, 1600)."""
    img = make_colored_image(300, 400)
    result = load_scaled(img, 0, display_mode='fit')
    assert result.size == (EPD_W, EPD_H), f'Expected (1200, 1600) but got {result.size}'


def test_fit_output_dimensions_landscape():
    """BG-01b: fit mode with landscape image returns (1200, 1600)."""
    img = make_colored_image(600, 300)
    result = load_scaled(img, 0, display_mode='fit')
    assert result.size == (EPD_W, EPD_H), f'Expected (1200, 1600) but got {result.size}'


# --- BG-02: fit mode background pixels differ from white (blur applied) ---


def test_fit_background_not_white():
    """BG-02: fit mode with colored image — letterbox bar is NOT white after blur."""
    # 600x1000 → orig_ratio=0.6 < epd_ratio=0.75 → fit-width → letterbox bars top/bottom
    img = make_colored_image(600, 1000, color=(200, 100, 50))
    result = load_scaled(img, 0, display_mode='fit')
    assert result.size == (EPD_W, EPD_H)

    # The sharp image in fit-width occupies new_height = EPD_H (1600), new_width = int(1600*0.6) = 960
    # Offset: x = (1200-960)//2 = 120, y = 0 — so top/bottom bars don't exist here
    # For fit-width: bars are left (x<120) and right (x>1079)
    # Actually check: letterbox happens when orig_ratio < epd_ratio → bars left/right
    # Check left bar column 0, any row — should not be pure white
    top_left_pixel = result.getpixel((0, 0))
    assert top_left_pixel != (255, 255, 255), (
        f'Expected blurred (non-white) pixel at (0,0) but got {top_left_pixel}. ' 'Blur not implemented yet.'
    )


# --- BG-03: fill mode is completely unaffected ---


def test_fill_mode_unchanged():
    """BG-03: fill mode with landscape image still returns (1200, 1600)."""
    img = make_colored_image(600, 300, color=(200, 100, 50))
    result = load_scaled(img, 0, display_mode='fill')
    assert result.size == (EPD_W, EPD_H), f'fill mode broke: expected (1200, 1600) but got {result.size}'


# --- BG-04: fit-width sub-case (portrait image, bars left/right) ---


def test_fit_width_subcase():
    """BG-04: fit mode with portrait image (fit-width) — pillarbox bars are not white."""
    # 600x1000 → orig_ratio=0.6 < epd_ratio=0.75 → fit-width → bars left and right
    img = make_colored_image(600, 1000, color=(200, 100, 50))
    result = load_scaled(img, 0, display_mode='fit')
    # Left pillarbox bar: column 0, row 800 (middle)
    left_bar_pixel = result.getpixel((0, 800))
    assert left_bar_pixel != (255, 255, 255), (
        f'Expected blurred (non-white) pixel at (0, 800) but got {left_bar_pixel}. ' 'Blur not implemented yet.'
    )


# --- BG-05: fit-height sub-case (landscape image, bars top/bottom) ---


def test_fit_height_subcase():
    """BG-05: fit mode with landscape image (fit-height) — letterbox bars are not white."""
    # 1000x600 → orig_ratio=1.667 > epd_ratio=0.75 → fit-height → bars top and bottom
    img = make_colored_image(1000, 600, color=(200, 100, 50))
    result = load_scaled(img, 0, display_mode='fit')
    # Top letterbox bar: row 0, column 600 (middle)
    top_bar_pixel = result.getpixel((600, 0))
    assert top_bar_pixel != (255, 255, 255), (
        f'Expected blurred (non-white) pixel at (600, 0) but got {top_bar_pixel}. ' 'Blur not implemented yet.'
    )


# --- BG-06: blur_radius kwarg accepted and produces visually different results ---


def make_gradient_image(width, height):
    """Return a gradient RGB PIL Image — needed for blur radius comparison (uniform images
    produce identical blur output regardless of radius; a gradient has texture to reveal)."""
    img = Image.new('RGB', (width, height))
    img.putdata([(x % 256, y % 256, (x + y) % 256) for y in range(height) for x in range(width)])
    return img


def test_blur_radius_config():
    """BG-06: load_scaled accepts blur_radius kwarg; different radii produce different results."""
    # Use a gradient image — a uniform solid color produces identical blur output for any radius.
    # A gradient has texture that is smoothed differently at radius=5 vs radius=60.
    img = make_gradient_image(1000, 600)
    result_low = load_scaled(img, 0, display_mode='fit', blur_radius=5)
    result_high = load_scaled(img, 0, display_mode='fit', blur_radius=60)
    # The top letterbox bar (row 0-439) should differ between radii due to different blur spread
    pixel_low = result_low.getpixel((0, 300))
    pixel_high = result_high.getpixel((0, 300))
    # With different blur radii the blurred background will differ (lower radius = more texture)
    assert pixel_low != pixel_high, (
        f'Expected different pixels for blur_radius=5 vs blur_radius=60, ' f'but both returned {pixel_low}.'
    )
