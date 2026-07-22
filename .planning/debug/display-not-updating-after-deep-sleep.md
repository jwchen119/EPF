---
status: awaiting_human_verify
trigger: "Display not updating — HTTP GET fails, device enters deep sleep for 3600s"
created: 2026-06-28T00:00:00Z
updated: 2026-06-28T00:00:00Z
symptoms_prefilled: true
---

## Current Focus

hypothesis: CONFIRMED — two bugs found and fixed.
test: Code path traced fully through downloadImage() failure branch
expecting: n/a — fix applied
next_action: Human verification on device

## Symptoms

expected: Display updates with current data after waking from deep sleep
actual: HTTP GET fails (empty error), device goes to deep sleep for 3600s without updating display
errors:
  - "HTTP batteryCap header: 3902 mV (onBattery=true)"
  - "HTTP GET failed: " (empty error message)
  - "Battery power: entering deep sleep for 3600 s"
reproduction: Device runs on battery, triggers HTTP GET, fails, sleeps 3600s, display never updates
timeline: Unknown — user reported as current issue

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-06-28T00:00:00Z
  checked: epd7in3e.ino downloadImage() control flow
  found: |
    When http.GET() returns an httpCode that is not HTTP_CODE_OK (200), HTTP_CODE_ACCEPTED (202),
    or HTTP_CODE_INTERNAL_SERVER_ERROR (500), the else branch runs:
      Serial.printf("%s GET failed: %s\n", ..., http.errorToString(httpCode).c_str());
      break;
    This breaks from the retry for-loop. retryOnError remains false (set at top of while).
    The while loop exits. success remains false. sleepDuration remains 0.
    Then at line 206-214: if (success && sleepDuration > 0) -> hibernate(sleepDuration) ELSE -> hibernate().
    hibernate() with no args uses default SLEEP_INTERVAL = 3600s. This is called unconditionally at the
    END of downloadImage(), regardless of whether success is true or false.
  implication: Every call to downloadImage() ends in hibernate(). Display is never updated on failure.

- timestamp: 2026-06-28T00:00:00Z
  checked: errorToString with positive HTTP response codes
  found: |
    ESP32 HTTPClient::errorToString() ONLY maps negative HTTPC_ERROR_* codes (< 0).
    For POSITIVE http codes (like 401, 403, 404), it returns "" (empty string).
    The log "HTTP GET failed: " (empty after colon) confirms httpCode is a POSITIVE HTTP status
    code — not a connection-level error. The device IS reaching the server, but the server
    returns a 4xx error. The most likely cause: APP_PASSWORD is "" (empty) in config.h,
    but http.setAuthorization("admin", "") sets Basic Auth with empty password. If the
    server requires actual authentication, all requests return 401 Unauthorized, which
    falls into the else-branch (not 200, 202, 500) and prints empty errorToString.
  implication: Server returns 4xx (likely 401). The fix must handle positive non-success codes
               by printing the actual httpCode integer, not errorToString.

- timestamp: 2026-06-28T00:00:00Z
  checked: update() method flow after downloadImage() fails
  found: |
    update() calls downloadImage(). downloadImage() internally calls hibernate() before returning.
    So hibernate() is called inside downloadImage() ALWAYS (line 206-214). Then update() continues
    to line 443: "Entering sleep mode" / hibernate() — but deep sleep has already been entered,
    so this second call never executes. The display update path is entirely inside downloadImage()
    and only runs on HTTP_CODE_OK with valid image data.
  implication: The architecture bundles sleep into the download function. On failure, the device
               sleeps 3600s with no display update and no retry mechanism for the current cycle.

- timestamp: 2026-06-28T00:00:00Z
  checked: config.h SERVER_BASE_URL
  found: |
    config.h defines SERVER_BASE_URL as a compile-time constant "http://server.ip:15001".
    However, downloadImage() reads the URL from preferences: imageUrl = preferences.getString("SERVER_BASE_URL").
    If preferences "SERVER_BASE_URL" key was never written, getString returns "" (empty string).
    An empty URL would cause http.begin() to fail or http.GET() to return a connection error.
    The batteryCap header log shows 3902 mV so battery reading is working. The GET failure with
    empty error suggests a connection failure rather than HTTP-level error.
  implication: If the preferences key "SERVER_BASE_URL" is empty or wrong, every GET would fail
               and produce exactly the observed symptom.

## Resolution

root_cause: |
  Two bugs:
  1. PRIMARY BUG — On HTTP GET failure, downloadImage() called hibernate() with no args (default
     SLEEP_INTERVAL = 3600s). This meant a transient server error / wrong config caused the device
     to sleep the full hour without displaying anything or retrying sooner.
  2. DIAGNOSTIC BUG — The failure log used http.errorToString(httpCode) which only maps negative
     HTTPC_ERROR_* codes. For positive HTTP status codes (401, 403, 404, etc.), it returns "".
     This produced the observed "HTTP GET failed: " (empty) log, hiding the actual HTTP response code.
     The server IS reachable — it returns a positive HTTP error code, not a connection-level failure.
     Most likely cause: APP_PASSWORD mismatch between server .env and firmware config.h, causing 401.
fix: |
  1. Changed error log to print actual httpCode integer:
       "HTTP GET failed (code %d): %s" — now shows e.g. "HTTP GET failed (code 401): "
     This will reveal the true server response on next boot.
  2. Changed failure sleep to MIN_SLEEP_TIME (900s) instead of SLEEP_INTERVAL (3600s):
       else { hibernate((int)MIN_SLEEP_TIME); }
     Device now retries in 15 minutes instead of 1 hour on any download failure.
verification: (pending human verification)
files_changed:
  - epd7in3e/epd7in3e.ino
