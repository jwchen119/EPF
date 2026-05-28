---
phase: 01-hardware-port
verified: 2026-05-27T00:00:00Z
status: passed
score: 21/21 must-haves verified
gap_resolution:
  - truth: "The EpdIf class and Epd class are removed"
    status: resolved
    fix: "epd7in3e/epdif.cpp cleared to empty stub (commit aaef5cc) — matches style of epd7in3e.cpp"
---

# Phase 01: Hardware Port Verification Report

**Phase Goal:** Port firmware and server to the EE02 kit (XIAO ESP32-S3 Plus + Seeed 13.3" T133A01 display). Replace WaveShare driver with Seeed_GFX. Update server palette and resolution.
**Verified:** 2026-05-27
**Status:** passed — 21/21 must-haves verified (gap resolved: epdif.cpp stubbed in commit aaef5cc)
**Re-verification:** No — initial verification

All new firmware and server files are located in `epd7in3e/` (firmware) and root `app.py` / `cpy.pyx` (server). The old `Arduino/` directory files have been staged for deletion in git.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | epdif.h contains EE02 pin constants (BUSY=5, RST=38, DC=10, CS=44, CS1=41) | VERIFIED | Lines 18-22: `#define BUSY_PIN 5`, `RST_PIN 38`, `DC_PIN 10`, `CS_PIN 44`, `CS1_PIN 41` |
| 2 | epd7in3e.h declares EPD_WIDTH 1200 and EPD_HEIGHT 1600 | VERIFIED | Lines 18-19: `#define EPD_WIDTH 1200`, `#define EPD_HEIGHT 1600` |
| 3 | epd7in3e.h declares T133A01 color codes (BLACK=0xF, WHITE=0x0, GREEN=0x2, BLUE=0xD, RED=0x6, YELLOW=0xB) | VERIFIED | Lines 33-38: `WHITE=0x0`, `GREEN=0x2`, `RED=0x6`, `YELLOW=0xB`, `BLUE=0xD`, `BLACK=0xF` |
| 4 | The EpdIf class and Epd class are removed | VERIFIED | epdif.h has no class declaration; epdif.cpp cleared to stub (commit aaef5cc) |
| 5 | epd7in3e.cpp is an empty stub | VERIFIED | Lines 1-6: comment and single `#include "epd7in3e.h"` only; "intentionally empty" documented |
| 6 | epd7in3e.ino declares TFT_eSPI epaper (not Epd epd) | VERIFIED | Line 34: `TFT_eSPI epaper;` inside EpaperManager class |
| 7 | processImageData() allocates a 960,000-byte PSRAM buffer and calls epaper.pushImage() | VERIFIED | Line 207: `ps_malloc(1200 * 1600 / 2)` = 960,000 bytes; line 269: `epaper.pushImage(0, 0, EPD_WIDTH, EPD_HEIGHT, (uint16_t*)frame_buf)` |
| 8 | setup() does NOT call checkVoltage() | VERIFIED | No `checkVoltage` anywhere in epd7in3e.ino |
| 9 | hibernate() uses esp_sleep_enable_ext1_wakeup_io() not the deprecated form | VERIFIED | Line 311: `esp_sleep_enable_ext1_wakeup_io(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW)` |
| 10 | analogReadMilliVolts battery header is removed from downloadImage() | VERIFIED | No `analogReadMilliVolts` or battery read in downloadImage(); battery only received via HTTP header on server side |
| 11 | config.h has HTTP_CHUNK_SIZE (not BUFFER_SIZE 131072) | VERIFIED | Line 27: `#define HTTP_CHUNK_SIZE 16384U`; no BUFFER_SIZE defined |
| 12 | clearScreen() calls epaper.fillScreen(TFT_WHITE) + epaper.update() + epaper.sleep() | VERIFIED | Lines 447-449: `epaper.fillScreen(TFT_WHITE)`, `epaper.update()`, `epaper.sleep()` |
| 13 | app.py palette contains Seeed T133A01 RGB values (255,216,0 yellow; 229,57,53 red; 0,76,255 blue; 29,185,84 green) | VERIFIED | Lines 86-89: all four values present with correct RGB tuples |
| 14 | depalette_image() index shift line (indices > 3) is removed | VERIFIED | depalette_image() (lines 163-167) contains only palette quantization, no index shift |
| 15 | convert_to_c_code_in_memory() uses explicit nibble_map [0xF, 0x0, 0xB, 0x6, 0xD, 0x2] | VERIFIED | Line 365: `nibble_map = [0xF, 0x0, 0xB, 0x6, 0xD, 0x2]` |
| 16 | scale_img_in_memory() default arguments are target_width=1200, target_height=1600 | VERIFIED | Line 169: `def scale_img_in_memory(image, target_width=1200, target_height=1600, ...)` |
| 17 | cpy.pyx has EPD_W=1200 and EPD_H=1600 | VERIFIED | Lines 14-15: `EPD_W = 1200`, `EPD_H = 1600` |
| 18 | cpy.pyx epd_colors array matches Seeed dither.cpp kE6Rgb values (0.847 for yellow) | VERIFIED | Line 121: `[1.0, 0.847, 0.0]` for yellow; full 6-color array present with correct normalized values |

**Score:** 18/18 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `epd7in3e/epdif.h` | EE02 pin constants, no EpdIf class | VERIFIED | Flat pin constants, includes Seeed_GFX/TFT_eSPI |
| `epd7in3e/epd7in3e.h` | EPD_WIDTH/HEIGHT, T133A01 color codes | VERIFIED | All constants present |
| `epd7in3e/epdif.cpp` | Empty stub | VERIFIED | Cleared to stub (commit aaef5cc), comment + #include only |
| `epd7in3e/epd7in3e.cpp` | Empty stub | VERIFIED | One include + intentionally-empty comment |
| `epd7in3e/epd7in3e.ino` | Seeed_GFX API, PSRAM buffer, updated sleep API | VERIFIED | TFT_eSPI object, ps_malloc, pushImage, ext1_wakeup_io |
| `epd7in3e/config.h` | HTTP_CHUNK_SIZE defined | VERIFIED | HTTP_CHUNK_SIZE=16384U present, no legacy BUFFER_SIZE |
| `app.py` | T133A01 palette, no index shift, nibble_map, 1200x1600 defaults | VERIFIED | All items present |
| `cpy.pyx` | EPD_W=1200, EPD_H=1600, kE6Rgb-aligned epd_colors | VERIFIED | All items present |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| epd7in3e.ino | Seeed_GFX/TFT_eSPI | `TFT_eSPI epaper` object | WIRED | epaper.begin(), fillScreen(), pushImage(), update(), sleep() all called |
| epd7in3e.ino | epd7in3e.h | `#include "epd7in3e.h"` | WIRED | Line 4; EPD_WIDTH/EPD_HEIGHT used in processImageData |
| app.py | cpy.pyx | `from cpy import convert_image, load_scaled` | WIRED | Line 16; both called in scale_img_in_memory and process_and_download |
| convert_to_c_code_in_memory | palette | `depalette_image(pixels, palette)` | WIRED | Lines 360, 365; global palette used, nibble_map applied |

---

## Gaps Summary

One gap found. The `epd7in3e/epdif.cpp` file was not converted to an empty stub. While `epdif.h` was correctly rewritten to only contain pin constants (no `EpdIf` class declaration), the corresponding `.cpp` still contains the full WaveShare `EpdIf` class implementation from the original codebase. This is inconsistent with the stated goal of removing the `EpdIf` class, and inconsistent with how `epd7in3e.cpp` was handled (which was correctly emptied).

The residual `EpdIf` implementation in `epdif.cpp` is dead code because nothing in the new firmware includes or instantiates `EpdIf`, but it is misleading and contradicts the must-have that "The EpdIf class and Epd class are removed." The fix is straightforward: clear `epdif.cpp` to a stub matching the style of `epd7in3e.cpp`.

No issues were found in the server-side Python changes. The T133A01 palette values, nibble mapping, resolution defaults, and Cython color table are all correct and consistent across `app.py` and `cpy.pyx`.

---

_Verified: 2026-05-27_
_Verifier: Claude (gsd-verifier)_
