# Research: EPF Hardware Port — FireBeetle ESP32-C6 + WaveShare 7.3" → XIAO ESP32-S3 Plus + Seeed 13.3" Spectra 6

**Researched:** 2026-05-27
**Domain:** Embedded C++ (Arduino), ESP32-S3 deep sleep, SPI e-paper displays, Python image processing
**Confidence:** HIGH for hardware pins and library choices; MEDIUM for exact T133A01 protocol details (Seeed docs are sparse)

---

## Summary

This port replaces both ends of the system: the MCU changes from FireBeetle ESP32-C6 to XIAO ESP32-S3 Plus, and the display changes from a WaveShare 7.3" 800×480 6-color panel to a Seeed 13.3" 1200×1600 6-color Spectra panel. The number and identity of display colors stays at 6 (black, white, yellow, red, blue, green — no orange), so the server-side palette and dithering pipeline requires only a resolution change and minor color-value tweaks, not a structural rewrite.

The largest firmware change is the display driver: the current hand-rolled driver must be replaced with Seeed's `Seeed_GFX` library (specifically its T133A01 back-end), because Seeed's 60-pin FFC display connector is not compatible with WaveShare's direct-SPI header and the T133A01 controller sequence differs significantly from the WaveShare UC8179-family used in the 7.3" panel.

GPIO renumbering is the second major change. The XIAO ESP32-S3 Plus exposes a different pin set. SPI bus pins, BUSY/RST/DC assignments, CONFIG_PIN, and the battery-voltage ADC pin all need updating. The deep-sleep API is functionally identical between C6 and S3 but the S3 supports ext1 wakeup on GPIO 0–21 (all RTC-capable), while the C6 uses `esp_sleep_enable_ext1_wakeup_io()`. The existing `rtc_gpio_init()` + `esp_sleep_enable_ext1_wakeup()` call sequence continues to compile on S3 but `esp_sleep_enable_ext1_wakeup()` is deprecated in IDF v6; the new call is `esp_sleep_enable_ext1_wakeup_io()`.

WiFi stack (`ESPAsyncWebServer` / `AsyncTCP`), `Preferences`, and `HTTPClient` are all fully compatible with ESP32-S3 Arduino core; no changes needed beyond recompilation.

**Primary recommendation:** Replace the custom WaveShare driver entirely with `Seeed_GFX`. Treat that library as a black box for SPI; only expose a `sendRawByte()` shim so the existing streaming image pipeline (`epd.SendCommand(0x10)` → byte-by-byte `epd.SendData()`) can be preserved, or refactor the download path to buffer the full 4bpp packed image and call `epaper.pushImage()`.

---

## Standard Stack

### Firmware (Arduino / ESP32-S3)

| Library | Version (verified 2026-05) | Purpose | Why standard |
|---------|---------------------------|---------|--------------|
| Seeed_GFX | latest master (no semver tag) | T133A01 display driver + GFX abstraction | Official Seeed library; only supported driver for T133A01 |
| ESP32 Arduino core | 3.x (esp32async fork) | ESP32-S3 HAL | Maintained by Espressif |
| AsyncTCP (esp32async fork) | 3.3.x | Async TCP for captive portal | Original repo archived Jan 2025; use `esp32async` org fork |
| ESPAsyncWebServer (esp32async fork) | 3.8.x | WiFi captive portal | Same fork; compatible with S3 and IDF 5 |
| ArduinoJson | 6.x or 7.x | JSON parsing for sleep endpoint | Already in use |
| Preferences | built-in | NVS key-value store | Already in use; identical API on S3 |
| HTTPClient | built-in | Image download | Already in use |

### Server-side Python

| Library | Version | Purpose | Change needed |
|---------|---------|---------|---------------|
| Pillow | current | Image resize, color ops | None — only constants change |
| NumPy | current | Pixel array ops | None |
| Cython (cpy.pyx) | current | Floyd-Steinberg dithering | `EPD_W`/`EPD_H` constants must be updated to 1600/1200 |

### Installation (firmware)

```bash
# In Arduino IDE: Sketch > Include Library > Add .ZIP Library
# Download Seeed_GFX from https://github.com/Seeed-Studio/Seeed_GFX
# OR use Arduino Library Manager search: "Seeed_GFX"

# AsyncTCP + ESPAsyncWebServer — use esp32async org:
# Board manager URL: https://espressif.github.io/arduino-esp32/package_esp32_index.json
# Library: "ESP Async WebServer" by esp32async
```

