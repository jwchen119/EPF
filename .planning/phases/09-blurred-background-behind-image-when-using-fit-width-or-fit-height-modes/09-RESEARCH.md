# Phase 9: Blurred Background Behind Image (Fit Modes) - Research

**Researched:** 2026-06-07
**Domain:** PIL/Pillow image compositing — GaussianBlur, resize, paste
**Confidence:** HIGH

---

## Summary

When `display_mode` is `fit` (the current default, opposed to `fill`), the image is letterboxed or pillarboxed onto a plain white 1200×1600 background with `Image.new('RGB', (EPD_W, EPD_H), (255, 255, 255))`. This leaves visible white bars on either side (pillarbox) or top/bottom (letterbox). The goal of Phase 9 is to replace that plain white background with a blurred, upscaled version of the same photo — a technique common in music players and photo apps.

The implementation lives entirely inside `cpy_fallback.py`'s `load_scaled()` function (and the compiled Cython equivalent `cpy.pyx`/`cpy.so` if present, but the fallback is the canonical reference). The change requires: (1) detecting `fit-width` vs `fit-height` sub-cases (already implicit in the existing `else` branch), (2) creating a fill-scaled blurred version of the image as the background layer, and (3) pasting the letterboxed/pillarboxed sharp image on top.

The display is a 6-color e-paper (T133A01). Heavy Gaussian blur on the background is desirable: it produces a visually calm, low-frequency color field that dithers well to the 6-color palette. A blur radius of 20–40 px is appropriate. No new config keys are needed for the MVP; a configurable radius is a low-priority enhancement that can be deferred.

**Primary recommendation:** Extend `load_scaled()` in `cpy_fallback.py` (and mirror in `cpy.pyx`) to blur-fill the background canvas in `fit` mode. Wire blur radius as a new optional config key `blur_radius` with a sensible default (e.g., 30).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow  | 11.0.0 (pinned in requirements.txt) | GaussianBlur, resize, paste, Image.new | Already the single image-processing dependency; `ImageFilter.GaussianBlur` is the standard API |

### No New Dependencies Required

All required capabilities (`ImageFilter.GaussianBlur`, `Image.resize`, `Image.paste`) are already in Pillow 11.0.0. No new packages needed.

**Installation:** none — already installed.

---

## Architecture Patterns

### How `load_scaled` Currently Works

```
load_scaled(image, angle, display_mode='fit'):
  1. img.rotate(angle, expand=True)        # apply rotation
  2. if display_mode == 'fill':
       resize to overshoot, crop center    # fills 1200×1600, no bars
  3. else (fit):
       resize to fit-within 1200×1600
       bg = Image.new('RGB', (1200,1600), white)
       bg.paste(img, centered_offset)      # ← bars are white here
       return bg
```

The fit branch is the only code path that needs changing. The fill branch is unaffected.

### Recommended Pattern: Blur-Fill Background

```python
# Source: Pillow docs — ImageFilter.GaussianBlur + paste
from PIL import ImageFilter

# Inside the `else` (fit) branch of load_scaled():

# 1. Create blurred background — fill-scale the image, then blur
if orig_ratio > epd_ratio:
    # fit-height: image is wider than display → pillarbox → bars left/right
    bg_height = EPD_H
    bg_width = int(bg_height * orig_ratio)
else:
    # fit-width: image is taller than display → letterbox → bars top/bottom
    bg_width = EPD_W
    bg_height = int(bg_width / orig_ratio)

bg_img = img.resize((max(bg_width, EPD_W), max(bg_height, EPD_H)), Image.Resampling.LANCZOS)
# Center-crop to exact display dimensions
left = (bg_img.width - EPD_W) // 2
top = (bg_img.height - EPD_H) // 2
bg_img = bg_img.crop((left, top, left + EPD_W, top + EPD_H))
bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=30))

# 2. Fit-scale the sharp image (existing logic)
if orig_ratio > epd_ratio:
    new_width = EPD_W
    new_height = int(new_width / orig_ratio)
else:
    new_height = EPD_H
    new_width = int(new_height * orig_ratio)
sharp_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

# 3. Paste sharp image centered onto blurred background
offset = ((EPD_W - new_width) // 2, (EPD_H - new_height) // 2)
bg_img.paste(sharp_img, offset)
return bg_img
```

**Key insight:** The `fill` algorithm already exists in the `if display_mode == 'fill'` branch. For the background, we replicate the same scale-to-fill math, then blur, then paste the fit-scaled sharp image on top. The background does not need to be pixel-perfect for color accuracy because it will be heavily blurred before dithering.

### Cython Mirror (`cpy.pyx`)

`cpy.pyx` also contains a `load_scaled` function. It must receive the same change. The `.so` compiled artifact will need rebuilding. The `cpy_fallback.py` serves as the canonical reference and runs in tests; the Cython version is the production fast path. Both must be kept in sync.

### `blur_radius` Config Key

Following the existing pattern, add a new optional config key:

