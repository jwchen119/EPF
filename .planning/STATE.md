---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Milestone complete
last_updated: "2026-06-07T19:21:20.965Z"
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 24
  completed_plans: 24
---

# Project State

## Current Position

Phase: 09
Plan: Not started

## Phase 1 Complete

Phase 01 (hardware-port) completed all 3 plans:

- 01-01: WaveShare → EE02 pin constants / Seeed_GFX headers
- 01-02: Seeed_GFX API, PSRAM frame buffer, sleep API fixes
- 01-03: Server palette (T133A01 colors), nibble map, 1200×1600 resolution

## Phase 2 Plan Status

| Plan | Name | Status |
|------|------|--------|
| 02-01 | pytest infra + 9 failing test stubs | complete |
| 02-02 | parse_photo_date() + draw_date_overlay() helpers | complete |
| 02-03 | Wire overlay into pipeline + settings UI | complete |

## Key Decisions

- Test contracts locked before implementation: parse_photo_date signature, draw_date_overlay signature, DEFAULT_CONFIG keys (02-01)
- dejavu_or_default_font fixture falls back to PIL default when DejaVuSans not available (macOS compatibility) (02-01)
- parse_photo_date uses char at index 4 to distinguish EXIF ':' from ISO '-' format (02-02)
- bbox offset compensation (x - bbox[0], y - bbox[1]) applied on draw.text() for Pillow >= 9.2 compatibility (02-02)
- Unknown position_str falls back to POSITIONS["bottomRight"] via .get() default (02-02)
- .get() fallback in update_app_config for date_overlay keys (backward compat with old config.yaml) (02-03)
- date_overlay_enabled uses select on/off not checkbox to avoid unchecked-field omission in HTML POST (02-03)
- Dead draw_text_with_background nested function removed (-125 lines); EXIF fallback kept as date_time_raw (02-03)
- N816 noqa on rotationAngle global — rename would touch 7 call-sites with no behavior gain (03-01)
- .claude added to ruff extend-exclude to prevent scanning git worktrees (03-01)
- pyright basic mode required 0 code changes — all 13 diagnostics are missing-import warnings for third-party stubs (03-01)
- lint job installs only ruff (not full dev deps) for faster CI; test job installs libraw-dev + fonts-dejavu-core system libs matching Dockerfile (03-02)
- No needs: between CI jobs — parallel execution; branch protection enforces all-pass gate (03-02)
- semver validated via bash regex ^[0-9]+\.[0-9]+\.[0-9]+$ before checkout; tag-already-exists guard prevents silent overwrites (03-03)
- ${GITHUB_REPOSITORY,,} bash lowercase for ghcr.io image name; version+latest pushed atomically in single build-push-action step (03-03)
- fetch-depth: 0 required for generate_release_notes to diff against previous tag; GITHUB_TOKEN only — no extra secrets (03-03)
- Single-sample ADC read for low-battery guard; 50-sample average deferred to Plan 02 for HTTP header (04-01)
- USB/battery detection: vbatMv > 1500 mV means battery present; ≤1500 means USB-only, guard skipped (04-01)
- ADC_EN gate: OUTPUT LOW → ADC_11dB → HIGH → delay(10) → analogReadMilliVolts → LOW pattern (04-01)
- hibernate() stub left intact in Plan 01; Plan 02 will replace it with battery/USB-conditional sleep (04-01)
- 50-sample averaged ADC read placed inside while(retryOnError) before for(MAX_RETRIES) — header set once per outer attempt before http.GET() (04-02)
- hibernate() uses m_onBattery member directly (no parameter change needed) — refreshed by averaged read in downloadImage() (04-02)
- uint32_t cast guards delay overflow: delay((uint32_t)sleep_interval * 1000UL) safe for intervals > 2147s (04-02)
- Single atomic README write covers Tasks 1+2 — pin layout table sourced from epd7in3e.ino header; ghcr.io path uses lennartschmidt-de/epf (05-01)
- stroke_width passed to textbbox probe only in outline mode — background mode bbox matches legacy exactly (D-14 compat) (06-02)
- outline mode omits draw.rectangle() entirely; stroke provides visual separation per D-07 (06-02)
- OVERLAY_COLORS dict placed after palette list to co-locate authoritative RGB source with derived RGBA lookup (06-02)
- 6 overlay globals added to update_app_config() global statement with .get() fallback reads; backward compat with old config.yaml (06-03)
- int() cast on slider values in both update_app_config() and POST handler; prevents type errors when YAML loads values as strings (06-03)
- Color dropdowns always visible — no JS show/hide; small-text labels describe applicability per style mode (06-03)
- float() cast on IFDRational DMS components before arithmetic — required for Pillow GPS EXIF parsing (07-02 D-15)
- Cache key uses round(float(lat),3),round(float(lon),3) — aligns with GEO-07/08 test assertions (07-02 D-12)
- Nominatim module-level import, function-level instantiation — enables monkeypatching while avoiding module-level instantiation anti-pattern (07-02)
- pre_transpose_image captured before exif_transpose so GPS EXIF safely readable from original image object (07-03)
- serve_immich_image passes selected_image.get('exifInfo', {}) (empty dict, not None) for consistent type in parse_photo_location (07-03)
- require_auth reads APP_PASSWORD at call time (not capture time) — allows monkeypatching in tests (08-02)
- @require_auth stacked below @app.route so Flask registers original function name (avoids 404s on protected routes) (08-02)
- hmac.compare_digest used instead of == for constant-time timing-safe password comparison (08-02 AUTH-07)
- Username hardcoded as 'admin' per D-03 — no APP_USERNAME env var to keep auth surface minimal (08-02)
- blur_radius module-level global initialized from DEFAULT_CONFIG; scale_img_in_memory reads globals directly so module-level init is required for test isolation (09-02)
- BG-06 test fixed to use gradient image — GaussianBlur of uniform solid color produces identical output regardless of radius; only non-uniform images reveal blur radius differences (09-02)
- fill branch in load_scaled() completely unchanged; blur logic added only to fit (else) branch (09-02)
- max(bg_width, EPD_W) + max(bg_height, EPD_H) guards in background resize prevent edge artifacts from undersize background (09-02)
- cpy.pyx retains Image.LANCZOS (not Image.Resampling.LANCZOS) — required to avoid Cython compile errors; mirrors cpy_fallback.py logic otherwise identically (09-03)
- blur_radius slider in settings.html uses step=5, range 5-80, default 30; reset function uses nextElementSibling.textContent pattern matching existing sliders (09-03)