---

## Architecture Patterns

### XIAO ESP32-S3 Plus Pin Mapping

The XIAO form factor exposes these physical header pins (GPIO numbers are the ESP32-S3 chip GPIO, not silkscreen labels):

| Silkscreen | GPIO | Primary function on XIAO S3+ |
|------------|------|-------------------------------|
| D0/A0 | GPIO2 | ADC, general GPIO |
| D1/A1 | GPIO3 | ADC (strapping pin — use with care) |
| D2/A2 | GPIO4 | ADC, general GPIO |
| D3/A3 | GPIO5 | ADC, general GPIO |
| D4/SDA | GPIO6 | I2C data |
| D5/SCL | GPIO7 | I2C clock |
| D8/SCK | GPIO8 | SPI clock (hardware HSPI on S3) |
| D9/MISO | GPIO9 | SPI MISO |
| D10/MOSI | GPIO10 | SPI MOSI |
| D20/RX | GPIO20 | UART RX |
| D21/TX | GPIO21 | UART TX |

Additionally, the S3 Plus board routes several internal GPIOs not on headers:
- GPIO41, GPIO42: labeled A11/A12 but do NOT support ADC
- GPIO43/44: used for internal UART on reTerminal variants

**Battery ADC: GPIO10 (ADC_BAT label in schematic)**
The XIAO ESP32-S3 Plus schematic labels GPIO10 as `ADC_BAT`. However, according to Seeed forum discussions (April 2025), the on-board voltage divider resistors are not populated on all revisions. If the divider is absent, an external 2×200kΩ divider from VBAT to GPIO10 is required. The current firmware reads `analogReadMilliVolts(0)` (GPIO0/pin D0 on C6 boards), which will need to change. Use `analogReadMilliVolts(10)` with a ×2 multiplier, or switch to GPIO2 (A0) with the same divider approach confirmed on earlier XIAO boards.

**Confidence: MEDIUM** — verify divider presence with a multimeter on your specific PCB revision before trusting GPIO10.

### SPI Configuration for Seeed_GFX on EE02 / 13.3" Display

The `Setup510_Seeed_XIAO_EPaper_13inch3_colorful.h` setup file defines:

```cpp
#define TFT_SCLK  D8   // GPIO8
#define TFT_MOSI  D10  // GPIO9 — NOTE: confusingly labeled; actual MOSI is D10/GPIO9
#define TFT_MISO  D9   // -1 in board pins setup (write-only display)
#define TFT_CS    D7   // Primary chip-select
#define TFT_CS1   41   // Secondary CS (second driver IC on 13.3" panel)
#define TFT_DC    10   // Data/Command
#define TFT_RST   38   // Reset (internal GPIO on S3 Plus, not on header)
#define TFT_BUSY  D3   // Busy signal, GPIO5
#define TFT_ENABLE D6  // Display power enable, GPIO... check EPaper_Board_Pins_Setups.h

// ESP32-S3: HSPI port used
#define USE_HSPI_PORT
```

**Important:** The T133A01 uses a 60-pin FFC connector, not a 4-wire SPI header. The Seeed EE02 board provides the FFC-to-SPI bridge. You must use the EE02 driver board as the physical interface; you cannot directly wire the FPC connector to the XIAO headers.

The `SPI.begin()` call in `Seeed_GFX` for ESP32-S3 HSPI becomes:
```cpp
SPI.begin(8, 9, 9, -1);  // SCK=GPIO8, MISO=GPIO9, MOSI=GPIO9 (write-only)
```
This is handled internally by `Seeed_GFX`; the sketch only calls `epaper.begin()`.

### T133A01 Display: Key Specifications

| Property | Value |
|----------|-------|
| Controller | T133A01 (Seeed proprietary / OEM) |
| Resolution | 1200 × 1600 pixels (portrait native) |
| Colors | 6: Black, White, Yellow, Red, Blue, Green |
| Bits per pixel | 4 (two pixels packed per byte, nibble-packed) |
| Interface | 60-pin FFC → SPI via EE02 bridge board |
| Refresh time | ~12 seconds (full refresh) |
| Data format | Same 4bpp nibble packing as WaveShare: `(color_a << 4) | color_b` |
| Buffer size | 1200 × 1600 / 2 = **960,000 bytes** per full frame |

