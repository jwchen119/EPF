---
phase: 04-battery-voltage
verified: 2026-05-28T09:15:00Z
status: human_needed
score: 9/9 automated must-haves verified
human_verification:
  - test: "Flash firmware to EE02 board with battery connected. Open Serial Monitor."
    expected: "Serial shows 'Battery voltage: XXXX mV' (3400-4200 mV range for charged cell); after image update device enters deep sleep; re-wakes on timer."
    why_human: "Cannot execute arduino-cli compile or flash hardware in dev environment; real ADC read requires physical hardware."
  - test: "Flash firmware to EE02 board USB-only (no battery attached). Open Serial Monitor."
    expected: "Serial shows 'Battery voltage: 0 mV' (or very low ~0-200 mV); batteryCap header = 0 visible in server log; device does NOT enter deep sleep — it delays then restarts."
    why_human: "USB vs battery path branching requires physical board without battery to exercise."
  - test: "Temporarily lower MIN_BATTERY_VOLTAGE to a value above the measured battery voltage (e.g., 4500U), flash, connect battery."
    expected: "Serial shows low-battery warning ('Battery low: XXXX mV < YYYY mV — sleeping 24h'), screen is cleared, device enters 24h deep sleep immediately (does not proceed to WiFi connect or image download)."
    why_human: "Low-battery guard requires hardware + bench modification to trigger safely."
  - test: "Capture HTTP request from device to server while on battery (e.g., via Wireshark or server log)."
    expected: "Request contains 'batteryCap: XXXX' header with a non-zero mV value matching Serial output."
    why_human: "HTTP header verification requires live network traffic capture against a running server."
---

# Phase 4: Battery Voltage Verification Report

