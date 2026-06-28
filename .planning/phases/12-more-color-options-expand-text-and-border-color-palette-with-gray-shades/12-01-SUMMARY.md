---
phase: 12-more-color-options-expand-text-and-border-color-palette-with-gray-shades
plan: 01
subsystem: ui
tags: [overlay, color, settings, jinja2, pytest]

# Dependency graph
requires:
  - phase: 06-text-customization-colors-styles-and-border-mode
    provides: OVERLAY_COLORS dict and three color dropdowns in settings.html
provides:
  - OVERLAY_COLORS extended with grey_100–grey_900 (9-step scale, 100=darkest to 900=lightest)
  - Nine gray options in each of the three color select dropdowns in settings UI
  - Updated TC-01/CLR-01 contract test asserting 15-key OVERLAY_COLORS set
affects: [any future phase using OVERLAY_COLORS or overlay color settings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Overlay-only colors: grays added only to OVERLAY_COLORS, never to the T133A01 palette list — keeps hardware quantization intact"
    - "Additive dict extension: OVERLAY_COLORS.get() call sites are transparent to new keys; no call-site changes needed"

key-files:
  created: []
  modified:
    - app.py
    - tests/test_overlay_customization.py
    - templates/settings.html

key-decisions:
  - "Gray entries (grey_100–grey_900) added to OVERLAY_COLORS only — NOT to the T133A01 palette list (D-06); on e-paper they nearest-neighbor to black or white as expected (D-02)"
  - "Dict insertion order: grey_100–grey_900 placed after white and before yellow; 100=darkest (25,25,25) to 900=lightest (230,230,230) per user convention"
  - "No POST handler or update_app_config changes needed — existing .get() lookups are key-transparent"

patterns-established:
  - "Overlay color additions require only OVERLAY_COLORS dict + test update + HTML dropdown options; the POST/config machinery is zero-change"

requirements-completed: [CLR-01, CLR-02, CLR-03, CLR-04]

# Metrics
duration: 15min
completed: 2026-06-28
---

# Phase 12 Plan 01: More Color Options Summary

**OVERLAY_COLORS extended to 15 entries with grey_100–grey_900 (9-step scale), and all three settings dropdowns updated with the full gray range between White and Yellow**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-28T19:30:00Z
- **Completed:** 2026-06-28T19:45:00Z
- **Tasks:** 3 (2 auto + 1 human-verify)
- **Files modified:** 3

## Accomplishments
- Added 9-step gray scale (`grey_100`–`grey_900`) to OVERLAY_COLORS in `app.py` (100=darkest at (25,25,25,255), 900=lightest at (230,230,230,255)), replacing the initial 3-shade prototype
- Updated `test_overlay_colors_dict` to assert the complete 15-key set with exact RGBA values (CLR-01, CLR-02)
- Added nine gray `<option>` entries to each of the three color dropdowns in `settings.html` (overlay_bg_color, overlay_text_color, overlay_border_color) positioned between White and Yellow with correct per-dropdown defaults (CLR-03)
- Full test suite passes with no regressions; human verification confirmed gray options appear, persist, and render without error (CLR-04)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add three gray entries to OVERLAY_COLORS and update the contract test** - `a23b7cc` (feat)
2. **Task 2: Add gray option entries to all three color dropdowns in settings.html** - `82e0aa6` (feat)
3. **Task 3: Human verify — grays render and persist** - human-approved

## Files Created/Modified
- `app.py` - OVERLAY_COLORS dict extended from 6 to 15 entries (grey_100–grey_900 replacing dark_gray/gray/light_gray)
- `tests/test_overlay_customization.py` - test_overlay_colors_dict updated to assert 15-key set with all 9 gray RGBA values
- `templates/settings.html` - Nine new `<option>` entries per dropdown (27 option tags total added across 3 dropdowns)

## Decisions Made
- Gray shades are overlay-only RGB values; they go into OVERLAY_COLORS only, never into the T133A01 palette list (which controls hardware nibble quantization). On physical e-paper they will nearest-neighbor to black or white — this is the expected D-02 behavior documented in the plan.
- After human verification of the initial 3-shade implementation, the range was expanded to a full 9-step numbered scale (grey_100–grey_900) per user request. Convention: 100=darkest (25,25,25), 900=lightest (230,230,230).
- No changes to POST handler or `update_app_config` — the existing `OVERLAY_COLORS.get(key, default)` call sites handle new keys transparently.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all verification steps passed first time.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Gray overlay colors are immediately available to users via the settings UI
- The OVERLAY_COLORS pattern is established: future color additions require only dict entry + test assertion + HTML option (zero call-site changes)
- Ready for Phase 13 (battery indicator icon work)

---
*Phase: 12-more-color-options-expand-text-and-border-color-palette-with-gray-shades*
*Completed: 2026-06-28*