**Color index mapping** (T133A01 firmware codes, from `dither.h` in the Seeed_GFX repo):

| Index in palette | Color | RGB | E-paper 4bpp code |
|-----------------|-------|-----|-------------------|
| 0 | White | (255, 255, 255) | 0x0 |
| 1 | Green | (29, 185, 84) | 0x2 |
| 2 | Red | (229, 57, 53) | 0x6 |
| 3 | Yellow | (255, 216, 0) | 0xB |
| 4 | Blue | (0, 76, 255) | 0xD |
| 5 | Black | (0, 0, 0) | 0xF |

The `COLOR_GET` macro in `T133A01_Defines.h` remaps TFT_eSPI internal color values to these codes at transmission time.

### Deep Sleep API on ESP32-S3

The current code uses `rtc_gpio_init()` + `esp_sleep_enable_ext1_wakeup()`. Both compile on S3. However:

- `esp_sleep_enable_ext1_wakeup()` is deprecated in IDF v6; migrate to `esp_sleep_enable_ext1_wakeup_io()`.
- ESP32-S3 RTC GPIO range is GPIO0–GPIO21 (21 pins). Any of these can be used for ext1 wakeup.
- The current `WAKEUP_PIN GPIO_NUM_2` is valid on S3 (GPIO2 is RTC-capable).
- Wakeup logic changed: ESP32-C6 uses `ESP_EXT1_WAKEUP_ANY_LOW`; ESP32-S3 supports the same constant — no change needed.

**Recommended updated wakeup call for S3 (forward-compatible):**
```cpp
#include "driver/rtc_io.h"
// replaces the 3-line rtc_gpio_init block + old esp_sleep_enable_ext1_wakeup call:
esp_sleep_enable_ext1_wakeup_io(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW);
rtc_gpio_pullup_en(WAKEUP_PIN);
rtc_gpio_pulldown_dis(WAKEUP_PIN);
```

The include `"driver/rtc_io.h"` is identical on both targets.

### Image Streaming vs Buffer Approach

The current firmware streams the hex CSV response byte-by-byte directly to the display via `epd.SendData()` without buffering the full frame. This is memory-efficient (uses only 128 KB BUFFER_SIZE).

For the 13.3" display with `Seeed_GFX`, there are two approaches:

**Option A: Keep streaming, bypass Seeed_GFX for pixel write**
- Call `epaper.startWrite()` then push raw 4bpp bytes directly to T133A01.
- Requires understanding the undocumented T133A01 raw write interface — risk: HIGH.

**Option B: Buffer full frame, use `epaper.pushImage()`**
- Allocate 960 KB in PSRAM (`ps_malloc()`), fill from HTTP stream, then call `epaper.pushImage(0, 0, 1200, 1600, buf)`.
- The XIAO ESP32-S3 Plus has 8 MB PSRAM — easily fits 960 KB.
- Recommended approach: straightforward, uses documented library API.
- `BUFFER_SIZE` in `config.h` must be raised or removed (replace with PSRAM allocation).

**Option C: Server sends the image in Seeed_GFX-expected 2-byte-per-pixel TFT format**
- The `pushImage()` call takes `uint16_t*` and internally maps through `COLOR_GET` to 4bpp.
- This requires the server to pack colors as 16-bit TFT color values — more complex server change.

**Recommendation: Option B**. PSRAM is available; the buffer approach is documented and maintainable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| T133A01 init sequence | Custom register command list | `Seeed_GFX` T133A01 driver | Controller init is undocumented; Seeed_GFX is the only public implementation |
| Floyd-Steinberg dithering for new palette | New cpy.pyx | Update existing cpy.pyx palette constants | Working Cython dithering already exists; only EPD_W/H and color values change |
| SPI begin with explicit pins | Manual SPI.beginTransaction | `Seeed_GFX`'s `epaper.begin()` | Handles HSPI port selection, CS management, and timing internally |
| WiFi captive portal | New portal code | Existing `WifiCaptive` + `ESPAsyncWebServer` (esp32async fork) | Already working; just recompile for S3 target |

---

## Common Pitfalls

### Pitfall 1: Wrong SPI GPIO Numbers (MOSI/MISO Confusion)
**What goes wrong:** The XIAO S3+ Setup510 header lists `TFT_MOSI D10` but the internal `EPaper_Board_Pins_Setups.h` for `USE_XIAO_EPAPER_DISPLAY_BOARD_EE02` wires `MOSI` to the GPIO that D10 maps to (GPIO9 via HSPI, not GPIO10). Different Seeed sources use different conventions.
**How to avoid:** Trust `EPaper_Board_Pins_Setups.h` and the EE02 schematic over the setup file header comments. Verify with a logic analyzer on first bring-up.

