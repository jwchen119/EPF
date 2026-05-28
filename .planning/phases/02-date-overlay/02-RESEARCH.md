# Phase 2: Date Overlay — Research

**Researched:** 2026-05-27
**Domain:** Pillow text rendering / Flask config pattern / HTML form controls
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Overlay is **off by default**. The default config value for `date_overlay_enabled` should be `false` so existing deployments are unaffected until the user explicitly enables it in settings.
- **D-02:** The settings UI must include an on/off toggle for the overlay.
- **D-03:** When no date can be extracted (no EXIF tags, no Immich `exifInfo.dateTimeOriginal`, no fallback), the overlay is **silently hidden**. No placeholder text ("Unknown date") is shown.
- **D-04:** 9 configurable positions: `topLeft`, `topCenter`, `topRight`, `centerLeft`, `center`, `centerRight`, `bottomLeft`, `bottomCenter`, `bottomRight`. These are **positions on the final rendered image** (after rotation is applied).
- **D-05:** Config key is `date_overlay_position` with default value `bottomRight`.

### Claude's Discretion

- Date format: `DD.MM.YYYY` (e.g. `05.01.2022`) as the default.
- Font size: 24–28px bold, auto-detected from DejaVuSans-Bold or fallback to PIL default.
- Visual style: White text with semi-transparent/solid black background rectangle — matching the existing partial `draw_text_with_background()`. Not configurable.
- Padding around text: 5–8px on all sides.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DO-01 | Extract photo date from EXIF (local images) and from Immich `exifInfo.dateTimeOriginal` (Immich images) | EXIF tag 36867 already read inside `scale_img_in_memory()`; Immich path has the field on the asset dict at line 753 — must be passed as a parameter |
| DO-02 | Render date as text overlay with black background pill/rectangle | Pillow `ImageDraw.textbbox()` + `draw.rectangle()` + `draw.text()` — pattern already exists as dead code in `draw_text_with_background()` |
| DO-03 | Overlay is off by default; silently hidden when no date available | Add `date_overlay_enabled: false` to `DEFAULT_CONFIG`; guard in rendering with `if date_overlay_enabled and date_text` |
| DO-04 | 9 configurable overlay positions applied to the final (post-rotation) image | Compute x/y from image dimensions and position string after all rotation/scaling is done — see Architecture Patterns |
| DO-05 | Position and enable/disable settable via `config.yaml` and web UI | Follow existing config pattern: `DEFAULT_CONFIG` → `update_app_config()` → global → form field → POST handler |
</phase_requirements>

---

## Summary

Phase 2 is a focused in-process change to a single Python file (`app.py`) and one Jinja2 template (`templates/settings.html`). No new dependencies are needed — Pillow (`PIL`) is already imported and used for image manipulation, and Flask/Jinja2 handle the settings UI.

The existing codebase already contains a near-complete but commented-out implementation of `draw_text_with_background()` (lines 274–357 of `app.py`). That function handles rotation-relative positioning with hard-coded offsets tied to the physical rotation angle. The key refactor is to decouple position from rotation: the overlay runs **after** `load_scaled()` and the color conversion pipeline, at which point the output image already reflects the final visible orientation. Rotation is therefore irrelevant to coordinate calculation — position can be computed purely from image dimensions and the 9-string enum.

The Immich code path (`serve_immich_image()`) calls `scale_img_in_memory(image)` without passing date metadata. The `exifInfo.dateTimeOriginal` field is already present on the `selected_image` dict (used for ordering at line 753). It must be passed as an optional parameter to `scale_img_in_memory()`. The local path extracts EXIF inside `scale_img_in_memory()` already; that path requires no structural change, only the refactored draw function.

**Primary recommendation:** Refactor `draw_text_with_background()` into a standalone helper that accepts `(draw, image_size, text, font, position_str, padding)` and computes coordinates from `position_str` and `image_size` — independent of rotation. Wire it into `scale_img_in_memory()` behind the `date_overlay_enabled` global. Pass Immich date from `serve_immich_image()` as a new optional parameter.

---

## Standard Stack

### Core (already installed — no new packages required)

| Library | Version in use | Purpose | Notes |
|---------|---------------|---------|-------|
| Pillow (PIL) | Already installed | `ImageDraw`, `ImageFont`, `textbbox`, `draw.text`, `draw.rectangle` | All overlay rendering |
| Flask / Jinja2 | Already installed | Settings route, HTML template | Config UI |
| PyYAML | Already installed | `config.yaml` read/write | Config persistence |

