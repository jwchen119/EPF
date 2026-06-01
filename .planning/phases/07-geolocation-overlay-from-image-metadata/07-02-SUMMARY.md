---
phase: 07-geolocation-overlay-from-image-metadata
plan: 02
subsystem: geolocation
tags: [geopy, nominatim, gps, exif, geocoding, caching, tdd]

# Dependency graph
requires:
  - phase: 07-01
    provides: test contracts GEO-01..GEO-08, synthetic_gps_image, mock_geo_cache_dir fixtures

provides:
  - extract_gps_from_exif(image) — DMS to decimal, float() cast, None-safe
  - reverse_geocode_cached(lat, lon) — JSON cache + Nominatim, null-caches on failure
  - parse_photo_location(local_image, immich_exif) — Immich-first, local GPS fallback
  - _geo_cache_path(), _load_geo_cache(), _save_geo_cache() — persistent cache helpers
  - geopy==2.4.1 in requirements.txt

affects:
  - 07-03-PLAN.md (wires parse_photo_location into scale_img_in_memory)

# Tech tracking
tech-stack:
  added:
    - geopy==2.4.1 (Nominatim reverse geocoding)
  patterns:
    - "float() cast on DMS IFDRational values before arithmetic (Pitfall 2 from research)"
    - "Module-level _GEO_CACHE=None lazily loaded; reset via monkeypatch in tests"
    - "Cache key: f-string of round(float(lat),3),round(float(lon),3)"
    - "Nominatim instantiated inside function only, never at module level"

key-files:
  created: []
  modified:
    - requirements.txt — added geopy==2.4.1
    - app.py — added import json, geopy imports, _GEO_CACHE, extract_gps_from_exif, _geo_cache_path, _load_geo_cache, _save_geo_cache, reverse_geocode_cached, parse_photo_location

key-decisions:
  - "float() cast applied to each DMS component — handles Pillow IFDRational type that doesn't support direct division (D-15 Pitfall 2)"
  - "Cache key uses round(float(lat),3)/round(float(lon),3) per D-12; round(48.1351,3)==48.135 and round(10.0,3)==10.0 match test expectations"
  - "Nominatim instantiated inside reverse_geocode_cached only — monkeypatching app.Nominatim works correctly (GEO-07/GEO-08)"
  - "parse_photo_location uses 'or empty-string' guard for empty Immich strings (Pitfall 4) — empty string is falsy, treated same as None"
  - "Merged feature/geo-text into worktree branch before execution to obtain Plan 01 test fixtures"

# Metrics
duration: 8min
completed: 2026-06-01
---

# Phase 7 Plan 02: Geolocation Overlay — TDD GREEN Pure Logic Summary

**GPS extraction + Nominatim reverse geocoding with persistent JSON cache using geopy==2.4.1; extract_gps_from_exif, reverse_geocode_cached, and parse_photo_location implemented against locked GEO-01..GEO-08 contracts**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-01T18:38:00Z
- **Completed:** 2026-06-01T18:46:45Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `geopy==2.4.1` to `requirements.txt` and `import json`, `from geopy.geocoders import Nominatim`, `from geopy.exc import GeocoderServiceError, GeocoderTimedOut` to `app.py`
- Implemented `extract_gps_from_exif(image)` with float() cast on IFDRational DMS values, handles missing GPS tag and no-exif gracefully (GEO-01, 02, 03)
- Implemented `_geo_cache_path()`, `_load_geo_cache()`, `_save_geo_cache()` for persistent JSON geocache in `IMMICH_PHOTO_DEST` directory
- Implemented `reverse_geocode_cached(lat, lon)` with cache-first lookup, Nominatim on miss, null-caches failures (GEO-07, 08)
- Implemented `parse_photo_location(local_image, immich_exif)` with Immich exifInfo priority and local GPS fallback (GEO-04, 05, 06)
- 8 of 12 GEO tests now pass; GEO-09..12 remain RED (wired in Plan 03 — expected)
- No regression: 22 existing tests in test_date_overlay.py and test_overlay_customization.py still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add geopy to requirements.txt and import Nominatim + json** - `b6e0b41` (chore)
2. **Task 2: Implement extract_gps_from_exif, geo cache helpers, reverse_geocode_cached** - `f9869ac` (feat)
3. **Task 3: Implement parse_photo_location** - `5f51e2b` (feat)

## Files Created/Modified

- `requirements.txt` — Added `geopy==2.4.1` between pillow_heif and PyYAML
- `app.py` — Added 103 lines: geopy/json imports + 3 functions + 3 helpers + `_GEO_CACHE` var, placed in "Geolocation helpers" section after `parse_photo_date`

## Decisions Made

- `float()` cast applied to each DMS component before arithmetic — handles Pillow `IFDRational` type that doesn't support direct division without explicit cast (D-15, Pitfall 2 from research)
- Cache key `f"{round(float(lat), 3)},{round(float(lon), 3)}"` — `round(48.1351, 3) == 48.135`, `round(10.0, 3) == 10.0`, both match GEO-07/GEO-08 test expectations (D-12)
- `Nominatim` imported at module level so `monkeypatch.setattr(app, 'Nominatim', ...)` works in tests, but instantiated inside `reverse_geocode_cached` only (no module-level instantiation per RESEARCH anti-pattern)
- `parse_photo_location` uses `immich_exif.get('city') or ''` — treats empty strings as missing (Pitfall 4); both `{'city':'','country':''}` and `{}` correctly return `None`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Merged feature/geo-text into worktree before execution**
- **Found during:** Pre-task setup
- **Issue:** Worktree branch `worktree-agent-aa912ec081a1c9436` was based on `592622b` (before Plan 01 commits), missing `tests/test_geo_overlay.py` and the new fixtures in `tests/conftest.py`
- **Fix:** Ran `git merge feature/geo-text` to fast-forward the worktree branch and include Plan 01's artifacts
- **Files modified:** tests/conftest.py, tests/test_geo_overlay.py, .planning/ phase files
- **Commit:** Absorbed via fast-forward merge (merge commit `b975974`)

## Known Stubs

None — all functions return real values from EXIF data, Nominatim, or cached results. No hardcoded data flows.

## Self-Check: PASSED

- `requirements.txt` contains `geopy==2.4.1`: confirmed
- `app.py` contains `def extract_gps_from_exif`, `def reverse_geocode_cached`, `def parse_photo_location`: confirmed
- Commits b6e0b41, f9869ac, 5f51e2b exist in git log: confirmed
- 8 GEO tests pass: confirmed
- 22 regression tests pass: confirmed

---
*Phase: 07-geolocation-overlay-from-image-metadata*
*Completed: 2026-06-01*
