---
phase: "02"
plan: "01"
subsystem: testing
tags: [pytest, tdd, red-state, date-overlay]
dependency_graph:
  requires: []
  provides: [tests/test_date_overlay.py, tests/conftest.py, pytest-infrastructure]
  affects: [02-02, 02-03]
tech_stack:
  added: [pytest]
  patterns: [TDD RED state, fixture-based testing]
key_files:
  created:
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_date_overlay.py
  modified:
    - requirements.txt
decisions:
  - "Test contracts locked before implementation: parse_photo_date signature, draw_date_overlay signature, DEFAULT_CONFIG keys"
  - "dejavu_or_default_font fixture falls back to PIL default when DejaVuSans not available (macOS compatibility)"
metrics:
  duration: "92 seconds"
  completed: "2026-05-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 02 Plan 01: pytest Infrastructure + 9 Failing Test Stubs Summary

**One-liner:** pytest infrastructure with 9 RED-state test stubs locking DO-01..DO-05 contracts before implementation.

## What Was Built

Established the Wave 0 TDD foundation for Phase 2 (Date Overlay). Created pytest infrastructure and 9 failing test stubs that specify the exact contracts for functions Plans 02-02 and 02-03 will implement.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | pytest infrastructure (package marker, conftest, requirements) | 802e193 | tests/__init__.py, tests/conftest.py, requirements.txt |
| 2 | 9 failing test stubs covering DO-01 through DO-05 | 401076a | tests/test_date_overlay.py |

## Verification Results

- `pytest --collect-only tests/` exits 0, collects 0 errors
- `pytest tests/test_date_overlay.py --collect-only -q` reports exactly 9 tests collected
- `python -m py_compile tests/test_date_overlay.py` exits 0 (syntax valid)
- `pytest tests/test_date_overlay.py -x` FAILS with ImportError (RED state confirmed)
- `grep -c "^def test_" tests/test_date_overlay.py` returns 9

## Test Contract Summary

| Test | Requirement | Contract |
|------|-------------|---------|
| test_parse_exif_date | DO-01 | EXIF 'YYYY:MM:DD HH:MM:SS' -> 'DD.MM.YYYY' |
| test_parse_immich_date | DO-01 | ISO 8601 'YYYY-MM-DDTHH:MM:SS.sssZ' -> 'DD.MM.YYYY' |
| test_parse_none | DO-01 | None/empty/"not-a-date" -> None |
| test_draw_overlay_renders | DO-02 | Modifies pixels, black rect in bottom-right |
| test_overlay_disabled | DO-03 | date_overlay_enabled=False -> 0 black pixels |
| test_overlay_no_date | DO-03 | enabled=True but no date -> 0 black pixels |
| test_position_topleft | DO-04 | topLeft -> black in top-left, none in bottom-right |
| test_position_bottomright | DO-04 | bottomRight -> black in bottom-right, none in top-left |
| test_default_config | DO-05 | DEFAULT_CONFIG has enabled=False, position='bottomRight' |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - this plan intentionally creates failing tests (RED state). The stubs target functions/config that Plans 02-02 and 02-03 will implement.

## Self-Check: PASSED

- tests/__init__.py exists: FOUND
- tests/conftest.py exists: FOUND
- tests/test_date_overlay.py exists: FOUND
- Commit 802e193 (Task 1): FOUND
- Commit 401076a (Task 2): FOUND
