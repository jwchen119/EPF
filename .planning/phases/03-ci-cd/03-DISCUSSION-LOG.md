# Phase 3: CI/CD - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 03-ci-cd
**Areas discussed:** Pyright strictness

---

## Pyright Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| basic | Common errors without exhaustive annotations. Realistic for 900-line Flask app. | ✓ |
| standard | Stricter inference, more required annotations — middle ground | |
| strict | Full type coverage required — significant annotation investment | |

**User's choice:** basic
**Notes:** The 900-line `app.py` retroactive annotation effort would be too large for strict mode. Basic is realistic to hit green in one prerequisite sprint.

---

## Claude's Discretion

- Ruff rule selection (E, W, F baseline; I for isort, N for naming)
- Dev dependency management strategy (requirements-dev.txt vs requirements.txt)
- GitHub Actions runner version
- pip caching strategy in CI
- Docker image naming convention (ghcr.io/<owner>/<repo>:<version>)
- PR workflow branch scope (defaulted to PRs targeting main)
- Semver validation in deploy workflow

## Deferred Ideas

None.