**Phase Goal:** Restore battery voltage reading and power-aware behavior — read BAT_ADC on GPIO1 via GPIO5 gate, enforce low-battery sleep guard, send batteryCap HTTP header, and restore real hibernate() with USB/battery branching.
**Verified:** 2026-05-28T09:15:00Z
**Status:** human_needed (all automated checks PASS; hardware validation pending)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | config.h defines BAT_ADC_PIN=1U, ADC_EN_PIN=5U, MIN_BATTERY_VOLTAGE=3050U | VERIFIED | Lines 18-20 of epd7in3e/config.h, verbatim match |
| 2 | Firmware reads battery voltage via ADC on GPIO1 with GPIO5 ADC_EN gate | VERIFIED | checkVoltage() at line 486: pinMode(ADC_EN_PIN,OUTPUT), HIGH/delay(10)/analogReadMilliVolts(BAT_ADC_PIN)/LOW |
| 3 | Battery voltage is printed to Serial as 'Battery voltage: XXXX mV' during boot | VERIFIED | Line 499: Serial.printf("Battery voltage: %d mV\n", vbatMv) — called from setup() via checkVoltage() |
| 4 | If onBattery and voltage < 3050 mV firmware clears screen, disables WiFi, and enters 24h deep sleep | VERIFIED | enforceLowBatteryGuard() lines 510-519; called from setup() line 556 before begin() |
| 5 | downloadImage() does a 50-sample averaged ADC read and sends batteryCap HTTP header in mV | VERIFIED | Lines 92-115 of epd7in3e.ino — loop 50x analogReadMilliVolts, (plusV/50)*2, addHeader("batteryCap", String(headerValue)) |
| 6 | When USB-only (onBattery==false), batteryCap header value is 0 | VERIFIED | Line 109: int headerValue = avgOnBattery ? avgBatteryMv : 0 |
| 7 | hibernate() on battery enters real esp_deep_sleep_start() with timer + EXT1 wakeup | VERIFIED | Lines 325-343: WiFi off, fs_deinit, timer wakeup, rtc_gpio pullup, EXT1 wakeup on WAKEUP_PIN, esp_deep_sleep_start() |
| 8 | hibernate() on USB skips deep sleep, delays for sleepDuration seconds, then ESP.restart() | VERIFIED | Lines 313-320: !m_onBattery branch; delay((uint32_t)sleep_interval * 1000UL); ESP.restart() |
| 9 | BQ24070 charge LED limitation documented in code near setup() | VERIFIED | Lines 532-535: KNOWN HARDWARE LIMITATION comment with D5/D16, STAT1/STAT2 attribution |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `epd7in3e/config.h` | BAT_ADC_PIN=1U, ADC_EN_PIN=5U, MIN_BATTERY_VOLTAGE=3050U | VERIFIED | All three defines present at lines 18-20; header guard intact |
| `epd7in3e/epd7in3e.ino` | checkVoltage(), enforceLowBatteryGuard(), isOnBattery(), batteryVoltageMv() methods; setup() integration | VERIFIED | Methods at lines 486, 510, 505, 506; setup() calls at lines 555-556 |
| `epd7in3e/epd7in3e.ino` | Restored hibernate() with USB/battery branching + batteryCap header in downloadImage() | VERIFIED | hibernate() at line 309 fully implemented; batteryCap block at lines 91-116 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| setup() | checkVoltage() + enforceLowBatteryGuard() | direct call before epaperManager.begin() | VERIFIED | Lines 555-556 confirmed before line 558 (if epaperManager.begin()) |
| checkVoltage() | ADC_EN_PIN HIGH/LOW gating | digitalWrite around analogReadMilliVolts | VERIFIED | Line 489 LOW, line 492 HIGH, line 495 LOW |
| downloadImage() | isOnBattery() / m_onBattery | branch on avgOnBattery to pick header value | VERIFIED | Line 108-109: avgOnBattery checked, headerValue set to 0 or mV |
| downloadImage() | http.addHeader("batteryCap", ...) | direct HTTPClient call before http.GET() | VERIFIED | Line 110 addHeader before line 120 http.GET() |
| hibernate() | esp_deep_sleep_start() | battery branch (m_onBattery == true) | VERIFIED | Line 343 inside battery path at lines 322-343 |
| hibernate() | ESP.restart() | USB branch after delay | VERIFIED | Line 320 inside !m_onBattery path at lines 313-320 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| checkVoltage() | rawMv / vbatMv | analogReadMilliVolts(BAT_ADC_PIN) with ADC_EN gate | Real ADC hardware read (cannot static-verify) | WIRED — code path complete; hardware verification pending |
| downloadImage() batteryCap | avgBatteryMv | 50x analogReadMilliVolts(BAT_ADC_PIN) averaged | Same ADC path, 50 samples | WIRED — code path complete; hardware verification pending |
| hibernate() m_onBattery | m_onBattery | Set by checkVoltage() at boot; refreshed in downloadImage() | Flows from ADC read → member state → hibernate() branch | VERIFIED flow path |

### Behavioral Spot-Checks

Step 7b: SKIPPED — firmware targets embedded ESP32 hardware; cannot execute arduino-cli compile or flash/run without physical board in this environment. All acceptance criteria verified via grep as documented in both SUMMARY files.

| Behavior | Method | Result | Status |
|----------|--------|--------|--------|
| BAT_ADC_PIN=1U, ADC_EN_PIN=5U, MIN_BATTERY_VOLTAGE=3050U in config.h | grep | exact match lines 18-20 | PASS |
| checkVoltage() exists and calls analogReadMilliVolts(BAT_ADC_PIN) | grep | line 494 | PASS |
| 50-sample averaged read in downloadImage() before http.GET() | grep + line order | lines 102-120 confirmed before line 120 | PASS |
| batteryCap header inserted before http.GET() | grep + line order | addHeader line 110 before GET() line 120 | PASS |
| hibernate() TODO stub removed | grep | 0 matches for "TODO: re-enable deep sleep" | PASS |
| hibernate() USB path: delay + ESP.restart() | grep | line 319-320 | PASS |
| hibernate() battery path: esp_deep_sleep_start() | grep | line 343 | PASS |
| EXT1 wakeup on WAKEUP_PIN with RTC pullup | grep | lines 336-338 | PASS |
| checkVoltage() + enforceLowBatteryGuard() called before epaperManager.begin() in setup() | grep + line order | lines 555, 556, 558 | PASS |
| BQ24070 LED limitation comment present | grep | lines 532-535 | PASS |
| Commits c47e5d1, 5cbd06b, 9ce6da6, 11e4b1e exist in git log | git log | all 4 commits confirmed on feature/battery-voltage | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| BV-01 | 04-01 | Battery voltage ADC read via GPIO1 + GPIO5 gate | SATISFIED | checkVoltage() with ADC_EN gating; analogSetAttenuation(ADC_11dB); rawMv*2 divider compensation |
| BV-02 | 04-02 | USB-only detection; skip deep sleep on USB | SATISFIED | hibernate() !m_onBattery branch: delay + ESP.restart(), no deep sleep |
| BV-03 | 04-02 | Re-enable deep sleep on battery; restore hibernate() | SATISFIED | hibernate() battery path: WiFi off, fs_deinit, timer + EXT1 wakeup, esp_deep_sleep_start() |
| BV-04 | 04-02 | batteryCap HTTP header (mV on battery, 0 on USB) | SATISFIED | downloadImage() addHeader("batteryCap", String(headerValue)); headerValue=0 on USB |
| BV-05 | 04-01 + 04-02 | Document LED limitation; preserve low-battery guard | SATISFIED | enforceLowBatteryGuard() present; BQ24070 comment at lines 532-535 with D5/D16 and STAT1/STAT2 |

