---
phase: 08-auth
plan: 01
subsystem: auth
tags: [pytest, http-basic-auth, tdd, flask, monkeypatch]

# Dependency graph
requires:
  - phase: 07-geolocation-overlay-from-image-metadata
    provides: test conventions — import app as app_module + monkeypatch pattern
provides:
  - 8 failing contract tests (AUTH-01..AUTH-08) for HTTP Basic Auth decorator in app.py
affects: [08-02-PLAN, 08-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD RED — contract tests written before implementation, import-and-monkeypatch pattern for Flask module globals, _basic_header() helper for Base64 auth headers]

key-files:
  created: [tests/test_auth.py]
  modified: []

key-decisions:
  - "monkeypatch.setattr(app_module, 'APP_PASSWORD', ...) requires raising=False NOT needed since APP_PASSWORD is checked at fixture setup — tests are RED by design"
  - "test_app_password_loaded_from_env uses importlib.reload() to re-read os.getenv after monkeypatch.setenv() — consistent with module-level os.getenv pattern"
  - "parametrize over ['/', '/setting', '/download', '/sleep'] locks the four exact routes that Plan 02 must protect"

patterns-established:
  - "Auth test fixtures: auth_client (APP_PASSWORD='secret') and open_client (APP_PASSWORD='') mirror prior geo overlay fixture conventions"
  - "_basic_header() helper encodes Base64 Authorization header — reusable by Plan 02 integration tests if needed"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-06, AUTH-08]

# Metrics
duration: 8min
completed: 2026-06-02
---

# Phase 8 Plan 01: HTTP Basic Auth — TDD RED contract tests Summary

**8 failing pytest contracts lock the HTTP Basic Auth interface (APP_PASSWORD env var, require_auth decorator, WWW-Authenticate: Basic realm="EPF", 4-route protection) before any implementation exists**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-02T07:00:00Z
- **Completed:** 2026-06-02T07:08:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `tests/test_auth.py` with 8 test functions covering AUTH-01..AUTH-08
- Tests are confirmed RED: `AttributeError: module 'app' has no attribute 'APP_PASSWORD'`
- Contract values locked: username `admin`, realm `"EPF"`, opt-in empty-password behavior, 4 protected routes

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/test_auth.py with 8 failing contract tests (RED)** - `bfdb857` (test)

**Plan metadata:** _(final docs commit below)_

## Files Created/Modified
- `tests/test_auth.py` - 8 failing tests for AUTH-01..AUTH-08; auth_client/open_client fixtures; _basic_header() helper; module docstring mapping req IDs to behaviors

## Decisions Made
- `monkeypatch.setattr(app_module, 'APP_PASSWORD', 'secret')` used over env var approach since the fixture targets already-loaded module globals — consistent with geo overlay test pattern
- `importlib.reload(app_module)` in `test_app_password_loaded_from_env` is the correct pattern to test that module-level `os.getenv()` is re-read after env change
- `'uth' in record.getMessage()` substring check for the logging test accepts both "Auth failed" and "auth" — flexible but contracts the WARNING level requirement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 08-01 complete — tests/test_auth.py is the GREEN target for Plan 08-02
- Plan 08-02 must add `APP_PASSWORD = os.getenv('APP_PASSWORD', '')` (after line 329 in app.py) and `require_auth` decorator applied to 4 routes
- Plan 08-03 will add Arduino `HTTPClient` Basic Auth header sending + regression tests

---
*Phase: 08-auth*
*Completed: 2026-06-02*