### Pitfall 2: Buffer Size Insufficient for 1.2 MP Display
**What goes wrong:** `BUFFER_SIZE 131072` (128 KB) in `config.h` was sized for the 800×480/2 = 192 KB WaveShare display. The 13.3" frame is 960 KB. Streaming through a 128 KB read buffer into PSRAM is fine, but allocating the destination in SRAM will panic.
**How to avoid:** Use `ps_malloc(960000)` from PSRAM, not stack or heap. Check `ESP.getFreePsram()` before allocation. Update `BUFFER_SIZE` constant or remove it.
**Warning signs:** `malloc` returns NULL, or `ets_printf` shows heap allocation failure.

### Pitfall 3: Display Orientation / Resolution Mismatch Between Server and Firmware
**What goes wrong:** The 13.3" panel is portrait-native (1200 wide × 1600 tall) but the server's `cpy.pyx` hardcodes `EPD_W = 800` and `EPD_H = 480`. The `scale_img_in_memory()` function uses those constants throughout.
**How to avoid:** Update `EPD_W = 1200` and `EPD_H = 1600` in `cpy.pyx` and recompile the Cython extension. Also update `target_width=800, target_height=480` defaults in `scale_img_in_memory()`. The existing rotation logic handles portrait/landscape; no structural change needed — only the constants.

### Pitfall 4: Server Palette RGB Values Don't Match T133A01
**What goes wrong:** The current `app.py` palette uses rough RGB values (e.g., Yellow = `(255, 255, 0)`, Red = `(255, 0, 0)`, Blue = `(0, 0, 255)`, Green = `(0, 255, 0)`). The T133A01's actual primaries per Seeed's own dither.cpp are different (Yellow = `(255, 216, 0)`, Red = `(229, 57, 53)`, Blue = `(0, 76, 255)`, Green = `(29, 185, 84)`). Nearest-neighbor quantization to incorrect targets produces wrong colors on-panel.
**How to avoid:** Update both the `palette` list on line ~82 of `app.py` and the `epd_colors` array in `cpy.pyx` to match the values from Seeed's `dither.cpp` (kE6Rgb table — values documented above).

### Pitfall 5: `esp_sleep_enable_ext1_wakeup()` Deprecation Warning
**What goes wrong:** With IDF v5+, this function triggers a deprecation warning. It still works on S3 but compiles with warnings that may break `-Werror` builds.
**How to avoid:** Replace with `esp_sleep_enable_ext1_wakeup_io()` (takes a bitmask of IOs and a mode).

### Pitfall 6: AsyncTCP / ESPAsyncWebServer from Archived Repo
**What goes wrong:** The original `me-no-dev` repository was archived January 2025. Installing from it gives outdated code that does not compile cleanly with ESP32 Arduino core 3.x.
**How to avoid:** Use the `esp32async` organization fork on GitHub/Arduino Library Manager.

### Pitfall 7: Battery ADC Divider May Not Be Populated
**What goes wrong:** If the GPIO10 ADC_BAT voltage divider is absent on the PCB, `analogReadMilliVolts(10)` reads garbage and the battery check logic shuts down the device erroneously.
**How to avoid:** Verify with a multimeter or omit battery voltage checking until hardware is confirmed. The `checkVoltage()` function returning false causes the device to enter 24-hour sleep — a silently broken device.

---

## Code Examples

### EE02 Board Init with Seeed_GFX

```cpp
// Source: Seeed_GFX Bitmap_13inch30.ino example
#include <Seeed_GFX.h>
#include <TFT_eSPI.h>

TFT_eSPI epaper;

void setup() {
  Serial.begin(115200);
  epaper.begin();
  epaper.fillScreen(TFT_WHITE);
  epaper.update();   // triggers full display refresh
  epaper.sleep();    // enters e-paper sleep mode
}
```

### PSRAM-backed frame buffer

