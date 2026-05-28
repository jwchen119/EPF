---
phase: 04-battery-voltage
plan: "01"
subsystem: firmware
tags: [esp32, arduino, adc, battery, deep-sleep, gpio]

# Dependency graph
requires: []
provides:
  - "BAT_ADC_PIN=1U, ADC_EN_PIN=5U, MIN_BATTERY_VOLTAGE=3050U constants in config.h"
  - "EpaperManager::checkVoltage() — GPIO5-gated single-sample ADC read on GPIO1, returns mV"
  - "EpaperManager::enforceLowBatteryGuard() — 24h deep sleep when battery < 3050 mV"
  - "EpaperManager::isOnBattery() / batteryVoltageMv() accessors for Plan 02 to consume"
  - "m_batteryVoltageMv and m_onBattery private state members populated at boot"
affects: [04-02-battery-voltage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ADC_EN gate: set OUTPUT + LOW before read, HIGH during read, LOW after to save power"
    - "analogSetAttenuation(ADC_11dB) before analogReadMilliVolts() to cover 0-2.1V divider range"
    - "1:1 voltage divider compensation: rawMv * 2 to recover VBAT from R28/R29 10kΩ pair"
    - "USB detection: vbatMv <= 1500 means no battery, guard is skipped"

key-files:
  created: []
  modified:
    - epd7in3e/config.h
    - epd7in3e/epd7in3e.ino

key-decisions:
  - "Single-sample read for low-battery guard (Plan 01); 50-sample average reserved for HTTP header in Plan 02"
  - "USB/battery detection threshold: vbatMv > 1500 mV means battery present"
  - "checkVoltage() and enforceLowBatteryGuard() placed in public: section after clearScreen()"
  - "hibernate() stub deliberately left intact — Plan 02 replaces it"
  - "arduino-cli compile not available in dev environment; all acceptance criteria verified via grep"

patterns-established:
  - "ADC_EN gate pattern: OUTPUT LOW → ADC_11dB → HIGH → delay(10) → read → LOW"
  - "Battery guard pattern: read voltage → gate on m_onBattery && below threshold → guard action"

requirements-completed: [BV-01, BV-05]

# Metrics
duration: 15min
completed: 2026-05-28
---

# Phase 04 Plan 01: Battery Voltage Reading Primitive Summary

**GPIO5-gated ADC read on GPIO1 with 1:1 divider compensation, 3050 mV low-battery guard, and 24h deep sleep enforcement added to EpaperManager before WiFi init**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-28T00:00:00Z
- **Completed:** 2026-05-28T00:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added BAT_ADC_PIN=1U, ADC_EN_PIN=5U, MIN_BATTERY_VOLTAGE=3050U to config.h following existing U-suffix convention
- Implemented checkVoltage(): GPIO5-gated ADC read with ADC_11dB attenuation, ×2 divider compensation, serial logging, and m_onBattery/m_batteryVoltageMv state storage
- Implemented enforceLowBatteryGuard(): clears screen, disables WiFi, enters 24h deep sleep when battery detected and below threshold
- Wired both calls into setup() before epaperManager.begin() — same placement as original firmware

## Task Commits

Each task was committed atomically:

1. **Task 1: Add battery pin and threshold defines to config.h** - `c47e5d1` (feat)
2. **Task 2: Implement checkVoltage() helper and integrate low-battery guard** - `5cbd06b` (feat)

## Files Created/Modified
- `epd7in3e/config.h` - Added BAT_ADC_PIN, ADC_EN_PIN, MIN_BATTERY_VOLTAGE defines in GPIO Configuration section
- `epd7in3e/epd7in3e.ino` - Added m_batteryVoltageMv/m_onBattery members; checkVoltage(), enforceLowBatteryGuard(), isOnBattery(), batteryVoltageMv() methods; setup() integration

## Decisions Made
- Single-sample read used for low-battery guard (matches original firmware design); 50-sample average deferred to Plan 02 for the HTTP header
- vbatMv > 1500 threshold for USB vs battery detection — when no battery, ADC reads ~0V through divider
- New public methods placed after existing clearScreen() to maintain natural code organization
- hibernate() stub deliberately left untouched as specified — Plan 02 will replace it

## Deviations from Plan

None - plan executed exactly as written.

**Note on compile verification:** arduino-cli is not installed in this development environment. All 15 acceptance criteria were verified via grep and manual code review. The implementation follows existing ESP32 Arduino SDK patterns precisely (analogSetAttenuation, analogReadMilliVolts, esp_sleep_enable_timer_wakeup, esp_deep_sleep_start are standard ESP32 Arduino APIs).

## Issues Encountered
- arduino-cli not available for compile verification. All acceptance criteria verified via grep. Code changes follow established patterns from the existing firmware — no novel APIs introduced.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can immediately consume: `epaperManager.isOnBattery()`, `epaperManager.batteryVoltageMv()`
- Plan 02 targets: replace hibernate() stub, add 50-sample averaged ADC read in downloadImage(), send batteryCap HTTP header
- No blockers identified

---
*Phase: 04-battery-voltage*
*Completed: 2026-05-28*
