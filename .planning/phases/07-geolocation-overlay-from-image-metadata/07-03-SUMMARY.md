---
phase: 07-geolocation-overlay-from-image-metadata
plan: 03
subsystem: geolocation
tags: [geolocation, overlay, scale_img_in_memory, immich, settings-ui, tdd]

# Dependency graph
requires:
  - phase: 07-01
    provides: test contracts GEO-09..GEO-12 (scale_img integration tests)
  - phase: 07-02
    provides: parse_photo_location, extract_gps_from_exif, reverse_geocode_cached

provides:
  - scale_img_in_memory(immich_exif_raw=None) — extended signature with geo+date fallback chain
  - serve_immich_image wiring — passes immich_exif_raw=selected_image.get('exifInfo', {})
  - settings.html Date Overlay section — static note explaining location alongside date

affects:
  - app.py (scale_img_in_memory signature + overlay block; serve_immich_image call site)
  - templates/settings.html (static location note in Date Overlay card)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pre_transpose_image captured before ImageOps.exif_transpose for GPS EXIF read safety"
    - "D-19 fallback chain: geo+date -> bullet string, geo-only, date-only, or hidden"
    - "bullet separator: U+2022 with single spaces ' • '"

# Key files
key-files:
  modified:
    - app.py: scale_img_in_memory extended with immich_exif_raw param + D-19 overlay assembly; serve_immich_image passes immich_exif_raw
    - templates/settings.html: static location note added to Date Overlay card

# Decisions
decisions:
  - "pre_transpose_image = image captured before exif_transpose so GPS EXIF is safely readable from original image object (Pitfall from plan)"
  - "overlay_text assembly: f'{location_str} • {date_str}' uses U+2022 bullet with single spaces as per D-04"
  - "serve_immich_image passes selected_image.get('exifInfo', {}) — returns empty dict (not None) so parse_photo_location receives a consistent type"
  - "Settings note uses existing 'small-text' CSS class to match help-text styling in the page; no new controls (D-14), no new config keys (D-13)"

# Metrics
metrics:
  duration: "5 minutes"
  completed: "2026-06-01T18:52:03Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  tests_passing: 34
---

# Phase 7 Plan 03: Wire geo overlay into image pipeline — SUMMARY

**One-liner:** Wired parse_photo_location into scale_img_in_memory with D-19 fallback chain (geo+date bullet string, geo-only, date-only, or hidden) and passed immich_exif_raw from serve_immich_image.

## Objective

Wave 2 (integration GREEN): Connect the pure geo functions from Plan 02 to the actual rendering call site and Immich data flow, turning GEO-09..GEO-12 green. Extend `scale_img_in_memory()` signature, assemble the combined overlay text, wire `immich_exif_raw` from `serve_immich_image()`, and add a static note in the settings UI.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend scale_img_in_memory signature + overlay text assembly | d37c6a6 | app.py |
| 2 | Wire immich_exif_raw from serve_immich_image + settings UI note | 33825f0 | app.py, templates/settings.html |

## Implementation Details

### Task 1: scale_img_in_memory extension

- Added `immich_exif_raw=None` as the 6th keyword parameter (keyword-only with default — existing callers in test_date_overlay.py remain unaffected, Pitfall 6)
- Added `pre_transpose_image = image` capture before `ImageOps.exif_transpose(image)` to preserve original image reference for GPS EXIF reading
- Replaced the date-only overlay block with the D-19 fallback chain:
  - `parse_photo_location(local_image=pre_transpose_image, immich_exif=immich_exif_raw)` called first
  - Assembly: `f"{location_str} • {date_str}"` when both available, else `location_str` or `date_str` alone, or `None` (overlay hidden)
  - `draw_date_overlay` call unchanged in structure — same style/color/stroke params

### Task 2: serve_immich_image + settings.html

- `serve_immich_image` now passes `immich_exif_raw=selected_image.get('exifInfo', {})` alongside existing `immich_date_raw`
- `templates/settings.html` Date Overlay card gains a static `<p class="small-text">` note:  
  "When a photo includes location data (from Immich or GPS EXIF), the city and country are shown alongside the date, e.g. 'Munich, Germany • 05.01.2022'. If no location is available, only the date is shown."
- No new `<input>` or `<select>` controls added (D-14 honored)
- No new config keys (D-13 honored)

## Test Results

- GEO-09: scale_img renders 'Munich, Germany • 05.01.2022' when both available — PASS
- GEO-10: scale_img renders date-only when no geo — PASS
- GEO-11: scale_img renders location-only when no date — PASS
- GEO-12: overlay hidden when neither geo nor date — PASS
- All 12 GEO tests: PASS
- Full suite: 34 passed, 0 failed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All data flows are wired: local GPS via extract_gps_from_exif → reverse_geocode_cached → parse_photo_location; Immich geo via exifInfo dict → parse_photo_location; both paths reach draw_date_overlay through scale_img_in_memory.

## Self-Check: PASSED
