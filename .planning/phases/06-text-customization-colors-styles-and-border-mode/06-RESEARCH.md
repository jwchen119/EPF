# Phase 06: Text Customization — Colors, Styles, and Border Mode - Research

**Researched:** 2026-05-29
**Domain:** Pillow image rendering, Flask/Jinja2 form handling, Python config management
**Confidence:** HIGH

## Summary

Phase 6 extends the existing `draw_date_overlay()` function to accept configurable colors,
overlay style (background vs. outline), stroke color, stroke width, and font size. All new
parameters follow the Phase 2 config-pattern exactly: added to `DEFAULT_CONFIG['immich']`,
read via `.get()` fallback in `update_app_config()`, and wired into the settings.html form
and POST handler.

The Pillow 11.0.0 `ImageDraw.text()` stroke API (`stroke_width`, `stroke_fill`) is
confirmed available and working. The `textbbox()` call must pass `stroke_width` in outline
mode so that the measured bounding box correctly accounts for the expanded glyph footprint
(otherwise padding arithmetic is off by `stroke_width` pixels on each side).

Outline mode removes the `draw.rectangle()` call entirely and replaces the filled-rect
background with a `stroke_fill` outline on the text glyphs. Background mode keeps the
existing behavior intact. The 6-palette color name-to-RGBA mapping is a small dict
derived from the `palette` list already in `app.py:196-201`.

**Primary recommendation:** Add all 6 new config keys under the existing `immich` section
(not a new `overlay` subsection) to stay consistent with Phase 2. Extend `draw_date_overlay()`
with 5 new keyword arguments, each with a default that preserves the current visual exactly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Colors are selected from a 6-color dropdown `<select>` matching the T133A01
  e-paper palette: Black, White, Yellow, Red, Blue, Green. No free hex input.
- **D-02:** All 6 palette colors available for both bg color and text color. No
  text ≠ background validation — invisible overlay is the user's choice.
- **D-03:** Palette RGB values from `app.py:196-201`:
  - Black: `(0, 0, 0)` / White: `(255, 255, 255)` / Yellow: `(255, 216, 0)`
  - Red: `(229, 57, 53)` / Blue: `(0, 76, 255)` / Green: `(29, 185, 84)`
- **D-04:** Overlay style is a `<select>` with `"background"` and `"outline"` options.
- **D-05:** `<select>` (not checkbox) follows Phase 2 pattern (avoids unchecked-field
  omission in HTML POST).
- **D-06:** In `"background"` style: `overlay_bg_color` + `overlay_text_color` active.
- **D-07:** In `"outline"` style: `overlay_text_color` + `overlay_border_color` active.
  `overlay_bg_color` ignored (no rectangle drawn).
- **D-08:** `overlay_border_color` is a separate config key (not reused from text color).
- **D-09:** `overlay_stroke_width` is a slider from 1–5 px.
- **D-10:** Stroke thickness applies only in outline mode.
- **D-11:** Default stroke width: 2 px.
- **D-12:** `overlay_font_size` is a slider from 16–48 px.
- **D-13:** Default font size: 26 px (preserves current hardcoded value at `app.py:371`).
- **D-14:** New config key defaults preserve exact current visual behavior (zero visual
  change on upgrade):
  - `overlay_style`: `"background"`
  - `overlay_bg_color`: `"black"`
  - `overlay_text_color`: `"white"`
  - `overlay_border_color`: `"white"`
  - `overlay_stroke_width`: `2`
  - `overlay_font_size`: `26`
- **D-15:** All new keys use `.get()` fallback in `update_app_config()`.

### Claude's Discretion

- PIL text stroke implementation: use `draw.text(..., stroke_width=N, stroke_fill=(R,G,B,255))`.
- Where the 6-color name-to-RGBA mapping lives: a small dict in `app.py` near the existing
  `palette` list at line 196, or inline in `draw_date_overlay()`.
- Whether to add new config keys under `immich` or a new `overlay` subsection — consistency
  with Phase 2 pattern favors `immich`.
- UI organization: new controls appended to the existing "Date Overlay" card in settings.html
  rather than a new card.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 11.0.0 (pinned in requirements.txt) | Image drawing, text stroke | Already in project; `stroke_width`/`stroke_fill` confirmed available |
