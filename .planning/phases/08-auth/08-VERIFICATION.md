---
phase: 08-auth
verified: 2026-06-02T00:00:00Z
status: passed
score: 9/10 must-haves verified
human_verification:
  - test: "Browser native auth dialog appears and credentials work end-to-end"
    expected: "Browser shows native username/password dialog on any protected route; admin + APP_PASSWORD grants access; cancelling returns 401; restarting without APP_PASSWORD leaves app open"
    why_human: "AUTH-09 requires a browser to observe the native dialog triggered by WWW-Authenticate header — cannot be verified programmatically"
  - test: "ESP32 firmware authenticates against password-protected server"
    expected: "Device fetches and displays image successfully when server has APP_PASSWORD set and firmware has matching APP_PASSWORD constant; serial log shows HTTP 200, not 401"
    why_human: "AUTH-10 requires physical XIAO ESP32-S3 hardware — cannot be verified in CI"
---

# Phase 8: Auth Verification Report

**Phase Goal:** Add opt-in HTTP Basic Auth to all Flask routes and ESP32 firmware — zero change to existing deployments when APP_PASSWORD is unset.
**Verified:** 2026-06-02
**Status:** human_needed (all automated checks passed; AUTH-09 and AUTH-10 require human/hardware)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | When APP_PASSWORD is set, all 4 routes return 401 + WWW-Authenticate: Basic realm="EPF" without credentials | VERIFIED | 11/11 pytest tests pass, including parametrized test_all_routes_require_auth across /, /setting, /download, /sleep |
| 2 | Correct admin:APP_PASSWORD credentials grant access (200) | VERIFIED | test_protected_route_correct_credentials_returns_200 passes |
| 3 | When APP_PASSWORD is empty/absent, all routes are open (backward compatible) | VERIFIED | test_no_password_set_allows_access passes; require_auth short-circuits on empty string |
| 4 | Failed auth attempts are logged at WARNING level | VERIFIED | test_failed_auth_is_logged passes; app.logger.warning at app.py:390 |
| 5 | APP_PASSWORD documented in compose.yml, .env.example, and README.md | VERIFIED | All three files contain APP_PASSWORD; README has Access Control section at line 118 |
| 6 | Firmware sends HTTP Basic Auth credentials on /download and /sleep | VERIFIED | setAuthorization("admin", APP_PASSWORD) at epd7in3e.ino:112 (http client) and :148 (sleepHttp client), both before GET() |
| 7 | When APP_PASSWORD is empty in config.h, firmware behavior is unchanged | VERIFIED | config.h defines APP_PASSWORD "" (empty string default); setAuthorization with empty password is harmless against open server |
| 8 | Password comparison uses hmac.compare_digest (constant-time, no timing leak) | VERIFIED | hmac.compare_digest at app.py:388 |
| 9 | Browser shows native auth dialog (AUTH-09) | HUMAN NEEDED | Cannot verify programmatically — requires browser observation; SUMMARY records human approval |
| 10 | ESP32 device authenticates and fetches image against protected server (AUTH-10) | HUMAN NEEDED | Requires physical hardware; SUMMARY records human tested with APP_PASSWORD "test" |

