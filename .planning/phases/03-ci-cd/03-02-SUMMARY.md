---
phase: 03-ci-cd
plan: 02
subsystem: infra
tags: [github-actions, ci, ruff, pyright, pytest, python]

# Dependency graph
requires:
  - phase: 03-01
    provides: ruff/pyright/pytest all green locally; requirements-dev.txt and pyproject.toml with tool config
provides:
  - ".github/workflows/ci.yml — three-job parallel PR quality gate"
affects: [branch-protection-setup, future PRs]

# Tech tracking
tech-stack:
  added: [github-actions, actions/checkout@v4, actions/setup-python@v5]
  patterns: [parallel-ci-jobs, pip-caching-via-setup-python, system-deps-for-native-libs]

key-files:
  created:
    - .github/workflows/ci.yml
  modified: []

key-decisions:
  - "lint job installs only ruff (not full requirements-dev.txt) — faster because rawpy/numpy not needed for linting"
  - "test job installs system libs libraw-dev + fonts-dejavu-core (verbatim from Dockerfile) for rawpy and date overlay font tests"
  - "cache: pip on setup-python keyed on both requirements.txt and requirements-dev.txt — covers all three jobs' install inputs"
  - "No needs: between jobs — all three run in parallel; branch protection (user-configured) enforces all-pass requirement"

patterns-established:
  - "Native-lib tests: apt-get install system deps before pip install in test job"
  - "Lean lint job: pin only the linter version, skip heavy runtime deps"

requirements-completed: [CI-02, CI-03]

# Metrics
duration: 5min
completed: 2026-05-28
---

# Phase 3 Plan 2: CI Workflow Summary

**GitHub Actions CI with three parallel jobs (lint/typecheck/test) gating PRs to main on Python 3.9 with pip caching**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-28T05:19:51Z
- **Completed:** 2026-05-28T05:24:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `.github/workflows/ci.yml` that triggers on every PR targeting `main`
- Three parallel jobs (no `needs:` dependency) satisfy CI-02 and CI-03
- `lint` job runs `ruff check .` + `ruff format --check .` with pinned `ruff==0.8.4`
- `typecheck` job installs full `requirements-dev.txt` so pyright resolves imports (basic mode from pyproject.toml)
- `test` job installs `libraw-dev` + `fonts-dejavu-core` system libraries matching Dockerfile, then runs `pytest tests/ -v`
- Pip download cache enabled on all three jobs via `cache: 'pip'` keyed on both requirements files

## Task Commits

1. **Task 1: Create .github/workflows/ci.yml** - `880e5e1` (feat)

**Plan metadata:** (to be added after docs commit)

## Files Created/Modified
- `.github/workflows/ci.yml` — GitHub Actions CI workflow: three parallel quality-gate jobs for PRs to main

## Decisions Made
- lint job installs only `ruff==0.8.4` rather than full dev deps — rawpy/numpy not needed for linting, keeps the job lean
- test job adds `libraw-dev` + `fonts-dejavu-core` system packages (taken verbatim from Dockerfile) because rawpy at import time and DejaVuSans-Bold.ttf at test fixture time both require them
- pip cache keyed on `requirements.txt` + `requirements-dev.txt` for all three jobs — covers every install input used across the workflow
- Jobs have no `needs:` declarations → GitHub runs them in parallel; branch protection rules (configured by user out-of-band) enforce the all-three-must-pass gate

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
Branch protection on `main` must be configured manually to require all three status checks (`Lint (ruff)`, `Typecheck (pyright)`, `Test (pytest)`) before merging. The workflow file itself is fully automated.

## Next Phase Readiness
- CI workflow is live: `.github/workflows/ci.yml` exists and will activate the moment the branch is merged to main and a PR is opened
- Plan 03-03 (final phase plan) can proceed; it does not depend on this file beyond its existence

---
*Phase: 03-ci-cd*
*Completed: 2026-05-28*
