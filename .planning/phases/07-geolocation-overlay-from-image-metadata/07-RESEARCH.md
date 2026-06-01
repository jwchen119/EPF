# Phase 7: Geolocation Overlay from Image Metadata - Research

**Researched:** 2026-06-01
**Domain:** Python EXIF GPS extraction, geopy/Nominatim reverse geocoding, persistent JSON caching, PIL overlay assembly
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Display city + country only — e.g., `"Munich, Germany"`. State/region omitted.
- **D-02:** For Immich: use `exifInfo.city` and `exifInfo.country` directly — no extra API call.
- **D-03:** For local images with GPS EXIF: extract lat/lon from tag 34853, call Nominatim via `geopy.geocoders.Nominatim`. Add `geopy` to `requirements.txt`.
- **D-04:** Both available → single line: `"Munich, Germany • 05.01.2022"` (location first, bullet, date in DD.MM.YYYY).
- **D-05:** Date only → show date alone (existing Phase 2 behavior).
- **D-06:** Location only → show location alone: `"Munich, Germany"`.
- **D-07:** Fallback chain: geo+date → geo → date → hidden.
- **D-08:** `date_overlay_enabled` toggle controls the entire overlay; no new config key.
- **D-09:** Add `geopy` to `requirements.txt`. Use `Nominatim(user_agent="epf-photo-frame")`.
- **D-10:** Cache in `geo_cache.json` in `IMMICH_PHOTO_DEST` directory. Key: `"{lat_rounded},{lon_rounded}"`. Value: `"City, Country"` string or `null`.
- **D-11:** Cache lookup before network. On miss: call Nominatim, store result including `null`. On exception: treat as `null`, log, no crash.
- **D-12:** Round to 3 decimal places for cache key (≈111m precision).
- **D-13:** No new config keys.
- **D-14:** No new settings UI controls — add only a static note to existing "Date Overlay" section.
- **D-15:** New `extract_gps_from_exif(image)` — takes PIL Image, returns `(lat, lon)` tuple or `None`.
- **D-16:** New `parse_photo_location(local_image=None, immich_exif=None)` — returns `"City, Country"` string or `None`.
- **D-17:** `scale_img_in_memory()` gets `immich_exif_raw=None` parameter.
- **D-18:** `serve_immich_image()` passes `immich_exif_raw=selected_image.get('exifInfo', {})`.
- **D-19:** Overlay text assembly inside `scale_img_in_memory()` per the snippet in CONTEXT.md.

### Claude's Discretion

- Where `geo_cache.json` is written if `IMMICH_PHOTO_DEST` is not set: default to project root or `/photos` (matching existing tracking.txt behavior).
- Whether `extract_gps_from_exif()` lives in `app.py` or a new helper module — `app.py` is consistent with existing patterns.
- Nominatim response parsing: use `location.raw['address']` components.
- Whether to add Nominatim timeout (recommend 3–5 seconds, fail gracefully).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 7 extends the existing date overlay to show `"City, Country • DD.MM.YYYY"` when geolocation data is present. The implementation has two input paths: (1) local images — extract GPS DMS coordinates from EXIF tag 34853 then reverse-geocode via geopy/Nominatim with a persistent JSON cache; (2) Immich images — read pre-geocoded `city`/`country` strings directly from the already-fetched `exifInfo` dict.

All decisions are locked in CONTEXT.md. The design closely mirrors the existing `parse_photo_date()` pattern: a new `parse_photo_location()` pure function returns a string or `None`, and assembly happens inside `scale_img_in_memory()` before calling the unchanged `draw_date_overlay()`. No rendering code changes are needed — only the text passed in changes.

The key technical risks are: Nominatim's mandatory user_agent + 1 req/sec rate limit, the EXIF GPSInfo DMS-to-decimal conversion, and the empty-string vs `None` distinction for Immich `city`/`country` fields.

