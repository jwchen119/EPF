---
phase: 06-text-customization-colors-styles-and-border-mode
plan: 01
subsystem: testing/tdd
tags: [tdd, red, overlay, customization, contracts]
dependency_graph:
  requires: []
  provides: [TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09]
  affects: [app.py, tests/test_overlay_customization.py]
tech_stack:
  added: []
  patterns: [TDD-RED, import-inside-test, fixture-args]
key_files:
  created:
    - tests/test_overlay_customization.py
  modified: []
decisions:
  - TC-06 (test_default_params_match_current) passes in RED state because draw_date_overlay already accepts positional args without new kwargs — this is intentional; the test validates backward compatibility and must remain green after Plans 02/03 land
  - import-inside-test pattern followed exactly as in test_date_overlay.py (conftest fixtures reused, not redefined)
metrics:
  duration: ~5 minutes
  completed: "2026-05-29"
  tasks_completed: 2
  files_changed: 1
requirements: [TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09]
---

# Phase 6 Plan 01: TDD RED — Overlay Customization Contract Tests Summary

**One-liner:** 9 failing TDD contract tests locking OVERLAY_COLORS dict, extended draw_date_overlay() signature, background/outline rendering modes, and 6 new DEFAULT_CONFIG keys.

## What Was Built

Created `tests/test_overlay_customization.py` with 9 test functions (TC-01..TC-09) that define the full contract for Phase 6 text customization. These tests are intentionally RED until Plans 06-02 and 06-03 implement the production code.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing contract tests for OVERLAY_COLORS and draw_date_overlay() modes | 388465c | tests/test_overlay_customization.py |
| 2 | Add failing config-contract tests (TC-02, TC-08, TC-09) | 3e9aa5f | tests/test_overlay_customization.py |

## Test Contracts Locked

| Test | ID | Contract |
|------|----|----------|
| test_overlay_colors_dict | TC-01 | OVERLAY_COLORS has 6 keys with exact RGBA tuples mirroring palette |
| test_default_config_new_keys | TC-02 | DEFAULT_CONFIG has overlay_style/bg_color/text_color/border_color/stroke_width/font_size |
| test_background_mode_uses_bg_color | TC-03 | style='background' fills rect with bg_color |
| test_outline_mode_no_rect | TC-04 | style='outline' paints far fewer fill pixels than background |
| test_outline_mode_border_color | TC-05 | style='outline' uses border_color for stroke |
| test_default_params_match_current | TC-06 | Default kwargs preserve black rect + white text (backward compat) |
| test_stroke_width_zero | TC-07 | stroke_width=0 produces no border_color pixels distinct from text |
| test_update_config_new_keys | TC-08 | update_app_config sets overlay globals with .get() fallback for legacy configs |
| test_post_handler_font_size_int | TC-09 | overlay_font_size and overlay_stroke_width stored as ints |

## Verification Results

- `pytest tests/test_overlay_customization.py`: 8 failed, 1 passed (TC-06 passes — correct per design)
- `pytest tests/test_date_overlay.py`: 13 passed — no Phase 2 regression

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- TC-06 (`test_default_params_match_current`) passes in RED state because the existing `draw_date_overlay` function already works when called without the new kwargs. This is the intended behavior — the test verifies backward compatibility and will remain green after Plans 02/03 add the new parameters with matching defaults.
- The plan specified 9 tests but acceptance criteria said 6 for Task 1 and 3 for Task 2. Followed the two-commit task structure: 6 tests in commit 388465c, 3 more in commit 3e9aa5f.

## Self-Check: PASSED

- tests/test_overlay_customization.py: FOUND
- Commit 388465c: FOUND
- Commit 3e9aa5f: FOUND
- 9 test functions: CONFIRMED (grep -c "def test_" = 9)
- 8 failing RED tests: CONFIRMED
- Phase 2 regression: NONE (13 passed)