**Score:** 8/10 truths verified automatically; 2 require human/hardware (but SUMMARY records both as approved)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_auth.py` | 8 contract tests for AUTH-01..AUTH-08 | VERIFIED | 97 lines, 8 test functions (11 collected due to parametrize), all pass |
| `app.py` | require_auth decorator + APP_PASSWORD global + 4 protected routes | VERIFIED | import hmac (line 2), from functools import wraps (line 9), make_response in flask import (line 16), APP_PASSWORD = os.getenv (line 332), def require_auth (line 376), 4× @require_auth (lines 850, 955, 1128, 1161) |
| `compose.yml` | Commented APP_PASSWORD env var example | VERIFIED | Line 8: `# - APP_PASSWORD=your-password-here   # Uncomment and set to enable HTTP Basic Auth (username: admin)` |
| `.env.example` | APP_PASSWORD placeholder for local dev | VERIFIED | File exists, line 8: `APP_PASSWORD=` with explanatory comments |
| `epd7in3e/config.h` | APP_PASSWORD compile-time constant | VERIFIED | Lines 35-36: `#define APP_PASSWORD ""` with comment explaining usage |
| `epd7in3e/epd7in3e.ino` | setAuthorization on both http and sleepHttp clients | VERIFIED | Line 112 (http client), line 148 (sleepHttp client) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `@app.route('/setting')` | `require_auth` | decorator stacked below @app.route | WIRED | Lines 849-850: @app.route then @require_auth, correct order |
| `@app.route('/')` | `require_auth` | decorator stacked below @app.route | WIRED | Lines 954-955 |
| `@app.route('/download')` | `require_auth` | decorator stacked below @app.route | WIRED | Lines 1127-1128 |
| `@app.route('/sleep')` | `require_auth` | decorator stacked below @app.route | WIRED | Lines 1160-1161 |
| `require_auth` | `request.authorization + hmac.compare_digest` | constant-time password comparison | WIRED | app.py:388: `hmac.compare_digest(auth.password or '', APP_PASSWORD)` |
| `epd7in3e.ino http client` | `config.h APP_PASSWORD` | `http.setAuthorization("admin", APP_PASSWORD)` after begin(), before GET() | WIRED | Line 112 before line 123 (http.GET()) |
| `epd7in3e.ino sleepHttp client` | `config.h APP_PASSWORD` | `sleepHttp.setAuthorization("admin", APP_PASSWORD)` after begin(), before GET() | WIRED | Line 148 before line 150 (sleepHttp.GET()) |

All key links verified. Decorator order is correct: @app.route is topmost so Flask registers the original function name; @require_auth sits below.

---

### Data-Flow Trace (Level 4)

Not applicable — this phase implements an auth guard (decorator pattern), not a data-rendering component. The decorator reads `APP_PASSWORD` from the module global at call time (not captured at definition time), which is the correct pattern for monkeypatch to work in tests. Verified the module-level read at app.py:332 and confirmed test_app_password_loaded_from_env passes (importlib.reload picks up env change).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Auth tests all pass | `python -m pytest tests/test_auth.py -v` | 11 passed in 0.28s | PASS |
| Full suite no regressions | `python -m pytest tests/ -q` | 50 passed in 1.96s | PASS |
| require_auth defined in app.py | `grep -q "def require_auth" app.py` | found at line 376 | PASS |
| 4 routes decorated | `grep -c "@require_auth" app.py` | 4 | PASS |
| hmac.compare_digest used | `grep -q "hmac.compare_digest" app.py` | found at line 388 | PASS |
| 2 setAuthorization calls in firmware | `grep -c 'setAuthorization' epd7in3e/epd7in3e.ino` | 2 | PASS |
| setAuthorization before http.GET() | line 112 vs 123 | 112 < 123 | PASS |
| setAuthorization before sleepHttp.GET() | line 148 vs 150 | 148 < 150 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-01 | 08-01, 08-02 | require_auth passes request through when APP_PASSWORD is empty (opt-in) | SATISFIED | test_no_password_set_allows_access passes; app.py:385 `if not APP_PASSWORD: return f(...)` |
| AUTH-02 | 08-01, 08-02 | Unauthenticated/wrong-credential requests get 401 + WWW-Authenticate: Basic realm="EPF" | SATISFIED | test_protected_route_no_credentials_returns_401, test_401_includes_www_authenticate_header, test_wrong_password_returns_401 all pass |
| AUTH-03 | 08-01, 08-02 | All four routes protected: /, /setting, /download, /sleep | SATISFIED | test_all_routes_require_auth parametrized across all 4 routes, all pass; 4× @require_auth confirmed |
| AUTH-04 | 08-01, 08-02 | APP_PASSWORD read from environment via os.getenv | SATISFIED | test_app_password_loaded_from_env passes; app.py:332 |
| AUTH-05 | 08-02 | APP_PASSWORD documented as commented example in compose.yml | SATISFIED | compose.yml line 8 contains commented APP_PASSWORD example |
| AUTH-06 | 08-03 | Firmware sends credentials on /download and /sleep via setAuthorization | SATISFIED | epd7in3e.ino:112 + :148 both confirmed |
| AUTH-07 | 08-02 | Password comparison uses hmac.compare_digest (constant-time) | SATISFIED | app.py:388 confirmed, no == comparison used |
| AUTH-08 | 08-01, 08-02 | Failed auth attempts logged at WARNING level | SATISFIED | test_failed_auth_is_logged passes; app.logger.warning at app.py:390 |
| AUTH-09 | 08-03 | Browser shows native auth dialog triggered by WWW-Authenticate header | NEEDS HUMAN | Cannot verify programmatically; SUMMARY records human approval |
| AUTH-10 | 08-03 | ESP32 device authenticates and fetches image against protected server | NEEDS HUMAN | Requires physical hardware; SUMMARY records human tested with APP_PASSWORD "test" |

