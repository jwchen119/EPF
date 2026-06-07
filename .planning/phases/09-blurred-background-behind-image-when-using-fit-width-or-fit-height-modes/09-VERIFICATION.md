---
phase: 09-blurred-background-behind-image-when-using-fit-width-or-fit-height-modes
verified: 2026-06-07T14:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 9: Blurred Background (Fit Modes) Verification Report

**Phase Goal:** Replace plain white letterbox/pillarbox bars in fit mode with a fill-scaled, heavily Gaussian-blurred version of the same photo. Sharp fit-scaled photo pasted on top. Implemented in cpy_fallback.py and mirrored in cpy.pyx. blur_radius config key (default 30) persisted and exposed via settings UI slider.
**Verified:** 2026-06-07
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | fit mode returns a blurred (non-white) background where letterbox/pillarbox bars were | VERIFIED | `cpy_fallback.py` fit branch: fill-scale → center-crop → GaussianBlur → paste sharp image. All 4 blur pixel tests pass. |
| 2 | fill mode behavior is completely unchanged | VERIFIED | Fill branch in `cpy_fallback.py` is untouched; BG-03 `test_fill_mode_unchanged` passes |
| 3 | blur_radius kwarg accepted by load_scaled with default=30 | VERIFIED | `def load_scaled(image, angle, display_mode='fit', blur_radius=30)` in both `cpy_fallback.py` and `cpy.pyx` |
| 4 | blur_radius config key persists through DEFAULT_CONFIG and update_app_config | VERIFIED | `app.py` line 64 (DEFAULT_CONFIG), line 325 (module global), line 785 (update_app_config), line 514 (call site), lines 922-924 (POST handler) |
| 5 | All 7 tests in test_blur_background.py pass (GREEN) | VERIFIED | `python -m pytest tests/test_blur_background.py -v` — 7 passed in 0.77s |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `cpy_fallback.py` | load_scaled with blur-fill background in fit mode | VERIFIED | Contains `from PIL import ImageFilter`, signature `blur_radius=30`, 6-step blur-fill else branch, `GaussianBlur(radius=blur_radius)` at line 62 |
| `app.py` | blur_radius global, DEFAULT_CONFIG entry, update_app_config wiring, scale_img_in_memory pass-through | VERIFIED | 7 occurrences of `blur_radius` across all required locations |
| `tests/test_blur_background.py` | 7 contract tests BG-01 through BG-06 | VERIFIED | 7 test functions present; `make_gradient_image` helper added for BG-06 (deviation from plan, documented) |
| `cpy.pyx` | Cython production path with blur logic | VERIFIED | `from PIL import Image, ImageFilter` at line 10, `blur_radius=30` at line 61, `GaussianBlur(radius=blur_radius)` at line 116, uses `Image.LANCZOS` (not `Image.Resampling.LANCZOS`) as required |
| `templates/settings.html` | blur_radius slider in Display Mode card | VERIFIED | Range input `name="blur_radius"` min=5 max=80 step=5 at lines 428-435; reset wired at lines 741-743 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py scale_img_in_memory` | `cpy_fallback.load_scaled` | `blur_radius=blur_radius` kwarg | WIRED | `load_scaled(image, rotation, display_mode, blur_radius=blur_radius)` at line 514 |
| `app.py update_app_config` | `app.py blur_radius global` | `int() cast + .get() fallback` | WIRED | `blur_radius = int(new_config['immich'].get('blur_radius', 30))` at line 785; `global ... blur_radius` in global statement at line 744 |
| `templates/settings.html` | `app.py POST handler` | `form input name='blur_radius'` | WIRED | `<input name="blur_radius">` at line 430; consumed at lines 922-924 via `request.form.get('blur_radius', ...)` |
| `cpy.pyx load_scaled` | `cpy_fallback.py load_scaled` | identical blur logic (sync) | WIRED | Both files contain identical 6-step blur-fill fit branch; cpy.pyx correctly uses `Image.LANCZOS` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `cpy_fallback.py load_scaled` | `bg_img` (blurred background) | `img.resize(...)` then `.filter(GaussianBlur)` then `.paste(sharp_img)` | Yes — derives from input image, not hardcoded | FLOWING |
| `app.py scale_img_in_memory` | `blur_radius` | module global initialized from DEFAULT_CONFIG; overwritten by `update_app_config` | Yes — integer value from config | FLOWING |
| `templates/settings.html` | `config['immich'].get('blur_radius', 30)` | Flask template context dict (`config`) passed from route | Yes — reads persisted config | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 7 BG contract tests pass | `python -m pytest tests/test_blur_background.py -v` | 7 passed in 0.77s | PASS |
| Full suite has no regressions | `python -m pytest tests/ -x -q` | 57 passed, 10 warnings in 2.62s | PASS |
| `cpy_fallback.py` has GaussianBlur and blur_radius | `grep -n "GaussianBlur\|blur_radius\|ImageFilter" cpy_fallback.py` | 3 matches (import, signature, filter call) | PASS |
| `app.py` has 7 blur_radius occurrences | `grep -n "blur_radius" app.py` | 7 lines (DEFAULT_CONFIG, module init, global stmt, update_app_config body, call site, POST handler ×2) | PASS |
| `cpy.pyx` mirrors blur logic | `grep -n "GaussianBlur\|blur_radius\|ImageFilter" cpy.pyx` | 4 matches | PASS |
| `settings.html` has blur_radius slider | `grep -n "blur_radius" templates/settings.html` | 5 lines (label, input, output, reset ×2) | PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| BG-01 | 09-01, 09-02, 09-03 | fit mode returns exact display dimensions (1200×1600) regardless of input image ratio | SATISFIED | `test_fit_output_dimensions_portrait` and `test_fit_output_dimensions_landscape` pass |
| BG-02 | 09-01, 09-02, 09-03 | fit mode background pixels are non-white (blur applied to letterbox/pillarbox area) | SATISFIED | `test_fit_background_not_white` passes — pixel at (0,0) is non-white |
| BG-03 | 09-01, 09-02, 09-03 | fill mode is completely unaffected by blur changes | SATISFIED | `test_fill_mode_unchanged` passes; fill branch untouched in code |
| BG-04 | 09-01, 09-02, 09-03 | fit-width sub-case (portrait image) — pillarbox bars not white | SATISFIED | `test_fit_width_subcase` passes — pixel at (0, 800) is non-white |
| BG-05 | 09-01, 09-02, 09-03 | fit-height sub-case (landscape image) — letterbox bars not white | SATISFIED | `test_fit_height_subcase` passes — pixel at (600, 0) is non-white |
| BG-06 | 09-01, 09-02, 09-03 | load_scaled accepts blur_radius kwarg; different radii produce different blurred output | SATISFIED | `test_blur_radius_config` passes with gradient image; `pixel_low != pixel_high` holds |

All 6 requirements satisfied across all 3 plans. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No stubs, placeholders, or hollow implementations detected. The fit branch produces real blurred pixels derived from the input image. The fill branch is unmodified from prior phase.

---

### Human Verification

One item was already approved by a human during plan execution:

**Visual Blur Quality (Plan 03 checkpoint — approved 2026-06-07)**
Already approved during Phase 9 Plan 03 execution. Human confirmed:
- Blurred colorful background renders correctly in fit mode filling the entire 1200x1600 canvas
- Fill mode unaffected (full-bleed, no background bars)
- blur_radius slider visible in settings below Display Mode dropdown

No further human verification required.

---

### Gaps Summary

No gaps. All must-haves verified across all three levels (exists, substantive, wired) plus data-flow (Level 4). The one notable deviation from Plan 01 — BG-06 test updated to use `make_gradient_image` instead of a solid-color image — was correctly identified and auto-fixed during Plan 02 execution and is not a gap.

---

_Verified: 2026-06-07T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
