---
phase: 08-auth
plan: 02
subsystem: auth
tags: [flask, http-basic-auth, hmac, python, security]

# Dependency graph
requires:
  - phase: 08-01
    provides: tests/test_auth.py with 11 failing RED contract tests for HTTP Basic Auth
provides:
  - require_auth decorator with hmac.compare_digest timing-safe password check
  - APP_PASSWORD module global read from environment (opt-in, empty = open)
  - All 4 Flask routes (/, /setting, /download, /sleep) protected by @require_auth
  - compose.yml commented APP_PASSWORD example
  - .env.example with IMMICH_API_KEY and APP_PASSWORD placeholders
  - README.md Access Control subsection documenting admin username and opt-in behavior
affects: [08-03, arduino-firmware]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Opt-in HTTP Basic Auth via module global APP_PASSWORD — empty/absent means open access (backward compatible)"
    - "require_auth decorator stacked below @app.route (Flask registration order preserved)"
    - "hmac.compare_digest for constant-time password comparison (timing-attack safe)"
    - "app.logger.warning on failed auth attempts with client IP"

key-files:
  created:
    - .env.example
  modified:
    - app.py
    - compose.yml
    - README.md

key-decisions:
  - "require_auth reads APP_PASSWORD at call time (not capture time) — allows monkeypatching in tests"
  - "@require_auth stacked below @app.route so Flask registers the original function name (avoids 404s)"
  - "Username hardcoded as 'admin' per D-03 — no APP_USERNAME env var"
  - "hmac.compare_digest used instead of == to prevent timing oracle attacks"

patterns-established:
  - "Auth decorator pattern: @app.route on top, @require_auth directly below"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-07, AUTH-08]

# Metrics
duration: 15min
completed: 2026-06-02
---

# Phase 8 Plan 02: HTTP Basic Auth Implementation Summary

**opt-in HTTP Basic Auth via require_auth Flask decorator using hmac.compare_digest, protecting all 4 routes, with APP_PASSWORD env var documented in compose.yml, .env.example, and README**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-02T07:40:00Z
- **Completed:** 2026-06-02T07:55:40Z
- **Tasks:** 2
- **Files modified:** 4 (app.py, compose.yml, README.md, .env.example created)

## Accomplishments
- Added require_auth decorator with constant-time hmac.compare_digest, WARNING-level logging on failure, and 401 + WWW-Authenticate: Basic realm="EPF" response
- Protected all 4 Flask routes (/, /setting, /download, /sleep) with @require_auth
- APP_PASSWORD module global reads from environment; empty/absent means open access (zero behavior change for existing deployments)
- All 11 contract tests from 08-01 GREEN; full 50-test suite passes with no regressions

## Task Commits

1. **Task 1: Add require_auth decorator + APP_PASSWORD, protect 4 routes** - `ec7f870` (feat)
2. **Task 2: Document APP_PASSWORD in compose.yml, .env.example, and README** - `dcf794e` (docs)

## Files Created/Modified
- `app.py` - Added import hmac, from functools import wraps, make_response; APP_PASSWORD global; require_auth decorator; @require_auth on all 4 routes
- `compose.yml` - Added commented APP_PASSWORD example in environment block
- `.env.example` - New file with IMMICH_API_KEY and APP_PASSWORD placeholders
- `README.md` - Added ### Access Control subsection documenting opt-in behavior and fixed admin username

## Decisions Made
- require_auth reads `APP_PASSWORD` at call time (not as a default argument) so monkeypatching `app_module.APP_PASSWORD` in tests works correctly
- @require_auth stacked directly below @app.route (not above) so Flask registers the original function name and URL routing remains correct
- Username hardcoded as 'admin' per D-03 — no configurable APP_USERNAME to keep the auth surface minimal
- hmac.compare_digest used instead of == to prevent timing oracle attacks

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Worktree was behind feature/auth branch (missing plan files and test_auth.py from 08-01). Resolved by merging feature/auth into the worktree branch before starting implementation.

## User Setup Required
None - no external service configuration required. APP_PASSWORD is opt-in; existing deployments unchanged.

## Next Phase Readiness
- HTTP Basic Auth fully implemented and tested; ready for Plan 08-03 (Arduino HTTPClient auth + ESP32 firmware documentation)
- All 11 auth contract tests GREEN; no regressions in existing 39 overlay/geo/date tests

---
*Phase: 08-auth*
*Completed: 2026-06-02*
