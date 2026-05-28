---
phase: 03-ci-cd
verified: 2026-05-28T07:00:00Z
status: passed
score: 15/15 must-haves verified
re_verification: false
---

# Phase 3: CI/CD Verification Report

**Phase Goal:** Establish CI/CD pipeline with GitHub Actions for automated testing and Docker image release
**Verified:** 2026-05-28T07:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ruff check . exits 0 on entire repo (excluding cpy.pyx and tests/conftest.py per D-04) | VERIFIED | `ruff check .` → "All checks passed!", exit 0 |
| 2 | ruff format --check . exits 0 on entire repo | VERIFIED | `ruff format --check .` → "4 files already formatted", exit 0 |
| 3 | pyright exits 0 in basic mode on all .py files (cpy.pyx excluded per D-02) | VERIFIED | `pyright` → "0 errors, 13 warnings", exit 0 |
| 4 | pytest tests/ still exits 0 after refactor (Phase 2 tests unchanged) | VERIFIED | `pytest tests/ -x -q` → "13 passed, 4 warnings", exit 0 |
| 5 | ruff and pyright installed via requirements-dev.txt (not requirements.txt, keeps Docker image lean per D-13) | VERIFIED | ruff/pyright absent from requirements.txt; requirements-dev.txt has both pinned |
| 6 | On every pull request targeting main, a CI workflow runs automatically (D-05) | VERIFIED | ci.yml triggers on `pull_request: branches: [main]` |
| 7 | Three jobs run in parallel: lint, typecheck, test (D-06) | VERIFIED | 3 job names in ci.yml; no `needs:` between them |
| 8 | lint job runs both ruff check . and ruff format --check . (D-03) | VERIFIED | ci.yml lines 30–32: `ruff check .` and `ruff format --check .` |
| 9 | typecheck job runs pyright in basic mode (D-01) | VERIFIED | ci.yml line 56: `run: pyright`; basic mode from pyproject.toml |
| 10 | test job runs pytest tests/ | VERIFIED | ci.yml line 85: `pytest tests/ -v` |
| 11 | All three jobs use Python 3.9 (D-07) | VERIFIED | `python-version: '3.9'` appears 3 times in ci.yml |
| 12 | Pip dependencies are cached for faster CI runs | VERIFIED | `cache: 'pip'` appears 3 times in ci.yml, keyed on both requirements files |
| 13 | Deploy workflow is manually triggered via workflow_dispatch with a version input (D-08, D-09) | VERIFIED | deploy.yml trigger is `workflow_dispatch:` only; version input declared `required: true` |
| 14 | Version input is validated as semver MAJOR.MINOR.PATCH (reject 'v1.0', reject non-numeric) | VERIFIED | Regex `^[0-9]+\.[0-9]+\.[0-9]+$` validated in bash before any other step |
| 15 | Workflow creates git tag v{version} on the dispatched commit | VERIFIED | `TAG=v$VERSION` + `git tag -a "$TAG"` + `git push origin "$TAG"` |
| 16 | Workflow builds Docker image using the existing Dockerfile | VERIFIED | `file: ./Dockerfile`, `context: .` in docker/build-push-action@v5 step |
| 17 | Workflow pushes image to ghcr.io/<owner>/<repo>:<version> AND :latest atomically (D-10) | VERIFIED | Both tags in single `build-push-action` step; lowercase via `${GITHUB_REPOSITORY,,}` |
| 18 | Workflow creates a GitHub Release with auto-generated notes since previous tag (D-11) | VERIFIED | `softprops/action-gh-release@v2` with `generate_release_notes: true`, `fetch-depth: 0` |
| 19 | Authentication uses GITHUB_TOKEN — no additional secrets required | VERIFIED | Only `secrets.GITHUB_TOKEN` referenced in deploy.yml |