No `pip install` commands needed for this phase.

### Font availability (runtime environment — Raspberry Pi / Linux)

| Font path | Availability | Fallback |
|-----------|-------------|---------|
| `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` | Standard on Debian/Ubuntu/Raspberry Pi OS | `ImageFont.load_default()` already in existing code |

The existing pattern (`try: truetype ... except: load_default()`) is correct and must be preserved. Recommended size: 26px (midpoint of 24–28 range from decisions).

---

## Architecture Patterns

### Key Insight: Overlay Must Run on the Post-Pipeline Image

The current code flow in `scale_img_in_memory()`:

```
load_scaled(image, rotation, display_mode)   → rotated + scaled PIL image
  → ImageEnhance.Color / Contrast
  → convert_image() dithering                 → numpy array
  → Image.fromarray()                         → output_img (final PIL image, correct orientation)
  → [OVERLAY HERE]                            ← insert draw call here
  → output_img.save(img_io, 'BMP')
```

`output_img` at the overlay insertion point already has the correct pixel dimensions for the display and the correct visual orientation. The physical `rotation` value is irrelevant to overlay coordinate math.

### Pattern 1: Position String → Coordinate Mapping

**What:** Convert a 9-value enum string into (x, y) pixel coordinates for the overlay rectangle's anchor corner, given image dimensions and text bounding box.

**When to use:** Inside the refactored `draw_text_with_background()` helper.

```python
# Source: derived from Pillow docs (textbbox pattern)
POSITIONS = {
    "topLeft":      lambda w, h, tw, th, p: (p, p),
    "topCenter":    lambda w, h, tw, th, p: ((w - tw) // 2, p),
    "topRight":     lambda w, h, tw, th, p: (w - tw - p, p),
    "centerLeft":   lambda w, h, tw, th, p: (p, (h - th) // 2),
    "center":       lambda w, h, tw, th, p: ((w - tw) // 2, (h - th) // 2),
    "centerRight":  lambda w, h, tw, th, p: (w - tw - p, (h - th) // 2),
    "bottomLeft":   lambda w, h, tw, th, p: (p, h - th - p),
    "bottomCenter": lambda w, h, tw, th, p: ((w - tw) // 2, h - th - p),
    "bottomRight":  lambda w, h, tw, th, p: (w - tw - p, h - th - p),
}

def draw_date_overlay(output_img, text, font, position_str, padding=6):
    """Draw white text with black background rectangle at position_str."""
    draw = ImageDraw.Draw(output_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    w, h = output_img.size
    get_xy = POSITIONS.get(position_str, POSITIONS["bottomRight"])
    x, y = get_xy(w, h, tw, th, padding)
    rect = [x - padding, y - padding, x + tw + padding, y + th + padding]
    draw.rectangle(rect, fill=(0, 0, 0))
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
```

No text rotation needed — `output_img` is already in final orientation.

### Pattern 2: Date String Extraction and Normalization

Two source paths, one normalized string:

```python
# Path A — EXIF (local images, inside scale_img_in_memory)
# EXIF tag 36867 = DateTimeOriginal, tag 306 = DateTime
# Format: "YYYY:MM:DD HH:MM:SS"
try:
    exif = image._getexif()
    date_time_raw = (exif or {}).get(36867) or (exif or {}).get(306)
except Exception:
    date_time_raw = None

# Path B — Immich (passed as parameter)
# Format: ISO 8601 "YYYY-MM-DDTHH:MM:SS.sssZ"
# Already available on selected_image['exifInfo']['dateTimeOriginal']

def parse_photo_date(raw_str):
    """Return DD.MM.YYYY string or None if unparseable."""
    if not raw_str:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(raw_str[:19], fmt[:len(fmt.split('%')[0])+2*len(fmt.split('%'))-2]).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return None
```

Simpler and more robust: use `raw_str[:10]` slicing for ISO 8601 from Immich (always `YYYY-MM-DD`), and `strptime` for EXIF format.

### Pattern 3: Config Integration (Established Project Pattern)

Add two keys to `DEFAULT_CONFIG['immich']`:

```python
'date_overlay_enabled': False,   # D-01: off by default
'date_overlay_position': 'bottomRight',  # D-05
```

Add two globals to `update_app_config()` signature and body:

```python
global ..., date_overlay_enabled, date_overlay_position
# ...
date_overlay_enabled = new_config['immich'].get('date_overlay_enabled', False)
date_overlay_position = new_config['immich'].get('date_overlay_position', 'bottomRight')
```

Add to POST handler in `settings()`:

```python
'date_overlay_enabled': request.form.get('date_overlay_enabled') == 'on',
'date_overlay_position': request.form.get('date_overlay_position', 'bottomRight'),
```

### Pattern 4: Passing Immich Date Through the Call Chain

`serve_immich_image()` must extract the date and pass it to `scale_img_in_memory()`:

```python
# In serve_immich_image(), after selected_image is set:
immich_date_raw = selected_image.get('exifInfo', {}).get('dateTimeOriginal')

# Then:
processed_image = scale_img_in_memory(image, immich_date_raw=immich_date_raw)
```

`scale_img_in_memory()` signature change:

```python
def scale_img_in_memory(image, target_width=1200, target_height=1600,
                         bg_color=(255, 255, 255), immich_date_raw=None):
```

Inside the function, EXIF extraction serves as fallback when `immich_date_raw` is None. Priority: Immich field first, EXIF second.

### Pattern 5: Settings UI Toggle and Select

HTML to add inside a new `.card` block in `settings.html`, following the existing `select`/`form-group` pattern:

```html
<div class="card">
    <h2 class="card-title">Date Overlay</h2>
    <div class="form-group">
        <label for="date_overlay_enabled">Show Photo Date:</label>
        <select id="date_overlay_enabled" name="date_overlay_enabled">
            <option value="off" {% if not config['immich'].get('date_overlay_enabled', false) %}selected{% endif %}>Off</option>
            <option value="on"  {% if config['immich'].get('date_overlay_enabled', false) %}selected{% endif %}>On</option>
        </select>
        <div class="small-text">Display the date the photo was taken on the image</div>
    </div>
    <div class="form-group">
        <label for="date_overlay_position">Overlay Position:</label>
        <select id="date_overlay_position" name="date_overlay_position">
            <option value="topLeft"      {% if config['immich'].get('date_overlay_position') == 'topLeft' %}selected{% endif %}>Top Left</option>
            <option value="topCenter"    {% if config['immich'].get('date_overlay_position') == 'topCenter' %}selected{% endif %}>Top Center</option>
            <option value="topRight"     {% if config['immich'].get('date_overlay_position') == 'topRight' %}selected{% endif %}>Top Right</option>
            <option value="centerLeft"   {% if config['immich'].get('date_overlay_position') == 'centerLeft' %}selected{% endif %}>Center Left</option>
            <option value="center"       {% if config['immich'].get('date_overlay_position') == 'center' %}selected{% endif %}>Center</option>
            <option value="centerRight"  {% if config['immich'].get('date_overlay_position') == 'centerRight' %}selected{% endif %}>Center Right</option>
            <option value="bottomLeft"   {% if config['immich'].get('date_overlay_position') == 'bottomLeft' %}selected{% endif %}>Bottom Left</option>
            <option value="bottomCenter" {% if config['immich'].get('date_overlay_position') == 'bottomCenter' %}selected{% endif %}>Bottom Center</option>
            <option value="bottomRight"  {% if config['immich'].get('date_overlay_position','bottomRight') == 'bottomRight' %}selected{% endif %}>Bottom Right</option>
        </select>
    </div>
</div>
```

Note: HTML `<input type="checkbox">` with `name="date_overlay_enabled"` would be the natural toggle, but the existing UI pattern uses `<select>`. The boolean is read as `request.form.get('date_overlay_enabled') == 'on'` in the POST handler. Both approaches work; the select approach (`'on'/'off'`) is most consistent with the codebase and avoids the absent-key problem with unchecked checkboxes in HTML forms.

### Anti-Patterns to Avoid