```cpp
// Allocate 13.3" frame in PSRAM (960,000 bytes for 4bpp 1200x1600)
uint8_t* frame_buf = (uint8_t*)ps_malloc(1200 * 1600 / 2);
if (!frame_buf) {
  Serial.println("PSRAM allocation failed");
  return false;
}
// Fill frame_buf from HTTP stream, then:
epaper.pushImage(0, 0, 1200, 1600, (uint16_t*)frame_buf);
epaper.update();
free(frame_buf);
```

### Updated Deep Sleep (ESP32-S3 forward-compatible)

```cpp
// Source: Espressif IDF docs + Seeed XIAO S3 sleep wiki
#include "driver/rtc_io.h"

// Timer wakeup — identical on S3
esp_sleep_enable_timer_wakeup(sleep_time_us);

// Ext1 wakeup — new API (replaces rtc_gpio_init block)
esp_sleep_enable_ext1_wakeup_io(1ULL << GPIO_NUM_2, ESP_EXT1_WAKEUP_ANY_LOW);
rtc_gpio_pullup_en(GPIO_NUM_2);
rtc_gpio_pulldown_dis(GPIO_NUM_2);

esp_deep_sleep_start();
```

### Updated Battery Voltage Read (XIAO S3 Plus)

```cpp
// GPIO10 = ADC_BAT on S3 Plus schematic (verify divider is populated)
analogReadResolution(12);
int raw = 0;
for (int i = 0; i < 50; i++) {
  raw += analogReadMilliVolts(10);  // was analogReadMilliVolts(0) on C6
  delay(5);
}
int batteryVoltage = (raw / 50) * 2;  // ×2 for 1:2 voltage divider
```

### Updated SPI.begin() in epdif.cpp (if keeping custom driver shim)

```cpp
// ESP32-S3 HSPI explicit pin assignment
// SCK=GPIO8, MISO=GPIO9, MOSI=GPIO9 (write-only; MISO unused by display)
SPI.begin(8, 9, 9, -1);
SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
// Note: T133A01 max SPI clock is lower than WaveShare; 2 MHz confirmed working, 10 MHz reported working too
```

---

## Delta Map: Current vs Target

### `epdif.h` — PIN CHANGES REQUIRED

| Current (FireBeetle C6) | Target (XIAO S3 Plus / EE02) | Notes |
|------------------------|-------------------------------|-------|
| `BUSY_PIN 18` | `BUSY_PIN` = GPIO5 (D3) | Per EPaper_Board_Pins_Setups.h USE_XIAO_EPAPER_DISPLAY_BOARD_EE02 |
| `RST_PIN 14` | `RST_PIN` = GPIO38 (internal) | Not on header; wired on EE02 board |
| `DC_PIN 8` | `DC_PIN` = GPIO10 | Per setup510 |
| `CS_PIN 1` | `CS_PIN` = GPIO44 (D7 mapping) + secondary `CS1_PIN` = 41 | Dual CS for T133A01 |
| `SPI.begin()` (default) | `SPI.begin(8, 9, 9, -1)` explicit HSPI | S3 requires explicit HSPI port selection |

### `epd7in3e.h` — RESOLUTION AND COLOR CHANGES REQUIRED

| Current | Target |
|---------|--------|
| `EPD_WIDTH 800` | `EPD_WIDTH 1200` |
| `EPD_HEIGHT 480` | `EPD_HEIGHT 1600` |
| `EPD_7IN3E_GREEN 0x2` | T133A01 green code `0x2` — same |
| `EPD_7IN3E_BLUE 0x3` | T133A01 blue code `0xD` — DIFFERENT |
| `EPD_7IN3E_RED 0x4` | T133A01 red code `0x6` — DIFFERENT |
| `EPD_7IN3E_YELLOW 0x5` | T133A01 yellow code `0xB` — DIFFERENT |
| `EPD_7IN3E_BLACK 0x0` | T133A01 black code `0xF` — DIFFERENT |
| `EPD_7IN3E_WHITE 0x1` | T133A01 white code `0x0` — DIFFERENT |

**All color index values are different.** The server's `depalette_image()` function maps indices back to display codes; both ends need updating consistently.

### `config.h` — CHANGES REQUIRED

| Current | Target | Reason |
|---------|--------|--------|
| `CONFIG_PIN 2U` | pick a free GPIO (e.g., GPIO4/D2) | GPIO2 is CONFIG_PIN AND WAKEUP_PIN — safe to keep if pull-up prevents false trigger |
| `WAKEUP_PIN GPIO_NUM_2` | can keep GPIO_NUM_2 | GPIO2 is RTC-capable on S3 |
| `BUFFER_SIZE 131072U` | remove or set to HTTP chunk size only | Frame buffer now lives in PSRAM |