**Score:** 19/19 truths verified (15 from plan must_haves, 4 additional confirmed)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Ruff + pyright config (D-12) | VERIFIED | 24 lines; [tool.ruff], [tool.ruff.lint], [tool.ruff.format], [tool.pyright] all present |
| `requirements-dev.txt` | Dev dependencies (ruff, pyright) | VERIFIED | 3 lines; `-r requirements.txt`, `ruff==0.8.4`, `pyright==1.1.391` |
| `app.py` | Lint-clean, type-clean Flask app | VERIFIED | ruff and pyright both exit 0; Phase 2 function signatures preserved |
| `cpy_fallback.py` | Lint-clean, type-clean fallback module | VERIFIED | No lint or type errors |
| `.github/workflows/ci.yml` | PR quality gate workflow | VERIFIED | 85 lines; 3 parallel jobs; YAML valid |
| `.github/workflows/deploy.yml` | Manual deploy + release workflow | VERIFIED | 82 lines; workflow_dispatch; YAML valid |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml` | ruff/pyright tools | `[tool.ruff]` and `[tool.pyright]` sections | WIRED | Both sections present and active |
| `requirements-dev.txt` | Dockerfile | NOT referenced — dev deps stay out of image | WIRED | ruff/pyright absent from requirements.txt |
| `.github/workflows/ci.yml` | `requirements-dev.txt` | pip install step | WIRED | typecheck job: `pip install -r requirements-dev.txt` |
| `.github/workflows/ci.yml` | `pyproject.toml` | ruff and pyright auto-discovery | WIRED | Both tools auto-read pyproject.toml from repo root |
| `.github/workflows/deploy.yml` | `Dockerfile` | docker/build-push-action reads ./Dockerfile | WIRED | `file: ./Dockerfile`, `context: .` |
| `.github/workflows/deploy.yml` | `ghcr.io` | docker/login-action with GITHUB_TOKEN | WIRED | `registry: ghcr.io`, auth via GITHUB_TOKEN |
| `.github/workflows/deploy.yml` | GitHub Releases API | softprops/action-gh-release with generate_release_notes | WIRED | action@v2 with `generate_release_notes: true` |

---

### Data-Flow Trace (Level 4)

Not applicable. All phase artifacts are configuration files and workflow definitions — no dynamic data rendering or state variables involved.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ruff lints entire repo cleanly | `ruff check .` | "All checks passed!" exit 0 | PASS |
| ruff format is consistent | `ruff format --check .` | "4 files already formatted" exit 0 | PASS |
| pyright type-checks with 0 errors | `pyright` | "0 errors, 13 warnings" exit 0 | PASS |
| pytest suite passes | `pytest tests/ -x -q` | "13 passed, 4 warnings" exit 0 | PASS |
| ci.yml YAML is syntactically valid | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` | exit 0 | PASS |
| deploy.yml YAML is syntactically valid | `python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` | exit 0 | PASS |
| ruff not in requirements.txt | `grep -q "ruff" requirements.txt` | no match (exit 1) | PASS |
| ruff and pyright in requirements-dev.txt | `grep -E "^(ruff|pyright)" requirements-dev.txt` | 2 matches | PASS |
| ci.yml has 3 parallel jobs (no needs:) | `grep -E "^  (lint|typecheck|test):" ci.yml \| wc -l` and `grep -q "needs:" ci.yml` | 3 jobs, no needs: | PASS |
| All 3 ci.yml jobs use Python 3.9 | `grep -c "python-version: '3.9'" ci.yml` | 3 | PASS |
| All 3 ci.yml jobs cache pip | `grep -c "cache: 'pip'" ci.yml` | 3 | PASS |
| deploy.yml uses workflow_dispatch only | `grep -n "push:" deploy.yml` | line 66 is docker push: true (action param, not trigger) | PASS |
| semver regex present in deploy.yml | `grep '\[0-9\]'` | regex `^[0-9]+\.[0-9]+\.[0-9]+$` found | PASS |
| all workflow actions pinned (not @main/@master) | `grep -E "@(main\|master)"` in both workflows | no matches | PASS |
| deploy.yml uses only GITHUB_TOKEN | `grep "secrets\." deploy.yml` | only GITHUB_TOKEN (twice) | PASS |
| Phase 2 function signatures preserved | `grep "def parse_photo_date\|def draw_date_overlay" app.py` | both found | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CI-01 | 03-01-PLAN.md | Dev tooling baseline: ruff + pyright installed, configured in pyproject.toml, codebase CI-green locally | SATISFIED | pyproject.toml with [tool.ruff]/[tool.pyright]; requirements-dev.txt with pinned versions; all four quality checks exit 0 |
| CI-02 | 03-02-PLAN.md | PR workflow exists — triggers automatically on every PR to main | SATISFIED | ci.yml `on: pull_request: branches: [main]`; commit 880e5e1 |
| CI-03 | 03-02-PLAN.md | Three parallel quality gates (lint, typecheck, test) all must pass for PR to be green | SATISFIED | Three jobs in ci.yml with no `needs:` dependency; branch protection configuration left to user per SUMMARY |
| CI-04 | 03-03-PLAN.md | Manual deploy workflow with semver version input and validation | SATISFIED | deploy.yml with workflow_dispatch, required version input, bash regex validation; commit a34c35b |
| CI-05 | 03-03-PLAN.md | Docker image pushed to ghcr.io with version + latest tags; GitHub Release auto-generated | SATISFIED | atomic push of `{version}` + `latest` tags in single build-push-action step; softprops/action-gh-release@v2 with generate_release_notes |

