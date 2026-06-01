---
phase: 07-geolocation-overlay-from-image-metadata
verified: 2026-06-01T19:10:00Z
status: passed
score: 12/12 must-haves verified
re_verification: null
gaps: []
human_verification:
  - test: "Live photo with Immich exifInfo containing city/country displays 'City, Country • DD.MM.YYYY' on e-paper"
    expected: Overlay renders the combined geo+date string on the actual frame display
    why_human: Requires running Immich, live image fetch, and visual inspection of e-paper output
  - test: "Local JPEG with real GPS EXIF produces a Nominatim reverse-geocode call and geo_cache.json is written"
    expected: geo_cache.json appears in IMMICH_PHOTO_DEST with a JSON entry mapping rounded lat/lon to 'City, Country'
    why_human: Requires a real GPS-tagged JPEG file and Nominatim network access; cannot verify without live environment
  - test: "Settings page Date Overlay card shows the static location note"
    expected: The note 'When a photo includes location data...' is visible in the UI below the date overlay controls
    why_human: Visual UI inspection; functional content confirmed programmatically but rendering context requires human
---

# Phase 7: Geolocation Overlay from Image Metadata — Verification Report

**Phase Goal:** Overlay the photo's geolocation (city, country) alongside the date on the photo frame display, sourcing location from Immich exifInfo or local GPS EXIF metadata.
**Verified:** 2026-06-01T19:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | extract_gps_from_exif(image) returns (lat, lon) for geotagged images and None otherwise | VERIFIED | app.py:96-120; GEO-01,02,03 pass |
| 2 | reverse_geocode_cached reads geo_cache.json before any network call and null-caches failures | VERIFIED | app.py:147-168; GEO-07,08 pass |
| 3 | parse_photo_location returns 'City, Country' from Immich exifInfo first, then local GPS fallback | VERIFIED | app.py:170-192; GEO-04,05,06 pass |
| 4 | scale_img_in_memory renders 'City, Country • DD.MM.YYYY' when both geo and date are available | VERIFIED | app.py:528-548; GEO-09 pass |
| 5 | scale_img_in_memory renders date-only when no geo, location-only when no date, hides overlay when neither | VERIFIED | app.py:530-536; GEO-10,11,12 pass |
| 6 | serve_immich_image passes immich_exif_raw so Immich city/country reach the overlay | VERIFIED | app.py:1063 passes selected_image.get('exifInfo', {}) |
| 7 | Settings UI Date Overlay section has a static note explaining location alongside date | VERIFIED | templates/settings.html:461 contains note with 'location' and Munich example |
| 8 | geopy is declared in requirements.txt at version 2.4.1 | VERIFIED | requirements.txt contains geopy==2.4.1 |
| 9 | All 12 GEO contract tests pass; no regression in existing 22 tests | VERIFIED | pytest tests/ → 34 passed, 0 failed |

