---
phase: 07-geolocation-overlay-from-image-metadata
plan: 01
subsystem: testing
tags: [pytest, pillow, exif, gps, geopy, nominatim, tdd]

# Dependency graph
requires:
  - phase: 06-text-customization-colors-styles-and-border-mode
    provides: draw_date_overlay() extended signature, OVERLAY_COLORS dict, config globals

provides:
  - 12 failing contract tests (GEO-01..GEO-12) in tests/test_geo_overlay.py
  - synthetic_gps_image fixture (PIL Image with GPSInfo EXIF for Munich 48.1351N, 11.5820E)
  - mock_geo_cache_dir fixture (isolated cache dir via IMMICH_PHOTO_DEST + _GEO_CACHE reset)

affects:
  - 07-02-PLAN.md (implements extract_gps_from_exif, parse_photo_location, reverse_geocode_cached)
  - 07-03-PLAN.md (wires immich_exif_raw into scale_img_in_memory and serve_immich_image)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED: import target functions inside test body so collection succeeds before implementation exists"
    - "_getexif monkeypatching via lambda for PIL fixture control"
    - "IMMICH_PHOTO_DEST + _GEO_CACHE monkeypatching for isolated cache tests"

key-files:
  created:
    - tests/test_geo_overlay.py
  modified:
    - tests/conftest.py

key-decisions:
  - "Fixture monkeypatches _getexif with lambda returning exif_dict — avoids piexif dependency while giving full control over sub-tag structure"
  - "mock_geo_cache_dir resets app._GEO_CACHE to None via monkeypatch.setattr to prevent test isolation issues with module-level cache"
  - "Cache key for GEO-07/08 uses round(lat,3)/round(lon,3) per D-12 — tests use 48.135,11.582 and 10.0,20.0 as expected keys"

patterns-established:
  - "Pattern: import inside test body (from app import X) — collection survives ImportError until implementation exists"
  - "Pattern: monkeypatch.setattr(app, 'parse_photo_location', lambda **k: ...) for scale_img_in_memory integration tests"

requirements-completed: [GEO-01, GEO-02, GEO-03, GEO-04, GEO-05, GEO-06, GEO-07, GEO-08, GEO-09, GEO-10, GEO-11, GEO-12]

# Metrics
duration: 2min
completed: 2026-06-01
---

# Phase 7 Plan 01: Geolocation Overlay — TDD RED Contract Tests Summary

**12 failing contract tests locking extract_gps_from_exif, parse_photo_location, reverse_geocode_cached, and immich_exif_raw signatures before any implementation exists**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-01T18:38:40Z
- **Completed:** 2026-06-01T18:40:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `synthetic_gps_image` and `mock_geo_cache_dir` fixtures to `tests/conftest.py` (5 fixtures total)
- Created `tests/test_geo_overlay.py` with 12 contract tests covering GEO-01..GEO-12
- Confirmed RED: all 12 tests fail with `ImportError: cannot import name 'extract_gps_from_exif'`
- Confirmed no regression: existing 22 tests (test_date_overlay.py + test_overlay_customization.py) pass unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Add synthetic_gps_image and mock_geo_cache_dir fixtures to conftest.py** - `fb616ff` (test)
2. **Task 2: Write 12 failing contract tests in tests/test_geo_overlay.py** - `0754bc1` (test)

## Files Created/Modified

- `tests/conftest.py` — Appended synthetic_gps_image (Munich GPS EXIF stub) and mock_geo_cache_dir (IMMICH_PHOTO_DEST isolation) fixtures
- `tests/test_geo_overlay.py` — 12 GEO contract tests; all fail until Plans 02/03 implement the target functions

## Decisions Made

- Fixture monkeypatches `_getexif` with lambda returning dict — avoids piexif dependency while giving full control over GPSInfo sub-tag structure (1=LatRef, 2=Lat DMS, 3=LonRef, 4=Lon DMS)
- `mock_geo_cache_dir` resets `app._GEO_CACHE` to `None` via `monkeypatch.setattr` to prevent test isolation issues from the module-level lazy-loaded cache dict
- Cache key assertions in GEO-07/08 use `round(lat,3)/round(lon,3)` per D-12: `48.135,11.582` and `10.0,20.0`
- Integration tests (GEO-09..GEO-12) monkeypatch `app.parse_photo_location` with `lambda **k: ...` to avoid geocoder network calls

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 can now implement `extract_gps_from_exif()`, `parse_photo_location()`, `reverse_geocode_cached()` in `app.py` against locked contracts
- Plan 03 can wire `immich_exif_raw=None` into `scale_img_in_memory()` and `serve_immich_image()`
- `geopy==2.4.1` must be added to `requirements.txt` in Plan 02 (GEO-07/08 tests monkeypatch `app.Nominatim` directly)

---
*Phase: 07-geolocation-overlay-from-image-metadata*
*Completed: 2026-06-01*