### `epd7in3e.ino` — CHANGES REQUIRED

| Current line | Change |
|-------------|--------|
| `analogReadMilliVolts(0)` (GPIO0 on C6) | `analogReadMilliVolts(10)` (GPIO10 ADC_BAT on S3+) |
| Custom driver instantiation `Epd epd` | Replace with `TFT_eSPI epaper` from Seeed_GFX |
| `epd.Init()` | `epaper.begin()` |
| `epd.SendCommand(0x10)` + `epd.SendData(byte)` loop | Allocate PSRAM buf, stream into it, then `epaper.pushImage()` |
| `epd.TurnOnDisplay()` | `epaper.update()` |
| `epd.Sleep()` | `epaper.sleep()` |
| `epd.Clear(EPD_7IN3E_WHITE)` | `epaper.fillScreen(TFT_WHITE); epaper.update()` |
| `#include "driver/rtc_io.h"` | Keep same include |
| `esp_sleep_enable_ext1_wakeup(...)` | Replace with `esp_sleep_enable_ext1_wakeup_io(...)` |

### `app.py` and `cpy.pyx` — SERVER CHANGES REQUIRED

| Location | Current | Target |
|----------|---------|--------|
| `cpy.pyx` line 14 | `EPD_W = 800` | `EPD_W = 1200` |
| `cpy.pyx` line 15 | `EPD_H = 480` | `EPD_H = 1600` |
| `cpy.pyx` epd_colors array | `[0,0,0],[1,1,1],[1,1,0],[1,0,0],[0,0,1],[0,1,0]` | Update to Seeed values: `[0,0,0],[1,1,1],[1.0,0.847,0],[0.898,0.224,0.208],[0,0.298,1],[0.114,0.725,0.329]` |
| `app.py` line ~82 `palette` (depalette_image) | `(255,255,0),(191,0,0),(100,64,255),(67,138,28)` | `(255,216,0),(229,57,53),(0,76,255),(29,185,84)` |
| `app.py` scale_img palette ~line 214 | `255,255,0` / `255,0,0` / `0,0,255` / `0,255,0` | Match above Seeed values |
| `scale_img_in_memory(target_width=800, target_height=480)` | `target_width=1200, target_height=1600` | Recompile cpy.pyx after change |
| `depalette_image` index shift | `indices[indices > 3] += 1` | Re-examine: this was WaveShare-specific to skip color index 3 (CLEAN). T133A01 has no CLEAN code — verify or remove this line |

---

## Environment Availability Audit

Step 2.6: SKIPPED for server side (Python env is pre-existing Docker container).

For firmware compilation, the target is Arduino IDE / PlatformIO on the developer's machine — not auditable in this environment. Dependencies to confirm before build:

| Dependency | Required by | Action |
|------------|------------|--------|
| Seeed_GFX library | New display driver | Install from GitHub |
| ESP32 Arduino core 3.x | ESP32-S3 support | Update board manager |
| ESPAsyncWebServer (esp32async) | WifiCaptive | Replace archived library |
| XIAO ESP32-S3 Plus board definition | Arduino target | Add Seeed board manager URL |

---

## Open Questions

1. **EE02 board required or raw display?**
   - What we know: The 13.3" FPC uses a 60-pin connector. The Seeed EE02 board provides the FPC socket, level shifting, power regulation, and FPC-to-SPI bridge. Seeed_GFX is designed to run on the EE02's ESP32-S3.
   - What's unclear: Whether the user is buying the EE02 kit (which already contains an S3 Plus) or wiring the raw display panel to a standalone XIAO S3 Plus. If it's the standalone XIAO + bare panel, a custom FPC breakout board is required — that is non-trivial.
   - Recommendation: Clarify before planning. If using EE02 kit, the XIAO S3 Plus is already on the board and pin choices are fixed by EE02 schematic. If separate XIAO + raw panel, requires FPC breakout.

2. **Battery ADC on GPIO10 — divider populated?**
   - What we know: Schematic labels GPIO10 as ADC_BAT but forum post from April 2025 says the voltage divider may not be physically present on all revisions.
   - What's unclear: PCB revision of the actual hardware being used.
   - Recommendation: Measure VBAT pin at GPIO10 with a multimeter before writing battery check code. Fallback: use GPIO2 (D0/A0) with an external divider identical to the XIAO C3 approach.

