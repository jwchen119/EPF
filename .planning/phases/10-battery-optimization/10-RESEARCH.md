# Phase 10: Battery Optimization - Research

**Researched:** 2026-06-24
**Domain:** ESP32-S3 firmware power management, image transport protocol
**Confidence:** HIGH (firmware) / MEDIUM (binary transport impact)

---

## Summary

The EPF device is an XIAO ESP32-S3 Plus on a Seeed EE02 HAT driving a 13.3" color e-paper display. Battery
drain originates almost entirely in the active wake cycle — the time between deep-sleep wakeup and returning
to `esp_deep_sleep_start()`. Deep sleep itself draws ~7 µA (chip) to ~20 µA (board), which is negligible.
All optimization targets are therefore in the active period.

Three independent, high-impact problems were identified:

1. **The 3 second boot delay.** `setup()` calls `delay(3000)` to wait for USB-CDC serial monitor. This runs
   on every wake-up from deep sleep and costs ~0.056 mAh per cycle. At 1-hour refresh intervals (24
   cycles/day) this alone wastes ~1.34 mAh/day. Over a year with a 1000 mAh battery this single delay
   consumes ~49% of battery capacity.

2. **Hex-CSV image transport.** The server transmits each frame byte as "0F," (3 ASCII characters), inflating
   the 960 KB binary frame to ~2.8 MB of text. At 500 KB/s WiFi throughput this extends the download from
   ~1.9 s (binary) to ~5.6 s (hex). Since WiFi is the second largest active-period consumer (~80 mA), the
   extra 3.7 s costs ~0.082 mAh per cycle.

3. **WiFi TX power and CPU frequency during active period.** No `WiFi.setTxPower()` or
   `setCpuFrequencyMhz()` call exists in the firmware. The ESP32-S3 defaults to 240 MHz and maximum TX
   power (19.5 dBm). For a device communicating with a server on the same LAN, lower TX power (~8–11 dBm)
   is sufficient and reduces WiFi modem current. Reducing CPU frequency from 240 to 80 MHz cuts active
   current from ~67 mA to ~33 mA during processing phases.

**Primary recommendation:** Implement all three optimizations in this order of impact/risk: (1) remove or
gate the 3 s boot delay, (2) switch image transport to raw binary, (3) add `setCpuFrequencyMhz(80)` and
`WiFi.setTxPower(WIFI_POWER_8_5dBm)`.

---

## Project Constraints (from CLAUDE.md)

No CLAUDE.md exists in this project. No project-specific constraints beyond the global rules apply.

**Global rules that apply here:**
- Immutability: return new objects, never mutate in place (Python server side)
- Many small files, 200–400 lines typical (existing codebase already follows this)
- TDD mandatory: write tests first (RED), implement (GREEN), refactor
- 80% test coverage minimum
- Error handling at every level
- Functions < 50 lines

---

## Standard Stack

### Core (existing — no new libraries needed for optimizations 1 and 3)

| Library / API | Version | Purpose | Notes |
|---------------|---------|---------|-------|
| Arduino-ESP32 (WiFi) | bundled | `WiFi.setTxPower()`, `setCpuFrequencyMhz()` | Built-in; no install needed |
| ESP-IDF sleep API | bundled | `esp_sleep_pd_config`, `rtc_gpio_isolate` | Already included via `esp_sleep_enable_timer_wakeup` |
| Flask `send_file` | existing | Server binary response | Already used; change mimetype + content |
| Python `struct` / `bytes` | stdlib | Pack nibble bytes as raw binary | No new dependency |

### For binary transport (server-side change)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| Python `struct` | Pack bytes_array as raw binary | Replace `io.StringIO` hex loop |
| Flask `Response` / `send_file` with `mimetype='application/octet-stream'` | Return binary body | Replace `text/plain` |

No new Arduino libraries are required. The existing `stream.readBytes()` call in `processImageData()` already
reads raw bytes — the only change is removing the hex-decode step.

**Installation:** No new packages.

---

## Architecture Patterns

### Current Wake Cycle Flow (annotated with power cost)