## Phase 9 Plan Status

| Plan | Name | Status |
|------|------|--------|
| 09-01 | TDD RED contract tests (BG-01..BG-06) | complete |
| 09-02 | Blur-fill background implementation + blur_radius config wiring | complete |
| 09-03 | cpy.pyx mirror + settings UI slider | complete |

## Phase 8 Plan Status

| Plan | Name | Status |
|------|------|--------|
| 08-01 | TDD RED contract tests (AUTH-01..AUTH-08) | complete |
| 08-02 | require_auth decorator + APP_PASSWORD + documentation | complete |
| 08-03 | Arduino HTTPClient auth + firmware documentation | not started |

## Phase 6 Plan Status

| Plan | Name | Status |
|------|------|--------|
| 06-01 | TDD RED contract tests (TC-01..TC-09) | complete |
| 06-02 | OVERLAY_COLORS, config schema, extended draw_date_overlay() | complete |
| 06-03 | UI/POST wiring and settings.html | complete |

## Phase 7 Plan Status

| Plan | Name | Status |
|------|------|--------|
| 07-01 | TDD RED contract tests (GEO-01..GEO-12) | complete |
| 07-02 | extract_gps_from_exif, reverse_geocode_cached, parse_photo_location | complete |
| 07-03 | Wire immich_exif_raw into scale_img_in_memory + settings UI | complete |

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260601-tat | Add geo overlay toggle to settings — allow showing date, location, both, or neither | 2026-06-01 | 6cdb4dd | [260601-tat-add-geo-overlay-toggle-to-settings-allow](.planning/quick/260601-tat-add-geo-overlay-toggle-to-settings-allow/) |
| 260601-udz | Add language switching for geo-location overlay | 2026-06-01 | 532bcb5 | [260601-udz-add-language-switching-for-geo-location-](.planning/quick/260601-udz-add-language-switching-for-geo-location-/) |

## Accumulated Context

### Roadmap Evolution

- Phase 6 added: Text customization — colors, styles, and border mode (timestamp background color, text color, border style option with configurable border/text color; all exposed in Configuration UI)
- Phase 7 added: Geolocation overlay from image metadata — extend overlay to show rough location from EXIF/Immich API; fall back to timestamp if no geo info present
- Phase 8 added: Auth — secure access to the app so it's not simply open in the local network without any access control
- Phase 9 added: Blurred background behind image when using fit-width or fit-height modes
