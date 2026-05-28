# Phase 4: Battery Voltage - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Restore battery voltage monitoring removed in Phase 1. The scope is:
- Read battery voltage via ADC on the XIAO ESP32-S3 Plus EE02 board
- Detect whether device is powered by battery or USB (by reading ADC: no battery → reads ~0V)
- Re-enable deep sleep when running on battery (remove the Phase 1 TODO stub)
- On USB power: skip deep sleep, instead wait the server-specified interval and refresh in a loop
- Send battery voltage to the server as the `batteryCap` HTTP header (mV, same as original)
- The green LEDs are hardware-controlled by the BQ24070 PMIC — **no software path to suppress them**; document as known limitation

**Server-side is already complete** — `app.py` already handles the `batteryCap` header, stores `last_battery_voltage`, performs piecewise linear interpolation against `BATTERY_LEVELS`, and displays % in the settings UI. No server changes needed.

</domain>

<decisions>
## Implementation Decisions

### Battery Voltage Reading — CONFIRMED FROM EE02 SCHEMATIC

- **D-01:** Battery ADC pin = **GPIO1** (A0/D0, XIAO pin 1) — this is the `BAT_ADC` net on the EE02 board
  - NOT GPIO0 (original FireBeetle) and NOT GPIO10 (XIAO's own VBAT pin, unused here)
  - Use `analogReadMilliVolts(1)` in Arduino
- **D-02:** ADC enable pin = **GPIO5** (A4/D4, XIAO pin 5) — the `ADC_EN` net drives U17 TPS22916CYFPR load switch
  - Must `digitalWrite(ADC_EN_PIN, HIGH)` before reading, then `LOW` after to save power
  - Add `#define BAT_ADC_PIN 1` and `#define ADC_EN_PIN 5` to `config.h`
- **D-03:** Voltage divider is 1:1 (R28=R29=10KΩ) → multiply ADC reading × 2 to get VBAT in mV
- **D-04:** Use `analogSetAttenuation(ADC_11dB)` before reading — needed to cover 0–2.1V range (4.2V battery → 2.1V after divider)
- **D-05:** Multi-sample average: 50 samples with 5ms delay (same as original), to reduce noise
- **D-06:** Send as `batteryCap` HTTP header in mV (integer) — matches existing server handler at `app.py:861`

### USB vs Battery Detection — CONFIRMED FROM EE02 SCHEMATIC

- **D-07:** Detect battery presence by ADC reading: when no battery is connected, VBAT = 0V → ADC reads ~0 mV after divider
  - Battery present: `batteryVoltage > 1500` mV (≈3.0V after × 2, i.e., ADC reads > 750 mV)
  - USB only (no battery): `batteryVoltage ≤ 1500` mV
- **D-08:** On **USB power** (no battery detected): skip deep sleep entirely. After displaying image, wait the server-specified sleep duration (`sleepDuration` from `/sleep` endpoint), then loop without sleeping.
- **D-09:** On **battery power**: use `esp_deep_sleep_start()` as originally designed — restores full `hibernate()` implementation

### Low Battery Protection

- **D-10:** Keep original threshold: if battery voltage < 3050 mV (3.05V), enter deep sleep for 24 hours
- **D-11:** On low battery: clear screen, disconnect WiFi (`WiFi.disconnect(true); WiFi.mode(WIFI_OFF)`), sleep 24h (`esp_sleep_enable_timer_wakeup(86400ULL * 1000000ULL); esp_deep_sleep_start()`)

### Charge LED — HARDWARE ONLY, NO SOFTWARE PATH

- **D-12:** The flashing green LEDs (D5, D16) are driven by **BQ24070 STAT1/STAT2 open-drain outputs** — these are PMIC-controlled and not connected to any XIAO GPIO
- **D-13:** BQ24070 STAT pin behavior when no battery: enters fault/no-battery state → LEDs blink. This cannot be changed via firmware.
- **D-14:** Accepted limitation: **LED behavior when no battery is hardware-only**. Document in code with a comment. No firmware action possible.

### Claude's Discretion

- USB idle loop implementation details (use `delay(sleepDuration * 1000)` then `ESP.restart()`, or a watchdog-friendly loop)
- Whether to call `analogSetAttenuation` once at boot or before each read
- Order of operations in `setup()`: ADC enable → read voltage → ADC disable → decide sleep/continue

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current Firmware
- `epd7in3e/epd7in3e.ino` — Current firmware; `hibernate()` stub at line 279 with TODO, no battery code present
- `epd7in3e/config.h` — GPIO pin defines, sleep constants (`SLEEP_INTERVAL`, `WAKEUP_PIN`, `WAKEUP_LEVEL`)

### Hardware Schematic (source of truth for all pin assignments)
- `202000224_XIAO_ePaper_Display_Board_EE02_V1.pdf` — EE02 board schematic
  - Page 4 (Power): BQ24070 PMIC, BAT ADC DETE circuit (R28/R29 divider + U17 switch), LED wiring
  - Page 5 (XIAO): GPIO1=BAT_ADC, GPIO5=ADC_EN net assignments confirmed

### Server Battery Infrastructure (already complete — no changes needed)
- `app.py` lines 563–629 — `BATTERY_LEVELS` table and `calculate_battery_percentage()` function
- `app.py` lines 857–864 — `batteryCap` header reading in `/download` endpoint

### Original Battery Implementation (reference for restoration)
- Git commit `8a000e1:Arduino/epd7in3e.ino` contains original code:
  - `checkVoltage()` method — single ADC read, 3.05V threshold check
  - `downloadImage()` header section — 50-sample average, original `analogReadMilliVolts(0)` × 2 (GPIO0 was FireBeetle, now GPIO1)
  - `setup()` low-battery branch — clear screen, WiFi off, 24h sleep

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hibernate(int sleepDuration = 0)` in `epd7in3e.ino:279` — exists, stubbed with TODO; just needs implementation
- `CONFIG_PIN`, `WAKEUP_PIN`, `SLEEP_INTERVAL` in `config.h` — pattern for new `BAT_ADC_PIN`, `ADC_EN_PIN`, `MIN_BATTERY_VOLTAGE`

### Established Patterns
- Hardware constants defined in `config.h` with `#define` — all new pins/thresholds follow this
- Multi-sample ADC average (50 samples, 5ms delay) from original code — prevents noise spikes
- `preferences.getString("SERVER_BASE_URL")` pattern for NVS reads

### Integration Points
- `downloadImage()` — battery voltage header inserted before `http.GET()`, same as original
- `setup()` — `checkVoltage()` called early, before `epaperManager.begin()`, same as original flow
- `hibernate()` — replace TODO stub: battery present → deep sleep; USB only → wait-loop

</code_context>

<specifics>
## Specific Ideas

- Original `checkVoltage()` used a **single** ADC read for the low-voltage guard (not averaged). The 50-sample average was only for the HTTP header. This distinction should be preserved.
- Deep sleep wakeup pin stays at `GPIO_NUM_2` with `ESP_GPIO_WAKEUP_GPIO_LOW` — already in `config.h`, must not change.
- `ADC_EN_PIN` (GPIO5) must be set to OUTPUT and driven LOW by default; only pulsed HIGH during ADC reads.
- When no battery is detected (USB mode), send `batteryCap: 0` in the HTTP header (server already handles `voltage == 0` gracefully at `app.py:626`).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-battery-voltage*
*Context gathered: 2026-05-28 — updated with EE02 schematic findings*
