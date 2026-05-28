---
phase: 02-date-overlay
verified: 2026-05-27T12:00:00Z
status: passed
score: 7/7 must-haves verified
---

# Phase 2: Date Overlay Verification Report

**Phase Goal:** Extract the date a photo was taken (from Immich API metadata or file EXIF) and render it as a configurable text overlay on the processed image. The overlay position (9 alignments: topLeft, topCenter, topRight, centerLeft, center, centerRight, bottomLeft, bottomCenter, bottomRight) must be configurable via config.yaml and the web settings UI.
**Verified:** 2026-05-27
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                        | Status     | Evidence                                                                                      |
|----|----------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| 1  | EXIF date string 'YYYY:MM:DD HH:MM:SS' is parsed to 'DD.MM.YYYY'                            | VERIFIED   | `parse_photo_date` at app.py:50; test_parse_exif_date passes                                 |
| 2  | Immich ISO 8601 date 'YYYY-MM-DDTHH:MM:SS.sssZ' is parsed to 'DD.MM.YYYY'                   | VERIFIED   | `parse_photo_date` handles '-' separator at index 4; test_parse_immich_date passes            |
| 3  | None/empty/unparseable input returns None (no crash, no placeholder)                         | VERIFIED   | Guard clause at app.py:58; test_parse_none passes                                             |
| 4  | draw_date_overlay renders a black rectangle and white text in the chosen position             | VERIFIED   | `draw_date_overlay` at app.py:90, uses ImageDraw.Draw + textbbox; test_draw_overlay_renders passes |
| 5  | All 9 position strings map to distinct pixel regions without raising                         | VERIFIED   | POSITIONS dict at app.py:77 with all 9 lambdas; test_position_topleft + test_position_bottomright pass |
| 6  | Overlay is disabled by default and hidden when enabled but no date is available               | VERIFIED   | DEFAULT_CONFIG sets `date_overlay_enabled: False`; `if date_overlay_enabled` guard at app.py:321; test_overlay_disabled + test_overlay_no_date pass |
| 7  | Settings UI exposes enable toggle and 9-position select; POST persists them to config         | VERIFIED   | settings.html lines 460-480; settings POST handler at app.py:577-578; update_app_config at app.py:478-479 |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact                   | Expected                                                          | Status     | Details                                                                              |
|----------------------------|-------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------|
| `tests/__init__.py`        | Python package marker for tests/                                  | VERIFIED   | File exists (empty)                                                                  |
| `tests/conftest.py`        | Shared PIL image fixtures for overlay tests                       | VERIFIED   | Contains blank_rgb_image, large_rgb_image, dejavu_or_default_font fixtures           |
| `tests/test_date_overlay.py` | 9 tests covering DO-01..DO-05                                  | VERIFIED   | 9 tests collected and all passing                                                    |
| `requirements.txt`         | pytest dev dependency listed                                      | VERIFIED   | Contains `pytest` line                                                               |
| `app.py`                   | parse_photo_date, draw_date_overlay, POSITIONS, config keys, wiring | VERIFIED | All functions and globals present; correctly wired into scale_img_in_memory          |
| `templates/settings.html`  | Date Overlay card with toggle and 9-option position select        | VERIFIED   | Lines 460-480; "Date Overlay" heading, name="date_overlay_enabled", name="date_overlay_position" with 9 options |

---

### Key Link Verification

| From                             | To                                      | Via                                                | Status     | Details                                               |
|----------------------------------|-----------------------------------------|----------------------------------------------------|------------|-------------------------------------------------------|
| `tests/test_date_overlay.py`     | `app.parse_photo_date, app.draw_date_overlay` | `from app import`                            | WIRED      | Import in each test function; all 9 tests pass        |
| `app.draw_date_overlay`          | `PIL.ImageDraw`                         | `ImageDraw.Draw(output_img)`                       | WIRED      | app.py:103                                            |
| `app.scale_img_in_memory`        | `app.parse_photo_date, app.draw_date_overlay` | direct call after `Image.fromarray`           | WIRED      | app.py:321-329; `draw_date_overlay(output_img, ...)` |
| `app.serve_immich_image`         | `app.scale_img_in_memory`               | `scale_img_in_memory(image, immich_date_raw=...)` | WIRED      | app.py:767-768; passes `exifInfo.dateTimeOriginal`    |
| `templates/settings.html`        | `app.settings` POST handler             | form fields `date_overlay_enabled` and `date_overlay_position` | WIRED | app.py:577-578; `request.form.get(...)` reads both fields |

---

### Data-Flow Trace (Level 4)

