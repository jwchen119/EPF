---
phase: 03-ci-cd
plan: "03"
subsystem: infra
tags: [github-actions, docker, ghcr, semver, workflow_dispatch, releases]

# Dependency graph
requires:
  - phase: 03-01
    provides: clean codebase (ruff/pyright green) that CI/CD can build
provides:
  - manual deploy workflow with semver validation, ghcr.io push, and GitHub Release creation
affects: [future deploy runs, container registry, release management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - workflow_dispatch with validated version input for controlled deploys
    - atomic version + latest tag push in single docker/build-push-action step
    - bash lowercase substitution for ghcr.io image name (${GITHUB_REPOSITORY,,})

key-files:
  created:
    - .github/workflows/deploy.yml
  modified: []

key-decisions:
  - "Version input validated via bash regex ^[0-9]+\\.[0-9]+\\.[0-9]+$ before any action (reject v1.0, reject 1.0, reject 1.0.0-rc1)"
  - "Tag-already-exists guard runs before Docker build to fail fast on duplicate versions"
  - "Both version and latest tags pushed atomically in single build-push-action step (D-10)"
  - "fetch-depth: 0 required so generate_release_notes can diff against previous tag (D-11)"
  - "Image name lowercased via ${GITHUB_REPOSITORY,,} — ghcr.io rejects uppercase owner/repo"

patterns-established:
  - "GitHub Container Registry auth: docker/login-action@v3 with GITHUB_TOKEN (no extra secrets)"
  - "GitHub Release auto-notes: softprops/action-gh-release@v2 with generate_release_notes: true"
  - "Explicit permissions block: contents: write + packages: write (default repo perms may be read-only)"

requirements-completed: [CI-04, CI-05]

# Metrics
duration: 5min
completed: 2026-05-28
---

# Phase 03 Plan 03: Deploy Workflow Summary

**Manual GitHub Actions deploy workflow: semver-validated version input, atomic ghcr.io push of `{version}` + `latest`, git tag creation, and auto-generated GitHub Release using GITHUB_TOKEN only**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-28T05:30:00Z
- **Completed:** 2026-05-28T05:35:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `.github/workflows/deploy.yml` with `workflow_dispatch` trigger only (no automatic push trigger)
- Semver validation via bash regex rejects `v1.0`, `1.0`, `1.0.0-rc1` — accepts `MAJOR.MINOR.PATCH` numeric only
- Image pushed atomically with both versioned tag and `latest` in single `docker/build-push-action@v5` step
- Tag-already-exists guard prevents accidental re-release of same version
- GitHub Release auto-generated with commits since previous tag (`generate_release_notes: true`, `fetch-depth: 0`)

## Task Commits

1. **Task 1: Create deploy.yml — manual semver build + ghcr push + release** - `a34c35b` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.github/workflows/deploy.yml` — Manual deploy workflow: workflow_dispatch, semver validate, git tag, docker build+push to ghcr.io, GitHub Release

## Decisions Made

- Version input validated before checkout to fail fast without cloning the full repo
- `${GITHUB_REPOSITORY,,}` bash lowercase substitution for ghcr.io image name (uppercase rejected by registry)
- `fetch-depth: 0` ensures full git history for release notes comparison against previous tag
- Duplicate tag guard (`git rev-parse "$TAG" >/dev/null 2>&1`) prevents silent overwrites

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions.

## Next Phase Readiness

Phase 03 (CI/CD) is now complete:
- 03-01: Ruff + pyright config, codebase linting/type-check green
- 03-02: PR workflow (lint + typecheck + test jobs on pull_request → main)
- 03-03: Deploy workflow (manual semver deploy + ghcr push + GitHub Release)

All three plans satisfy the CI/CD requirements. The project is ready for production deploys via `workflow_dispatch`.

---
*Phase: 03-ci-cd*
*Completed: 2026-05-28*
