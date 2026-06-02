---
plan: 08-03
phase: 08-auth
status: complete
completed: 2026-06-02
tasks_total: 2
tasks_completed: 2
checkpoint: human-verified
---

# Plan 08-03 Summary: Firmware Auth + Human Verification

## What Was Built

Added HTTP Basic Auth credentials to the ESP32 firmware so the device can authenticate against the now-protected server. Used `HTTPClient::setAuthorization()` — no manual base64 encoding. Password is a compile-time constant in `config.h`, matching the existing pattern for `SERVER_BASE_URL` and `HTTP_TIMEOUT`.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| Task 1 | Add APP_PASSWORD constant + setAuthorization to firmware | d0f9360 |
| Task 2 | Human verify browser auth dialog + device fetch | ✓ approved |

## Key Files

### Created
- (none)

### Modified
- `epd7in3e/config.h` — Added `#define APP_PASSWORD ""` compile-time constant
- `epd7in3e/epd7in3e.ino` — Added `http.setAuthorization("admin", APP_PASSWORD)` before both image download and sleep request GET calls
- `README.md` — Added Auth note to "Build and flash" section

## Verification Results

- ✓ `#define APP_PASSWORD` constant in config.h
- ✓ 2× `setAuthorization("admin", APP_PASSWORD)` calls in epd7in3e.ino (http + sleepHttp clients)
- ✓ Both setAuthorization calls placed after begin() and before GET() (correct order)
- ✓ Python test suite: 50 passed, no regressions
- ✓ Human verified: browser shows native auth dialog, admin credentials grant access, empty APP_PASSWORD leaves app open

## Human Verification

AUTH-09 (browser dialog): **Approved** — native browser auth dialog confirmed, admin/password grants access.
AUTH-10 (firmware E2E): User tested with `APP_PASSWORD "test"` set in config.h.

## Decisions

- `setAuthorization` placed immediately before `http.addHeader("batteryCap", ...)` in the image download flow — after both HTTPS/HTTP `begin()` branches converge, before `GET()` in the retry loop.
- `setAuthorization` placed immediately before `sleepHttp.addHeader("Accept", ...)` in the sleep flow.
- Username hardcoded as `"admin"` per AUTH-03 / D-03.
- Default `APP_PASSWORD ""` (empty = opt-in off, no auth required).

## Requirements Addressed

- AUTH-06: Firmware sends Basic Auth on /download and /sleep via setAuthorization
- AUTH-09: Browser native auth dialog confirmed by human
- AUTH-10: Device auth tested with hardware (APP_PASSWORD set in config.h)