| Artifact                        | Data Variable         | Source                                                      | Produces Real Data | Status    |
|---------------------------------|-----------------------|-------------------------------------------------------------|--------------------|-----------|
| `app.scale_img_in_memory`       | `immich_date_raw`     | `selected_image.get('exifInfo', {}).get('dateTimeOriginal')` (Immich API) | Yes, from live API call | FLOWING |
| `app.scale_img_in_memory`       | `date_time_raw`       | `image._getexif()` then `exif.get(36867)` (PIL EXIF)       | Yes, from image file EXIF | FLOWING |
| `app.scale_img_in_memory`       | `date_overlay_enabled` | Module global, set from config via `update_app_config()`   | Real config value  | FLOWING   |
| `templates/settings.html`       | `config['immich']['date_overlay_enabled']` | `current_config` passed by Flask render_template | Real runtime config | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                      | Command                                                                                    | Result              | Status  |
|-----------------------------------------------|--------------------------------------------------------------------------------------------|---------------------|---------|
| All 9 date overlay tests pass                 | `python -m pytest tests/test_date_overlay.py -v`                                          | 9 passed, 0 failed  | PASS    |
| parse_photo_date returns correct value        | `python -c "import sys; sys.path.insert(0, '.'); import app; print(app.parse_photo_date('2022:01:05 14:30:00'))"` | `05.01.2022` | PASS |
| Module globals have correct defaults          | `python -c "import sys; sys.path.insert(0, '.'); import app; print(app.date_overlay_enabled, app.date_overlay_position)"` | `False bottomRight` | PASS |
| POSITIONS dict has all 9 entries             | `python -c "import sys; sys.path.insert(0, '.'); import app; print(len(app.POSITIONS))"` | `9` | PASS |
| Dead code removed                             | `grep -c "draw_text_with_background" app.py`                                              | `0`                 | PASS    |
| app.py compiles without errors                | `python -m py_compile app.py`                                                             | exit 0              | PASS    |

---

### Requirements Coverage

No `REQUIREMENTS.md` file exists in `.planning/`. Requirements are declared inline in plan frontmatter and ROADMAP.md. Coverage is assessed by mapping requirement IDs to test and code evidence.

| Requirement | Source Plans         | Description                                                              | Status    | Evidence                                                             |
|-------------|----------------------|--------------------------------------------------------------------------|-----------|----------------------------------------------------------------------|
| DO-01       | 02-01, 02-02, 02-03  | Parse photo date from EXIF ('YYYY:MM:DD HH:MM:SS') and Immich ISO 8601  | SATISFIED | `parse_photo_date()` at app.py:50; 3 parse tests pass; both paths wired in `scale_img_in_memory` |
| DO-02       | 02-01, 02-02         | Render date as text overlay on processed image (white text, black rect)  | SATISFIED | `draw_date_overlay()` at app.py:90; test_draw_overlay_renders verifies black pixels rendered |
| DO-03       | 02-01, 02-03         | Overlay disabled by default; silently hidden when no date available       | SATISFIED | `DEFAULT_CONFIG['immich']['date_overlay_enabled'] = False`; guard at app.py:321; test_overlay_disabled + test_overlay_no_date pass |
| DO-04       | 02-01, 02-02         | 9 configurable overlay positions                                          | SATISFIED | `POSITIONS` dict at app.py:77 with all 9 lambdas; test_position_topleft + test_position_bottomright verify correct placement |
| DO-05       | 02-01, 02-03         | Position configurable via config.yaml and web settings UI                 | SATISFIED | `DEFAULT_CONFIG` has `date_overlay_position: 'bottomRight'`; settings.html has 9-option select; POST handler reads and persists value |

All 5 requirements (DO-01 through DO-05) are satisfied.

---

### Anti-Patterns Found

| File   | Line | Pattern                                                  | Severity | Impact  |
|--------|------|----------------------------------------------------------|----------|---------|
| app.py | 684  | `scale_img_in_memory(image)` — no `immich_date_raw` kwarg passed from `serve_local_image` | INFO | Not a bug: local images use the internal EXIF fallback path (`date_time_raw` via `image._getexif()`), which is correct. The overlay will use the file's own EXIF data. |

No blockers or warnings found. The one noted item is intentional design (local path uses EXIF, Immich path passes the API date explicitly).

---

### Human Verification Required

#### 1. Visual overlay appearance on device

**Test:** Enable date_overlay_enabled in settings UI, set a position, trigger an image fetch from Immich, observe the e-paper display.
**Expected:** Date rendered as white text on black background rectangle in the configured corner/position, in DD.MM.YYYY format.
**Why human:** Cannot verify pixel rendering on physical e-paper display programmatically.

#### 2. Settings UI persistence across reload

**Test:** Open /settings, enable Date Overlay, select a non-default position (e.g., topLeft), save, reload the page.
**Expected:** The saved values are reflected as selected options in both selects after the page reload.
**Why human:** Requires a running Flask server and browser interaction to verify Jinja2 template rendering with saved config values.

#### 3. Config round-trip with missing keys (backward compatibility)

**Test:** Use an existing config.yaml that does NOT contain `date_overlay_enabled` or `date_overlay_position`, start the app.
**Expected:** App starts without KeyError; overlay defaults to disabled with bottomRight position.
**Why human:** `.get(key, default)` guards exist in code (app.py:478-479) but the actual old-config scenario requires a real config file to test safely.

---

### Gaps Summary

No gaps. All must-haves are verified at all four levels (exists, substantive, wired, data-flowing). All 9 automated tests pass. All 5 requirement IDs (DO-01 through DO-05) are satisfied by concrete, non-stub implementations. Dead code (`draw_text_with_background`) is confirmed removed. Three items are flagged for human verification (visual display output, UI persistence, backward compatibility with old configs) but none block automated goal achievement.

---

_Verified: 2026-05-27_
_Verifier: Claude (gsd-verifier)_
