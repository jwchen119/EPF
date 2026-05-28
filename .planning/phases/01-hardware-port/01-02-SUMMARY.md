---
phase: 01-hardware-port
plan: 02
subsystem: display-driver
tags: [arduino, esp32-s3, eink, seeed-gfx, tft-espi, t133a01, ee02, psram, deep-sleep]

requires:
  - phase: 01-hardware-port
    plan: 01
    provides: [TFT_eSPI/Seeed_GFX includes in epdif.h, T133A01 color constants in epd7in3e.h, EE02 pin constants]

provides:
  - epd7in3e.ino rewritten with Seeed_GFX API (TFT_eSPI epaper object)
  - PSRAM frame buffer allocation (960KB ps_malloc) for 1200x1600 4bpp display
  - HTTP chunk streaming into PSRAM buffer (HTTP_CHUNK_SIZE 16384)
  - Battery guard removed (checkVoltage + analogReadMilliVolts)
  - IDF v5 sleep API (esp_sleep_enable_ext1_wakeup_io replacing deprecated form)
  - Updated config.h: BUFFER_SIZE replaced with HTTP_CHUNK_SIZE

affects: [01-03, app.py, cpy.pyx]

tech-stack:
  added: []
  patterns:
    - "PSRAM frame buffer: ps_malloc(960000) then epaper.pushImage() instead of streaming SendData()"
    - "processImageData signature changed to (WiFiClient &stream, int contentLength)"
    - "epaper.begin() once in begin() and clearScreen(); no re-init before each display op"

key-files:
  created: []
  modified:
    - epd7in3e/epd7in3e.ino
    - epd7in3e/config.h

key-decisions:
  - "PSRAM buffer approach (Option B): ps_malloc 960KB, stream HTTP into buffer, then pushImage() — avoids undocumented T133A01 raw write interface"
  - "processImageData refactored to take (WiFiClient &stream, int contentLength) — cleaner separation from HTTPClient lifecycle"
  - "Battery guard entirely removed: GPIO10 ADC divider may not be populated on all PCB revisions; removal prevents silent 24h sleep on new hardware"
  - "HTTP_CHUNK_SIZE 16384 replaces BUFFER_SIZE 131072 — chunk buffer is heap-only, frame buffer lives in PSRAM"
  - "epaper.begin() kept in begin() and clearScreen() — Seeed_GFX requires init before display operations"

patterns-established:
  - "PSRAM allocation pattern: ps_malloc with null check + free(frame_buf) after pushImage"
  - "HTTP streaming into fixed-size PSRAM buffer with overflow guard (frame_offset < FRAME_SIZE check)"

requirements-completed: []

duration: 10min
completed: 2026-05-27
---

# Phase 01 Plan 02: Rewrite main .ino — Seeed_GFX API, PSRAM frame buffer, remove battery guard, fix sleep API — Summary

**epd7in3e.ino fully migrated from WaveShare driver to Seeed_GFX: TFT_eSPI object, 960KB PSRAM frame buffer with HTTP chunk streaming, IDF v5 sleep API, and battery guard removed.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-27
- **Completed:** 2026-05-27
- **Tasks:** 2 completed (config.h update + 9-change .ino rewrite)
- **Files modified:** 2

## Accomplishments

- Replaced `Epd epd` with `TFT_eSPI epaper` and all associated API calls (Init/SendCommand/SendData/TurnOnDisplay/Sleep/Clear)
- Rewrote `processImageData()` to allocate 960KB PSRAM frame buffer, stream HTTP hex-CSV into it, then call `epaper.pushImage()` + `epaper.update()` + `epaper.sleep()`
- Removed `checkVoltage()` method and battery guard block in `setup()` (removes `analogReadMilliVolts` dependency entirely)
- Updated `hibernate()` to use `esp_sleep_enable_ext1_wakeup_io()` (IDF v5 API), removing `rtc_gpio_init` + `rtc_gpio_set_direction` calls
- Replaced `BUFFER_SIZE 131072` with `HTTP_CHUNK_SIZE 16384` in `config.h`
- Updated pin layout comment to XIAO ESP32-S3 Plus / EE02 HAT

## Task Commits

1. **Task 1 + Task 2 combined** - `8528ce3` (feat)

## Files Created/Modified

- `epd7in3e/epd7in3e.ino` — All 9 targeted changes applied; WiFi/Preferences/HTTPClient logic untouched
- `epd7in3e/config.h` — BUFFER_SIZE replaced with HTTP_CHUNK_SIZE 16384

## Decisions Made

- `processImageData` signature changed from `(HTTPClient *http)` to `(WiFiClient &stream, int contentLength)` because the PSRAM implementation no longer needs the full HTTPClient handle — only the byte stream and its length. The call site was updated to pass `*http.getStreamPtr()` and `http.getSize()`.
- Battery guard removed entirely rather than updated to GPIO10: the research document flagged that the voltage divider may not be physically populated on all board revisions, which would cause the device to enter 24h sleep silently on first boot. Removal is safer until hardware is verified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated processImageData call site to match new signature**
- **Found during:** Task 2, Change 4
- **Issue:** Plan specified new signature `(WiFiClient &stream, int contentLength)` but did not explicitly update the call site at `success = processImageData(&http)`
- **Fix:** Updated call to `success = processImageData(*http.getStreamPtr(), http.getSize())`
- **Files modified:** `epd7in3e/epd7in3e.ino`
- **Verification:** Grep confirms no `processImageData(&http)` remains
- **Committed in:** `8528ce3`

---

**Total deviations:** 1 auto-fixed (Rule 1 - call site consistency)
**Impact on plan:** Required for code to compile. No scope creep.

## Issues Encountered

None beyond the call site deviation above.

## Verification Results

All acceptance criteria passed:

| Criterion | Result |
|-----------|--------|
| `TFT_eSPI epaper;` present | PASS (1 occurrence) |
| `ps_malloc(1200 * 1600 / 2)` present | PASS (1 occurrence) |
| `epaper.pushImage(0, 0, EPD_WIDTH, EPD_HEIGHT` present | PASS (1 occurrence) |
| `esp_sleep_enable_ext1_wakeup_io` present | PASS (1 occurrence) |
| `Epd epd` absent | PASS (0 occurrences) |
| `epd.Init()` absent | PASS (0 occurrences) |
| `epd.SendData` absent | PASS (0 occurrences) |
| `checkVoltage` absent | PASS (0 occurrences) |
| `analogReadMilliVolts` absent | PASS (0 occurrences) |
| `rtc_gpio_init(` absent | PASS (0 occurrences) |
| `WifiCaptivePortal` >= 3 occurrences | PASS (6 occurrences) |
| `preferences.begin` >= 1 occurrence | PASS (2 occurrences) |
| `BUFFER_SIZE` absent from config.h | PASS |
| `HTTP_CHUNK_SIZE 16384` present in config.h | PASS |

## Known Stubs

None — all display operations are wired to the Seeed_GFX API. The PSRAM buffer approach is fully implemented. WiFi, Preferences, and HTTPClient remain unchanged from working pre-port state.

## Next Phase Readiness

- `epd7in3e.ino` and `config.h` are ready for plan 01-03 (server-side Python changes: cpy.pyx resolution + palette, app.py palette)
- Firmware will not compile until `Seeed_GFX` library is installed in the Arduino environment (expected — library install is a hardware setup step, not a code task)

---
*Phase: 01-hardware-port*
*Completed: 2026-05-27*