```
esp_deep_sleep_start() → [sleep: ~20 µA] → timer/EXT1 wakeup
  → setup()
      Serial.begin(115200)
      delay(3000)              ← [WASTE: 3s @ ~67 mA = 0.056 mAh]
      checkVoltage()           ← [OK: necessary, gated]
      begin()
          epaper.begin()
          WiFi.mode(WIFI_STA)  ← [MISSING: no setCpuFreqMhz, no setTxPower]
          WifiCaptivePortal.autoConnect()  ← WiFi connect ~3s @ ~100 mA
      update()
          downloadImage()
              ADC read (50 samples)
              http.GET() → stream hex-CSV → parse hex ← [SLOW: 5.6s @ ~80 mA]
              sleep GET
              hibernate()
                  WiFi.disconnect()
                  esp_deep_sleep_start()
```

### Recommended Wake Cycle Flow (after optimization)

```
esp_deep_sleep_start() → [sleep: ~20 µA] → timer/EXT1 wakeup
  → setup()
      Serial.begin(115200)
      delay(50)               ← [down from 3000; 50ms needed for USB-CDC init]
      setCpuFrequencyMhz(80)  ← [CPU 240→80 MHz: saves ~34 mA during processing]
      checkVoltage()
      begin()
          epaper.begin()
          WiFi.mode(WIFI_STA)
          WiFi.setTxPower(WIFI_POWER_8_5dBm)  ← [LAN-adequate TX power]
          WifiCaptivePortal.autoConnect()
      update()
          downloadImage()
              ADC read
              http.GET() → stream raw binary → direct memcpy ← [1.9s @ ~80 mA]
              sleep GET
              hibernate()
                  rtc_gpio_isolate() on unused pins  ← [reduce leakage]
                  WiFi.disconnect()
                  esp_deep_sleep_start()
```

### Pattern 1: Conditional Serial Boot Delay