3. **Raw SPI access to T133A01 vs mandatory Seeed_GFX abstraction**
   - What we know: Seeed_GFX manages the complete init sequence. The T133A01_Init.h contains register commands; they are in the public repo but poorly documented.
   - What's unclear: Whether `pushImage()` can be called without the GFX sprite layer, or whether the existing hex-CSV streaming can be reimplemented via direct `SPI.transfer()`.
   - Recommendation: Use the PSRAM buffer + `pushImage()` path (Option B). Attempting to bypass Seeed_GFX's init sequence is high risk.

4. **`depalette_image` index shift line (`indices[indices > 3] += 1`)**
   - What we know: In the WaveShare 7.3" driver, color index 3 is BLUE and color index 4 is RED, but there is a CLEAN color at index 3 (0x3) that must be skipped. The shift line in `app.py` compensates for this.
   - What's unclear: The T133A01's nibble codes (0x0/0x2/0x6/0xB/0xD/0xF) are non-contiguous — `depalette_image` returns 0–5 indices, not these raw codes. The entire `depalette_image()` → `convert_to_c_code_in_memory()` pipeline may need to be replaced with a mapping table that converts palette indices to T133A01 codes directly.
   - Recommendation: Rewrite `convert_to_c_code_in_memory()` to use an explicit `index_to_nibble` lookup table: `[0x0, 0x2, 0x6, 0xB, 0xD, 0xF]`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| `esp_sleep_enable_ext1_wakeup()` | `esp_sleep_enable_ext1_wakeup_io()` | IDF v5.x | Old API deprecated in v6; still compiles |
| me-no-dev AsyncTCP/ESPAsyncWebServer | esp32async fork | Jan 2025 (original archived) | Must use fork for IDF 5 / Arduino core 3 |
| Direct WaveShare SPI driver | Seeed_GFX library abstraction | N/A (new display) | Library handles init complexity |

---

## Sources

### Primary (HIGH confidence)
- Seeed_GFX GitHub `TFT_Drivers/T133A01_Defines.h` — resolution (1200×1600), 4bpp, color code mapping
- Seeed_GFX GitHub `User_Setups/EPaper_Board_Pins_Setups.h` — EE02 pin definitions (BUSY, RST, DC, CS, CS1, ENABLE)
- Seeed_GFX GitHub `examples/reTerminal_E1004_SDcard_Color6/dither.cpp` — PAL_E6 color RGB values
- Seeed_GFX GitHub `User_Setups/Setup510_Seeed_XIAO_EPaper_13inch3_colorful.h` — 1200×1600, T133A01_DRIVER, USE_HSPI_PORT
- Espressif ESP-IDF docs (sleep_modes.html) — ESP32-S3 RTC GPIO range (0–21), ext1 API
- Seeed Studio Wiki XIAO ESP32-S3 Getting Started — SPI pins GPIO7/8/9, battery ADC note

### Secondary (MEDIUM confidence)
- Seeed Studio Forum thread "XIAO ESP32S3 Plus ADC_BAT on GPIO10" (Apr 2025) — GPIO10 voltage divider may be unpopulated
- CNX Software EE02 review (Feb 2026) — confirms 1600×1200, 6 colors, Seeed_GFX library name, 60-pin FFC
- espboards.dev XIAO ESP32S3 Plus — complete GPIO table
- Espressif ESP32-S3 RTC GPIO table (GPIO 0–21) — confirmed in IDF docs

### Tertiary (LOW confidence)
- Seeed Wiki reTerminal E1004 Arduino page — pin numbers for reTerminal variant (different board than standalone EE02; pin mapping may differ)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Seeed_GFX is the only supported library; AsyncTCP/ESPAsyncWebServer migration is well-documented
- Architecture (pin map): MEDIUM-HIGH — confirmed from Seeed_GFX source; EE02 schematic not directly read
- Color palette: HIGH — sourced directly from Seeed's own dither.cpp in the official repo
- Battery ADC: MEDIUM — GPIO10 confirmed in schematic label but physical divider presence unverified
- Display streaming approach (Option B / PSRAM): MEDIUM — pushImage() is documented; 8MB PSRAM capacity is confirmed for S3 Plus

**Research date:** 2026-05-27
**Valid until:** 2026-08-27 (stable hardware; 90-day estimate)
