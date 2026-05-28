---
phase: 02-date-overlay
plan: "02"
subsystem: image-processing
tags: [pillow, python, date-parsing, image-overlay, tdd]

# Dependency graph
requires:
  - phase: 02-01
    provides: "pytest infrastructure, conftest fixtures, 9 failing test stubs"
provides:
  - "parse_photo_date() module-level function in app.py (EXIF + ISO 8601 -> DD.MM.YYYY)"
  - "POSITIONS dict with 9 anchor lambdas for overlay positioning"
  - "draw_date_overlay() module-level function that mutates PIL Image in-place"
affects:
  - "02-03: wire overlay into pipeline from scale_img_in_memory"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level pure helper functions testable via direct import from app"
    - "textbbox() offset compensation for Pillow >= 9.2 default font quirk"
    - "POSITIONS dict of lambdas for positional coordinate calculation"

key-files:
  created: []
  modified:
    - "app.py"

key-decisions:
  - "Inserted parse_photo_date() and POSITIONS/draw_date_overlay() between DEFAULT_CONFIG and current_config = DEFAULT_CONFIG.copy() to keep all module-level helpers co-located"
  - "bbox offset compensation (x - bbox[0], y - bbox[1]) applied on draw.text() call to handle Pillow >= 9.2 font rendering quirks"
  - "Unknown position_str falls back to POSITIONS['bottomRight'] via .get() default"

patterns-established:
  - "parse_photo_date pattern: check char at index 4 to distinguish EXIF ':' from ISO '-' separator"
  - "draw_date_overlay pattern: textbbox -> POSITIONS lambda -> rectangle -> text with bbox offset compensation"

requirements-completed:
  - DO-01
  - DO-02
  - DO-04

# Metrics
duration: 15min
completed: 2026-05-27
---

# Phase 02 Plan 02: parse_photo_date() and draw_date_overlay() helpers Summary

**Pure date-parsing and PIL image overlay helpers added at module level in app.py, making 6 of 9 TDD tests GREEN with EXIF/ISO 8601 support and 9-position anchor system**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-27T20:00:00Z
- **Completed:** 2026-05-27T20:15:00Z
- **Tasks:** 2
- **Files modified:** 1 (app.py)

## Accomplishments
- `parse_photo_date()` handles EXIF format (`YYYY:MM:DD HH:MM:SS`) and ISO 8601 (`YYYY-MM-DD...`) returning `DD.MM.YYYY`, or None for unparseable input
- `POSITIONS` dict maps 9 string keys to coordinate-computing lambdas (topLeft, topCenter, topRight, centerLeft, center, centerRight, bottomLeft, bottomCenter, bottomRight)
- `draw_date_overlay()` mutates PIL Image in-place: draws black background rectangle then white text, with bbox offset compensation for Pillow >= 9.2
- 6 of 9 Wave 0 tests GREEN; remaining 3 correctly blocked on Plan 03 wiring

## Task Commits

Each task was committed atomically:

1. **Task 1: Add parse_photo_date()** - `4e3b457` (feat)
2. **Task 2: Add POSITIONS dict and draw_date_overlay()** - `ba009fc` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `/Users/lennart/Dev/privat/EPF/app.py` - Added parse_photo_date(), POSITIONS, draw_date_overlay() at lines 48-113

## Decisions Made
- Inserted new functions between `DEFAULT_CONFIG = {...}` block and `current_config = DEFAULT_CONFIG.copy()` for logical grouping of module-level helpers
- Used `draw.textbbox((0, 0), text, font=font)` and compensated with `(x - bbox[0], y - bbox[1])` on `draw.text()` to handle Pillow's non-zero bbox origin for default fonts
- Unknown `position_str` falls back to `POSITIONS["bottomRight"]` via `.get()` default (per RESEARCH.md pattern)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] test_date_overlay.py already existed from a partial Plan 01 execution**
- **Found during:** Pre-execution dependency check
- **Issue:** Plan 01 had created tests/__init__.py and conftest.py but test_date_overlay.py was also found to already exist with all 9 tests. No recreation was needed.
- **Fix:** Verified test file content matched plan spec exactly; proceeded without modification
- **Files modified:** None (no change needed)
- **Verification:** pytest --collect-only tests/ showed 9 tests collected
- **Committed in:** N/A (no change)

---

**Total deviations:** 1 observed (no code change required)
**Impact on plan:** No scope creep. Pre-existing test file matched plan spec exactly.

## Issues Encountered
- `flask` and other dependencies not installed in the test environment initially; installed via pip to reach proper RED state before implementing GREEN
- `cpy.so` binary is invalid for the current macOS architecture (falls back to `cpy_fallback.py` automatically — expected behavior, no impact on tests)

## Known Stubs
None — all implemented functions are fully wired. Remaining 3 failing tests (test_overlay_disabled, test_overlay_no_date, test_default_config) require Plan 03's pipeline wiring, which is the planned next step.

## Next Phase Readiness
- Plan 03 can call `parse_photo_date()` and `draw_date_overlay()` from `scale_img_in_memory()` with no ambiguity
- `POSITIONS` dict is ready for use with the config-driven `date_overlay_position` key that Plan 03 will add to DEFAULT_CONFIG
- 3 remaining tests define the exact interface contracts Plan 03 must satisfy

---
*Phase: 02-date-overlay*
*Completed: 2026-05-27*