No orphaned requirements — all 5 BV-01..BV-05 are claimed in plan frontmatter (04-01: BV-01, BV-05; 04-02: BV-02, BV-03, BV-04) and verified in code.

No REQUIREMENTS.md file exists in .planning/ — requirement definitions are sourced from ROADMAP.md Phase 4 entry and plan frontmatter. No orphan risk.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | — |

No anti-patterns detected. The original `TODO: re-enable deep sleep` stub is fully removed (0 matches). No empty implementations, placeholders, or hardcoded empty returns found in modified sections.

Note: A second `ESP.restart()` exists at line 569 (inside config portal timeout handler) — this is pre-existing, unrelated to Phase 4, and not a stub.

### Human Verification Required

#### 1. Battery-connected boot path

**Test:** Flash current firmware to EE02 board with a LiPo battery connected. Open Serial Monitor at 115200 baud.
**Expected:** Serial shows "Battery voltage: XXXX mV" (3400-4200 mV for a charged cell), followed by normal boot. After image update completes, device enters deep sleep ("Entering deep sleep..."). Timer wakeup resumes correctly ("Wakeup caused by timer").
**Why human:** analogReadMilliVolts() returns hardware ADC values; cannot verify without physical ESP32-S3 + battery circuit.

#### 2. USB-only (no battery) path

**Test:** Flash firmware to EE02 board with no battery — USB power only. Open Serial Monitor.
**Expected:** Serial shows "Battery voltage: 0 mV" (or very low value <=1500 mV), "Power source: USB". After image update, device delays SLEEP_INTERVAL seconds then restarts — does NOT enter deep sleep.
**Why human:** The USB vs battery detection threshold (1500 mV) depends on real ADC hardware behaviour.

#### 3. Low-battery guard (24h sleep)

**Test:** Temporarily change MIN_BATTERY_VOLTAGE to 4500U in config.h, flash to board with battery connected.
**Expected:** Serial shows "Battery low (XXXX mV < 4500 mV) — sleeping 24h", display is cleared, device immediately enters 24h deep sleep. Device does not connect to WiFi or download an image.
**Why human:** Requires hardware + temporary code modification to simulate the low-battery condition.

#### 4. batteryCap HTTP header on live traffic

**Test:** With battery connected, capture HTTP request from device to server (server log or network proxy). Observe the batteryCap header value.
**Expected:** Header value matches the Serial output "HTTP batteryCap header: XXXX mV (onBattery=true)". On USB-only, header value is "0".
**Why human:** Header transmission verification requires live network traffic between device and server.

### Gaps Summary

No automated gaps found. All 9 observable truths verified, all 5 requirements satisfied, all key links confirmed wired, all commits verified present in git history. The phase goal is fully implemented in firmware source.

The only open items are hardware validation tests (items 1-4 above) that require physical flashing and observation — these are documented in 04-VALIDATION.md and are expected manual steps for this embedded firmware phase.

---

_Verified: 2026-05-28T09:15:00Z_
_Verifier: Claude (gsd-verifier)_