**Score:** 9/9 observable truths verified (covers all 12 requirement IDs)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_geo_overlay.py` | 12 contract tests GEO-01..GEO-12 | VERIFIED | 12 test functions confirmed; all pass |
| `tests/conftest.py` | synthetic_gps_image + mock_geo_cache_dir fixtures | VERIFIED | Both fixtures present; 5 fixtures total |
| `requirements.txt` | geopy==2.4.1 dependency | VERIFIED | Exact pin confirmed |
| `app.py` | extract_gps_from_exif, reverse_geocode_cached, parse_photo_location, geo cache helpers | VERIFIED | All 6 functions at lines 96-192 |
| `app.py` | extended scale_img_in_memory with immich_exif_raw + D-19 fallback assembly | VERIFIED | Signature at line 442; assembly at lines 528-548 |
| `app.py` | serve_immich_image wiring | VERIFIED | Lines 1062-1063 pass both immich_date_raw and immich_exif_raw |
| `templates/settings.html` | Static note about location in Date Overlay section | VERIFIED | Line 461; uses class="small-text"; contains 'location' and Munich example |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app.parse_photo_location | app.reverse_geocode_cached | local GPS path calls reverse_geocode_cached(lat, lon) | WIRED | app.py:190 confirmed |
| app.reverse_geocode_cached | geo_cache.json | json load/dump in IMMICH_PHOTO_DEST dir | WIRED | app.py:122-144 _geo_cache_path, _load_geo_cache, _save_geo_cache confirmed |
| app.reverse_geocode_cached | Nominatim | geopy reverse geocoding only on cache miss | WIRED | app.py:155 Nominatim instantiated inside function after cache check at line 151 |
| app.scale_img_in_memory | app.parse_photo_location | location_str = parse_photo_location(local_image=pre_transpose_image, immich_exif=immich_exif_raw) | WIRED | app.py:528 confirmed |
| app.serve_immich_image | app.scale_img_in_memory | immich_exif_raw=selected_image.get('exifInfo', {}) | WIRED | app.py:1063 confirmed |
| scale_img_in_memory assembly | draw_date_overlay | overlay_text passed when truthy | WIRED | app.py:536/546 confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| app.scale_img_in_memory | location_str | parse_photo_location → extract_gps_from_exif/reverse_geocode_cached or Immich exifInfo dict | Yes — real EXIF GPS or Immich exifInfo city/country; cache-backed for Nominatim | FLOWING |
| app.scale_img_in_memory | date_str | parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw from EXIF) | Yes — real EXIF date or Immich dateTimeOriginal | FLOWING |
| app.reverse_geocode_cached | result | Nominatim.reverse() → address.city/country; falls back to None with null-caching | Yes — real Nominatim geocoder result or cached result | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 12 GEO tests pass | pytest tests/test_geo_overlay.py -v | 12 passed in 0.77s | PASS |
| No regression in full test suite | pytest tests/ -x -q | 34 passed, 0 failed | PASS |
| app.py importable with geopy | python -c "import app; assert hasattr(app, 'Nominatim')" | exits 0 (inferred from test run) | PASS |
| scale_img_in_memory accepts immich_exif_raw | grep in app.py line 442 | immich_exif_raw=None present in signature | PASS |
| serve_immich_image passes exifInfo | grep in app.py line 1063 | immich_exif_raw=selected_image.get('exifInfo', {}) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| GEO-01 | 07-01/07-02 | extract_gps_from_exif returns decimal coords for geotagged image | SATISFIED | test_extract_gps_from_exif passes; app.py:96 |
| GEO-02 | 07-01/07-02 | extract_gps_from_exif returns None when no GPS tag in EXIF | SATISFIED | test_extract_gps_no_gps_tag passes; app.py:105 |
| GEO-03 | 07-01/07-02 | extract_gps_from_exif returns None when _getexif() returns None | SATISFIED | test_extract_gps_no_exif_method passes; app.py:99 |
| GEO-04 | 07-01/07-02 | parse_photo_location returns 'City, Country' from Immich exifInfo | SATISFIED | test_location_from_immich_exif passes; app.py:172-179 |
| GEO-05 | 07-01/07-02 | parse_photo_location returns None for empty/missing Immich fields | SATISFIED | test_location_immich_empty_fields passes; app.py:175-178 |
| GEO-06 | 07-01/07-02 | parse_photo_location falls back to local GPS when no Immich exif | SATISFIED | test_location_from_local_gps passes; app.py:181-191 |
| GEO-07 | 07-01/07-02 | reverse_geocode_cached returns cache hit without network call | SATISFIED | test_geocache_hit_no_network_call passes; app.py:151-153 |
| GEO-08 | 07-01/07-02 | reverse_geocode_cached caches None on Nominatim failure | SATISFIED | test_geocache_stores_null_on_error passes; app.py:160-168 |
| GEO-09 | 07-01/07-03 | scale_img renders 'City, Country • DD.MM.YYYY' when both available | SATISFIED | test_scale_img_geo_plus_date_overlay passes; app.py:531 |
| GEO-10 | 07-01/07-03 | scale_img renders date-only when no geo available | SATISFIED | test_scale_img_date_fallback passes; app.py:535 |
| GEO-11 | 07-01/07-03 | scale_img renders location-only when no date available | SATISFIED | test_scale_img_location_only passes; app.py:533 |
| GEO-12 | 07-01/07-03 | scale_img hides overlay when neither geo nor date available | SATISFIED | test_scale_img_no_overlay passes; app.py:536 |

Note: No REQUIREMENTS.md file exists in `.planning/` — requirement descriptions sourced from plan frontmatter, ROADMAP.md, and CONTEXT.md. All 12 GEO IDs claimed by plans 07-01/07-02/07-03 are accounted for. No orphaned requirements found.

### Anti-Patterns Found

No blockers or warnings found in geo-related new code.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| app.py | 103 | `except (AttributeError, Exception)` — bare Exception catch | Info | Acceptable: intentional never-raises contract per D-15; mirrors existing pattern at app.py:358 |
| app.py | 163 | `except (GeocoderTimedOut, GeocoderServiceError, Exception)` — broad catch | Info | Acceptable: intentional null-caching on any geocoder failure; explicit log printed |

No TODOs, FIXMEs, hardcoded empty returns, or placeholder patterns found in new geo functions. No stub indicators in `parse_photo_location`, `extract_gps_from_exif`, `reverse_geocode_cached`, or the updated `scale_img_in_memory` overlay block.

The `_GEO_CACHE = None` module-level variable is the lazy-load sentinel, not a stub — it is populated by `_load_geo_cache()` on first use and reset correctly in tests via `monkeypatch.setattr`.

### Human Verification Required

#### 1. Live Immich geo overlay on e-paper

**Test:** Load a photo from an Immich library where the asset has `exifInfo.city` and `exifInfo.country` populated. Trigger a frame refresh.
**Expected:** The overlay on the displayed image reads `"[City], [Country] • DD.MM.YYYY"` in the configured font/position.
**Why human:** Requires a live Immich instance, real asset data, and visual inspection of the rendered e-paper output. Cannot be verified programmatically without a running server and display.

#### 2. Local GPS EXIF → Nominatim → geo_cache.json written

**Test:** Place a GPS-tagged JPEG in the local photo directory, set `IMMICH_PHOTO_DEST`, and trigger a frame refresh (local image mode).
**Expected:** `geo_cache.json` is created in `IMMICH_PHOTO_DEST` containing an entry `{"lat_rounded,lon_rounded": "City, Country"}`. The overlay displays the reverse-geocoded location.
**Why human:** Requires a GPS-tagged image file, Nominatim network access, and filesystem inspection of the output directory.

#### 3. Settings UI — location note visible in Date Overlay card

**Test:** Open the web settings page and navigate to the Date Overlay section.
**Expected:** A help note reading "When a photo includes location data (from Immich or GPS EXIF), the city and country are shown alongside the date..." is visible below the date overlay controls.
**Why human:** Programmatic content confirmed (templates/settings.html:461), but rendered layout and visibility requires browser inspection.

### Gaps Summary

No gaps. All 12 requirement contracts are satisfied. The phase goal is fully achieved: geolocation (city, country) is overlaid alongside the date on the photo frame display, sourced from Immich exifInfo (priority) or local GPS EXIF (fallback), with persistent JSON caching for reverse geocoding, and a static settings UI note. The D-19 fallback chain (geo+date, geo-only, date-only, hidden) is implemented and verified by all 12 GEO tests with a full suite score of 34/34.

---

_Verified: 2026-06-01T19:10:00Z_
_Verifier: Claude (gsd-verifier)_