All 10 requirement IDs accounted for. No orphaned requirements.

---

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| None | — | — | No stubs, TODOs, hardcoded empty returns, or placeholder patterns found in auth-related code |

The `require_auth` decorator is fully implemented with real logic (authorization header parsing, constant-time comparison, 401 response with WWW-Authenticate header, WARNING log). No placeholder returns detected.

Note: `config.h` has `#define APP_PASSWORD ""` (empty string default). This is intentional opt-in behavior per AUTH-01 and D-07 — not a stub. The SUMMARY confirms the human tester temporarily set it to `"test"` for hardware verification.

---

### Human Verification Required

#### 1. Browser Native Auth Dialog (AUTH-09)

**Test:** Start the Flask app with `APP_PASSWORD=test python app.py`. Open `http://localhost:5000/` (or the mapped port) in a browser. Observe whether the browser shows its native username/password dialog (not a plain HTML page).

**Expected:** The browser's native auth dialog appears. Entering username `admin` and password `test` loads the settings page. Cancelling returns a plain "Unauthorized" response. Restarting the app without `APP_PASSWORD` loads the page with no dialog.

**Why human:** The `WWW-Authenticate: Basic realm="EPF"` header is present and verified by pytest, but whether the browser renders its native dialog in response to that header cannot be verified programmatically. The 08-03-SUMMARY.md records human approval of this test.

#### 2. ESP32 Firmware End-to-End Authentication (AUTH-10)

**Test:** Flash the XIAO ESP32-S3 with `#define APP_PASSWORD "test"` in `epd7in3e/config.h`. Run the server with `APP_PASSWORD=test`. Confirm the device fetches and displays an image successfully (serial monitor shows HTTP 200, not 401).

**Expected:** Device authenticates using the hardcoded password, receives HTTP 200, and displays the image. If the passwords don't match, the serial log would show 401.

**Why human:** Requires physical hardware (XIAO ESP32-S3 on Seeed EE02 board). The 08-03-SUMMARY.md records that the human tester verified this with `APP_PASSWORD "test"`.

---

### Gaps Summary

No automated gaps. The phase goal is fully achieved for all programmatically-verifiable aspects:

- The Flask app's opt-in HTTP Basic Auth is fully implemented and tested (11 tests, all passing).
- The decorator ordering is correct (no Flask routing regression risk).
- Constant-time comparison via hmac.compare_digest prevents timing attacks.
- Documentation is in place in all three required locations (compose.yml, .env.example, README.md).
- The firmware sends credentials via setAuthorization on both /download and /sleep, before GET(), after begin().
- Zero regressions: all 50 existing tests pass.

The two human_needed items (AUTH-09, AUTH-10) are inherent to the nature of browser UI and embedded hardware — they cannot be automated. The 08-03-SUMMARY.md records both as approved/tested by the human.

---

_Verified: 2026-06-02_
_Verifier: Claude (gsd-verifier)_
