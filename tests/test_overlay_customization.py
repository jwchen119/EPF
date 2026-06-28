"""Tests for Phase 6: Text Customization (TC-01..TC-09).

These tests target interfaces that Plans 06-02 and 06-03 will create.
They MUST fail (RED) until those plans land — that is the TDD contract.

TC-01: OVERLAY_COLORS dict shape and exact RGBA values
TC-03: background mode uses bg_color for filled rect
TC-04: outline mode does NOT paint a solid filled rect
TC-05: outline mode uses border_color for stroke
TC-06: default params preserve current visual (black rect + white text)
TC-07: stroke_width=0 produces no border_color pixels distinct from text
"""

# --- Rendering contract (TC-01, TC-03..TC-07) ---


def test_overlay_colors_dict():
    """TC-01/CLR-01: OVERLAY_COLORS has exactly 9 keys with exact RGBA tuples."""
    from app import OVERLAY_COLORS

    assert set(OVERLAY_COLORS.keys()) == {
        'black', 'white', 'dark_gray', 'gray', 'light_gray',
        'yellow', 'red', 'blue', 'green',
    }
    assert OVERLAY_COLORS['black'] == (0, 0, 0, 255)
    assert OVERLAY_COLORS['white'] == (255, 255, 255, 255)
    assert OVERLAY_COLORS['dark_gray'] == (64, 64, 64, 255)
    assert OVERLAY_COLORS['gray'] == (128, 128, 128, 255)
    assert OVERLAY_COLORS['light_gray'] == (192, 192, 192, 255)
    assert OVERLAY_COLORS['yellow'] == (255, 216, 0, 255)
    assert OVERLAY_COLORS['red'] == (229, 57, 53, 255)
    assert OVERLAY_COLORS['blue'] == (0, 76, 255, 255)
    assert OVERLAY_COLORS['green'] == (29, 185, 84, 255)


def test_background_mode_uses_bg_color(blank_rgb_image, dejavu_or_default_font):
    """TC-03: style='background' paints at least one pixel equal to bg_color in the image."""
    from app import draw_date_overlay

    img = blank_rgb_image
    draw_date_overlay(
        img,
        '05.01.2022',
        dejavu_or_default_font,
        'bottomRight',
        padding=6,
        style='background',
        bg_color=(229, 57, 53, 255),
        text_color=(255, 255, 255, 255),
    )
    pixels = list(img.getdata())
    assert (229, 57, 53) in pixels  # filled rect uses bg_color


def test_outline_mode_no_rect(blank_rgb_image, dejavu_or_default_font):
    """TC-04: style='outline' paints far fewer fill-color pixels than style='background'."""
    from app import draw_date_overlay

    bg_img = blank_rgb_image.copy()
    draw_date_overlay(
        bg_img,
        '05.01.2022',
        dejavu_or_default_font,
        'bottomRight',
        padding=6,
        style='background',
        bg_color=(0, 0, 0, 255),
        text_color=(255, 255, 255, 255),
    )
    bg_black = list(bg_img.getdata()).count((0, 0, 0))

    outline_img = blank_rgb_image.copy()
    draw_date_overlay(
        outline_img,
        '05.01.2022',
        dejavu_or_default_font,
        'bottomRight',
        padding=6,
        style='outline',
        text_color=(0, 0, 0, 255),
        border_color=(0, 0, 0, 255),
        stroke_width=2,
    )
    outline_black = list(outline_img.getdata()).count((0, 0, 0))

    # Outline mode paints only stroke+glyph pixels, NOT a solid filled rect -> far fewer black pixels
    assert outline_black < bg_black


def test_outline_mode_border_color(blank_rgb_image, dejavu_or_default_font):
    """TC-05: style='outline' uses border_color for stroke, producing that color in the image."""
    from app import draw_date_overlay

    img = blank_rgb_image
    draw_date_overlay(
        img,
        '05.01.2022',
        dejavu_or_default_font,
        'bottomRight',
        padding=6,
        style='outline',
        text_color=(255, 255, 255, 255),
        border_color=(229, 57, 53, 255),
        stroke_width=2,
    )
    assert (229, 57, 53) in list(img.getdata())  # stroke uses border_color


def test_default_params_match_current(blank_rgb_image, dejavu_or_default_font):
    """TC-06: calling draw_date_overlay with no new kwargs preserves legacy behavior."""
    from app import draw_date_overlay

    img = blank_rgb_image
    draw_date_overlay(img, '05.01.2022', dejavu_or_default_font, 'bottomRight', padding=6)
    pixels = list(img.getdata())
    assert (0, 0, 0) in pixels  # default bg rect is black
    assert (255, 255, 255) in pixels  # default text is white


def test_stroke_width_zero(blank_rgb_image, dejavu_or_default_font):
    """TC-07: stroke_width=0 in outline mode produces no border_color pixels when it differs from text_color."""
    from app import draw_date_overlay

    img = blank_rgb_image
    draw_date_overlay(
        img,
        '05.01.2022',
        dejavu_or_default_font,
        'bottomRight',
        padding=6,
        style='outline',
        text_color=(255, 255, 255, 255),
        border_color=(229, 57, 53, 255),
        stroke_width=0,
    )
    # With stroke_width=0 there is no stroke, so the distinct border_color must NOT appear
    assert (229, 57, 53) not in list(img.getdata())


# --- Config contract (TC-02, TC-08, TC-09) ---


def test_default_config_new_keys():
    """TC-02: DEFAULT_CONFIG['immich'] contains all 6 new overlay keys with correct defaults."""
    from app import DEFAULT_CONFIG

    imm = DEFAULT_CONFIG['immich']
    assert imm['overlay_style'] == 'background'
    assert imm['overlay_bg_color'] == 'black'
    assert imm['overlay_text_color'] == 'white'
    assert imm['overlay_border_color'] == 'white'
    assert imm['overlay_stroke_width'] == 2
    assert imm['overlay_font_size'] == 26


def test_update_config_new_keys():
    """TC-08: update_app_config reads new overlay globals; missing keys fall back to defaults."""
    import app

    new_config = {'immich': dict(app.DEFAULT_CONFIG['immich'])}
    new_config['immich']['overlay_style'] = 'outline'
    new_config['immich']['overlay_bg_color'] = 'red'
    new_config['immich']['overlay_text_color'] = 'yellow'
    new_config['immich']['overlay_border_color'] = 'blue'
    new_config['immich']['overlay_stroke_width'] = 4
    new_config['immich']['overlay_font_size'] = 40
    app.update_app_config(new_config)
    assert app.overlay_style == 'outline'
    assert app.overlay_bg_color == 'red'
    assert app.overlay_text_color == 'yellow'
    assert app.overlay_border_color == 'blue'
    assert app.overlay_stroke_width == 4
    assert app.overlay_font_size == 40

    # backward-compat: a config missing the new keys must NOT raise (.get fallback)
    legacy = {'immich': {k: v for k, v in app.DEFAULT_CONFIG['immich'].items() if not k.startswith('overlay_')}}
    app.update_app_config(legacy)
    assert app.overlay_style == 'background'  # fell back to default
    assert app.overlay_font_size == 26


def test_post_handler_font_size_int():
    """TC-09: overlay_font_size and overlay_stroke_width globals are stored as ints."""
    import app

    new_config = {'immich': dict(app.DEFAULT_CONFIG['immich'])}
    new_config['immich']['overlay_font_size'] = 32
    new_config['immich']['overlay_stroke_width'] = 3
    app.update_app_config(new_config)
    assert isinstance(app.overlay_font_size, int)
    assert isinstance(app.overlay_stroke_width, int)
