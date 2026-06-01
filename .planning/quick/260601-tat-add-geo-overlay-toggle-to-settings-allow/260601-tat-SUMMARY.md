---
phase: quick
plan: 260601-tat
subsystem: overlay-pipeline
tags: [geo-overlay, settings-ui, config, tdd]
dependency_graph:
  requires: [feature/geo-text phase 7 geo overlay pipeline]
  provides: [geo_overlay_enabled global, DEFAULT_CONFIG entry, update_app_config wiring, POST handler, scale_img_in_memory guard, settings.html toggle]
  affects: [app.py, templates/settings.html, tests/test_geo_overlay.py]
tech_stack:
  added: []
  patterns: [select on/off pattern (no checkbox), .get() fallback for backward compat, module-level global mirroring existing overlay globals]
key_files:
  created: []
  modified:
    - app.py
    - templates/settings.html
    - tests/test_geo_overlay.py
decisions:
  - geo_overlay_enabled defaults to True in DEFAULT_CONFIG — preserves existing behavior for all current deployments that have location data
  - .get() fallback in update_app_config uses True (not False) — backward compat with configs written before this toggle existed
  - POST handler maps 'off' default to False (form omits unchecked selects) — consistent with date_overlay_enabled pattern
  - parse_photo_location call is conditionally replaced with None in-line rather than skipping the call block — minimal code delta, no restructuring
metrics:
  duration: ~10 minutes
  completed: 2026-06-01
  tasks_completed: 2
  files_modified: 3
  tests_added: 3
  tests_total: 37
---

# Quick Task 260601-tat: Add geo_overlay_enabled Toggle Summary

**One-liner:** Independent `geo_overlay_enabled=True` toggle in config, pipeline, POST handler, and settings.html select that suppresses location text from the date/geo overlay without affecting the date display.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED  | Failing tests GEO-13/14/15 | f341d91 | tests/test_geo_overlay.py |
| 1    | geo_overlay_enabled config + pipeline guard | 4e9e5d1 | app.py |
| 2    | geo_overlay_enabled toggle in settings.html | 9fbaebe | templates/settings.html |

## What Was Built

### Task 1: app.py changes

Six touch-points mirroring the `date_overlay_enabled` pattern exactly:

1. `DEFAULT_CONFIG['immich']['geo_overlay_enabled'] = True` (line ~53)
2. Module-level global `geo_overlay_enabled = DEFAULT_CONFIG['immich']['geo_overlay_enabled']` (line ~307)
3. `geo_overlay_enabled,` added to `update_app_config` global declaration
4. `geo_overlay_enabled = new_config['immich'].get('geo_overlay_enabled', True)` in assignment block
5. `parse_photo_location(...)` guarded: `... if geo_overlay_enabled else None` in `scale_img_in_memory`
6. `'geo_overlay_enabled': request.form.get('geo_overlay_enabled', 'off') == 'on'` in POST handler

### Task 2: templates/settings.html changes

- Updated Date Overlay card description to: "Configure which information appears on the image. Enable the date and/or location overlay below."
- Added "Show Location" `<select>` form-group immediately after the `date_overlay_enabled` form-group
- Jinja2 default is `true` (Jinja2 lowercase boolean), matching server default True

## Test Results

- 3 new tests: GEO-13 (geo disabled → date only), GEO-14 (geo enabled → full overlay), GEO-15 (missing key defaults to True)
- Full suite: **37 passed, 0 failed**
- No regressions in test_date_overlay.py, test_overlay_customization.py, or existing GEO-01..GEO-12

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- app.py modified: confirmed (4e9e5d1)
- templates/settings.html modified: confirmed (9fbaebe)
- tests/test_geo_overlay.py modified: confirmed (f341d91)
- Commits exist: f341d91, 4e9e5d1, 9fbaebe — all verified in git log
