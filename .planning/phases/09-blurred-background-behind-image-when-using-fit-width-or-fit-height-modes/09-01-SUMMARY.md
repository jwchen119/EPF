---
phase: 09-blurred-background-behind-image-when-using-fit-width-or-fit-height-modes
plan: "01"
subsystem: testing
tags: [pillow, tdd, image-processing, fit-mode, blur]

# Dependency graph
requires:
  - phase: 02-date-overlay
    provides: cpy_fallback.load_scaled signature (image, angle, display_mode)
provides:
  - Contract tests BG-01 through BG-06 for blurred background feature (tests/test_blur_background.py)
affects:
  - 09-02 (implementation plan must make all 4 failing tests pass)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED: Write failing tests before implementing blurred background in load_scaled()"

key-files:
  created:
    - tests/test_blur_background.py
  modified: []

key-decisions:
  - "BG-02 test samples pixel at (0,0) — left pillarbox bar for fit-width sub-case (600x1000 portrait)"
  - "BG-04 samples (0, 800) — middle of left bar for portrait fit-width"
  - "BG-05 samples (600, 0) — middle column of top bar for landscape fit-height"
  - "BG-06 tests TypeError path for blur_radius kwarg before implementation"
  - "3 regression tests (BG-01a, BG-01b, BG-03) pass today to guard existing dimensions and fill mode"

patterns-established:
  - "Test helper make_colored_image(width, height, color) creates solid-color RGB PIL Images without fixtures"

requirements-completed:
  - BG-01
  - BG-02
  - BG-03
  - BG-04
  - BG-05
  - BG-06

# Metrics
duration: 1min
completed: 2026-06-07
---

# Phase 09 Plan 01: Blurred Background — TDD RED Contract Tests Summary

**7 pytest contract tests locking BG-01 through BG-06 behavioral contracts for fit-mode blurred background (3 pass, 4 fail — RED confirmed)**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-06-07T13:06:53Z
- **Completed:** 2026-06-07T13:07:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/test_blur_background.py with 7 test functions covering BG-01 through BG-06
- Confirmed RED phase: 3 regression tests pass (dimensions + fill mode guard), 4 blur-behavior tests fail as expected
- BG-06 fails with TypeError confirming blur_radius kwarg does not yet exist on load_scaled()

## Task Commits

1. **Task 1: Write failing contract tests for blurred background (BG-01 through BG-06)** - `adaf1ce` (test)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `tests/test_blur_background.py` - 7 contract tests (BG-01a, BG-01b, BG-02, BG-03, BG-04, BG-05, BG-06) for blurred background in fit mode

## Decisions Made

- BG-02 checks pixel at (0,0) — the left bar of a 600x1000 portrait image in fit-width sub-case
- BG-04 checks pixel at (0, 800) — middle row of left pillarbox bar (same 600x1000 portrait)
- BG-05 checks pixel at (600, 0) — middle column of top letterbox bar (1000x600 landscape)
- BG-06 simply calls load_scaled with blur_radius=5 and blur_radius=60; before implementation this raises TypeError which constitutes the FAIL

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (implementation) must make all 4 failing tests pass by adding blurred fill background to `load_scaled()` fit branch and accepting a `blur_radius` keyword argument
- Regression tests BG-01a, BG-01b, BG-03 must continue to pass after Plan 02 changes

---
*Phase: 09-blurred-background-behind-image-when-using-fit-width-or-fit-height-modes*
*Completed: 2026-06-07*
