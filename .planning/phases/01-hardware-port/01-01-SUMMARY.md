---
phase: 01-hardware-port
plan: 01
subsystem: display-driver
tags: [arduino, esp32-s3, eink, seeed-gfx, tft-espi, t133a01, ee02]

requires: []
provides:
  - EE02/XIAO ESP32-S3 Plus pin constants (BUSY=5, RST=38, DC=10, CS=44, CS1=41)
  - T133A01 display resolution constants (1200x1600)
  - T133A01 4bpp color nibble codes (WHITE=0x0, GREEN=0x2, RED=0x6, YELLOW=0xB, BLUE=0xD, BLACK=0xF)
  - Seeed_GFX / TFT_eSPI includes replacing WaveShare SPI class
  - Empty epd7in3e.cpp stub (all display ops delegated to Seeed_GFX)
affects: [epd7in3e.ino, config.h, app.py, cpy.pyx]

tech-stack:
  added: [Seeed_GFX, TFT_eSPI]
  patterns: [flat pin constants replacing class-based HAL, Seeed_GFX as display abstraction]

key-files:
  created: [epd7in3e/epdif.h, epd7in3e/epd7in3e.h, epd7in3e/epd7in3e.cpp]
  modified: []

key-decisions:
  - "Remove EpdIf class entirely; use flat #define pin constants — Seeed_GFX owns the SPI layer"
  - "CS_PIN=44, CS1_PIN=41 — dual chip-select required by T133A01 (two driver ICs)"
  - "RST_PIN=38 is an internal GPIO on EE02, not exposed on XIAO header"
  - "ALL color nibble values differ from WaveShare UC8179: BLACK=0xF not 0x0, WHITE=0x0 not 0x1, etc."
  - "epd7in3e.cpp left intentionally empty — WaveShare Init/SendCommand/TurnOnDisplay replaced by epaper.begin()/pushImage()/update()"

patterns-established:
  - "Seeed_GFX as black-box display driver: sketch calls epaper.begin(), epaper.pushImage(), epaper.update(), epaper.sleep()"
  - "Pin constants in epdif.h serve as documentation reference for EE02 board wiring"

requirements-completed: []

duration: 1min
completed: 2026-05-27
---

# Phase 01 Plan 01: Replace WaveShare HAL with EE02 pin constants and Seeed_GFX includes — Summary

**WaveShare EpdIf class and 346-line UC8179 driver replaced with flat EE02 pin constants and a Seeed_GFX include stub, correcting all six T133A01 4bpp color codes and updating resolution from 800x480 to 1200x1600.**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-05-27T15:58:53Z
- **Completed:** 2026-05-27T15:59:48Z
- **Tasks:** 3 completed
- **Files modified:** 3

## Accomplishments

- Rewrote `epdif.h`: removed EpdIf class, defined 5 EE02 board pin constants, included Seeed_GFX and TFT_eSPI headers
- Rewrote `epd7in3e.h`: updated resolution to 1200x1600, replaced all 6 WaveShare color codes with T133A01 4bpp nibble values
- Replaced `epd7in3e.cpp` (346 lines of WaveShare UC8179 commands) with 6-line intentionally-empty stub

## Task Commits

1. **All three tasks (epdif.h + epd7in3e.h + epd7in3e.cpp)** - `3bd6117` (feat)

## Files Created/Modified

- `epd7in3e/epdif.h` — EE02 pin constants (BUSY=5, RST=38, DC=10, CS=44, CS1=41), Seeed_GFX/TFT_eSPI includes, no EpdIf class
- `epd7in3e/epd7in3e.h` — T133A01 resolution (1200x1600) and color codes, no Epd class
- `epd7in3e/epd7in3e.cpp` — intentionally empty stub (WaveShare driver removed)

## Verification Results

```
BUSY_PIN  5   // GPIO5
RST_PIN   38  // GPIO38
DC_PIN    10  // GPIO10
CS_PIN    44  // GPIO44
CS1_PIN   41  // GPIO41

EPD_WIDTH  1200
EPD_HEIGHT 1600

EPD_7IN3E_WHITE  0x0
EPD_7IN3E_GREEN  0x2
EPD_7IN3E_RED    0x6
EPD_7IN3E_YELLOW 0xB
EPD_7IN3E_BLUE   0xD
EPD_7IN3E_BLACK  0xF

epd7in3e.cpp: 6 lines (< 10)
No SendCommand/TurnOnDisplay/EPD_7IN3E_BusyHigh in .cpp
No Epd class in .h
EpdIf only appears in a comment (no class definition)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `epd7in3e/epd7in3e.cpp` — intentionally empty by design; display operations to be implemented in `epd7in3e.ino` using Seeed_GFX (`epaper.begin()`, `epaper.pushImage()`, `epaper.update()`). This stub is the stated goal of plan 01-01; the `.ino` rewrite is a later plan.

## Self-Check: PASSED

- `epd7in3e/epdif.h` — FOUND
- `epd7in3e/epd7in3e.h` — FOUND
- `epd7in3e/epd7in3e.cpp` — FOUND
- Commit `3bd6117` — FOUND