| Flask/Jinja2 | 3.1.0 | Web UI + form POST | Already in project |
| PyYAML | 6.0.2 | Config persistence | Already in project |

No new dependencies required. All changes are within the existing stack.

**Version verification:** Pillow 11.0.0 confirmed installed via `.venv/bin/python -c "import PIL; print(PIL.__version__)"`. `stroke_width` and `stroke_fill` parameters of `ImageDraw.text()` confirmed present and working.

## Architecture Patterns

### Established Config Pattern (Phase 2)

All new keys follow the Phase 2 config pattern without deviation:

1. Add to `DEFAULT_CONFIG['immich']` at `app.py:43-56` with backward-compat defaults
2. Declare as module globals (initialized from `DEFAULT_CONFIG`)
3. Declare in `global` statement at top of `update_app_config()`
4. Read via `.get()` fallback in `update_app_config()` (lines 543-544 pattern)
5. Read from `request.form.get(...)` in the POST handler `settings()` at `app.py:649-660`

### draw_date_overlay() Extension Pattern

**Current signature:**
```python
def draw_date_overlay(output_img, text, font, position_str, padding=6, rotation=0):
```

**Extended signature (Phase 6):**
```python
def draw_date_overlay(
    output_img, text, font, position_str, padding=6, rotation=0,
    style="background",       # "background" | "outline"
    bg_color=(0, 0, 0, 255),          # fill for background rect (background mode only)
    text_color=(255, 255, 255, 255),   # fill for text glyphs (both modes)
    border_color=(255, 255, 255, 255), # stroke color (outline mode only)
    stroke_width=2,                    # stroke thickness in px (outline mode only)
):
```

All defaults reproduce current visual exactly (D-14).

### Background Mode Logic

```python
# Source: existing app.py:134-136, parameterized
if style == "background":
    draw.rectangle(rect, fill=bg_color)
draw.text(
    (x - bbox[0], y - bbox[1]),
    text,
    fill=text_color,
    font=font,
)
```

### Outline Mode Logic

```python
# Source: Pillow 11.0.0 ImageDraw.text() API, verified locally
if style == "outline":
    # No rectangle — stroke_fill provides visual separation
    draw.text(
        (x - bbox[0], y - bbox[1]),
        text,
        fill=text_color,
        font=font,
        stroke_width=stroke_width,
        stroke_fill=border_color,
    )
```

**Critical:** In outline mode, `textbbox()` must be called with `stroke_width` so the
measured bounding box includes stroke expansion (each side expands by `stroke_width`
pixels). This ensures position and padding calculations are correct.

```python
# Probe with stroke_width in outline mode
_probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
if style == "outline":
    bbox = _probe.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
else:
    bbox = _probe.textbbox((0, 0), text, font=font)
```

### Color Name-to-RGBA Mapping

Place a dict near `palette` at `app.py:196-201` — single source of truth for palette RGB
values, avoids drift if palette values change:

```python
# Source: app.py:196-201 (authoritative palette RGB values)
OVERLAY_COLORS = {
    'black':  (0,   0,   0,   255),
    'white':  (255, 255, 255, 255),
    'yellow': (255, 216, 0,   255),
    'red':    (229, 57,  53,  255),
    'blue':   (0,   76,  255, 255),
    'green':  (29,  185, 84,  255),
}
```

`update_app_config()` stores the string name (e.g. `"black"`). The RGBA tuple is looked up
when `draw_date_overlay()` or the call site resolves the color.

**Recommendation (Claude's Discretion):** Store color names as strings in config (matches
YAML naturally), resolve to RGBA tuples at render time using `OVERLAY_COLORS`. This is
cleaner than storing tuples in YAML.

### Font Size Parameterization

Font size is loaded at `app.py:371` inside `scale_img_in_memory()`. Change the hardcoded
`26` to use the new `overlay_font_size` global:

```python
# app.py:371 — current
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)

# Phase 6 — parameterized
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', overlay_font_size)
```

### Settings UI — Slider Pattern

Replicate the existing slider pattern from `settings.html:121-145` for font size and
stroke width:

```html
<!-- Source: settings.html:450-456 — existing slider (dithering strength) -->
<div class="form-group">
    <label for="overlay_font_size">Font Size:</label>
    <div class="slider-container">
        <input type="range" id="overlay_font_size" name="overlay_font_size"
               min="16" max="48" step="1"
               value="{{ config['immich'].get('overlay_font_size', 26) }}"
               oninput="updateSliderValue(this)">
        <output class="slider-value">{{ config['immich'].get('overlay_font_size', 26) }}</output>
    </div>
</div>
```

### Settings UI — Color Dropdown Pattern

Replicate the existing `<select>` pattern from the position dropdown at `settings.html:471-481`:

```html
<div class="form-group">
    <label for="overlay_bg_color">Background Color:</label>
    <select id="overlay_bg_color" name="overlay_bg_color">
        <option value="black"  {% if config['immich'].get('overlay_bg_color', 'black')  == 'black'  %}selected{% endif %}>Black</option>
        <option value="white"  {% if config['immich'].get('overlay_bg_color', 'black')  == 'white'  %}selected{% endif %}>White</option>
        <option value="yellow" {% if config['immich'].get('overlay_bg_color', 'black')  == 'yellow' %}selected{% endif %}>Yellow</option>
        <option value="red"    {% if config['immich'].get('overlay_bg_color', 'black')  == 'red'    %}selected{% endif %}>Red</option>
        <option value="blue"   {% if config['immich'].get('overlay_bg_color', 'black')  == 'blue'   %}selected{% endif %}>Blue</option>
        <option value="green"  {% if config['immich'].get('overlay_bg_color', 'black')  == 'green'  %}selected{% endif %}>Green</option>
    </select>
</div>
```

Repeat for `overlay_text_color` (default `"white"`) and `overlay_border_color` (default `"white"`).

### Anti-Patterns to Avoid

- **Storing RGBA tuples in YAML:** PyYAML cannot round-trip Python tuples naturally;
  store color names as strings and resolve to RGBA at render time.
- **Calling textbbox() without stroke_width in outline mode:** The stroke expands the
  glyph bounding box; omitting `stroke_width` causes the stroke to overflow the computed
  padding rect. Confirmed empirically: at `stroke_width=2`, each side of bbox expands 2px.
- **Drawing a rectangle in outline mode:** Outline mode intentionally has no filled
  background; adding the rectangle negates the purpose of the mode.
- **Using a checkbox for overlay_style:** HTML POST omits unchecked checkboxes. Use
  `<select>` per D-05 / STATE.md key decision.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text stroke / outline effect | Custom multi-pass draw routine | `ImageDraw.text(..., stroke_width=N, stroke_fill=color)` | Pillow handles sub-pixel expansion correctly across fonts |
| Color validation / normalization | Custom color parser | Fixed 6-entry `OVERLAY_COLORS` dict | Only 6 valid colors exist for this hardware |

**Key insight:** Pillow's built-in `stroke_width` / `stroke_fill` is the correct tool.
It handles font-metric details (glyph outlines, antialiasing interactions) that a manual
approach would get wrong.

## Common Pitfalls

### Pitfall 1: textbbox without stroke_width in outline mode
**What goes wrong:** Overlay rect/padding is computed without stroke, but text is drawn
with stroke that expands outward — stroke pixels fall outside the computed padding region
or are clipped.
**Why it happens:** `textbbox()` only includes stroke expansion when `stroke_width` is
passed explicitly.
**How to avoid:** Pass `stroke_width=stroke_width` to `textbbox()` when `style == "outline"`.
**Warning signs:** Test that checks for outline pixels in bottom-right region fails, or
stroke appears to bleed outside the expected area.

### Pitfall 2: Forgetting new globals in `global` statement
**What goes wrong:** `update_app_config()` sets a local variable instead of the module
global — the overlay still uses the old hardcoded value at render time.
**Why it happens:** Python requires explicit `global varname` declaration inside functions
before assignment.
**How to avoid:** Add all 6 new names (`overlay_style`, `overlay_bg_color`, `overlay_text_color`,
`overlay_border_color`, `overlay_stroke_width`, `overlay_font_size`) to the `global`
statement at `app.py:505-512`.
**Warning signs:** Integration test that monkeypatches the global and checks rendered pixel
color fails to observe the change.

