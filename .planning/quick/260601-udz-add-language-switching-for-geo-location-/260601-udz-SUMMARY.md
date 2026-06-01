---
phase: quick-260601-udz
plan: 01
subsystem: geo-overlay
tags: [geo, language, nominatim, cache, settings]
dependency_graph:
  requires: [feature/geo-text geo overlay foundation]
  provides: [overlay_language config key, language-aware reverse_geocode_cached, settings Language dropdown]
  affects: [app.py, templates/settings.html, tests/test_geo_overlay.py]
tech_stack:
  added: []
  patterns: [language-suffixed cache key, module global for language setting]
key_files:
  created: []
  modified:
    - app.py
    - templates/settings.html
    - tests/test_geo_overlay.py
decisions:
  - overlay_language global read inside reverse_geocode_cached (no signature change) preserves all existing call-site contracts (GEO-06, parse_photo_location)
  - Cache key format is 'lat,lon:lang' (e.g. '48.135,11.582:en') — ':lang' suffix appended to existing coordinate string ensures backward-incompatible keys fail fast on old caches rather than returning wrong-language results
  - .get('overlay_language', 'en') fallback in update_app_config and POST handler ensures old config.yaml files without the key continue to work
  - Immich-supplied city/country strings are NOT re-translated; caveat documented in settings help text per plan objective
metrics:
  duration: ~15 minutes
  completed: "2026-06-01T19:59:00Z"
  tasks_completed: 2
  files_modified: 3
---

# Quick Task 260601-udz: Add Language Switching for Geo-Location — SUMMARY

**One-liner:** Language-aware Nominatim reverse geocoding with per-language cache keying and English/Deutsch settings dropdown.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (TDD RED) | Failing tests GEO-07/08 update + GEO-LANG-01/02 | e3e7618 | tests/test_geo_overlay.py |
| 1 (TDD GREEN) | Make reverse_geocode_cached language-aware | ec30143 | app.py |
| 2 | Wire overlay_language through config and settings UI | f8e9669 | app.py, templates/settings.html |

## What Was Built

### app.py changes

- Added `'overlay_language': 'en'` to `DEFAULT_CONFIG['immich']` (with `# 'en' | 'de'` comment)
- Added `overlay_language = DEFAULT_CONFIG['immich']['overlay_language']` to the module-level global init block (line ~316)
- Rewrote `reverse_geocode_cached` to use language-suffixed cache key `f'{round(float(lat),3)},{round(float(lon),3)}:{overlay_language}'` and pass `language=overlay_language` to `geolocator.reverse()`
- Added `overlay_language` to `update_app_config()` global declaration and assigned `new_config['immich'].get('overlay_language', 'en')`
- Added `overlay_language` to POST handler config dict with `request.form.get('overlay_language', current_config['immich'].get('overlay_language', 'en'))`

### templates/settings.html changes

- Added "Location Language" `<select>` dropdown with English/Deutsch options after the "Show Location" form-group
- Uses `config['immich'].get('overlay_language', 'en')` for selected-state rendering
- Help text notes that Immich-supplied place names are not re-translatable here

### tests/test_geo_overlay.py changes

- Updated GEO-07 cache seed key from `'48.135,11.582'` to `'48.135,11.582:en'`
- Updated GEO-08 assertion key from `'10.0,20.0'` to `'10.0,20.0:en'`
- Added GEO-LANG-01: verifies `overlay_language='de'` is passed as `language='de'` to Nominatim and result stored under `'48.135,11.582:de'` key
- Added GEO-LANG-02: verifies `'en'`-keyed cache entry is NOT returned when `overlay_language='de'` — Nominatim is called for a fresh lookup

## Verification Results

```
python -m pytest tests/test_geo_overlay.py -q
.................
17 passed in 0.85s

grep -n "language=overlay_language" app.py
162:        location = geolocator.reverse((lat, lon), exactly_one=True, language=overlay_language)

cache key line:
155:    key = f'{round(float(lat), 3)},{round(float(lon), 3)}:{overlay_language}'

grep -q overlay_language templates/settings.html
OK
```

## Deviations from Plan

None — plan executed exactly as written. Merging `feature/geo-text` into the worktree branch was a required prerequisite (geo overlay foundation was on a separate branch) handled automatically before task execution.

## Known Stubs

None. The `overlay_language` config key is fully wired end-to-end: DEFAULT_CONFIG to module global to update_app_config to POST handler to settings.html dropdown.

## Self-Check: PASSED

- `tests/test_geo_overlay.py` — modified, 17 tests pass
- `app.py` — modified, AST clean
- `templates/settings.html` — modified, contains `overlay_language`
- Commits e3e7618, ec30143, f8e9669 exist in git log
