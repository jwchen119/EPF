---
phase: 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display
plan: 01
subsystem: ui
tags: [pillow, pil, battery, overlay, image-processing, tdd]

requires:
  - phase: 02-date-overlay
    provides: draw_date_overlay() pattern and POSITIONS dict
  - phase: 04-battery-voltage
    provides: last_battery_voltage global and calculate_battery_percentage()

provides:
  - draw_battery_indicator(output_img, battery_pct, position_str, rotation, font_size, color) in app.py
  - BATTERY_LOW_THRESHOLD (20) and BATTERY_FLAT_THRESHOLD (5) constants in app.py
  - tests/test_battery_indicator.py with 10 contract tests covering all three battery states

affects:
  - 13-02 (wires draw_battery_indicator into pipeline, config, and settings UI)

tech-stack:
  added: []
  patterns:
    - "PIL viewer-space coordinate transformation for rotation-aware overlays (mirrors draw_date_overlay)"
    - "Warning-only icon pattern: no-op for healthy state, icon only for low/flat states"
    - "Three-state icon rendering: above threshold = no-op, low = partial fill, flat = empty outline"

key-files:
  created:
    - tests/test_battery_indicator.py
  modified:
    - app.py

key-decisions:
  - "POSITIONS lambda signature is (w, h, tw, th, p) — 5 params, not 7 as stated in plan context; CONTEXT.md ref was wrong; implementation uses actual signature"
  - "Test default color changed from white (255,255,255,255) to black (0,0,0,255) for detectability on white background — plan spec was internally inconsistent (count non-white pixels on white bg with white color = always 0)"
  - "icon_w = body_w + nub_w used for POSITIONS lookup (total footprint including nub)"
  - "padding=10 fixed inset (not overlay_margin_h/mv globals) as specified in CONTEXT Claude's Discretion"

patterns-established:
  - "draw_battery_indicator mirrors draw_date_overlay 5-step rotation technique exactly"
  - "Warning-only guard as first statement: if battery_pct > BATTERY_LOW_THRESHOLD: return"

requirements-completed: [BATIND-01, BATIND-02, BATIND-03]

duration: 3min
completed: 2026-06-28
---

# Phase 13 Plan 01: Battery Indicator Icon Summary

**PIL battery icon with three discrete warning states (no-op above 20%, partial fill 5-20%, empty outline at/below 5%) using rotation-aware viewer-space POSITIONS technique from draw_date_overlay**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-28T18:21:21Z
- **Completed:** 2026-06-28T18:24:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- TDD RED: 10 contract tests in tests/test_battery_indicator.py covering thresholds, signature, no-op, low/flat states, pixel-count comparison, and position sensitivity
- TDD GREEN: draw_battery_indicator() implemented with exact 5-step rotation-aware viewer-space technique mirroring draw_date_overlay()
- BATTERY_LOW_THRESHOLD=20 and BATTERY_FLAT_THRESHOLD=5 constants added above POSITIONS dict
- Full test suite passes with no regression (67/67 tests pass)

## Task Commits

1. **Task 1: Write failing contract tests (RED)** - `3da788a` (test)
2. **Task 2: Implement draw_battery_indicator + threshold constants (GREEN)** - `ddec05a` (feat)

## Files Created/Modified

- `tests/test_battery_indicator.py` - 10 contract tests for BATIND-01..03; covers no-op path, boundary conditions, partial fill vs empty outline pixel counts, position sensitivity
- `app.py` - Added BATTERY_LOW_THRESHOLD/BATTERY_FLAT_THRESHOLD constants + draw_battery_indicator() function after draw_date_overlay()

## Decisions Made

- Test default color changed from white to black: the plan spec said `color=(255,255,255,255)` but counting "non-white pixels" on a white canvas with white color is always zero. Black (0,0,0,255) makes the icon detectable. This is a Rule 1 (bug fix) auto-correction.
- POSITIONS lambda signature confirmed as 5-parameter `(w, h, tw, th, p)` — the plan's CONTEXT.md stated 7 params but actual code has 5. Implementation matches actual code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test default color corrected from white to black**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Plan specified `color=(255, 255, 255, 255)` (white) for tests that count non-white pixels on a white background. Drawing white on white produces no detectable change, making 7 of 10 tests fail even with a correct implementation.
- **Fix:** Changed `_DEFAULT_COLOR = (0, 0, 0, 255)` (black) in test module. No-op test still works correctly (pct=50 > 20, so black is never drawn).
- **Files modified:** tests/test_battery_indicator.py
- **Verification:** All 10 tests pass GREEN; no-op byte-identity test still passes
- **Committed in:** ddec05a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan spec)
**Impact on plan:** Required for correctness. Test logic was internally inconsistent in the plan spec.

## Issues Encountered

- pytest not available in the worktree Python environment — installed via pip3 (dev dependencies). Tests ran successfully after installing requirements-dev.txt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- draw_battery_indicator() and threshold constants are complete and tested
- Plan 13-02 can wire the function into scale_img_in_memory(), add config keys (battery_indicator_enabled, battery_indicator_position), and add the Settings UI card

---
*Phase: 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display*
*Completed: 2026-06-28*