### Pitfall 3: POST handler reads int/float for slider values
**What goes wrong:** `request.form.get('overlay_font_size', 26)` returns a string; the
font-load call fails with `TypeError: argument of type 'str' is not iterable` or similar.
**Why it happens:** HTML form POST values are always strings.
**How to avoid:** `int(request.form.get('overlay_font_size', 26))` and
`int(request.form.get('overlay_stroke_width', 2))` — same pattern as `sleep_start_hour`
at `app.py:643-644`.

### Pitfall 4: YAML round-trip of int slider values
**What goes wrong:** Config written as `overlay_font_size: '26'` (string) instead of
`overlay_font_size: 26` (int) causes TypeError at font load.
**Why it happens:** If the POST handler stores the string form value without `int()` cast,
PyYAML preserves it as a string.
**How to avoid:** Always cast to `int` in the POST handler before building the config dict
to write to YAML.

## Code Examples

### Full draw_date_overlay() structure (outline branch)

```python
# Source: Pillow 11.0.0 ImageDraw.text() API + existing app.py:95-148 pattern
def draw_date_overlay(
    output_img, text, font, position_str, padding=6, rotation=0,
    style="background",
    bg_color=(0, 0, 0, 255),
    text_color=(255, 255, 255, 255),
    border_color=(255, 255, 255, 255),
    stroke_width=2,
):
    bw, bh = output_img.size
    if rotation in (90, 270):
        vw, vh = bh, bw
    else:
        vw, vh = bw, bh

    _probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    sw = stroke_width if style == "outline" else 0
    bbox = _probe.textbbox((0, 0), text, font=font, stroke_width=sw)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    get_xy = POSITIONS.get(position_str, POSITIONS['bottomRight'])
    x, y = get_xy(vw, vh, tw, th, padding)

    viewer_canvas = Image.new('RGBA', (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(viewer_canvas)
    rect = [x - padding, y - padding, x + tw + padding, y + th + padding]

    if style == "background":
        draw.rectangle(rect, fill=bg_color)
        draw.text((x - bbox[0], y - bbox[1]), text, fill=text_color, font=font)
    else:  # outline
        draw.text(
            (x - bbox[0], y - bbox[1]), text,
            fill=text_color, font=font,
            stroke_width=stroke_width, stroke_fill=border_color,
        )

    if rotation != 0:
        viewer_canvas = viewer_canvas.rotate(rotation, expand=True)

    overlay_rgb = viewer_canvas.convert('RGB')
    mask = viewer_canvas.split()[3]
    output_img.paste(overlay_rgb, mask=mask)
```

### update_app_config() additions

```python
# Add to global statement (app.py:505-512):
global ..., overlay_style, overlay_bg_color, overlay_text_color, \
       overlay_border_color, overlay_stroke_width, overlay_font_size

# Add to variable assignments (after line 544):
overlay_style        = new_config['immich'].get('overlay_style', 'background')
overlay_bg_color     = new_config['immich'].get('overlay_bg_color', 'black')
overlay_text_color   = new_config['immich'].get('overlay_text_color', 'white')
overlay_border_color = new_config['immich'].get('overlay_border_color', 'white')
overlay_stroke_width = new_config['immich'].get('overlay_stroke_width', 2)
overlay_font_size    = new_config['immich'].get('overlay_font_size', 26)
```

### scale_img_in_memory() call site (app.py:366-374)

