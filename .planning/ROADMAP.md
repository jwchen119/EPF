# EPF Project Roadmap

## Phase 1: Hardware Port — FireBeetle C6 + WaveShare 7.3" → XIAO S3 Plus + Seeed 13.3" Color Eink

**Goal:** Port firmware and server to the EE02 kit (XIAO ESP32-S3 Plus + Seeed 13.3" T133A01 display). Replace WaveShare driver with Seeed_GFX. Update server palette and resolution.

**Requirements:** HW-01, HW-02, HW-03, HW-04, HW-05, HW-06, HW-07

**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Replace WaveShare driver headers with EE02 pin constants and Seeed_GFX includes
- [x] 01-02-PLAN.md — Rewrite main .ino: Seeed_GFX API, PSRAM frame buffer, remove battery guard, fix sleep API
- [x] 01-03-PLAN.md — Update server palette (T133A01 colors), nibble map, and 1200x1600 resolution

## Phase 2: Date Overlay — Show photo date on e-paper display

**Goal:** Extract the date a photo was taken (from Immich API metadata or file EXIF) and render it as a configurable text overlay on the processed image. The overlay position (9 alignments: topLeft, topCenter, topRight, centerLeft, center, centerRight, bottomLeft, bottomCenter, bottomRight) must be configurable via config.yaml and the web settings UI.

**Requirements:** DO-01, DO-02, DO-03, DO-04, DO-05

**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — Wave 0: pytest infra + 9 failing test stubs locking DO-01..DO-05 contracts
- [x] 02-02-PLAN.md — Add module-level parse_photo_date() and draw_date_overlay() helpers (TDD GREEN for pure logic)
- [x] 02-03-PLAN.md — Wire overlay into scale_img_in_memory + DEFAULT_CONFIG + settings UI; remove dead code

## Phase 3: CI/CD — GitHub Actions Workflows for Quality Gates and Deployment

**Goal:** Add GitHub Actions CI/CD to enforce code quality on pull requests and enable reproducible Docker image releases. Ruff and pyright are installed and all linting/type errors resolved before the workflows run in CI. A PR workflow runs automatically on every pull request to verify code style (ruff), types (pyright), and tests (pytest). A manual deploy workflow builds and pushes a Docker image to GitHub Container Registry (ghcr.io) using semantic versioning via git tags and GitHub Releases.

**Requirements:** CI-01, CI-02, CI-03, CI-04, CI-05

**Plans:** 3/3 plans complete

Plans:
- [x] 03-01-PLAN.md — Install ruff/pyright, configure in pyproject.toml, resolve all lint and type errors locally (prerequisite)
- [x] 03-02-PLAN.md — PR workflow: ruff + pyright + pytest as three parallel jobs on pull_request → main
- [x] 03-03-PLAN.md — Deploy workflow: manual workflow_dispatch with semver input, build & push to ghcr.io ({version} + latest), git tag, GitHub Release with auto-notes
