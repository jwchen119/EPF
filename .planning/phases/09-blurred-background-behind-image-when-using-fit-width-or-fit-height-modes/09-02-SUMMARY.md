---
phase: 09-blurred-background-behind-image-when-using-fit-width-or-fit-height-modes
plan: "02"
subsystem: image-processing
tags: [pillow, tdd, gaussian-blur, fit-mode, image-compositing, config]

# Dependency graph
requires:
  - phase: 09-blurred-background-behind-image-when-using-fit-width-or-fit-height-modes/09-01
    provides: Contract tests BG-01 through BG-06 (tests/test_blur_background.py)
  - phase: 02-date-overlay
    provides: cpy_fallback.load_scaled signature (image, angle, display_mode)
provides:
  - load_scaled() with GaussianBlur fill background in fit mode (cpy_fallback.py)
  - blur_radius config key flowing from DEFAULT_CONFIG through update_app_config into load_scaled
affects:
  - 09-03 (settings UI — expose blur_radius slider to user)

# Tech tracking
tech-stack:
  added:
    - PIL.ImageFilter (already in Pillow 11.0.0 — first use in this project)
  patterns:
    - Fill-scale + center-crop + GaussianBlur for letterbox/pillarbox background replacement
    - blur_radius kwarg with default=30, clamped to 1..100 via max(1, min(100, int(blur_radius)))
    - Module-level global initialization from DEFAULT_CONFIG (mirrors all other overlay globals)

key-files:
  created: []
  modified:
    - cpy_fallback.py
    - app.py
    - tests/test_blur_background.py

key-decisions:
  - "blur_radius module-level global required — scale_img_in_memory reads globals directly, no parameter passing to function"
  - "BG-06 test fixed to use gradient image — uniform solid-color images produce identical blur output regardless of radius (GaussianBlur of constant field is constant)"
  - "fill branch left completely unchanged — only the else (fit) branch receives blur-fill background"
  - "max(bg_width, EPD_W) and max(bg_height, EPD_H) guards prevent undersize background causing edge artifacts"

patterns-established:
  - "Blur background: fill-scale → center-crop → GaussianBlur → paste sharp fit image on top"

requirements-completed:
  - BG-01
  - BG-02
  - BG-03
  - BG-04
  - BG-05
  - BG-06

# Metrics
duration: 8min
completed: 2026-06-07
---

# Phase 09 Plan 02: Blurred Background — TDD GREEN Implementation Summary

**GaussianBlur fill background in load_scaled() fit branch using Pillow ImageFilter, wired through blur_radius config key in DEFAULT_CONFIG, update_app_config, and scale_img_in_memory**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-07T13:06:00Z
- **Completed:** 2026-06-07T13:14:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced plain white canvas in load_scaled() fit branch with fill-scale → center-crop → GaussianBlur background
- Added blur_radius=30 kwarg to load_scaled() with 1..100 clamping
- Wired blur_radius through DEFAULT_CONFIG, module-level global, update_app_config, scale_img_in_memory, and POST handler
- All 7 BG contract tests GREEN; full suite 57/57 passes

## Task Commits

1. **Task 1: Implement blur-fill background in cpy_fallback.py load_scaled()** - `a4db9e3` (feat)
2. **Task 2: Wire blur_radius config key through app.py** - `01002ab` (feat)

## Files Created/Modified

- `cpy_fallback.py` — load_scaled() signature adds blur_radius=30, fit branch replaced with blur-fill implementation using ImageFilter.GaussianBlur
- `app.py` — blur_radius added to DEFAULT_CONFIG, module-level global init, update_app_config global statement and body, scale_img_in_memory call site, POST handler new_config dict
- `tests/test_blur_background.py` — BG-06 test_blur_radius_config fixed to use gradient image helper

## Decisions Made

- `blur_radius` initialized at module level from DEFAULT_CONFIG (line 325) — required because `scale_img_in_memory` reads module globals directly and tests may not call `update_app_config` before calling `scale_img_in_memory`
- BG-06 test required a gradient image rather than a uniform solid-color image — GaussianBlur of a constant-value image produces the same constant value regardless of radius; only non-uniform images show radius-dependent differences
- fill branch is untouched — the plan and tests (BG-03) both require fill mode behavior to be completely unchanged

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_blur_radius_config to use gradient image**
- **Found during:** Task 1 (GREEN verification)
- **Issue:** BG-06 test used `make_colored_image(1000, 600, color=(200, 100, 50))` — a solid uniform color. GaussianBlur of a uniform image returns the same uniform image regardless of radius, making `pixel_low != pixel_high` impossible to satisfy
- **Fix:** Added `make_gradient_image(1000, 600)` helper inside test file that creates a pixel-varying gradient image; BG-06 now uses this to produce observable differences between blur_radius=5 and blur_radius=60
- **Files modified:** tests/test_blur_background.py
- **Verification:** All 7 BG tests pass; pixel_low != pixel_high holds for gradient image
- **Committed in:** a4db9e3 (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added module-level blur_radius global initialization**
- **Found during:** Task 2 (full suite regression)
- **Issue:** After adding blur_radius kwarg to load_scaled() call in scale_img_in_memory(), tests that call scale_img_in_memory() without first calling update_app_config() fail with NameError: name 'blur_radius' is not defined
- **Fix:** Added `blur_radius = DEFAULT_CONFIG['immich']['blur_radius']` at line 325 alongside all other module-level globals
- **Files modified:** app.py
- **Verification:** Full suite 57/57 passes after fix
- **Committed in:** 01002ab (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 test bug, 1 missing module-level init)
**Impact on plan:** Both fixes required for correctness. No scope creep.

## Issues Encountered

The test_blur_background.py file existed in the parent `feature/image-fit-modes` branch but not in this worktree branch. Cherry-picked commit `adaf1ce` to bring the test file in.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 can add the blur_radius settings UI slider (config key and wiring are complete)
- cpy.pyx (Cython production fast path) still needs the same load_scaled() changes mirrored for Docker production builds — this is noted in RESEARCH.md Pitfall 3 and should be part of Plan 03 or a follow-up

---
*Phase: 09-blurred-background-behind-image-when-using-fit-width-or-fit-height-modes*
*Completed: 2026-06-07*
