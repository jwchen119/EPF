# Phase 7: Geolocation Overlay from Image Metadata - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the existing date overlay to include the location where a photo was taken. The overlay shows a single-line string: `"City, Country • DD.MM.YYYY"` (location first, bullet separator, then date). When geo is unavailable, falls back to showing the date alone. When date is also unavailable, overlay is silently hidden.

Sources for location data:
- **Local images:** Extract GPS lat/lon from EXIF tag 34853 (GPSInfo), then reverse-geocode to city/country using geopy + Nominatim (OSM). Results cached in a persistent JSON file.
- **Immich images:** Use `exifInfo.city` and `exifInfo.country` directly from the already-fetched asset object — no extra API call needed.

All overlay visual appearance (style, colors, font size) remains controlled by the Phase 6 config keys. No new visual parameters added in Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Location Text Format
- **D-01:** Display **city + country only** — e.g., `"Munich, Germany"`. State/region is omitted (redundant for most non-US photos; increases text length without meaningful gain).
- **D-02:** For Immich: use `exifInfo.city` and `exifInfo.country` directly (pre-geocoded by Immich server). No extra API call needed.
- **D-03:** For local images with GPS EXIF: extract lat/lon from tag 34853, then call Nominatim reverse geocoding via `geopy.geocoders.Nominatim`. Add `geopy` to `requirements.txt`.

### Combined Display (location + date)
- **D-04:** When both location and date are available, the overlay text is a **single line**: `"Munich, Germany • 05.01.2022"` — location first, bullet (`•`) separator, then the date in DD.MM.YYYY format.
- **D-05:** When only date is available (geo fallback), show the date alone (existing behavior — no bullet, no prefix).
- **D-06:** When only location is available (date extraction fails), show location alone: `"Munich, Germany"`.

### Fallback Chain
- **D-07:** Overlay rendering priority:
  1. Geo + date → `"City, Country • DD.MM.YYYY"`
  2. Geo only → `"City, Country"`
  3. Date only → `"DD.MM.YYYY"` (existing Phase 2 behavior)
  4. Neither → overlay silently hidden (Phase 2 D-03 pattern)
- **D-08:** The fallback is automatic and requires no new config key — the existing `date_overlay_enabled` toggle controls whether any overlay (date or geo+date) is shown.

### Reverse Geocoding for Local Images
- **D-09:** Add `geopy` to `requirements.txt`. Use `geopy.geocoders.Nominatim` with a project-specific `user_agent` string (e.g. `"epf-photo-frame"`).
- **D-10:** Cache geocoding results in a **persistent JSON file** — `geo_cache.json` stored alongside `tracking.txt` in the `IMMICH_PHOTO_DEST` directory. Key: `"{lat_rounded},{lon_rounded}"` (rounded to 3 decimal places ≈ 111m precision). Value: `"City, Country"` string or `null` if geocoding failed.
- **D-11:** Cache lookup before any network call. On cache miss: call Nominatim, store result (including `null` for failures). On exception: treat as `null`, log error, do not crash.
- **D-12:** GPS coordinate rounding for cache key: round to 3 decimal places before lookup and storage. This prevents near-duplicate entries for the same location.

### Config / UI
- **D-13:** No new config keys added in Phase 7. The existing `date_overlay_enabled` toggle serves as the on/off for the combined geo+date overlay. When `false`, no overlay is shown; when `true`, the best available info (geo+date, geo, date) is shown.
- **D-14:** Settings UI: no new controls. The existing "Date Overlay" section already covers the toggle and position. Add a brief note in the UI (static text) explaining that location data is shown alongside the date when available.

### Implementation Shape
- **D-15:** New function `extract_gps_from_exif(image)` — takes a PIL Image, returns `(lat_float, lon_float)` tuple or `None`. Reads EXIF tag 34853 (GPSInfo), converts DMS tuples to decimal degrees.
- **D-16:** New function `parse_photo_location(local_image=None, immich_exif=None)` — accepts a PIL Image (for EXIF extraction) and/or Immich exifInfo dict. Returns `"City, Country"` string or `None`. Follows the `parse_photo_date()` signature pattern.
- **D-17:** `scale_img_in_memory()` signature extension: add `immich_exif_raw=None` parameter (the full `exifInfo` dict from Immich asset). Local EXIF GPS is extracted inside the function (same as how `date_time_raw` is extracted there today).
- **D-18:** `serve_immich_image()` passes `immich_exif_raw=selected_image.get('exifInfo', {})` to `scale_img_in_memory()`.
- **D-19:** Overlay text assembly inside `scale_img_in_memory()`:
  ```python
  location_str = parse_photo_location(local_image=image, immich_exif=immich_exif_raw)
  date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
  if location_str and date_str:
      overlay_text = f"{location_str} • {date_str}"
  elif location_str:
      overlay_text = location_str
  else:
      overlay_text = date_str  # may be None → overlay hidden
  ```

