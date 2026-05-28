# Phase 3: CI/CD - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Add GitHub Actions CI/CD to the repository:

1. **Prerequisite** — Install ruff and pyright as dev dependencies, resolve all linting errors and type errors, fix code style so the codebase is CI-green before workflows land.
2. **PR workflow** — Automatically runs on every pull request. Enforces code style (ruff), type correctness (pyright), and test passing (pytest).
3. **Deploy workflow** — Manually triggered. Builds the Docker image and pushes it to GitHub Container Registry (ghcr.io). Implements semantic versioning via git tags and GitHub Releases.

Firmware (Arduino/C++), CAD files, and runtime configuration are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Type checking (pyright)
- **D-01:** Use **basic** mode. The 900-line `app.py` should not require exhaustive type annotations to go green — basic mode catches common errors without demanding full annotation coverage.
- **D-02:** The Cython file `cpy.pyx` is excluded from pyright (it cannot be type-checked by pyright). Only `.py` files are checked.

### Code style (ruff)
- **D-03:** Ruff replaces both flake8 and isort. Run as a linter (`ruff check`) and formatter (`ruff format --check`) in CI.
- **D-04:** Claude's discretion on rule selection — a sensible default ruleset for Flask/Python 3.9 (E, W, F rules at minimum). Exclude the `tests/` conftest and any Cython-generated files.

### PR workflow
- **D-05:** Triggers on pull requests targeting `main`.
- **D-06:** Three jobs: `lint` (ruff check + ruff format), `typecheck` (pyright basic), `test` (pytest). Jobs run in parallel; all three must pass for the PR check to be green.
- **D-07:** Python version in CI: 3.9 (matches Dockerfile and runtime).

### Deploy workflow
- **D-08:** Manually triggered (`workflow_dispatch`) — not automatic on push to main.
- **D-09:** Semantic versioning via git tags. The workflow accepts a `version` input (e.g. `1.2.0`) at dispatch time, creates a git tag `v{version}`, builds and pushes the Docker image, and creates a GitHub Release.
- **D-10:** Docker image name: `ghcr.io/<github-owner>/<repo-name>:<version>`. Also tags `latest` on every successful deploy.
- **D-11:** GitHub Release notes are auto-generated from commits since the last tag.

### Tooling configuration
- **D-12:** Ruff and pyright config lives in `pyproject.toml` (create if it doesn't exist — no `setup.cfg` or separate config files).
- **D-13:** Ruff and pyright added to `requirements.txt` (or a new `requirements-dev.txt` if Claude judges that cleaner) — whichever keeps the Docker image lean.

### Claude's Discretion
- Exact ruff rule selection (E, W, F as baseline; add I for isort, N for naming if it passes cleanly)
- Whether to use `requirements-dev.txt` or add dev deps to `requirements.txt` with a comment
- GitHub Actions runner version (`ubuntu-latest`)
- Caching strategy for pip dependencies in CI
- Whether to add `--fail-under` to pytest for coverage enforcement (not required, but nice to have)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing infrastructure
- `Dockerfile` — Current Docker build (Python 3.9-slim, Cython compilation). Deploy workflow must reproduce this build faithfully.
- `requirements.txt` — Current runtime dependencies. Dev tools (ruff, pyright) should not bloat the production image.
- `compose.yml` — Docker Compose setup (for local reference; CI uses raw Docker build+push).

### Existing tests
- `tests/conftest.py` — pytest fixtures and configuration (set up in Phase 2).
- `tests/test_date_overlay.py` — Existing tests that must pass in CI.

### Core application
- `app.py` lines 1–56 — Global state, imports, DEFAULT_CONFIG. Primary target for ruff/pyright fixes.
- `cpy.pyx` — Cython source. Excluded from pyright; ruff also excludes it (not Python).
- `cpy_fallback.py` — Pure-Python fallback for Cython. Should be type-checked.

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile`: Multi-stage build with Cython compilation. The deploy workflow reuses this directly (`docker build .`).
- `tests/`: pytest infrastructure already in place from Phase 2.

### Established Patterns
- Docker deployment: project already ships as a Docker container. The deploy workflow extends this to ghcr.io with versioned tags.
- No existing CI: `.github/` directory does not exist — all workflow files are net-new.

### Integration Points
- GitHub Container Registry (ghcr.io): authenticate with `GITHUB_TOKEN` (automatically available in Actions). No additional secrets needed for the registry.
- GitHub Releases API: `gh release create` or the `actions/create-release` Action — generate release notes from git log since last tag.

</code_context>

<specifics>
## Specific Ideas

- Ruff and pyright must be installed and all errors resolved **before** the workflow files land — the prerequisite plan runs locally, not in CI.
- The deploy workflow version input should validate semver format (reject `v1.0` without patch, reject non-numeric).
- `latest` tag update should be atomic with the versioned tag push (both in same docker push step).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-ci-cd*
*Context gathered: 2026-05-27*