**Primary recommendation:** Implement `extract_gps_from_exif()` and `parse_photo_location()` in `app.py` (consistent with existing module structure), use `geopy==2.4.1`, and wrap every Nominatim call in a try/except logging `null` on any failure.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| geopy | 2.4.1 | Reverse geocoding via Nominatim | Locked by D-03/D-09; OSM Nominatim wrapper with built-in rate limiting |
| Pillow | 11.0.0 | EXIF extraction (`_getexif()`), tag 34853 | Already in use; no new dependency |
| json (stdlib) | — | Read/write `geo_cache.json` | Stdlib; no new dependency |
| os (stdlib) | — | Cache file path resolution | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| geopy.exc | (part of geopy) | `GeocoderTimedOut`, `GeocoderServiceError` | Catch all geocoder exceptions gracefully |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| geopy/Nominatim | Photon, Google Maps API | Photon requires self-hosted server; Google requires paid API key. Nominatim is free/OSM, locked by D-09. |

**Installation:**
```bash
pip install geopy==2.4.1
```

Add to `requirements.txt`:
```
geopy==2.4.1
```

**Version verification:** `pip3 index versions geopy` returns `geopy (2.4.1)` as latest — confirmed 2026-06-01.

---

## Architecture Patterns

### Recommended Code Location
All new code goes in `app.py` (consistent with existing module structure per Claude's Discretion note in CONTEXT.md). No new modules.

### New Functions

```
app.py
├── extract_gps_from_exif(image)         # NEW — D-15
├── reverse_geocode_cached(lat, lon)     # NEW — D-10/D-11/D-12 (name per Claude's discretion)
├── parse_photo_location(local_image, immich_exif)  # NEW — D-16
├── scale_img_in_memory(...)             # MODIFIED — add immich_exif_raw param (D-17)
└── serve_immich_image()                 # MODIFIED — pass immich_exif_raw (D-18)
```

### Pattern 1: GPS EXIF Extraction (D-15)

GPSInfo is at EXIF tag `34853`. The sub-tag structure:

```python
# Source: PIL EXIF spec + CONTEXT.md code_context
def extract_gps_from_exif(image):
    """Return (lat_float, lon_float) or None."""
    try:
        exif = image._getexif()
        if not exif:
            return None
        gps_info = exif.get(34853)
        if not gps_info:
            return None
        # Sub-tags: 1=LatRef('N'/'S'), 2=Lat DMS, 3=LonRef('E'/'W'), 4=Lon DMS
        lat_dms = gps_info.get(2)
        lat_ref = gps_info.get(1, 'N')
        lon_dms = gps_info.get(4)
        lon_ref = gps_info.get(3, 'E')
        if not lat_dms or not lon_dms:
            return None
        lat = lat_dms[0] + lat_dms[1] / 60 + lat_dms[2] / 3600
        lon = lon_dms[0] + lon_dms[1] / 60 + lon_dms[2] / 3600
        if lat_ref == 'S':
            lat = -lat
        if lon_ref == 'W':
            lon = -lon
        return (lat, lon)
    except Exception:
        return None
```

Note: PIL stores DMS values as `IFDRational` objects in newer Pillow (>=8.x). Arithmetic (`+`, `/`) works on `IFDRational` directly — no need to call `float()` explicitly, but `float()` cast is safer for cache key formatting.

### Pattern 2: Reverse Geocoding with Cache (D-10/D-11/D-12)

```python
# Source: geopy docs + CONTEXT.md decisions
import json
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

_GEO_CACHE = None  # module-level cache dict, loaded lazily

def _geo_cache_path():
    dest = os.environ.get('IMMICH_PHOTO_DEST', '')
    base = dest if dest else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'geo_cache.json')

def _load_geo_cache():
    global _GEO_CACHE
    if _GEO_CACHE is None:
        path = _geo_cache_path()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _GEO_CACHE = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _GEO_CACHE = {}
    return _GEO_CACHE

def _save_geo_cache(cache):
    path = _geo_cache_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[WARN] Could not save geo_cache.json: {e}')

def reverse_geocode_cached(lat, lon):
    """Return 'City, Country' string or None. Uses persistent JSON cache."""
    key = f"{round(lat, 3)},{round(lon, 3)}"
    cache = _load_geo_cache()
    if key in cache:
        return cache[key]  # may be None (cached failure)
    result = None
    try:
        geolocator = Nominatim(user_agent="epf-photo-frame/1.0", timeout=5)
        location = geolocator.reverse((lat, lon), exactly_one=True, language='en')
        if location:
            addr = location.raw.get('address', {})
            city = addr.get('city') or addr.get('town') or addr.get('village')
            country = addr.get('country')
            if city and country:
                result = f"{city}, {country}"
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        print(f'[WARN] Nominatim geocoding failed for ({lat},{lon}): {e}')
    cache[key] = result
    _save_geo_cache(cache)
    return result
```

### Pattern 3: parse_photo_location (D-16)

```python
def parse_photo_location(local_image=None, immich_exif=None):
    """Return 'City, Country' string or None.

    Priority: Immich exifInfo city/country first; local GPS EXIF second.
    Follows parse_photo_date() None-propagation contract.
    """
    # Immich path (D-02)
    if immich_exif:
        city = immich_exif.get('city') or ''
        country = immich_exif.get('country') or ''
        if city and country:
            return f"{city}, {country}"
        if city:
            return city
        if country:
            return country
    # Local EXIF path (D-03/D-15)
    if local_image is not None:
        coords = extract_gps_from_exif(local_image)
        if coords:
            return reverse_geocode_cached(coords[0], coords[1])
    return None
```

### Pattern 4: scale_img_in_memory overlay assembly (D-17/D-19)

Changes to existing function:
1. Add `immich_exif_raw=None` to signature
2. Replace `if date_str:` block with the D-19 assembly:

```python
if date_overlay_enabled:
    location_str = parse_photo_location(local_image=image, immich_exif=immich_exif_raw)
    date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
    if location_str and date_str:
        overlay_text = f"{location_str} • {date_str}"
    elif location_str:
        overlay_text = location_str
    else:
        overlay_text = date_str  # may be None — overlay hidden when None
    if overlay_text:
        # ... font load + draw_date_overlay() call (unchanged) ...
```

Note: `•` is the bullet character `•` (U+2022), confirmed renderable with DejaVuSans-Bold per CONTEXT.md specifics.

### Anti-Patterns to Avoid
- **Calling Nominatim on every request:** Cache lookup must precede every network call. The Nominatim free service enforces 1 req/sec; repeated calls for the same photo will hit rate limits.
- **Treating empty string as valid city/country:** Immich may return `""` instead of `None` for ungeolocated assets. Always use `or ''` and check truthiness.
- **Using IFDRational without arithmetic guard:** DMS values from PIL are `IFDRational` — arithmetic works but `float()` cast is safer when formatting the cache key.
- **Not handling `_getexif()` returning `None`:** JPEG without EXIF returns `None`; PNG/BMP always returns `None`. Guard required.
- **Module-level Nominatim instantiation:** Nominatim is cheap to construct; instantiate inside the function to avoid stale state and keep the module importable without network.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reverse geocoding | Custom HTTP call to Nominatim | `geopy.geocoders.Nominatim` | Handles rate limiting, error types, response parsing |
| DMS-to-decimal conversion | Custom IFDRational handling | Simple arithmetic (already documented in CONTEXT.md) | PIL stores as IFDRational which supports arithmetic operators |
| Address fallback (city → town → village) | Custom logic | `addr.get('city') or addr.get('town') or addr.get('village')` | One-liner per OSM address spec |

**Key insight:** geopy's Nominatim wrapper handles the HTTP session, Content-Type negotiation, and raises typed exceptions (`GeocoderTimedOut`, `GeocoderServiceError`) that make error handling clean. The address component fallback logic (city → town → village) is trivially simple with Python's `or` chaining.

---

## Common Pitfalls

### Pitfall 1: Nominatim User-Agent Rejection
**What goes wrong:** Requests fail with HTTP 403 or "Usage limit reached" if User-Agent is a generic library string.
**Why it happens:** OSM Nominatim policy requires a valid, application-specific User-Agent string. Stock geopy UA is rejected.
**How to avoid:** Always pass `user_agent="epf-photo-frame/1.0"` (or any project-specific string) to `Nominatim()`. Locked by D-09.
**Warning signs:** `GeocoderServiceError: HTTP Error 403` or `GeocoderServiceError: Usage limit reached` in logs.

### Pitfall 2: IFDRational arithmetic in GPS DMS
**What goes wrong:** `lat_dms[2] / 3600` raises `TypeError` or produces wrong result if values are `IFDRational` objects and code converts them incorrectly.
**Why it happens:** PIL >= 6.0 stores EXIF rational values as `IFDRational` (not plain `float` or `Fraction`). Division and addition work, but mixing with `round()` for cache key needs `float()` cast.
**How to avoid:** Apply `float()` cast when building the cache key: `f"{round(float(lat), 3)},{round(float(lon), 3)}"`.
**Warning signs:** `TypeError` in `round()` call, or cache keys containing `IFDRational(...)` string repr.

### Pitfall 3: geo_cache.json write race condition
**What goes wrong:** Concurrent image requests (unlikely but possible) both cache-miss the same coord, make two Nominatim calls, and the second write overwrites the first.
**Why it happens:** No file locking around cache read-write cycle.
**How to avoid:** Accept the minor redundancy — at worst two API calls for the same coord. The write is idempotent (same key, same value). Do not add file locking complexity; it contradicts the "no new config, minimal complexity" design of Phase 7.
**Warning signs:** Duplicate Nominatim calls in logs for identical coordinates. Harmless.

### Pitfall 4: Immich exifInfo missing or partially populated
**What goes wrong:** `immich_exif.get('city')` returns `None` or `""` for assets that Immich has not yet reverse-geocoded (Immich geocoding is async and may lag asset import).
**Why it happens:** Immich reverse-geocodes on the server side after import. Recently-added photos may lack city/country.
**How to avoid:** Always treat empty string same as `None`: `city = immich_exif.get('city') or ''`. Fall back silently to date-only overlay — this is the D-07 fallback chain.
**Warning signs:** Overlay shows only date even for geotagged Immich photos (indicates Immich has not yet geocoded the asset — expected behavior).

### Pitfall 5: _getexif() unavailable on non-JPEG images
**What goes wrong:** `AttributeError: 'PngImageFile' object has no attribute '_getexif'` when processing PNG or BMP images.
**Why it happens:** `_getexif()` is a JPEG-only PIL method (private API). PNG/BMP/GIF images do not have it.
**How to avoid:** Wrap in `try/except (AttributeError, Exception)` — already the pattern in the existing EXIF date extraction at `app.py:353-358`. `extract_gps_from_exif()` must follow the same defensive pattern.
**Warning signs:** `AttributeError` crash when serving non-JPEG local images.

### Pitfall 6: Tests monkeypatching scale_img_in_memory signature
**What goes wrong:** Existing tests call `scale_img_in_memory(large_rgb_image, immich_date_raw=...)` — the new `immich_exif_raw=None` parameter must be keyword-only with a default so existing call-sites are unaffected.
**Why it happens:** Signature extension without default breaks callers.
**How to avoid:** Add `immich_exif_raw=None` as a keyword argument with default. Existing test calls in `test_date_overlay.py` pass `immich_date_raw=...` and will continue to work unchanged.
**Warning signs:** `TypeError: scale_img_in_memory() got unexpected keyword argument` in existing tests.

---

## Code Examples

### Confirmed GPS DMS-to-decimal conversion
```python
# Source: CONTEXT.md code_context, EXIF spec
# DMS sub-tag values: (degrees, minutes, seconds) as IFDRational or tuple
lat_deg, lat_min, lat_sec = lat_dms[0], lat_dms[1], lat_dms[2]
lat = float(lat_deg) + float(lat_min) / 60.0 + float(lat_sec) / 3600.0
if lat_ref == 'S':
    lat = -lat
```

### Nominatim reverse call with timeout and exception handling
```python
# Source: geopy 2.4.1 docs (geopy.readthedocs.io)
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

geolocator = Nominatim(user_agent="epf-photo-frame/1.0", timeout=5)
try:
    location = geolocator.reverse((lat, lon), exactly_one=True, language='en')
    addr = location.raw['address']
    city = addr.get('city') or addr.get('town') or addr.get('village')
    country = addr.get('country')
except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
    print(f'[WARN] Nominatim failed: {e}')
    city = country = None
```

### Cache key construction
```python
# Source: CONTEXT.md D-12
key = f"{round(float(lat), 3)},{round(float(lon), 3)}"
```

### Overlay text assembly (D-19)
```python
# Source: CONTEXT.md D-19
location_str = parse_photo_location(local_image=image, immich_exif=immich_exif_raw)
date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
if location_str and date_str:
    overlay_text = f"{location_str} • {date_str}"
elif location_str:
    overlay_text = location_str
else:
    overlay_text = date_str  # None → overlay hidden
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual Nominatim HTTP calls | `geopy.geocoders.Nominatim` | geopy 1.x (2014+) | Handles retries, error types, rate awareness |
| `location.address` string | `location.raw['address']` dict | Always available | Structured component access (city, town, village, country) |

**Deprecated/outdated:**
- `geopy` v1.x: The `Nominatim` API is stable across 1.x→2.x but v1.x is EOL. v2.4.1 is the current release.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| geopy | Reverse geocoding (D-03) | ✗ (not installed) | — | Must install; `pip install geopy==2.4.1` |
| Nominatim (OSM) | Reverse geocoding | ✓ (public service) | — | `null` cached on network failure |
| DejaVuSans-Bold | Overlay rendering (existing) | ✓ (Docker image) | — | PIL default font (existing fallback) |
| `geo_cache.json` | Cache persistence | ✗ (first run) | — | Created automatically on first write |

**Missing dependencies with no fallback:**
- `geopy` package: must be added to `requirements.txt` and installed. Blocks local GPS geocoding if absent.

**Missing dependencies with fallback:**
- Nominatim network: if OSM is unreachable, result cached as `null` and overlay falls back to date-only (D-07).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, no version pin in requirements.txt) |
| Config file | none (pytest discovers `tests/` automatically) |
| Quick run command | `pytest tests/test_geo_overlay.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| GEO-01 | `extract_gps_from_exif()` returns correct (lat, lon) from synthetic EXIF | unit | `pytest tests/test_geo_overlay.py::test_extract_gps_from_exif -x` | ❌ Wave 0 |
| GEO-02 | `extract_gps_from_exif()` returns None for image without GPS | unit | `pytest tests/test_geo_overlay.py::test_extract_gps_no_gps_tag -x` | ❌ Wave 0 |
| GEO-03 | `extract_gps_from_exif()` returns None for non-JPEG (no _getexif) | unit | `pytest tests/test_geo_overlay.py::test_extract_gps_no_exif_method -x` | ❌ Wave 0 |
| GEO-04 | `parse_photo_location()` returns city+country from Immich exifInfo dict | unit | `pytest tests/test_geo_overlay.py::test_location_from_immich_exif -x` | ❌ Wave 0 |
| GEO-05 | `parse_photo_location()` returns None when Immich exifInfo has no city/country | unit | `pytest tests/test_geo_overlay.py::test_location_immich_empty_fields -x` | ❌ Wave 0 |
| GEO-06 | `parse_photo_location()` calls geocoder (mocked) for local image with GPS | unit | `pytest tests/test_geo_overlay.py::test_location_from_local_gps -x` | ❌ Wave 0 |
| GEO-07 | `reverse_geocode_cached()` uses cache on second call (no Nominatim call) | unit | `pytest tests/test_geo_overlay.py::test_geocache_hit_no_network_call -x` | ❌ Wave 0 |
| GEO-08 | `reverse_geocode_cached()` stores null on Nominatim exception | unit | `pytest tests/test_geo_overlay.py::test_geocache_stores_null_on_error -x` | ❌ Wave 0 |
| GEO-09 | `scale_img_in_memory()` renders geo+date combined overlay text | integration | `pytest tests/test_geo_overlay.py::test_scale_img_geo_plus_date_overlay -x` | ❌ Wave 0 |
| GEO-10 | `scale_img_in_memory()` renders date-only when no geo available | integration | `pytest tests/test_geo_overlay.py::test_scale_img_date_fallback -x` | ❌ Wave 0 |
| GEO-11 | `scale_img_in_memory()` renders location-only when no date available | integration | `pytest tests/test_geo_overlay.py::test_scale_img_location_only -x` | ❌ Wave 0 |
| GEO-12 | Overlay hidden when neither geo nor date available | integration | `pytest tests/test_geo_overlay.py::test_scale_img_no_overlay -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_geo_overlay.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_geo_overlay.py` — covers GEO-01 through GEO-12 (new file, entire test suite)
- [ ] `conftest.py` additions — `synthetic_gps_image` fixture (PIL Image with embedded GPSInfo EXIF), `mock_geo_cache_dir` fixture (tmp_path-based cache dir)

*(Existing `conftest.py` fixtures `blank_rgb_image`, `large_rgb_image`, `dejavu_or_default_font` are reusable for integration tests.)*

---

## Open Questions

1. **IFDRational vs float in DMS arithmetic**
   - What we know: PIL >= 6.0 uses `IFDRational`; arithmetic operators work; `float()` cast needed for `round()` and string formatting.
   - What's unclear: Whether PIL/Pillow 11.0.0 (project's pinned version) returns raw tuples or IFDRational for tag 34853 sub-values.
   - Recommendation: Defensively apply `float()` to each DMS component before arithmetic. Cost: zero.