```python
DEFAULT_CONFIG['immich']['blur_radius'] = 30  # px, int
```

And expose it as a module-level global `blur_radius`, added to the `global` statement in `update_app_config()`. Pass it through `scale_img_in_memory()` → `load_scaled()`. The settings UI can expose it later; MVP is hardcoded default with config-yaml override.

### Recommended Project Structure (no new files needed)

No new modules required. All changes are contained in:

```
cpy_fallback.py          # load_scaled() — canonical pure-Python implementation
cpy.pyx                  # load_scaled() — Cython production fast path (mirror)
app.py                   # DEFAULT_CONFIG + update_app_config() + scale_img_in_memory() signature
templates/settings.html  # optional: slider for blur_radius
tests/
└── test_blur_background.py   # NEW: Wave 0 contract tests
```

### Anti-Patterns to Avoid

- **Using `bg_color` parameter for fallback when blur fails:** The existing `bg_color` param in `scale_img_in_memory` is unused in the current `load_scaled` call. Do not conflate it with blur. Keep blur concerns in `load_scaled`.
- **Blurring after dithering:** Blur must happen on the RGB image BEFORE dithering/palette quantization. Blurring after converts palette-quantized colors back to gradients the ditherer won't see.
- **Using `Image.ANTIALIAS`:** Removed in Pillow 10+. Always use `Image.Resampling.LANCZOS`.
- **Forgetting the `fill` branch:** The `fill` mode already covers the full canvas — do NOT add blur logic there. Only the `fit` (else) branch needs changing.
- **Mutating the input image:** `cpy_fallback.py` already uses `img = image.copy()` at the top of `load_scaled`. Maintain this immutability discipline.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gaussian blur | Custom convolution kernel | `ImageFilter.GaussianBlur(radius=N)` | Pillow uses an optimized box-filter approximation; handles all edge cases |
| Fill-scale for background | Separate helper | Reuse the existing fill math already in the `if display_mode == 'fill'` branch | DRY; same logic is proven by existing behavior |

---

## Common Pitfalls

### Pitfall 1: `fit` vs `fill` mode naming confusion

**What goes wrong:** The phase description says "fit-width or fit-height modes". These are not separate `display_mode` values — they are the two sub-cases of the single `display_mode = 'fit'` branch, distinguished by aspect ratio comparison (`orig_ratio > epd_ratio` = fit-height/pillarbox; `orig_ratio <= epd_ratio` = fit-width/letterbox).

**How to avoid:** Do not add new `display_mode` values. Implement the blur inside the existing `else` branch of `load_scaled()`.

### Pitfall 2: Background overshoots causing black bars

**What goes wrong:** If the background resize math underestimates needed dimensions, the fill-and-crop step produces a black or white strip at the edge.

**How to avoid:** Use `max(bg_width, EPD_W)` and `max(bg_height, EPD_H)` in the background resize to guarantee the bg image always covers the full canvas before cropping.

**Warning signs:** Black/white strip on one edge of the blurred background.

### Pitfall 3: Cython `cpy.pyx` out of sync with `cpy_fallback.py`

**What goes wrong:** Changes made only to `cpy_fallback.py` work in tests (fallback is used when `.so` is absent or import fails) but are silently ignored in production (the compiled `.so` wins at import time).

**How to avoid:** Always update `cpy.pyx` in the same PR. The Cython `cpy.so` must be recompiled after `cpy.pyx` changes. The Dockerfile handles compilation at build time.

**Warning signs:** Tests pass (fallback), but the running Docker container produces unblurred images.

### Pitfall 4: Blur radius too low or too high for 6-color e-paper

**What goes wrong:** A low radius (< 10 px) leaves visible texture in the background that dithers into a noisy pattern. An extremely high radius (> 80 px) on a small image may raise a Pillow internal error or produce no visible effect.

**How to avoid:** Default radius of 20–40 px is visually effective for a 1200×1600 display. Validate with an int cast and a sensible clamp (1–100).

### Pitfall 5: `scale_img_in_memory` signature change breaks callers

**What goes wrong:** Adding `blur_radius` to `load_scaled()` signature requires updating every call site.

**How to avoid:** There are exactly two call sites for `load_scaled`: inside `scale_img_in_memory()` (which has one call to `load_scaled`). Use a keyword argument with a default: `load_scaled(image, rotation, display_mode, blur_radius=30)`. `scale_img_in_memory` reads from the global `blur_radius` and passes it through.

---

## Code Examples

### GaussianBlur (Pillow 11.0.0, verified via Context7)

```python
# Source: https://pillow.readthedocs.io/en/stable/_modules/PIL/ImageFilter.html
from PIL import ImageFilter

blurred = img.filter(ImageFilter.GaussianBlur(radius=30))
```

### Paste sharp image onto blurred background

```python
# Source: Pillow docs — Image.paste with 2-tuple offset
bg.paste(sharp_img, (offset_x, offset_y))
# No mask needed — sharp_img is fully opaque RGB
```

