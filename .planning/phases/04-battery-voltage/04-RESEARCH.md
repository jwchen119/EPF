# Phase 4: Battery Voltage - Research

**Researched:** 2026-05-28
**Domain:** ESP32-S3 ADC, deep sleep/wakeup, USB vs battery detection, Arduino firmware
**Confidence:** HIGH (all key decisions confirmed from schematic; API details verified against official Espressif docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Battery ADC pin = GPIO1 (A0/D0), use `analogReadMilliVolts(1)`
- **D-02:** ADC enable pin = GPIO5, drive HIGH before read and LOW after; add `BAT_ADC_PIN` and `ADC_EN_PIN` defines to `config.h`
- **D-03:** Voltage divider 1:1 (R28=R29=10KΩ), multiply ADC reading × 2 to get VBAT in mV
- **D-04:** Use `analogSetAttenuation(ADC_11dB)` to cover 0–2.1V input range
- **D-05:** 50-sample average with 5ms delay for HTTP header; single read for low-battery guard
- **D-06:** Send as `batteryCap` HTTP header in mV (integer)
- **D-07:** Battery present: `batteryVoltage > 1500` mV; USB only: ≤ 1500 mV
- **D-08:** USB power → skip deep sleep; wait server-specified `sleepDuration`, then loop
- **D-09:** Battery power → `esp_deep_sleep_start()` (restore full `hibernate()`)
- **D-10:** Low-battery threshold: 3050 mV → 24h deep sleep
- **D-11:** Low battery: clear screen, WiFi off, `esp_sleep_enable_timer_wakeup(86400ULL * 1000000ULL)`, then `esp_deep_sleep_start()`
- **D-12/D-13/D-14:** Charge LEDs (D5, D16) are BQ24070 PMIC-driven; no firmware path — document as known limitation only
- Server-side is already complete; no changes to `app.py` needed

### Claude's Discretion

- USB idle loop implementation: `delay(sleepDuration * 1000)` then `ESP.restart()`, or a watchdog-friendly loop
- Whether to call `analogSetAttenuation` once at boot or before each read
- Order of operations in `setup()`: ADC enable → read → disable → decide sleep/continue

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BV-01 | Read battery voltage via ADC on GPIO1 with ADC_EN on GPIO5 | D-01 through D-05; original `checkVoltage()` and header block in git commit 8a000e1 as reference |
| BV-02 | Detect USB-only vs battery power; skip deep sleep on USB | D-07, D-08; ADC reads ~0mV when no battery; threshold 1500mV confirmed from schematic |
| BV-03 | Re-enable deep sleep when on battery; restore `hibernate()` stub | D-09; original `hibernate()` implementation from 8a000e1 is the reference; EXT1 wakeup note below |
| BV-04 | Send `batteryCap` header in mV; send 0 when USB-only | D-06; `app.py:861` already handles 0 gracefully |
| BV-05 | Document charge LED limitation; preserve low-battery guard | D-10, D-11, D-12–D-14; low-battery path in original `setup()` from 8a000e1 |
</phase_requirements>

---

## Summary

Phase 4 restores battery voltage monitoring that was removed in Phase 1. The hardware design is fully confirmed from the EE02 schematic: GPIO1 (BAT_ADC) behind a 1:1 resistor divider, with GPIO5 (ADC_EN) gating a TPS22916 load switch. The original battery implementation from git commit 8a000e1 is directly reusable after changing the pin reference from GPIO0 to GPIO1 and adding the USB-mode idle loop. No new libraries are required — all APIs already present in the codebase.

The single most important implementation detail is that `analogSetAttenuation(ADC_11dB)` must be called before reading. Without it the default ADC range (~0–950mV on ESP32-S3) would clip the 0–2100mV signal range seen at GPIO1. The 50-sample average is critical for noise suppression on ADC1; a single read shows ±50–100mV jitter under WiFi load.

The deep sleep path from the original code (`esp_sleep_enable_ext1_wakeup` + `esp_sleep_enable_timer_wakeup`) is correct and functional. The newer per-pin API (`esp_sleep_enable_ext1_wakeup_io`) is the modern form, but both work on current Arduino-ESP32. Since the existing codebase already imports `driver/rtc_io.h` and uses `ESP_EXT1_WAKEUP_ANY_LOW` the original pattern is drop-in ready.

**Primary recommendation:** Restore the original battery code block-for-block, changing `analogReadMilliVolts(0)` to `analogReadMilliVolts(1)`, wrapping reads in ADC_EN HIGH/LOW pulses, adding USB-mode idle loop in `hibernate()`, and moving `checkVoltage()` to run before `epaperManager.begin()` as in the original.

---

## Standard Stack

### Core (already present in project — no new installs needed)

| API / Header | Source | Purpose | Notes |
|---|---|---|---|
| `analogReadMilliVolts(pin)` | Arduino-ESP32 built-in | ADC read with factory calibration applied | Returns calibrated mV; preferred over raw `analogRead` |
| `analogSetAttenuation(ADC_11dB)` | Arduino-ESP32 built-in | Sets all ADC channels to 11dB attenuation, covering 0–2500mV input range | Call once at boot |
| `analogReadResolution(12)` | Arduino-ESP32 built-in | 12-bit ADC resolution (0–4095) | Already used in original code |
| `esp_sleep_enable_timer_wakeup(uint64_t us)` | `esp_sleep.h` (IDF, already included) | Timer wakeup source | microseconds; `86400ULL * 1000000ULL` = 24h |
| `esp_sleep_enable_ext1_wakeup(mask, mode)` | `esp_sleep.h` | GPIO wakeup (multiple pins, RTC-capable only) | Valid pins 0–21 on S3; GPIO2 is pin 2 ✓ |
| `rtc_gpio_init`, `rtc_gpio_pullup_en` | `driver/rtc_io.h` (already imported) | Configure RTC GPIO pull-up before sleep | Required to keep pin stable during deep sleep |
| `esp_deep_sleep_start()` | `esp_sleep.h` | Enter deep sleep | Terminates execution; next resume is fresh boot |

### No new libraries required

All APIs are in Arduino-ESP32 core and ESP-IDF components already included via existing `#include "driver/rtc_io.h"`.

---

## Architecture Patterns

### Pattern 1: ADC Read with Power-Gate Control

**What:** GPIO5 (ADC_EN) gates a load switch that powers the voltage divider. Must be enabled only during reads to avoid ~0.6mA quiescent draw through divider.

**When to use:** Every ADC read session (both the averaged header read and the single `checkVoltage()` read).

```cpp
// Source: D-02 (schematic), analogSetAttenuation pattern from Arduino-ESP32 docs
pinMode(ADC_EN_PIN, OUTPUT);
digitalWrite(ADC_EN_PIN, LOW); // default: off

// Before read session:
analogSetAttenuation(ADC_11dB);   // once at boot is sufficient; set here as guard
analogReadResolution(12);
digitalWrite(ADC_EN_PIN, HIGH);
delay(10);                        // allow load switch + voltage divider to settle

// 50-sample average (for header):
int plusV = 0;
for (int i = 0; i < 50; i++) {
    plusV += analogReadMilliVolts(BAT_ADC_PIN);
    delay(5);
}
int batteryVoltage = (plusV / 50) * 2;  // × 2 for 1:1 divider

digitalWrite(ADC_EN_PIN, LOW);    // power-gate off immediately after
```

### Pattern 2: Battery vs USB Detection

**What:** When no battery is connected, VBAT floats/pulls to 0V. After the 1:1 divider, GPIO1 reads ~0mV. Threshold at 1500mV catches any voltage above ~3.0V battery floor with margin.

```cpp
// Source: D-07
bool onBattery = (batteryVoltage > 1500);
int headerValue = onBattery ? batteryVoltage : 0;
http.addHeader("batteryCap", String(headerValue));
```

### Pattern 3: hibernate() — Battery vs USB branching

**What:** Replace the current TODO stub with dual-mode behavior.

```cpp
// Source: D-08, D-09, original hibernate() from git 8a000e1
void hibernate(int sleepDuration = 0, bool onBattery = false) {
    int sleep_interval = sleepDuration > 0 ? sleepDuration : (int)SLEEP_INTERVAL;

    if (!onBattery) {
        // USB mode: wait, then restart (feeds watchdog via delay)
        Serial.printf("USB power: waiting %d s then restarting\n", sleep_interval);
        // delay() in Arduino-ESP32 calls vTaskDelay internally, which feeds TWDT
        delay((uint32_t)sleep_interval * 1000UL);
        ESP.restart();
        return;
    }

    // Battery mode: full deep sleep
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    fs_deinit();
    delay(50);

    uint64_t sleep_time = (uint64_t)sleep_interval * 1000000ULL;
    esp_sleep_enable_timer_wakeup(sleep_time);

    rtc_gpio_init(WAKEUP_PIN);
    rtc_gpio_set_direction(WAKEUP_PIN, RTC_GPIO_MODE_INPUT_ONLY);
    rtc_gpio_pullup_en(WAKEUP_PIN);
    rtc_gpio_pulldown_dis(WAKEUP_PIN);
    esp_sleep_enable_ext1_wakeup(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW);

    Serial.println("Entering deep sleep...");
    Serial.flush();
    delay(50);
    esp_deep_sleep_start();
}
```

### Pattern 4: Low-Battery Guard in setup()

**What:** Run before `epaperManager.begin()` (i.e., before WiFi connect). Single-sample read is sufficient — only need a yes/no threshold decision, not a precise value.

```cpp
// Source: original checkVoltage() from git 8a000e1, adapted for GPIO1 + ADC_EN
// In setup() before epaperManager.begin():
analogSetAttenuation(ADC_11dB);
analogReadResolution(12);
digitalWrite(ADC_EN_PIN, HIGH);
delay(10);
int rawMv = analogReadMilliVolts(BAT_ADC_PIN);
int vbatMv = rawMv * 2;
digitalWrite(ADC_EN_PIN, LOW);
Serial.printf("Battery voltage: %d mV\n", vbatMv);

bool onBattery = (vbatMv > 1500);

if (onBattery && vbatMv < MIN_BATTERY_VOLTAGE) {
    Serial.println("Battery low — sleeping 24h");
    epaperManager.clearScreen();
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    esp_sleep_enable_timer_wakeup(86400ULL * 1000000ULL);
    esp_deep_sleep_start();
}
```

### Anti-Patterns to Avoid

- **Reading ADC without enabling ADC_EN first:** GPIO1 reads ~0mV at all times because the voltage divider is unpowered. The firmware would think no battery is present and skip deep sleep indefinitely.
- **Using analogRead() (raw) instead of analogReadMilliVolts():** Raw counts are not calibrated; accuracy is ±10–15% without calibration. Always use `analogReadMilliVolts()` on ESP32-S3 which applies factory OTP calibration.
- **Leaving ADC_EN HIGH after reading:** Keeps ~0.6mA flowing through R28+R29 (10KΩ+10KΩ = 20KΩ, VBAT up to 4.2V → 0.21mA per divider arm) continuously during deep sleep. Defeats battery life purpose.
- **Calling analogSetAttenuation inside the sampling loop:** It's a one-time hardware configuration. One call at boot (or before the first read session) is correct. Calling it 50 times per read cycle adds unnecessary overhead.
- **Using `delay(sleepDuration * 1000)` when `sleepDuration` is stored as int:** If `sleepDuration` > 2147 seconds, `int * 1000` overflows. Cast to `uint32_t` or `uint64_t` before multiplication.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ADC calibration | Custom polynomial correction | `analogReadMilliVolts()` | ESP32-S3 stores factory eFuse calibration; the Arduino-ESP32 function applies it automatically |
| Deep sleep entry sequence | Custom power-down sequence | Original hibernate() from 8a000e1 | Already handles WiFi off, fs_deinit, timer + EXT1 wakeup, RTC GPIO pullup in correct order |
| USB detection | VBUS GPIO sensing | ADC-based method (voltage == 0) | No VBUS pin exposed on XIAO EE02 board; voltage divider method is the only available path |

---

## Common Pitfalls

### Pitfall 1: ADC_EN not initialized as OUTPUT
**What goes wrong:** `digitalWrite(ADC_EN_PIN, HIGH)` does nothing if `pinMode` was not called. GPIO5 starts as input-only, the load switch stays off, GPIO1 always reads ~0mV.
**Why it happens:** `pinMode` for ADC_EN was not in the original code (the original board had no enable gate).
**How to avoid:** Add `pinMode(ADC_EN_PIN, OUTPUT); digitalWrite(ADC_EN_PIN, LOW);` near the top of `setup()`, before the first read.
**Warning signs:** Battery voltage reads 0mV on hardware that has a battery connected.

### Pitfall 2: Attenuaton not set — ADC clips at ~950mV
**What goes wrong:** The ESP32-S3 default attenuation is `ADC_11dB` in Arduino-ESP32, which covers 0–2500mV. However, older board package versions default to `ADC_0dB` (0–750mV). If the voltage divider output at 4.2V battery (2.1V) exceeds the attenuation range, readings saturate.
**Why it happens:** Attenuation default varies across Arduino-ESP32 versions.
**How to avoid:** Explicitly call `analogSetAttenuation(ADC_11dB)` regardless of assumed defaults.
**Warning signs:** Battery reads constant max value (~2500mV / 2 = 5000mV after ×2) even at lower charge states.

### Pitfall 3: hibernate() receives sleepDuration from server but onBattery flag not threaded through
**What goes wrong:** `downloadImage()` calls `hibernate(sleepDuration)` but the current method signature has no `onBattery` parameter. On USB power, the device would deep-sleep instead of looping.
**Why it happens:** The battery detection happens in `setup()` (or just before the header is sent), but `hibernate()` is called inside `downloadImage()` which is a method on `EpaperManager`. The flag must be stored as a member variable or passed as a parameter.
**How to avoid:** Add `bool m_onBattery` as a private member of `EpaperManager`, set it during battery read, read it in `hibernate()`.
**Warning signs:** Device deep-sleeps despite USB-only operation.

### Pitfall 4: Integer overflow in delay for USB idle loop
**What goes wrong:** `delay(sleepDuration * 1000)` with `sleepDuration` as `int` overflows at 2148 seconds (about 35 minutes).
**Why it happens:** `int * int` arithmetic is 32-bit signed; 3600 * 1000 = 3,600,000 which fits, but 2149 * 1000 = 2,149,000,000 overflows.
**How to avoid:** Cast: `delay((uint32_t)sleepDuration * 1000UL)`. For intervals > ~49 days, use a `vTaskDelay` loop.
**Warning signs:** On USB power, device restarts far sooner than expected sleep interval.

### Pitfall 5: `esp_sleep_enable_ext1_wakeup` deprecated in IDF v6.0+
**What goes wrong:** Arduino-ESP32 built against IDF v6.0+ will emit a deprecation warning for `esp_sleep_enable_ext1_wakeup()`.
**Why it happens:** Espressif deprecated the single-call API in favour of per-pin `esp_sleep_enable_ext1_wakeup_io()`.
**How to avoid:** The original code uses the deprecated form; it still works in current Arduino-ESP32. If a warning becomes an error, replace with `esp_sleep_enable_ext1_wakeup_io(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW)`. This is a one-line change with identical behavior.
**Warning signs:** Compiler warning `deprecated since release/v6.0`.

---

## Code Examples

### config.h additions

```cpp
// Source: D-01, D-02, D-10
#define BAT_ADC_PIN    1U              // GPIO1 = BAT_ADC net on EE02 board
#define ADC_EN_PIN     5U              // GPIO5 = ADC_EN net (TPS22916 load switch)
#define MIN_BATTERY_VOLTAGE  3050U    // mV — below this → 24h sleep (original threshold)
```

### Full averaged battery read (for HTTP header)

```cpp
// Source: original git 8a000e1 downloadImage(), adapted for GPIO1 + ADC_EN
analogSetAttenuation(ADC_11dB);
analogReadResolution(12);
digitalWrite(ADC_EN_PIN, HIGH);
delay(10);
int plusV = 0;
for (int i = 0; i < 50; i++) {
    plusV += analogReadMilliVolts(BAT_ADC_PIN);
    delay(5);
}
int batteryVoltage = (plusV / 50) * 2;
digitalWrite(ADC_EN_PIN, LOW);
bool onBattery = (batteryVoltage > 1500);
http.addHeader("batteryCap", String(onBattery ? batteryVoltage : 0));
```

### Original hibernate() from git 8a000e1 (reference for restoration)

```cpp
// Source: git 8a000e1:Arduino/epd7in3e.ino lines 292–340
// Key elements to preserve:
//   WiFi.disconnect(true); WiFi.mode(WIFI_OFF); fs_deinit();
//   esp_sleep_enable_timer_wakeup(sleep_time);
//   rtc_gpio_init + pullup + esp_sleep_enable_ext1_wakeup(1ULL << WAKEUP_PIN, ...)
//   esp_deep_sleep_start();
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `esp_sleep_enable_ext1_wakeup(mask, mode)` | `esp_sleep_enable_ext1_wakeup_io(mask, mode)` per pin | IDF v5.1 (deprecated in v6.0) | Functional only — old form still works, emits deprecation warning |
| `analogRead()` + manual calibration table | `analogReadMilliVolts()` with eFuse calibration | Arduino-ESP32 2.x | Use `analogReadMilliVolts()` exclusively |
| `ADC_11db` (with lowercase b) | `ADC_11dB` (capital B) | Arduino-ESP32 2.0+ | Compile error if wrong case used |

**Deprecated/outdated:**
- Raw `analogRead()` for voltage measurement: replaced by `analogReadMilliVolts()` which applies eFuse OTP calibration automatically.
- `esp_sleep_enable_ext1_wakeup()`: deprecated in IDF v6.0; replacement is `esp_sleep_enable_ext1_wakeup_io()`. Functionally identical.

---

## Open Questions

1. **ADC settle time after ADC_EN HIGH**
   - What we know: The TPS22916 load switch has a rise time. The resistor divider needs to charge GPIO1's ADC sample capacitor.
   - What's unclear: Whether 10ms settle delay is sufficient (the original code had no ADC_EN gate, so no settle delay existed).
   - Recommendation: Start with 10ms (conservative). If readings are unstable, increase to 20ms. The 50-sample loop with 5ms delay (250ms total) provides ample additional stabilization.

2. **Attenuation constant name: `ADC_11dB` vs `ADC_ATTEN_DB_11`**
   - What we know: Arduino-ESP32 docs show `ADC_11dB` as the enum value for `analogSetAttenuation()`. The IDF-level enum is `ADC_ATTEN_DB_11`.
   - What's unclear: Which spelling the current Arduino-ESP32 version in this project accepts.
   - Recommendation: Use `ADC_11dB` (Arduino-style). If it fails to compile, fall back to `ADC_ATTEN_DB_11`.

---

## Environment Availability

Step 2.6: SKIPPED — this phase modifies firmware source files only (`.ino`, `config.h`). No external CLI tools, databases, or services are involved beyond the existing build toolchain already verified in prior phases.

---

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` — treat as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual hardware test + Serial Monitor verification (no unit test framework for `.ino` firmware) |
| Config file | none |
| Quick run command | Compile: Arduino IDE / `arduino-cli compile` |
| Full suite command | Flash to device, observe Serial Monitor output |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| BV-01 | Battery voltage read returns plausible mV value (3400–4200 on charged battery, 0 on USB-only) | manual | observe Serial Monitor `Battery voltage: XXXX mV` | ❌ Wave 0 |
| BV-02 | `onBattery` flag correct: USB → false (sends 0 header), battery → true (sends voltage) | manual | check server `last_battery_voltage` via settings UI | ❌ Wave 0 |
| BV-03 | Deep sleep entered on battery; idle loop (delay + restart) on USB | manual | confirm deep sleep via USB disconnect or 24h timer firing | ❌ Wave 0 |
| BV-04 | HTTP header `batteryCap` present and non-zero on battery; 0 on USB | manual | `curl -v <server>/download` logs or Serial print | ❌ Wave 0 |
| BV-05 | Low-battery guard: if simulated < 3050mV, device sleeps 24h | manual | mock with threshold tweak or bench power supply | ❌ Wave 0 |

### Sampling Rate
- **Per task:** Compile and check for zero errors/warnings
- **Per wave merge:** Flash to device and run Serial Monitor smoke test
- **Phase gate:** All 5 manual checks pass before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] No automated unit tests possible for `.ino` firmware — all verification is manual hardware testing with Serial Monitor
- [ ] Verification checklist document recommended as Wave 0 deliverable (optional)

