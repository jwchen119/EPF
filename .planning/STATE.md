---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Milestone complete
last_updated: "2026-05-28T09:03:00.523Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 11
  completed_plans: 11
---

# Project State

## Current Position

Phase: 04
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
