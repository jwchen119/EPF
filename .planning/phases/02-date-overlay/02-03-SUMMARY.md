---
phase: "02-date-overlay"
plan: "03"
subsystem: image-processing
tags: [python, pillow, flask, settings-ui, tdd, date-overlay, config]

dependency_graph:
  requires:
    - phase: 02-02
      provides: "parse_photo_date(), POSITIONS, draw_date_overlay() in app.py"
  provides:
    - "date_overlay_enabled / date_overlay_position in DEFAULT_CONFIG and module globals"
    - "scale_img_in_memory with immich_date_raw kwarg and overlay pipeline"
    - "Date Overlay card in settings.html (enable toggle + 9-position select)"
    - "settings() POST handler wires both overlay fields to config.yaml"
  affects:
    - "All 9 Wave 0 tests now GREEN"
    - "End-to-end overlay: config.yaml <-> settings UI <-> rendered image"

tech-stack:
  added: []
  patterns:
    - "module globals updated via update_app_config() with .get() fallback for backward compat"
    - "overlay behind flag: date_overlay_enabled guard -> parse -> draw (silently absent when no date)"
    - "Jinja2 .get() with defaults in template selects to handle old config.yaml files"

key-files:
  created: []
  modified:
    - "app.py"
    - "templates/settings.html"

key-decisions:
  - "Use .get('date_overlay_enabled', False) in update_app_config to not break existing deployments with old config.yaml"
  - "date_overlay_enabled select uses value='off'/'on' (not checkbox) to avoid unchecked-field omission in HTML form POST"
  - "EXIF extraction kept as date_time_raw fallback inside scale_img_in_memory for local image path (serve_local_image unchanged)"
  - "Dead draw_text_with_background nested function removed entirely (-125 lines of dead code)"

requirements:
  - DO-01
  - DO-03
  - DO-05

metrics:
  duration: "~3 minutes"
  completed: "2026-05-27"
  tasks_completed: 3
  tasks_total: 3
  files_created: 0
  files_modified: 2
---

# Phase 02 Plan 03: Wire Overlay into Pipeline + Settings UI Summary

**One-liner:** Date overlay wired end-to-end — DEFAULT_CONFIG keys, module globals, scale_img_in_memory pipeline, serve_immich_image date pass-through, settings UI card, and POST handler; 9/9 Wave 0 tests GREEN.

## What Was Built

Closed the final 3 failing Wave 0 tests by wiring Plan 02's pure helpers into the full request pipeline:

- `DEFAULT_CONFIG['immich']` now contains `date_overlay_enabled: False` and `date_overlay_position: 'bottomRight'`
- Module-level globals `date_overlay_enabled` and `date_overlay_position` initialized from config and updated by `update_app_config()` with `.get()` fallback for old config.yaml files
- `scale_img_in_memory` signature extended with `immich_date_raw=None`; overlay block inserted after dithering with silent-absent behaviour when flag is off or date is unavailable
- Dead `draw_text_with_background` nested function (120+ lines) and its commented-out call deleted
- `serve_immich_image` extracts `exifInfo.dateTimeOriginal` and forwards it to `scale_img_in_memory`
- `templates/settings.html` gains a "Date Overlay" card with an On/Off select and 9-position select
- `settings()` POST handler reads both fields with proper defaults; `date_overlay_enabled` stored as Python bool via `== 'on'` comparison

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add config keys, globals, update_app_config wiring | ac859cb | app.py |
| 2 | Wire overlay into scale_img_in_memory, remove dead code | b494eac | app.py |
| 3 | Date Overlay card in settings UI + POST handler | 84b1dd0 | templates/settings.html, app.py |

## Verification Results

- `pytest tests/test_date_overlay.py -v` — 9 passed, 0 failed
- `grep -c "draw_text_with_background" app.py` — 0
- `python -c "import app; print(app.date_overlay_enabled, app.date_overlay_position)"` — `False bottomRight`
- `python -m py_compile app.py` — exits 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all overlay functionality is fully wired. The overlay is intentionally off by default (D-01 requirement). Manual visual verification on-device remains (per VALIDATION.md) but is not a code stub.

## Self-Check: PASSED

- Commit ac859cb (Task 1): FOUND
- Commit b494eac (Task 2): FOUND
- Commit 84b1dd0 (Task 3): FOUND
- All 9 Wave 0 tests GREEN: VERIFIED
- `draw_text_with_background` references: 0 (dead code removed)
- `date_overlay_enabled` global exports `False`: VERIFIED
- Settings HTML has Date Overlay card: VERIFIED
