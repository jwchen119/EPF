# Phase 7: Geolocation Overlay from Image Metadata - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 07-geolocation-overlay-from-image-metadata
**Areas discussed:** Location text format, Fallback behavior, Date + location combined display, Reverse geocoding for local images

---

## Location Text Format

| Option | Description | Selected |
|--------|-------------|----------|
| City + country | Show 'Munich, Germany' — readable and compact. Uses Immich exifInfo.city + country fields directly; reverse geocoding for local EXIF. | ✓ |
| GPS coordinates only | Show '48.1°N 11.6°E' — always works, no library needed. Not human-friendly. | |
| Best available: city/country when present, coords as fallback | Try Immich city/country first, then EXIF GPS coordinates. | |

**User's choice:** City + country only (e.g. "Munich, Germany"). State/region omitted.

**Follow-up — include state/region?**

| Option | Description | Selected |
|--------|-------------|----------|
| City + country only | Compact: 'Munich, Germany' | ✓ |
| City + state + country | Fuller: 'Munich, Bavaria, Germany' | |
| City only | Minimal: just 'Munich' | |

**Notes:** Keep it compact — city + country is sufficient for a photo frame display.

---

## Fallback Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to the date | Show timestamp overlay when no location is found | ✓ |
| Show nothing | Silently hide overlay if no location — consistent with Phase 2 missing-date pattern | |

**User's choice:** Fall back to the date (timestamp) when geo is unavailable.

---

## Date + Location Combined Display

| Option | Description | Selected |
|--------|-------------|----------|
| Location only — replaces the date | Show 'Munich, Germany' instead of date when geo available | |
| Both: location + date on two lines | Two-line overlay block | |
| User-configurable (overlay_content setting) | New config key for date/location/both | |
| Other (user input) | Single line, location first, bullet separator | ✓ |

**User's choice (free text):** "The location and date should be one line, joined by a '•' (Bullet). Location first, then date"

**Confirmed format:** `"Munich, Germany • 05.01.2022"`
- When only date available: show date alone (no bullet)
- When only location available: show location alone
- When neither available: silently hidden

---

## Reverse Geocoding for Local Images

| Option | Description | Selected |
|--------|-------------|----------|
| Add reverse geocoding library (geopy + Nominatim) | Converts lat/lon to 'Munich, Germany' for local images. Adds geopy to requirements.txt + HTTP call to Nominatim (OSM). Free, no API key. | ✓ |
| Show GPS coordinates for local images | '48.1°N 11.6°E' for local; 'City, Country' for Immich. Zero new dependencies. | |
| Local images: skip geo entirely | Immich-only feature for human-readable names. Simpler code. | |

**User's choice:** Add geopy + Nominatim for local images.

**Follow-up — cache geocoding results?**

| Option | Description | Selected |
|--------|-------------|----------|
| Cache in-memory dict (per-server-run) | Fast re-display; lost on restart | |
| Cache to JSON file (persistent across restarts) | geo_cache.json — avoid re-querying for same coordinates ever | ✓ |
| No cache — call Nominatim each time | Simple but may hit rate limits | |

**Notes:** Persistent JSON cache in IMMICH_PHOTO_DEST directory (alongside tracking.txt). Cache key: lat/lon rounded to 3 decimal places.

---

## Claude's Discretion

- Where `extract_gps_from_exif()` lives: `app.py` (consistent with existing patterns)
- Nominatim timeout: 3–5 seconds with graceful failure
- Nominatim result parsing: try `city`, then `town`, then `village` from `location.raw['address']`
- Cache file location: IMMICH_PHOTO_DEST directory (same as tracking.txt)

## Deferred Ideas

None — discussion stayed within phase scope.