2. **geo_cache.json default path when IMMICH_PHOTO_DEST unset**
   - What we know: CONTEXT.md says "default to project root or `/photos`." Claude's Discretion covers this.
   - Recommendation: Use `os.path.dirname(os.path.abspath(__file__))` (the project root where `app.py` lives) as default. Matches the "alongside tracking.txt" intent without requiring the env var.

3. **Thread safety of module-level `_GEO_CACHE` dict**
   - What we know: Flask dev server is single-threaded; production use with gunicorn would be multi-threaded.
   - What's unclear: Project deployment model.
   - Recommendation: Accept read-write race (same idempotent outcome — both threads write the same cached value). Adding a threading.Lock adds complexity that contradicts Phase 7's minimal-scope intent.

---

## Sources

### Primary (HIGH confidence)
- `app.py` lines 61-83, 336-445, 865-947 — existing function signatures, EXIF extraction pattern, scale_img_in_memory structure
- `.planning/phases/07-geolocation-overlay-from-image-metadata/07-CONTEXT.md` — all locked decisions and implementation shape
- PyPI registry (`pip3 index versions geopy`) — confirmed geopy 2.4.1 as current version (2026-06-01)

### Secondary (MEDIUM confidence)
- [geopy.readthedocs.io](https://geopy.readthedocs.io/) — Nominatim constructor, `reverse()` signature, timeout parameter, exception types
- [Nominatim Usage Policy (OSM Foundation)](https://operations.osmfoundation.org/policies/nominatim/) — user_agent requirement, 1 req/sec limit, caching mandate
- [w3resource geopy exercise](https://www.w3resource.com/python-exercises/geopy/python-geopy-nominatim_api-exercise-6.php) — `location.raw['address']` dict structure with `city`/`town`/`village`/`country` keys

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — geopy 2.4.1 confirmed via pip registry; all other dependencies already in project
- Architecture: HIGH — all patterns directly mirror existing `parse_photo_date()` and `_getexif()` patterns in app.py
- Pitfalls: HIGH — IFDRational and Nominatim policy pitfalls are well-documented; Immich empty-string issue confirmed by reading existing Immich data access code

**Research date:** 2026-06-01
**Valid until:** 2026-07-01 (stable domain; geopy version may increment but API is stable)