No orphaned requirements found. All 5 CI requirements are claimed by plans and verified in the codebase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.py` | 156 | `# noqa: N816` on `rotationAngle` global | Info | Justified — renaming would touch 7 call-sites with no behavior change; documented in SUMMARY |

No blockers or warnings found. The single noqa suppression is per-line (not file-level), justified, and documented.

---

### Human Verification Required

#### 1. Branch Protection Configuration

**Test:** Open a test PR to main. Check that GitHub requires all three checks (Lint (ruff), Typecheck (pyright), Test (pytest)) to pass before merging is allowed.
**Expected:** PR cannot be merged until all three CI jobs are green.
**Why human:** Branch protection rules are configured in GitHub repository settings out-of-band (not in code). The workflow file enables the checks to exist, but the enforcement rule must be set manually by a repo admin.

#### 2. End-to-End Deploy Workflow Run

**Test:** Go to GitHub Actions, dispatch the deploy workflow with version `1.0.0`.
**Expected:** (1) Semver validation passes, (2) git tag `v1.0.0` is created, (3) Docker image is pushed to `ghcr.io/<owner>/<repo>:1.0.0` and `:latest`, (4) GitHub Release `v1.0.0` is created with auto-generated notes.
**Why human:** workflow_dispatch cannot be run locally or triggered by a commit — requires manual dispatch from the GitHub Actions UI or gh CLI on the remote repository.

#### 3. Duplicate Tag Guard

**Test:** Dispatch the deploy workflow a second time with the same version (e.g. `1.0.0`).
**Expected:** Workflow fails at the "Create git tag" step with the error message "Tag v1.0.0 already exists."
**Why human:** Requires the workflow to have run at least once to create the initial tag; cannot be verified without an actual GitHub Actions run.

---

### Gaps Summary

None. All automated checks passed. Three items require human verification involving GitHub Actions runtime behavior that cannot be checked locally.

---

## Summary

Phase 3 goal is fully achieved in the codebase. The local prerequisite is proven by four passing quality tools (ruff, ruff format, pyright, pytest). The CI workflow (`ci.yml`) is structurally complete and YAML-valid with the required three-job parallel layout. The deploy workflow (`deploy.yml`) is structurally complete and YAML-valid with semver validation, atomic dual-tag push, and auto-release-notes. All five requirements (CI-01 through CI-05) are satisfied by verifiable artifacts. No stubs, no blocker anti-patterns, all commits verified.

---

_Verified: 2026-05-28T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
