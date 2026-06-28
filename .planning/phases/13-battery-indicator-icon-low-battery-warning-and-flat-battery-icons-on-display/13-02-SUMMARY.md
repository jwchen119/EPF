---
phase: 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display
plan: 02
subsystem: ui
tags: [pil, battery, overlay, settings, config]

# Dependency graph
requires:
  - phase: 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display (plan 01)
    provides: draw_battery_indicator() function and BATTERY_LOW_THRESHOLD / BATTERY_FLAT_THRESHOLD constants

provides:
  - battery_indicator_enabled and battery_indicator_position config keys wired end-to-end
  - draw_battery_indicator() called from scale_img_in_memory() after date overlay
  - Battery Indicator card in settings.html (enable on/off + 9-position dropdown)

affects:
  - any future phase that adds overlay layers to scale_img_in_memory
  - settings UI layout (card order between Date Overlay and Power Management)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - select on/off toggle pattern (not checkbox) for enable flags — avoids HTML POST omission
    - .get() fallback in update_app_config() and POST handler for backward compat with old config.yaml
    - POSITIONS lambda called with mh=0, mv=0 when no margin needed (battery icon uses fixed padding)

key-files:
  created: []
  modified:
    - app.py
    - templates/settings.html

key-decisions:
  - "battery_indicator_enabled stored as raw string 'on'/'off' (not bool) — compared as string at call site (D-15)"
  - "POSITIONS lambda requires mh/mv args after phase 11; battery icon passes 0,0 since it uses fixed 10px padding (auto-fix)"
  - "last_battery_voltage > 0 guard is required — prevents false flat icon on USB/no-data devices (D-07)"
  - "Battery Indicator card is standalone — not merged into Date Overlay or Power Management cards (D-14)"

patterns-established:
  - "Config key pipeline: DEFAULT_CONFIG -> module global -> update_app_config global statement + .get() read -> POST handler .get() read"

requirements-completed: [BATIND-04, BATIND-05]

# Metrics
duration: 25min
completed: 2026-06-28
---

# Phase 13 Plan 02: Battery Indicator Wiring Summary

**battery_indicator_enabled/position config keys wired end-to-end through DEFAULT_CONFIG, globals, update_app_config, and POST handler; draw_battery_indicator() called from scale_img_in_memory() with white icon and last_battery_voltage guard; Battery Indicator settings card added between Date Overlay and Power Management**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-28T00:00:00Z
- **Completed:** 2026-06-28
- **Tasks:** 3 of 4 (Task 4 is a human-verify checkpoint)
- **Files modified:** 2

## Accomplishments

- Two new config keys (`battery_indicator_enabled`, `battery_indicator_position`) fully wired: DEFAULT_CONFIG → module globals → `update_app_config()` global declaration + `.get()` reads → settings POST handler reads
- `scale_img_in_memory()` now calls `draw_battery_indicator()` after the date overlay block, gated on enable flag and `last_battery_voltage > 0` guard, using white icon color
- New "Battery Indicator" settings card in `settings.html` between Date Overlay and Power Management cards, with Enable on/off select (default On) and 9-option Icon Position select (default Top Right)
- Fixed `draw_battery_indicator()` POSITIONS call to pass `mh=0, mv=0` (required after phase 11 added margin args to POSITIONS lambdas)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the two config keys through DEFAULT_CONFIG, globals, update_app_config, and POST handler** - `ede5654` (feat)
2. **Task 2: Call draw_battery_indicator from scale_img_in_memory after the date overlay** - `b461e67` (feat)
3. **Task 3: Add the Battery Indicator card to settings.html** - `d426c36` (feat)

## Files Created/Modified

- `app.py` - Added battery_indicator_enabled/position to DEFAULT_CONFIG, module globals, update_app_config global statement + .get() reads, POST handler; inserted draw_battery_indicator() call in scale_img_in_memory(); fixed POSITIONS call to pass mh=0, mv=0
- `templates/settings.html` - Added standalone Battery Indicator card with enable select and 9-option position dropdown

## Decisions Made

- `battery_indicator_enabled` stored as raw string `'on'`/`'off'` (not bool) per D-15 — avoids HTML POST omission and mirrors established select pattern
- POSITIONS lambdas now require 7 args (w, h, tw, th, p, mh, mv) since phase 11 added margin support; battery icon passes `0, 0` for mh/mv since it uses a fixed 10px inset
- Battery Indicator card is a standalone card (D-14), not merged into Date Overlay or Power Management

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed draw_battery_indicator() POSITIONS call missing mh/mv arguments**
- **Found during:** Task 1 verification (test run after initial Task 1 commit)
- **Issue:** `draw_battery_indicator()` was written in plan 13-01 before phase 11 extended POSITIONS lambdas to require `mh` and `mv` arguments. The call `get_xy(vw, vh, icon_w, icon_h, padding)` raised `TypeError: missing 2 required positional arguments: 'mh' and 'mv'`, causing 7 test failures.
- **Fix:** Changed call to `get_xy(vw, vh, icon_w, icon_h, padding, 0, 0)` — battery icon uses a fixed 10px inset, no passe-partout margin needed.
- **Files modified:** `app.py`
- **Verification:** 76 tests pass after fix (was 7 failures)
- **Committed in:** `ede5654` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug from POSITIONS signature change in phase 11)
**Impact on plan:** Essential correctness fix; no scope creep.

## Issues Encountered

None beyond the POSITIONS mh/mv argument mismatch documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Human verify checkpoint (Task 4) required: start app, confirm Battery Indicator card appears, test icon render at low/flat/healthy battery voltages, confirm persistence and backward compat
- After human approval, plan 13-02 is complete and phase 13 is done

---
*Phase: 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display*
*Completed: 2026-06-28*