The 3-second delay exists because USB-CDC (the XIAO's native USB) needs time to enumerate before the serial
monitor sees output. This matters only when a developer has a serial monitor open. On battery-powered
production use, no monitor is connected.

**Approach A (recommended):** Gate on wakeup reason — skip the delay when waking from deep sleep timer
(production cycle), keep it only on first boot / reset (where a developer might be present):

```cpp
// Source: ESP-IDF esp_sleep_get_wakeup_cause() docs
esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
bool isProductionWakeup = (wakeup_reason == ESP_SLEEP_WAKEUP_TIMER ||
                           wakeup_reason == ESP_SLEEP_WAKEUP_EXT1);
if (!isProductionWakeup) {
    delay(3000);  // Only wait for serial monitor on cold boot/reset
} else {
    delay(50);    // Minimal settle time always needed
}
```

**Approach B:** Remove entirely and rely on the existing `delay(50)` in `EpaperManager::begin()`. Works but
loses serial output on cold boot for debugging.

### Pattern 2: CPU Frequency Reduction

```cpp
// Source: Arduino-ESP32 API, valid values: 240, 160, 80, 40, 20, 10 MHz
// Must be called before WiFi.begin() — frequency change after WiFi init can disrupt modem
setCpuFrequencyMhz(80);  // 240→80 MHz: cuts CPU current from ~67 mA to ~33 mA
```

**Measured impact** (from Mischianti ESP32 power article, verified MEDIUM confidence):
- 240 MHz: 66.8 mA
- 80 MHz: 33.2 mA
- 40 MHz: 19.88 mA (but may cause WiFi stability issues; 80 MHz is the safe minimum with WiFi)

80 MHz is the minimum safe frequency when WiFi is active. The ESP32-S3 WiFi driver requires at minimum
80 MHz when the radio is on.

### Pattern 3: WiFi TX Power Reduction

```cpp
// Source: Arduino-ESP32 WiFi API
// Set after WiFi.mode(WIFI_STA) and before connect
// For LAN use, 8.5 dBm is adequate; reduces modem TX current
WiFi.setTxPower(WIFI_POWER_8_5dBm);
```

**Known issue:** `WIFI_POWER_MINUS_1dBm` is documented as buggy on some boards — call returns 0 and getter
returns old value. Use `WIFI_POWER_8_5dBm` (8.5 dBm) as the lowest confirmed-working level.
Confidence: MEDIUM (community reports; no Espressif official statement on the specific bug).

### Pattern 4: Binary Image Transport

**Server side** — replace hex-CSV encoding with raw binary:

```python
# Current (in convert_to_c_code_in_memory):
output = io.StringIO()
for i, byte_value in enumerate(bytes_array):
    output.write(f'{byte_value:02X},')
    if (i + 1) % 16 == 0:
        output.write('\n')
result = output.getvalue().encode('utf-8')

# Replace with:
import struct
result = bytes(bytes_array)  # Direct binary — no hex encoding
output_bytes = io.BytesIO(result)
output_bytes.seek(0)
return output_bytes
```

Return with `mimetype='application/octet-stream'` instead of `text/plain`.

**Firmware side** — replace hex-decode streaming loop with direct binary read:

```cpp
// Replace the hex-decode loop in processImageData() with:
size_t totalRead = 0;
while (stream.connected() && totalRead < FRAME_SIZE) {
    int available = stream.available();
    if (available > 0) {
        int toRead = min((size_t)available, FRAME_SIZE - totalRead);
        int read = stream.readBytes(frame_buf + totalRead, toRead);
        totalRead += read;
    } else {
        delay(1);
    }
}
```

This eliminates: the `hexBuffer` String accumulation, `strtol()` parsing, and the `chunk_buf` intermediate
allocation. Frame buffer fill becomes a direct `readBytes()` into PSRAM.

**Content-Length compatibility:** Binary response has exact `Content-Length: 960000`. The existing
`processImageData(WiFiClient &stream, int contentLength)` signature already uses `contentLength` to bound
the loop — this works correctly with binary (no off-by-one from hex newlines/commas).

### Pattern 5: GPIO Isolation Before Deep Sleep

```cpp
// Source: ESP-IDF sleep_modes.html — rtc_gpio_isolate()
// Call in hibernate() before esp_deep_sleep_start()
// Isolate pins that have internal pullups but are driven by external circuitry
// GPIO1 (BAT_ADC) and GPIO6 (ADC_EN) are driven; isolate to avoid leakage

#include "driver/rtc_io.h"  // already included

// In hibernate(), after WiFi.disconnect():
rtc_gpio_isolate(GPIO_NUM_1);  // BAT_ADC_PIN — prevent ADC leakage
rtc_gpio_isolate(GPIO_NUM_6);  // ADC_EN_PIN — TPS22916 load switch gate
```

**ADC leakage note:** The ESP32 ADC draws extra current when the ADC_EN gate is HIGH during deep sleep. The
existing code calls `digitalWrite(ADC_EN_PIN, LOW)` after reading, which should prevent this. The `rtc_gpio_isolate()`
call provides an additional safeguard.

### Anti-Patterns to Avoid

- **Removing delay(50) entirely:** The minimal 50ms settle is needed for USB-CDC enumeration even in
  production; without any delay some boards show garbled early serial output.
- **setCpuFrequencyMhz() after WiFi.begin():** Frequency changes after WiFi init can cause modem instability.
  Must be called before `WifiCaptivePortal.autoConnect()`.
- **Using WIFI_POWER_MINUS_1dBm:** Documented bug — call silently fails on some ESP32 variants. Use
  `WIFI_POWER_8_5dBm` instead.
- **Binary transport without Content-Length:** Without exact Content-Length, the stream termination relies
  on connection close. Always set Content-Length on the server (`send_file` does this automatically from
  BytesIO length).
- **Changing image format without updating both sides atomically:** Firmware expecting binary from a server
  still returning hex will silently corrupt the frame buffer. The server change and firmware change must be
  deployed together.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CPU clock management | Custom clock-scaling logic | `setCpuFrequencyMhz(80)` (Arduino-ESP32) | Built-in, handles APB_CLK dependencies automatically |
| WiFi power control | Custom PHY register writes | `WiFi.setTxPower(WIFI_POWER_8_5dBm)` | Built-in, safe API |
| Binary packing of nibble data | Custom bit-twiddling | `bytes(bytes_array)` (Python stdlib) | The nibble-packing is already done; output is already a `list[int]` |
| GPIO leakage prevention | Custom sleep hook registry | `rtc_gpio_isolate()` (ESP-IDF) | Designed exactly for this; one call per pin |

---

## Common Pitfalls

### Pitfall 1: Serial Output Lost on Wake-from-Sleep

**What goes wrong:** Removing the 3 s delay unconditionally means serial monitor misses all output on cold
boot, making firmware debugging very hard.
**Why it happens:** USB-CDC enumeration on XIAO takes ~1-2 s after power-on.
**How to avoid:** Gate on wakeup cause: skip delay only on `ESP_SLEEP_WAKEUP_TIMER` / `ESP_SLEEP_WAKEUP_EXT1`.
Cold boot / button-reset still gets 3 s.
**Warning signs:** Serial monitor shows no output at all after firmware flash.

### Pitfall 2: WiFi Modem Instability at Low CPU Frequency

**What goes wrong:** Setting CPU < 80 MHz while WiFi is active causes connection drops or HTTP timeouts.
**Why it happens:** WiFi driver requires 80 MHz minimum clock.
**How to avoid:** Use 80 MHz as the floor. Never call `setCpuFrequencyMhz(40)` before `WiFi.disconnect()`.
**Warning signs:** `WL_CONNECT_FAILED` or HTTP `-11` (connection refused) errors after adding frequency call.

### Pitfall 3: Binary/Hex Protocol Mismatch

**What goes wrong:** After changing server to binary, old firmware still tries to hex-decode. Frame buffer
fills with garbage; display shows random color noise.
**Why it happens:** No versioning or capability negotiation in the `/download` protocol.
**How to avoid:** Change both server and firmware in the same deployment. Add a response header
`X-Image-Format: binary` as a sanity check (easy to read in firmware log).
**Warning signs:** Display shows random-color noise after update; `frame_offset` log shows 960000 but image
is corrupt.

### Pitfall 4: `Content-Length` Mismatch with Binary Frames

**What goes wrong:** `processImageData()` uses `contentLength` to guard the read loop. If the server sends
the wrong Content-Length (e.g., still the hex size), the loop exits early or overruns.
**Why it happens:** Stale cached response or misconfigured Flask `send_file`.
**How to avoid:** `send_file(io.BytesIO(bytes_array_bytes))` automatically sets Content-Length to the
BytesIO length (960000). Verify in firmware log: `"content-length: 960000"`.
**Warning signs:** `Warning: expected 960000 bytes, received N` in serial output.

### Pitfall 5: ADC_EN Pin Left HIGH During Sleep

**What goes wrong:** If `ADC_EN_PIN` is HIGH when deep sleep starts, the TPS22916 load switch stays on,
powering the voltage divider circuit and causing ~mA-level leakage.
**Why it happens:** A crash or early return before `digitalWrite(ADC_EN_PIN, LOW)` is called.
**How to avoid:** Call `rtc_gpio_isolate(GPIO_NUM_6)` in `hibernate()` as a belt-and-suspenders measure.
**Warning signs:** Deep sleep current significantly higher than expected (>100 µA on bare chip).

---

## Code Examples

### Boot Delay Gate (firmware — setup())

```cpp
// Source: ESP-IDF esp_sleep_get_wakeup_cause() + Arduino-ESP32 pattern
esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
bool isDevelopmentBoot = (wakeup_reason != ESP_SLEEP_WAKEUP_TIMER &&
                          wakeup_reason != ESP_SLEEP_WAKEUP_EXT1);
if (isDevelopmentBoot) {
    delay(3000);  // USB-CDC enumeration window for serial monitor
} else {
    delay(50);    // Minimal settle; saves ~0.056 mAh per production cycle
}
```

### CPU + TX Power Setup (firmware — begin())

```cpp
// Source: Arduino-ESP32 WiFi API + community measurements
// Call before WifiCaptivePortal.autoConnect()
setCpuFrequencyMhz(80);              // 240→80 MHz: ~34 mA saving during active period
WiFi.mode(WIFI_STA);
WiFi.setTxPower(WIFI_POWER_8_5dBm); // LAN-adequate TX power
```

### Binary Frame Stream Read (firmware — processImageData())

```cpp
// Source: ESP32 HTTPClient stream API (Arduino-ESP32)
// Replace hex-decode loop with direct binary read
size_t totalRead = 0;
while (stream.connected() && totalRead < FRAME_SIZE) {
    int available = stream.available();
    if (available > 0) {
        size_t toRead = min((size_t)available, FRAME_SIZE - totalRead);
        int read = stream.readBytes(frame_buf + totalRead, (int)toRead);
        if (read > 0) totalRead += read;
    } else {
        delay(1);
    }
}
```

### Binary Frame Generation (server — app.py)

```python
# Source: Python stdlib struct / bytes
# Replace convert_to_c_code_in_memory() hex loop with:
def convert_to_binary_in_memory(image_data):
    """Convert processed image to raw binary nibble frame — T133A01 4bpp."""
    pixels = np.array(image_data)
    indices = depalette_image(pixels, palette)
    nibble_map = [0xF, 0x0, 0xB, 0x6, 0xD, 0x2]
    height, width = indices.shape
    bytes_array = [
        (nibble_map[indices[y, x]] << 4) | nibble_map[indices[y, x + 1]]
        if x + 1 < width
        else (nibble_map[indices[y, x]] << 4)
        for y in range(height)
        for x in range(0, width, 2)
    ]
    output_bytes = io.BytesIO(bytes(bytes_array))
    output_bytes.seek(0)
    return output_bytes
```

Return via `send_file(c_code, mimetype='application/octet-stream', ...)`.

### GPIO Isolation Before Sleep (firmware — hibernate())

```cpp
// Source: ESP-IDF sleep_modes.html — rtc_gpio_isolate()
// Add after WiFi.disconnect(true); WiFi.mode(WIFI_OFF);
rtc_gpio_isolate(GPIO_NUM_1);  // BAT_ADC_PIN — prevent ADC leakage path
rtc_gpio_isolate(GPIO_NUM_6);  // ADC_EN_PIN — gate TPS22916 load switch fully
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WaveShare hex buffer (array in .h file) | HTTP streaming hex-CSV | Phase 1 port | +WiFi; hex overhead introduced then |
| No battery monitoring | ADC gated by TPS22916 (ADC_EN) | Phase 4 | Better; leakage risk remains |
| Flat deep sleep | Timer + EXT1 wakeup | Phase 4 | Correct implementation |

**Gaps introduced during porting:**
- Hex-CSV was a developer convenience from early prototyping; never replaced with binary for production
- Boot delay is USB-CDC development artifact; never gated on wakeup cause
- No CPU frequency or TX power management has ever been added

---

## Environment Availability

Step 2.6: No new external tools required. All changes are within:
- Arduino C++ firmware (existing toolchain)
- Python 3 server (existing venv)

No environment audit needed.

---

## Validation Architecture

**nyquist_validation:** Not explicitly set to false in `.planning/config.json` — treat as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

**Note:** Firmware changes (boot delay, CPU freq, TX power, GPIO isolation, binary stream read) are pure
Arduino C++ and are **not unit-testable via pytest**. They require:
1. Compile verification (Arduino IDE / arduino-cli)
2. Human functional test on device: flash firmware, check serial output confirms correct wakeup path,
   verify display updates correctly

### Phase Requirements → Test Map

| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| BATT-01 | `convert_to_binary_in_memory()` returns bytes of correct length (960000) | unit | `python -m pytest tests/test_battery_optimization.py::test_binary_output_length -x` | ❌ Wave 0 |
| BATT-02 | Binary output nibble values match hex-CSV nibble values for same image | unit | `python -m pytest tests/test_battery_optimization.py::test_binary_nibble_parity -x` | ❌ Wave 0 |
| BATT-03 | `/download` endpoint returns `Content-Type: application/octet-stream` | integration | `python -m pytest tests/test_battery_optimization.py::test_download_mimetype -x` | ❌ Wave 0 |
| BATT-04 | `/download` response Content-Length equals 960000 | integration | `python -m pytest tests/test_battery_optimization.py::test_download_content_length -x` | ❌ Wave 0 |
| BATT-05 | Firmware boot delay gating — manual only (requires device) | manual | N/A | N/A |
| BATT-06 | Firmware binary stream decode — manual only (requires device) | manual | N/A | N/A |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_battery_optimization.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_battery_optimization.py` — covers BATT-01 through BATT-04
- [ ] No new conftest fixtures needed (existing `app` fixture from `tests/conftest.py` suffices)

---

## Open Questions

1. **Deploy atomicity: binary transport**
   - What we know: server and firmware must switch simultaneously
   - What's unclear: is there a staged rollout path (e.g., version header negotiation)?
   - Recommendation: Keep it simple — deploy server + firmware as a single coordinated update.
     Add `X-Image-Format: binary` response header so firmware can log/assert format matches expectation.

2. **XIAO ESP32-S3 Plus minimum CPU frequency with active WiFi**
   - What we know: ESP32 WiFi driver minimum is 80 MHz per community reports and Espressif guidance
   - What's unclear: XIAO S3 Plus may have additional constraints from PSRAM (OPI PSRAM requires specific clock ratios)
   - Recommendation: Start at 80 MHz. If PSRAM allocation fails after frequency change, raise to 160 MHz.

3. **e-paper display current during refresh**
   - What we know: e-paper "bistable" display holds image without power; refresh command takes ~10s
   - What's unclear: whether `Seeed_GFX` / T133A01 supports a "partial refresh" that would reduce refresh time
   - Recommendation: Out of scope for this phase — display driver is opaque and Seeed_GFX does not document partial refresh for T133A01.

---

## Quantified Impact Summary

All estimates assume 1-hour refresh interval (24 cycles/day) and a ~1000 mAh battery.

| Optimization | Per-Cycle Saving | Daily Saving | Confidence |
|-------------|-----------------|--------------|------------|
| Remove 3s boot delay (→ 50ms on production wakeup) | ~0.056 mAh | ~1.34 mAh/day | HIGH |
| Binary transport (hex 5.6s → binary 1.9s @ 80 mA) | ~0.082 mAh | ~1.97 mAh/day | MEDIUM |
| CPU 240→80 MHz during active period (~15s active) | ~0.034 mAh | ~0.82 mAh/day | MEDIUM |
| TX power reduction (LAN adequate) | ~0.010 mAh est. | ~0.24 mAh/day | LOW |
| GPIO isolation (ADC leakage prevention) | negligible/unknown | — | LOW |
| **Combined** | **~0.18 mAh** | **~4.4 mAh/day** | MEDIUM |

---

## Sources

### Primary (HIGH confidence)

- [ESP-IDF Sleep Modes — ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/sleep_modes.html) — GPIO hold, rtc_gpio_isolate, power domain configuration
- [ESP-IDF Low Power WiFi Scenarios — ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/low-power-mode/low-power-mode-wifi.html) — DFS + modem sleep interaction
- Existing codebase: `epd7in3e.ino`, `config.h`, `app.py` — confirmed current implementation details

### Secondary (MEDIUM confidence)

- [Mischianti ESP32 Power Saving — CPU and WiFi](https://mischianti.org/esp32-practical-power-saving-manage-wifi-and-cpu-1/) — measured current values at various CPU frequencies
- [ESP32-S3 Datasheet (Seeed)](https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/esp32-s3_datasheet.pdf) — deep sleep 7 µA typical
- [Hubble Network — Cutting Bootloader Latency](https://hubble.com/community/guides/cutting-bootloader-latency-esp32/) — boot delay optimization patterns

### Tertiary (LOW confidence, flagged for validation)

- [ESP32 Forum — hunt for ESP32-S3 deep sleep current leakage](https://esp32.com/viewtopic.php?t=32177) — community measurements, not official
- [WiFi.setTxPower MINUS_1dBm bug](https://github.com/espressif/arduino-esp32/issues/6851) — community bug report for WIFI_POWER_MINUS_1dBm

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all APIs are built-in Arduino-ESP32 / Python stdlib
- Architecture: HIGH — changes are surgical; no structural refactor
- Pitfalls: MEDIUM — binary transport protocol mismatch is a real risk; GPIO leakage numbers are LOW confidence
- Impact estimates: MEDIUM — calculations use published current values but actual XIAO board values not measured

**Research date:** 2026-06-24
**Valid until:** 2026-12-24 (Arduino-ESP32 API is stable; Espressif sleep API does not change frequently)