- **Do NOT pass rotation into the overlay helper.** The output image is already rotated by `load_scaled()`. Computing coordinates based on rotation angle re-introduces the complexity of the dead code and produces wrong results.
- **Do NOT use a nested function** for the helper (as the dead code does). Extract `draw_date_overlay()` as a module-level function so it can be tested independently.
- **Do NOT silently fall through with a malformed date.** If `parse_photo_date()` returns None, skip the overlay entirely (D-03). Do not render raw strings as fallback.
- **Do NOT put `date_overlay_enabled` check in the HTML template only.** Guard it in the Python pipeline — the template toggle only affects user preference persistence.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text bounding box measurement | Custom pixel counting | `ImageDraw.textbbox()` (Pillow built-in) | Handles kerning, font metrics correctly |
| EXIF date extraction | File-level byte parsing | `image._getexif()` with tag 36867 (already used) | JPEG/TIFF EXIF is complex; PIL handles it |
| Date string parsing | Regex / manual slicing | `datetime.strptime()` (stdlib) | Handles format variants; raises on malformed input |
| Config serialization | Custom file format | `yaml.safe_dump()` / `yaml.safe_load()` (already used) | Consistent with existing config pattern |

---

## Common Pitfalls

### Pitfall 1: Boolean Serialization in YAML

**What goes wrong:** Python `False` round-trips through `yaml.safe_dump` / `yaml.safe_load` correctly as `false`, but if the config file was manually edited or written without the key, `new_config['immich'].get('date_overlay_enabled')` returns `None`, not `False`.

**Why it happens:** `yaml.safe_load` of a missing key yields `None`; a truthy check on `None` is falsy but `None != False`.

**How to avoid:** Use `.get('date_overlay_enabled', False)` everywhere the key is read from the dict. The POST handler sets it via `request.form.get('date_overlay_enabled') == 'on'` which always yields a bool.

**Warning signs:** Overlay appears enabled on fresh deployments with no config file.

---

### Pitfall 2: HTML Checkbox Absent-Key Problem (if using checkbox instead of select)

**What goes wrong:** An unchecked HTML `<input type="checkbox">` submits NO value to the form. `request.form.get('date_overlay_enabled')` returns `None`, not `'off'` or `False`. The POST handler silently leaves the old value in the config or sets it to True.

**Why it happens:** This is standard HTML form behavior — unchecked boxes are omitted from the POST body.

**How to avoid:** Either use a `<select on/off>` (consistent with project pattern), or use `request.form.get('date_overlay_enabled', 'off') == 'on'` with an explicit default.

---

### Pitfall 3: Dead Code Left in Place

**What goes wrong:** The existing dead code block (lines 256–358 in `scale_img_in_memory()`) contains the conditional `if date_time:` plus `draw_text_with_background()` nested definition. If the new code is added alongside rather than replacing this block, both paths may run or conflict.

**Why it happens:** Fear of deleting working-ish code.

**How to avoid:** The implementation plan must explicitly replace the entire block (lines 255–358) with the new `draw_date_overlay()` call site. Remove the nested function definition entirely.

---

### Pitfall 4: textbbox Offset (Pillow ≥ 9.2)

**What goes wrong:** `draw.textbbox((0, 0), text, font=font)` returns `(left, top, right, bottom)` where `left` and `top` may be non-zero for certain fonts (especially with `load_default()`). Using `bbox[2] - bbox[0]` for width and `bbox[3] - bbox[1]` for height is correct, but drawing the text at `(x, y)` with `y` derived from `bbox[1]` offset can cause the text to appear slightly offset from the background rectangle.

**Why it happens:** Pillow's default font has a non-zero top offset in newer versions.

**How to avoid:** Use `draw.text((x - bbox[0], y - bbox[1]), ...)` to normalize for the offset, or use `font.getbbox(text)` and compensate. The simplest fix: draw text at `(x, y)` and set rect from `(x + bbox[0] - padding, y + bbox[1] - padding)` to `(x + bbox[2] + padding, y + bbox[3] + padding)`.

---

## Code Examples

### Immich `exifInfo.dateTimeOriginal` Format

From the existing ordering code (line 753), the field value is ISO 8601: `"2022-01-05T14:30:00.000Z"`. The date component is always `raw[:10]` → `"2022-01-05"`.