### Claude's Discretion
- Where `geo_cache.json` is written if `IMMICH_PHOTO_DEST` is not set: default to the project root or `/photos` (matching existing tracking.txt behavior).
- Whether `extract_gps_from_exif()` lives in `app.py` or a new helper module — `app.py` is consistent with existing patterns.
- Nominatim response parsing: use `result.address` components or the `geopy` Location object — whichever is cleanest for extracting city and country.
- Whether to add Nominatim timeout (recommend 3–5 seconds, fail gracefully).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core overlay function (Phase 6 parameterized version)
- `app.py:101-200` — `draw_date_overlay()`: renders any text string as overlay; Phase 7 passes the assembled geo+date string here. No signature change needed.
- `app.py:336-445` — `scale_img_in_memory()`: main call site for all overlay logic. GPS extraction (local), geo assembly, and `draw_date_overlay()` call all happen here. Signature extended with `immich_exif_raw=None`.

### Date extraction pattern to replicate for geo (Phase 2)
- `app.py:61-83` — `parse_photo_date()`: pure function pattern returning `None` when unparseable. New `parse_photo_location()` follows the same contract.
- `app.py:351-358` — EXIF extraction inside `scale_img_in_memory()`: `image._getexif()` pattern. GPS extraction at tag 34853 follows this same pattern.

### Immich data flow
- `app.py:942-943` — `immich_date_raw = selected_image.get('exifInfo', {}).get('dateTimeOriginal')` — the Immich exifInfo dict also contains `city`, `country`, `latitude`, `longitude`. Full dict will be passed as `immich_exif_raw`.
- `app.py:865-947` — `serve_immich_image()`: passes `immich_date_raw` today; will also pass `immich_exif_raw`.

### Config pattern (no new keys in Phase 7, but must preserve)
- `app.py:34-58` — `DEFAULT_CONFIG` — read to understand existing overlay key names.
- `app.py:505-544` — `update_app_config()` — no new globals, but existing `date_overlay_enabled` gate applies.

### Cache file pattern
- `app.py` — `load_downloaded_images()` / tracking.txt pattern: stores text in `IMMICH_PHOTO_DEST`. `geo_cache.json` stored in same directory.

### Prior phase decisions
- `.planning/phases/02-date-overlay/02-CONTEXT.md` — D-01: overlay off by default; D-03: silently hidden when no data; parse_photo_date() signature pattern.
- `.planning/phases/06-text-customization-colors-styles-and-border-mode/06-CONTEXT.md` — D-14: visual defaults; OVERLAY_COLORS dict; draw_date_overlay() call site in scale_img_in_memory().
- `.planning/STATE.md` — key decisions: `.get()` fallback for backward compat; select not checkbox for POST.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `draw_date_overlay()` (`app.py:101`): accepts any `text` string — the combined `"Munich, Germany • 05.01.2022"` is passed in as-is. Zero changes to rendering layer.
- `parse_photo_date()` (`app.py:61`): pattern for `parse_photo_location()` — same signature (`raw_input → string | None`), same None-propagation contract.
- `image._getexif()` pattern (`app.py:354`): already used for date extraction; GPS tag 34853 (GPSInfo) is extracted the same way.
- `IMMICH_PHOTO_DEST` env var: used for `tracking.txt` location — `geo_cache.json` goes in the same directory.

### Established Patterns
- EXIF access: `image._getexif()` returns dict; GPS is at key `34853`. GPSInfo sub-tags: `1`=GPSLatitudeRef, `2`=GPSLatitude (DMS tuples), `3`=GPSLongitudeRef, `4`=GPSLongitude (DMS tuples).
- DMS-to-decimal conversion: `deg + min/60 + sec/3600`, negate if `ref` is `'S'` or `'W'`.
- Immich `exifInfo` dict: `city` (str), `country` (str), `latitude` (float), `longitude` (float) — same object already accessed for `dateTimeOriginal`.

### Integration Points
- `scale_img_in_memory()`: add `immich_exif_raw=None` parameter; extract local GPS here (alongside existing EXIF date extraction); assemble overlay text before calling `draw_date_overlay()`.
- `serve_local_image()` (`app.py:844`): calls `scale_img_in_memory(image)` — no change needed since GPS is extracted inside from the image object.
- `serve_immich_image()` (`app.py:942`): extend to pass `immich_exif_raw=selected_image.get('exifInfo', {})`.

</code_context>

<specifics>
## Specific Ideas

- Bullet character: `•` (U+2022) — standard bullet, renders correctly with DejaVuSans-Bold. Surrounded by spaces: `" • "`.
- Cache key precision: `f"{round(lat, 3)},{round(lon, 3)}"` — 3 decimal places ≈ 111m, more than sufficient for "city-level" geo.
- Nominatim user_agent: `"epf-photo-frame/1.0"` — required by Nominatim usage policy.
- geopy Nominatim returns a Location object; `location.raw['address']` contains `city`, `town`, `village`, `country` keys. Strategy: try `city`, then `town`, then `village`, then fall back to `None`.
- For Immich: `immich_exif.get('city')` and `immich_exif.get('country')` — both may be `None` or empty string if Immich has not geocoded the asset. Treat empty string as missing.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-geolocation-overlay-from-image-metadata*
*Context gathered: 2026-06-01*
