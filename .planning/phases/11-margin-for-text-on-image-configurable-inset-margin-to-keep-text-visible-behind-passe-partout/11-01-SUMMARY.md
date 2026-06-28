---
phase: 11-margin-for-text-on-image-configurable-inset-margin-to-keep-text-visible-behind-passe-partout
plan: 01
subsystem: ui
tags: [pillow, overlay, positioning, tdd]

# Dependency graph
requires:
  - phase: 06-text-customization-colors-styles-and-border-mode
    provides: draw_date_overlay() with style/color params, POSITIONS dict, OVERLAY_COLORS
provides:
  - POSITIONS lambdas accepting (w, h, tw, th, p, mh, mv) with margin-aware x/y math
  - draw_date_overlay() with margin_h=0 and margin_v=0 keyword params
  - Contract tests for margin math (MARGIN-01, MARGIN-02) in test_overlay_margin.py
affects: [11-02-plan, scale_img_in_memory call site, settings UI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - POSITIONS lambda extended to 7 args (w, h, tw, th, p, mh, mv) — center ignores both margins; axis-center uses one axis
    - margin_h/margin_v default to 0 for full backward compatibility with all existing callers

key-files:
  created:
    - tests/test_overlay_margin.py
  modified:
    - app.py

key-decisions:
  - "POSITIONS lambdas accept (w, h, tw, th, p, mh, mv); center ignores both; axis-center positions use single relevant axis only"
  - "margin_h=0 and margin_v=0 default to zero so all existing draw_date_overlay() callers are unaffected"
  - "Margins are additive to padding p, not a replacement; p remains text-box breathing room, mh/mv are display-edge insets"

patterns-established:
  - "Lambda signature: lambda w, h, tw, th, p, mh, mv — pass 0 for backward compat"
  - "get_xy(vw, vh, tw, th, padding, margin_h, margin_v) call pattern for future call sites"

requirements-completed: [MARGIN-01, MARGIN-02]

# Metrics
duration: 2min
completed: 2026-06-28
---

# Phase 11 Plan 01: Margin-aware POSITIONS lambdas + draw_date_overlay margin params (TDD)

**9 POSITIONS lambdas extended to accept margin_h/margin_v args, draw_date_overlay gains margin_h=0 and margin_v=0 defaults with zero-margin backward compat verified by 5 contract tests**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-06-28T12:21:49Z
- **Completed:** 2026-06-28T12:23:38Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Wrote 5 contract tests (MARGIN-01, MARGIN-02) that initially failed RED (lambdas took 5 args, signature lacked margin params)
- Extended all 9 POSITIONS lambdas from `(w, h, tw, th, p)` to `(w, h, tw, th, p, mh, mv)` with correct per-position margin semantics
- Added `margin_h=0, margin_v=0` keyword params to `draw_date_overlay()` and threaded them into the POSITIONS call
- All 27 tests pass (5 new margin tests + 22 existing date/customization tests — zero regression)

## Task Commits

1. **Task 1: RED — write failing contract tests** - `e69863b` (test)
2. **Task 2: GREEN — extend lambdas and draw_date_overlay** - `455328c` (feat)

## Files Created/Modified
- `tests/test_overlay_margin.py` - 5 contract tests for margin math (MARGIN-01, MARGIN-02) and backward compat
- `app.py` - POSITIONS lambdas updated to 7-arg signature; draw_date_overlay extended with margin_h/margin_v

## Decisions Made
- center position ignores both mh and mv (geometric center unchanged) — implemented as lambda ignoring mh and mv entirely
- topCenter/bottomCenter apply only mv; centerLeft/centerRight apply only mh — axis-center positions use single axis
- Margins are additive to padding p (p remains text-box breathing room, margins are display-edge insets)
- Default margin_h=0 and margin_v=0 preserves exact pixel output for all existing callers (MARGIN-02 backward compat)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- POSITIONS contract and draw_date_overlay signature ready for Plan 11-02 to wire overlay_margin_h/overlay_margin_v config globals
- Call site in scale_img_in_memory() (app.py ~line 585) needs margin_h=overlay_margin_h, margin_v=overlay_margin_v kwargs added (Plan 11-02 task)
- DEFAULT_CONFIG, update_app_config(), POST handler, and settings.html sliders all ready to be added in Plan 11-02

---
*Phase: 11-margin-for-text-on-image-configurable-inset-margin-to-keep-text-visible-behind-passe-partout*
*Completed: 2026-06-28*
