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

## Phase 4: Battery Voltage — Detect power source, restore sleep, document charge LED limitation

**Goal:** Restore battery voltage monitoring that was removed in Phase 1. Read the battery ADC on GPIO1 (gated by GPIO5 ADC_EN on the EE02 board), detect whether the device is running on battery or USB power, send voltage to the server as the `batteryCap` HTTP header (mV; 0 on USB-only), re-enable deep sleep when on battery (USB-only loops via delay + ESP.restart), and document that the green charge LEDs are BQ24070 PMIC-controlled with no firmware path to suppress them.

**Requirements:** BV-01, BV-02, BV-03, BV-04, BV-05

**Plans:** 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — Add BAT_ADC_PIN/ADC_EN_PIN/MIN_BATTERY_VOLTAGE defines; implement checkVoltage() + enforceLowBatteryGuard() in EpaperManager; call from setup()
- [x] 04-02-PLAN.md — Add 50-sample averaged batteryCap HTTP header in downloadImage(); replace hibernate() stub with USB/battery branching; document BQ24070 LED limitation

## Phase 5: Documentation — Update README to Reflect Current Hardware and Features

**Goal:** Rewrite README.md to accurately describe the current project: XIAO ESP32-S3 Plus + Seeed 13.3" Color E-paper (EE02 HAT) hardware, all new server features (date overlay, local photo source, display modes, sleep scheduling, battery monitoring), updated setup instructions (ghcr.io image, compose.yml, required Arduino libraries including TFT_eSPI), and CI/CD workflows.

**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05

**Plans:** 1/1 plans complete

Plans:
- [x] 05-01-PLAN.md — Rewrite README.md end-to-end: new header/Features/Components/pin map (Task 1) + Installation/Firmware/Development/License with ghcr.io + compose + Arduino libs + CI/CD (Task 2)

### Phase 6: Text customization: colors, styles, and border mode

**Goal:** Make the timestamp overlay's visual appearance configurable: overlay style (filled background vs. outline/stroke), background color, text color, border/stroke color, stroke thickness, and font size — all selected from the 6-color T133A01 palette and exposed in the web Configuration UI, persisted to config.yaml. Defaults preserve the exact current visual so existing deployments see zero change until configured.

**Requirements:** TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09

**Depends on:** Phase 5

**Plans:** 2/3 plans executed

Plans:
- [x] 06-01-PLAN.md — Wave 0 (TDD RED): tests/test_overlay_customization.py with 9 failing contract tests (OVERLAY_COLORS, extended draw_date_overlay signature, bg/outline modes, config keys)
- [x] 06-02-PLAN.md — TDD GREEN: add OVERLAY_COLORS dict + 6 DEFAULT_CONFIG keys + globals; extend draw_date_overlay() with style/colors/stroke (TC-01..TC-07)
- [x] 06-03-PLAN.md — Wire update_app_config + POST handler + scale_img_in_memory call site + settings.html controls (TC-08, TC-09)
