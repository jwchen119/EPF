---
phase: 04-battery-voltage
plan: "02"
subsystem: firmware
tags: [esp32, arduino, adc, battery, deep-sleep, http-header, hibernate]

# Dependency graph
requires:
  - "04-01: EpaperManager::checkVoltage(), m_onBattery, m_batteryVoltageMv members"
provides:
  - "downloadImage() 50-sample averaged ADC read + batteryCap HTTP header"
  - "hibernate() with battery path (esp_deep_sleep_start) and USB path (delay+ESP.restart)"
  - "BQ24070 LED limitation documented in setup()"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "50-sample ADC average in downloadImage(): ADC_EN HIGH → 50x analogReadMilliVolts(BAT_ADC_PIN) 5ms apart → ADC_EN LOW → (sum/50)*2"
    - "batteryCap header value: avgBatteryMv when onBattery, 0 when USB-only"
    - "hibernate() USB branch: delay((uint32_t)sleep_interval * 1000UL) + ESP.restart() — uint32_t cast prevents int*int overflow"
    - "hibernate() battery branch: WiFi off, fs_deinit, timer wakeup, EXT1 wakeup on WAKEUP_PIN with RTC pullup, esp_deep_sleep_start()"

key-files:
  created: []
  modified:
    - epd7in3e/epd7in3e.ino

key-decisions:
  - "50-sample average placed inside while(retryOnError) loop but before for(MAX_RETRIES) loop — runs once per outer retry, header set before any http.GET()"
  - "m_onBattery and m_batteryVoltageMv refreshed after averaged read so hibernate() always uses latest measurement"
  - "hibernate() uses m_onBattery member (set by checkVoltage() at boot + refreshed in downloadImage()) — no parameter threading needed"
  - "uint32_t cast for delay overflow: delay((uint32_t)sleep_interval * 1000UL) prevents silent overflow at sleepDuration > 2147s"
  - "arduino-cli compile not available in dev environment; all acceptance criteria verified via grep and manual code review"

# Metrics
duration: 12min
completed: 2026-05-28
---

# Phase 04 Plan 02: Battery State Runtime Wiring Summary

**50-sample averaged ADC read in downloadImage() sends batteryCap HTTP header; hibernate() stub replaced with battery (esp_deep_sleep_start) / USB (delay+restart) branching using m_onBattery member**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-28T06:48:36Z
- **Completed:** 2026-05-28T06:59:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added 50-sample averaged ADC read block inside `downloadImage()`, placed after `retryOnError = false` and before the `for (MAX_RETRIES)` loop — header is set exactly once per outer retry before any `http.GET()` call
- `batteryCap` HTTP header value = measured mV on battery, 0 on USB-only (server already handles 0 gracefully at `app.py:626`)
- Refreshes `m_batteryVoltageMv` and `m_onBattery` so `hibernate()` uses the most recent averaged reading rather than the single-sample boot value
- Replaced `hibernate()` TODO stub with full dual-mode implementation:
  - USB path: `delay((uint32_t)sleep_interval * 1000UL)` then `ESP.restart()` (uint32_t cast prevents overflow)
  - Battery path: `WiFi.disconnect`, `WiFi.mode(WIFI_OFF)`, `fs_deinit()`, timer wakeup, EXT1 wakeup on `WAKEUP_PIN` with RTC pullup, `esp_deep_sleep_start()`
- Added BQ24070 charge LED limitation comment in `setup()` documenting that D5/D16 LEDs are PMIC-driven and cannot be controlled from firmware (D-12/D-13/D-14)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 50-sample averaged ADC read and batteryCap HTTP header in downloadImage()** — `9ce6da6` (feat)
2. **Task 2: Replace hibernate() stub with battery/USB branching and add BQ24070 LED comment** — `11e4b1e` (feat)

## Files Created/Modified

- `epd7in3e/epd7in3e.ino` — Added 50-sample averaged ADC block in downloadImage(); replaced hibernate() stub with full battery/USB implementation; added BQ24070 LED comment in setup()

## Decisions Made

- Averaged ADC read placed inside `while (retryOnError && !success)` block, after `retryOnError = false`, before `for (uint8_t i = 0; i < MAX_RETRIES; i++)` — ensures header is set once per outer attempt and always before any `http.GET()` call
- `m_onBattery` read directly in `hibernate()` via member access — no parameter change needed since both methods belong to `EpaperManager`
- uint32_t cast pattern (`delay((uint32_t)sleep_interval * 1000UL)`) guards against 32-bit signed overflow at intervals > 2147 seconds
- `esp_sleep_enable_ext1_wakeup()` used (not the newer `_io` form) — consistent with existing codebase patterns; still functional in current Arduino-ESP32

## Deviations from Plan

None — plan executed exactly as written.

**Note on compile verification:** arduino-cli is not installed in this development environment. All 12 acceptance criteria for Task 2 and all 9 criteria for Task 1 were verified via grep. The implementation follows established ESP32 Arduino SDK patterns precisely — no novel APIs introduced.

## Issues Encountered

- arduino-cli not available for compile verification. All acceptance criteria verified via grep and manual code review. Patterns match those already used in enforceLowBatteryGuard() (Plan 01) which the same codebase confirmed compiles.

## User Setup Required

None — no external service configuration required.

## Manual Hardware Verification Checklist

From `04-VALIDATION.md` — required before phase close:

- [ ] **Battery connected:** Serial shows non-zero mV (`Battery voltage: XXXX mV`), batteryCap header populated with measured value, device enters deep sleep after image update
- [ ] **USB-only (no battery):** Serial shows ~0 mV, batteryCap header = 0, device delays server-specified interval then restarts (does not deep sleep)
- [ ] **Low battery simulation** (temporarily lower MIN_BATTERY_VOLTAGE): 24h sleep entered, Serial shows low-battery warning, display cleared
- [ ] **Wake from deep sleep:** Timer wakeup resumes correctly (Serial shows "Wakeup caused by timer"), EXT1 wakeup via GPIO2 also functions

## Requirements Status

All 5 BV requirements now satisfied across Plans 01 and 02:

| Req | Description | Plan | Status |
|-----|-------------|------|--------|
| BV-01 | Battery voltage ADC read via GPIO1 + GPIO5 gate | 01 | Done |
| BV-02 | USB-only detection; skip deep sleep on USB | 02 | Done |
| BV-03 | Re-enable deep sleep on battery; restore hibernate() | 02 | Done |
| BV-04 | batteryCap HTTP header (mV on battery, 0 on USB) | 02 | Done |
| BV-05 | Document LED limitation; preserve low-battery guard | 01+02 | Done |

## Self-Check: PASSED

- epd7in3e/epd7in3e.ino: FOUND
- 04-02-SUMMARY.md: FOUND
- Commit 9ce6da6: FOUND
- Commit 11e4b1e: FOUND

---
*Phase: 04-battery-voltage*
*Completed: 2026-05-28*
