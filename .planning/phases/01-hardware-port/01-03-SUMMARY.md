---
phase: 01-hardware-port
plan: "03"
subsystem: server-image-pipeline
tags: [python, cython, palette, color-quantization, epaper, t133a01, seeed]

# Dependency graph
requires: []
provides:
  - Seeed T133A01 color primaries in app.py palette (kE6Rgb table values)
  - T133A01 nibble_map lookup in convert_to_c_code_in_memory()
  - 1200x1600 resolution defaults in scale_img_in_memory()
  - Matching normalized epd_colors in cpy.pyx for Floyd-Steinberg dithering
  - EPD_W=1200, EPD_H=1600 constants in cpy.pyx
affects: [cpy.pyx recompilation required, epd7in3e firmware nibble decoding]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit nibble_map array maps palette indices to T133A01 display codes"
    - "Palette order in app.py and epd_colors in cpy.pyx are kept in sync"

key-files:
  created: []
  modified:
    - app.py
    - cpy.pyx

key-decisions:
  - "Use Seeed kE6Rgb table values from dither.cpp rather than pure primaries — these are the actual T133A01 color targets"
  - "Explicit nibble_map [0xF, 0x0, 0xB, 0x6, 0xD, 0x2] replaces raw index packing — T133A01 codes are non-contiguous"
  - "Remove WaveShare-specific index shift (indices > 3 += 1) — T133A01 has no CLEAN/skip color code"
  - "Portrait-native resolution 1200x1600 set as defaults throughout pipeline"

patterns-established:
  - "nibble_map pattern: palette index → display nibble code via lookup table, not arithmetic"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-05-27
---

# Phase 01 Plan 03: Update Server Palette (T133A01 Colors), Nibble Map, and 1200x1600 Resolution Summary

**Replaced WaveShare color values and raw-index packing with Seeed T133A01 kE6Rgb primaries and an explicit nibble_map lookup, and updated both files to the 1200x1600 portrait resolution.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-27T15:59:42Z
- **Completed:** 2026-05-27T16:01:02Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

### Task 1: app.py — four targeted changes

1. **Palette replaced** (line ~82): WaveShare approximate values swapped for Seeed T133A01 kE6Rgb table:
   - Yellow: `(255, 243, 56)` → `(255, 216, 0)`
   - Red: `(191, 0, 0)` → `(229, 57, 53)`
   - Blue: `(100, 64, 255)` → `(0, 76, 255)`
   - Green: `(67, 138, 28)` → `(29, 185, 84)`

2. **Index shift removed** from `depalette_image()`: The line `indices[indices > 3] += 1` was a WaveShare-specific workaround for the CLEAN color at nibble 0x3. T133A01 has no such gap — removed.

3. **`convert_to_c_code_in_memory()` rewritten** with nibble_map:
   - `nibble_map = [0xF, 0x0, 0xB, 0x6, 0xD, 0x2]` maps palette index 0–5 to T133A01 codes
   - Previously packed raw indices directly (`indices[y, x] << 4`) — wrong for T133A01 since codes are non-contiguous

4. **`scale_img_in_memory()` defaults updated**: `target_width=800, target_height=480` → `target_width=1200, target_height=1600`. Inner palette also updated to Seeed values.

### Task 2: cpy.pyx — two targeted changes

1. **Constants updated**: `EPD_W = 800` → `EPD_W = 1200`, `EPD_H = 480` → `EPD_H = 1600`

2. **`epd_colors` array updated** with normalized Seeed T133A01 primaries:
   - Yellow: `[1, 1, 0]` → `[1.0, 0.847, 0.0]`
   - Red: `[1, 0, 0]` → `[0.898, 0.224, 0.208]`
   - Blue: `[0, 0, 1]` → `[0.0, 0.298, 1.0]`
   - Green: `[0, 1, 0]` → `[0.114, 0.725, 0.329]`

## Verification Results

```
app.py: PASS
cpy.pyx: PASS
```

Checks confirmed:
- `255, 216, 0` present (Seeed yellow)
- `nibble_map` present
- `indices > 3` NOT present (WaveShare shift removed)
- `EPD_W = 1200` present
- `EPD_H = 1600` present
- `0.847` present (normalized yellow in epd_colors)

## IMPORTANT: cpy.pyx Recompilation Required

The `cpy.pyx` changes (EPD_W, EPD_H, epd_colors) will NOT take effect until the Cython extension is recompiled:

```bash
python setup.py build_ext --inplace
```

This must be run in the server environment before the updated dithering pipeline is active.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- Commit d513aea verified: `git log --oneline -1` → `d513aea feat(01-03): update server palette to T133A01 Seeed colors and 1200x1600 resolution`
- `/Users/lennart/Dev/privat/EPF/app.py` modified
- `/Users/lennart/Dev/privat/EPF/cpy.pyx` modified