---

## Sources

### Primary (HIGH confidence)
- `git show 8a000e1:Arduino/epd7in3e.ino` — original `checkVoltage()`, `downloadImage()` battery block, original `hibernate()` implementation
- `202000224_XIAO_ePaper_Display_Board_EE02_V1.pdf` (project schematic) — GPIO1=BAT_ADC, GPIO5=ADC_EN, R28/R29 divider, BQ24070 LED wiring confirmed from schematic trace
- [Arduino-ESP32 ADC API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html) — `analogReadMilliVolts`, `analogSetAttenuation`, attenuation table verified
- [ESP32-S3 Sleep Modes IDF v6.0](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/sleep_modes.html) — EXT1 wakeup API, deprecation notice, GPIO2 as valid RTC pin verified

### Secondary (MEDIUM confidence)
- `app.py:857–864` — `batteryCap` header handling; confirmed 0 is handled gracefully at line 626
- WebSearch: ESP32-S3 ADC accuracy — factory eFuse calibration exists on S3; `analogReadMilliVolts` applies it automatically (multiple sources agree)
- WebSearch: Arduino-ESP32 watchdog — `delay()` feeds TWDT via `vTaskDelay` internally; safe for USB idle loop

### Tertiary (LOW confidence)
- WebSearch: 10ms settle time for load switch — reasonable but not from component datasheet; treat as starting estimate

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all APIs verified against official Espressif docs; original working code in git
- Architecture: HIGH — patterns derived directly from working original code + schematic confirmation
- Pitfalls: HIGH (ADC_EN init, attenuation) / MEDIUM (settle time, overflow) — most from code inspection

**Research date:** 2026-05-28
**Valid until:** 2026-08-28 (stable ESP-IDF/Arduino-ESP32 APIs; only risk is board package version upgrade)
