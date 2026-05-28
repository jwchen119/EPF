---
phase: 03-ci-cd
plan: "01"
subsystem: tooling
tags: [ruff, pyright, linting, type-checking, dev-dependencies]
dependency_graph:
  requires: []
  provides: [pyproject.toml-ruff-config, pyproject.toml-pyright-config, requirements-dev.txt]
  affects: [app.py, cpy_fallback.py, tests/test_date_overlay.py]
tech_stack:
  added: [ruff==0.8.4, pyright==1.1.391]
  patterns: [isort import grouping, ruff format single-quotes, pyright basic mode]
key_files:
  created: [pyproject.toml, requirements-dev.txt]
  modified: [app.py, cpy_fallback.py, tests/test_date_overlay.py]
decisions:
  - N816 noqa on rotationAngle global (rename would touch 7 call-sites with no behavior gain)
  - .claude added to ruff extend-exclude to prevent scanning git worktrees
  - pyright required 0 code changes — basic mode passed without annotation additions
metrics:
  duration: ~18min
  completed: "2026-05-28T05:17:36Z"
  tasks_completed: 3
  files_changed: 5
---

# Phase 3 Plan 1: CI Prerequisite — Ruff + Pyright Setup Summary

Dev tooling baseline established: ruff 0.8.4 and pyright 1.1.391 configured in pyproject.toml, all lint/format/type errors resolved in the Python codebase before CI workflows land.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add dev dependencies and pyproject.toml config | 2a597c4 | pyproject.toml, requirements-dev.txt |
| 2 | Fix all ruff lint + format errors | c5f6e73 | app.py, cpy_fallback.py, pyproject.toml |
| 3 | Verify pyright (basic mode) type errors | 97c9866 | tests/test_date_overlay.py |

## Verification Results

All six plan verification steps pass:

1. `ruff check .` — exit 0
2. `ruff format --check .` — exit 0
3. `pyright` — 0 errors, 13 warnings (all `reportMissingImports` at warning level — expected; third-party stubs not installed in dev env)
4. `pytest tests/ -x` — 13/13 passed
5. `requirements.txt | grep ^(ruff|pyright)` — empty (dev tools NOT in production image)
6. `requirements-dev.txt | grep ^(ruff|pyright)` — 2 matches

## Ruff Configuration

Rules selected (per D-04): `E` (pycodestyle errors), `W` (warnings), `F` (pyflakes), `I` (isort), `N` (pep8-naming).

`E501` ignored globally — line length enforced by `ruff format` (120 chars) rather than per-line linting.

Excluded: `cpy.pyx`, `cpy.c`, `tests/conftest.py`, `.claude` (git worktrees).

## Pyright Configuration

Mode: `basic` (D-01) — no exhaustive type annotation coverage required.

Python version: `3.9` (matches Dockerfile runtime, D-07).

Include: `app.py`, `cpy_fallback.py` only.

`reportMissingImports = "warning"` — third-party libraries without stubs (Flask, PIL, rawpy, etc.) produce warnings only, not errors.

## Fix Categories Applied

### Task 2 (ruff fixes)

| Category | Rule | Count | Action |
|----------|------|-------|--------|
| Import sorting | I001 | 2 blocks | Auto-fixed by `ruff check --fix` |
| Blank line whitespace | W293 | ~30 occurrences | Auto-fixed |
| Trailing whitespace | W291 | ~8 occurrences | Auto-fixed |
| Mixed-case global | N816 | 1 | `# noqa: N816` on `rotationAngle` line |
| Format (quotes, spacing) | — | 3 files | `ruff format .` |

### Task 3 (pyright)

No code changes required. Pyright basic mode found 0 errors on initial run. All 13 diagnostics are `reportMissingImports` warnings (third-party libraries without type stubs) — these are expected and configured to warn-only.

## Per-Line Suppressions Added

| File | Line | Suppression | Justification |
|------|------|-------------|---------------|
| app.py | 156 | `# noqa: N816` | `rotationAngle` is a long-standing global used in 7 places; rename would be pure churn with no behavior change |

No file-level `# ruff: noqa` or `# pyright: ignore` directives added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing config] Added `.claude` to ruff extend-exclude**
- **Found during:** Task 2
- **Issue:** ruff was scanning `.claude/worktrees/` (git worktrees used by the GSD executor), producing duplicate errors from the worktree copy of app.py
- **Fix:** Added `.claude` to `extend-exclude` in pyproject.toml
- **Files modified:** pyproject.toml
- **Commit:** c5f6e73

## Known Stubs

None — no placeholder data, TODO comments, or hardcoded empty values in created/modified files.

## Self-Check: PASSED

- pyproject.toml: FOUND
- requirements-dev.txt: FOUND
- 03-01-SUMMARY.md: FOUND
- Commit 2a597c4 (task 1): FOUND
- Commit c5f6e73 (task 2): FOUND
- Commit 97c9866 (task 3): FOUND