```python
# Fast parse for Immich ISO 8601
def parse_photo_date(raw_str):
    """Return 'DD.MM.YYYY' or None."""
    if not raw_str:
        return None
    # EXIF format: "2022:01:05 14:30:00"
    if len(raw_str) >= 10 and raw_str[4] == ':':
        try:
            dt = datetime.strptime(raw_str[:10], "%Y:%m:%d")
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            pass
    # ISO 8601 from Immich: "2022-01-05T14:30:00.000Z"
    if len(raw_str) >= 10 and raw_str[4] == '-':
        try:
            dt = datetime.strptime(raw_str[:10], "%Y-%m-%d")
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            pass
    return None
```

### Font Loading (reuse existing pattern)

```python
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
except (IOError, OSError):
    font = ImageFont.load_default()
```

### Overlay Insertion Point in `scale_img_in_memory()`

```python
output_img = Image.fromarray(output_img, mode="RGB")

# Date overlay (replaces dead code block, lines 255–358)
if date_overlay_enabled:
    date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
    if date_str:
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        except (IOError, OSError):
            font = ImageFont.load_default()
        draw_date_overlay(output_img, date_str, font, date_overlay_position, padding=6)

img_io = io.BytesIO()
output_img.save(img_io, 'BMP')
```

---

## Environment Availability

Step 2.6: SKIPPED — this phase makes no changes outside the Python codebase. All required libraries (Pillow, Flask, PyYAML) are already installed and exercised by the existing code. The DejaVuSans-Bold font is verified present by the existing fallback pattern.

---

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None detected — no test directory, no pytest.ini, no test scripts |
| Config file | None — Wave 0 must create |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DO-01 | `parse_photo_date()` parses EXIF format `"2022:01:05 14:30:00"` → `"05.01.2022"` | unit | `pytest tests/test_date_overlay.py::test_parse_exif_date -x` | Wave 0 |
| DO-01 | `parse_photo_date()` parses Immich ISO 8601 `"2022-01-05T14:30:00.000Z"` → `"05.01.2022"` | unit | `pytest tests/test_date_overlay.py::test_parse_immich_date -x` | Wave 0 |
| DO-01 | `parse_photo_date(None)` returns `None` | unit | `pytest tests/test_date_overlay.py::test_parse_none -x` | Wave 0 |
| DO-02 | `draw_date_overlay()` draws rectangle and text on image | unit | `pytest tests/test_date_overlay.py::test_draw_overlay_renders -x` | Wave 0 |
| DO-03 | `scale_img_in_memory()` returns image unchanged when `date_overlay_enabled=False` | unit | `pytest tests/test_date_overlay.py::test_overlay_disabled -x` | Wave 0 |
| DO-03 | Overlay silently absent when date is `None` even if enabled | unit | `pytest tests/test_date_overlay.py::test_overlay_no_date -x` | Wave 0 |
| DO-04 | `draw_date_overlay()` with `position_str="topLeft"` places rect near (0,0) | unit | `pytest tests/test_date_overlay.py::test_position_topleft -x` | Wave 0 |
| DO-04 | `draw_date_overlay()` with `position_str="bottomRight"` places rect at bottom-right | unit | `pytest tests/test_date_overlay.py::test_position_bottomright -x` | Wave 0 |
| DO-05 | Config round-trip: `date_overlay_enabled=False` and `date_overlay_position='bottomRight'` in `DEFAULT_CONFIG` | unit | `pytest tests/test_date_overlay.py::test_default_config -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_date_overlay.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/test_date_overlay.py` — covers DO-01 through DO-05
- [ ] `tests/conftest.py` — shared fixtures (minimal synthetic PIL images for unit tests)
- [ ] Framework install: `pip install pytest` — if not present in environment

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection of `/Users/lennart/Dev/privat/EPF/app.py` (lines 1–365, 460–631, 693–800) — all patterns verified against live source
- Direct inspection of `/Users/lennart/Dev/privat/EPF/templates/settings.html` — UI card/form-group pattern confirmed
- Pillow `ImageDraw.textbbox` and `draw.text` — standard API, unchanged since Pillow 9.2

### Secondary (MEDIUM confidence)

- Pillow textbbox offset behavior for `load_default()` — known behavioral characteristic; recommend testing with actual font on target platform

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; all libraries confirmed in existing imports
- Architecture: HIGH — patterns derived directly from live code inspection
- Pitfalls: HIGH (checkbox/YAML), MEDIUM (textbbox offset — platform-dependent)

**Research date:** 2026-05-27
**Valid until:** 2026-07-27 (Pillow API is stable; Flask config pattern is project-internal)