### Detecting fit sub-case

```python
# Already in cpy_fallback.py load_scaled():
orig_ratio = img.width / img.height
epd_ratio = EPD_W / EPD_H

if orig_ratio > epd_ratio:
    # Landscape image on portrait display → pillarbox (bars left/right)
    # fit-height: new_height = EPD_H, new_width < EPD_W
else:
    # Portrait/square image on portrait display → letterbox (bars top/bottom)
    # fit-width: new_width = EPD_W, new_height < EPD_H
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Image.ANTIALIAS` | `Image.Resampling.LANCZOS` | Pillow 10.0.0 | `ANTIALIAS` raises `AttributeError` on Pillow ≥ 10 |
| No background blur | Blurred fill background | Phase 9 | Visual improvement for fit mode |

---

## Open Questions

1. **Should `blur_radius` be exposed in the Settings UI?**
   - What we know: All previous visual config (font size, colors, stroke width) was exposed via sliders/dropdowns in `settings.html`.
   - What's unclear: Whether the user wants UI control or just a sensible default.
   - Recommendation: Implement as a config-yaml-backed global with a default of 30. Add a slider to `settings.html` for consistency with prior art. Treat as a LOW-priority task within the phase — skip if time-constrained.

2. **Does `cpy.pyx` need a rebuild step added to CI?**
   - What we know: The existing Dockerfile compiles `cpy.pyx` at build time. CI (pytest) uses `cpy_fallback.py` because the `.so` is not built in CI.
   - What's unclear: Whether ruff/pyright also scan `cpy.pyx`.
   - Recommendation: The existing CI setup is fine. Planner should note the Cython mirror requirement explicitly in the plan task.

---

## Environment Availability

Step 2.6: SKIPPED — phase is code/config-only; all required capabilities (Pillow GaussianBlur) are already installed in the project's `requirements.txt`.

---

## Validation Architecture

`workflow.nyquist_validation` key is absent from `.planning/config.json` — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed via `requirements.txt`) |
| Config file | `pyproject.toml` (no `[tool.pytest.ini_options]` section — pytest uses defaults) |
| Quick run command | `pytest tests/test_blur_background.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

Requirements for Phase 9 are TBD (not yet mapped in REQUIREMENTS.md). Based on the phase goal, the expected testable behaviors are:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BG-01 | `load_scaled` in `fit` mode returns an image of exactly 1200×1600 | unit | `pytest tests/test_blur_background.py::test_fit_output_dimensions -x` | ❌ Wave 0 |
| BG-02 | `load_scaled` in `fit` mode: background pixels outside the sharp image area differ from plain white (blur was applied) | unit | `pytest tests/test_blur_background.py::test_fit_background_not_white -x` | ❌ Wave 0 |
| BG-03 | `load_scaled` in `fill` mode: behavior unchanged (no blurred background, full-bleed image) | unit | `pytest tests/test_blur_background.py::test_fill_mode_unchanged -x` | ❌ Wave 0 |
| BG-04 | `load_scaled` in `fit` mode with portrait image (fit-width sub-case): background covers entire canvas | unit | `pytest tests/test_blur_background.py::test_fit_width_subcase -x` | ❌ Wave 0 |
| BG-05 | `load_scaled` in `fit` mode with landscape image (fit-height sub-case): background covers entire canvas | unit | `pytest tests/test_blur_background.py::test_fit_height_subcase -x` | ❌ Wave 0 |
| BG-06 | `blur_radius` config key accepted; changing it produces visually different blur (wider radius → more uniform pixels in bar area) | unit | `pytest tests/test_blur_background.py::test_blur_radius_config -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_blur_background.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_blur_background.py` — covers BG-01 through BG-06 (all new; no existing file)
- [ ] No new fixtures needed — `conftest.py` already has `blank_rgb_image` and `large_rgb_image` which are usable; add landscape variant if needed inline

---

## Sources

### Primary (HIGH confidence)

- `/websites/pillow_readthedocs_io_en_stable` — `ImageFilter.GaussianBlur` API, `Image.paste` API, `Image.Resampling.LANCZOS`
- `cpy_fallback.py` (project source) — existing `load_scaled()` implementation, both `fill` and `fit` branches
- `app.py` (project source) — `scale_img_in_memory()`, `DEFAULT_CONFIG`, `update_app_config()`, global variable pattern

### Secondary (MEDIUM confidence)

- `requirements.txt` — confirmed Pillow 11.0.0 is the pinned version
- `pyproject.toml` — confirmed ruff/pyright config scope

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — Pillow 11.0.0 already installed; GaussianBlur API verified via Context7
- Architecture: HIGH — existing `load_scaled()` code read directly; pattern is straightforward
- Pitfalls: HIGH — derived from direct reading of the codebase (Cython sync, fill/fit confusion, resize math)

**Research date:** 2026-06-07
**Valid until:** 2026-07-07 (Pillow is stable; project stack is pinned)