```python
if date_overlay_enabled:
    date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
    if date_str:
        try:
            font = ImageFont.truetype(
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                overlay_font_size,  # was hardcoded 26
            )
        except (IOError, OSError):
            font = ImageFont.load_default()
        draw_date_overlay(
            output_img, date_str, font, date_overlay_position, padding=6,
            rotation=rotation,
            style=overlay_style,
            bg_color=OVERLAY_COLORS.get(overlay_bg_color, (0, 0, 0, 255)),
            text_color=OVERLAY_COLORS.get(overlay_text_color, (255, 255, 255, 255)),
            border_color=OVERLAY_COLORS.get(overlay_border_color, (255, 255, 255, 255)),
            stroke_width=overlay_stroke_width,
        )
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed in .venv, no config file — runs from project root) |
| Config file | none (relies on test discovery defaults) |
| Quick run command | `.venv/bin/python -m pytest tests/ -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` |

**Baseline:** 13 tests, all passing (confirmed 2026-05-29).

### Phase Requirements → Test Map

| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| TC-01 | `OVERLAY_COLORS` dict contains exactly 6 palette entries with correct RGBA | unit | `pytest tests/test_overlay_customization.py::test_overlay_colors_dict -x` | Wave 0 |
| TC-02 | `DEFAULT_CONFIG` has all 6 new keys with correct defaults (D-14) | unit | `pytest tests/test_overlay_customization.py::test_default_config_new_keys -x` | Wave 0 |
| TC-03 | `draw_date_overlay()` background mode renders filled rect with `bg_color` | unit | `pytest tests/test_overlay_customization.py::test_background_mode_uses_bg_color -x` | Wave 0 |
| TC-04 | `draw_date_overlay()` outline mode renders stroke pixels, no filled rect | unit | `pytest tests/test_overlay_customization.py::test_outline_mode_no_rect -x` | Wave 0 |
| TC-05 | `draw_date_overlay()` outline mode uses `border_color` for stroke | unit | `pytest tests/test_overlay_customization.py::test_outline_mode_border_color -x` | Wave 0 |
| TC-06 | `draw_date_overlay()` default params match current behavior (no regression) | unit | `pytest tests/test_overlay_customization.py::test_default_params_match_current -x` | Wave 0 |
| TC-07 | `draw_date_overlay()` with `stroke_width=0` equals background mode (no stroke) | unit | `pytest tests/test_overlay_customization.py::test_stroke_width_zero -x` | Wave 0 |
| TC-08 | `update_app_config()` reads new keys into globals via `.get()` with fallback | integration | `pytest tests/test_overlay_customization.py::test_update_config_new_keys -x` | Wave 0 |
| TC-09 | POST handler reads `overlay_font_size` as `int` (not string) | integration | `pytest tests/test_overlay_customization.py::test_post_handler_font_size_int -x` | Wave 0 |
| TC-10 | Existing 13 Phase 2 tests continue to pass (no regression) | regression | `.venv/bin/python -m pytest tests/ -q` | YES (`tests/test_date_overlay.py`) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_overlay_customization.py` — covers TC-01 through TC-09

*(Existing test infrastructure covers TC-10; `conftest.py` fixtures reused)*

## Open Questions

1. **Validation of unknown color strings**
   - What we know: `OVERLAY_COLORS.get(name, fallback)` silently ignores invalid names
   - What's unclear: Should invalid color names in config.yaml log a warning?
   - Recommendation: Silent `.get()` with fallback is consistent with Phase 2 pattern.
     Add a warning log if desired, but not required.

2. **stroke_width interaction with ImageFont.load_default()**
   - What we know: `load_default()` returns a bitmap font with limited glyph metrics
   - What's unclear: Whether `stroke_width` works correctly with bitmap fonts on all
     platforms (stroke is a vector operation)
   - Recommendation: Test passes on macOS with default font. In production (Linux/Docker),
     DejaVuSans-Bold is always available. Low risk.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Pillow | `ImageDraw.text(stroke_width=...)` | Yes | 11.0.0 | — |
| DejaVuSans-Bold.ttf | Font load at app.py:371 | Linux/Docker only | — | `ImageFont.load_default()` (test env) |
| pytest | Test runner | Yes (.venv) | latest | — |

## Sources

### Primary (HIGH confidence)
- Pillow 11.0.0 installed locally — `ImageDraw.text()` signature inspected via `inspect.signature()`; `stroke_width`/`stroke_fill` confirmed present
- `textbbox()` stroke expansion verified empirically: at `stroke_width=2`, bbox expands by 2px per side
- Outline pixel rendering confirmed: 140 black stroke pixels produced in test
- Existing codebase read directly: `app.py`, `templates/settings.html`, `tests/test_date_overlay.py`, `tests/conftest.py`

### Secondary (MEDIUM confidence)
- Pillow changelog (stroke_width available since Pillow 5.3.0; definitely present in 11.0.0)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt, Pillow stroke API verified locally
- Architecture: HIGH — follows established Phase 2 patterns, no new patterns introduced
- Pitfalls: HIGH — all identified via code inspection and local verification

**Research date:** 2026-05-29
**Valid until:** 2026-08-29 (stable Pillow API, no fast-moving dependencies)
