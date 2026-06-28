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

### Phase 7: Geolocation overlay from image metadata

**Goal:** Extend the image overlay to show the rough location where a photo was taken as a single-line `"City, Country • DD.MM.YYYY"` string. For local images, extract GPS from EXIF tag 34853 and reverse-geocode via geopy/Nominatim with a persistent JSON cache. For Immich images, read the pre-geocoded `city`/`country` from the already-fetched `exifInfo` dict (no extra API call). Fall back through geo+date → geo → date → hidden. No new config keys or UI controls — the existing date-overlay toggle and a static UI note suffice.

**Requirements:** GEO-01, GEO-02, GEO-03, GEO-04, GEO-05, GEO-06, GEO-07, GEO-08, GEO-09, GEO-10, GEO-11, GEO-12

**Depends on:** Phase 6

**Plans:** 3/3 plans complete

Plans:
- [x] 07-01-PLAN.md — Wave 0 (TDD RED): tests/test_geo_overlay.py with 12 failing contract tests + synthetic_gps_image/mock_geo_cache_dir fixtures (GEO-01..GEO-12)
- [x] 07-02-PLAN.md — TDD GREEN: add geopy==2.4.1; implement extract_gps_from_exif() + reverse_geocode_cached() (JSON cache) + parse_photo_location() (GEO-01..GEO-08)
- [x] 07-03-PLAN.md — Integration: extend scale_img_in_memory() with immich_exif_raw + geo/date fallback assembly; wire serve_immich_image; static settings UI note (GEO-09..GEO-12)

### Phase 8: Auth — Secure access to the app with opt-in HTTP Basic Auth

**Goal:** Add opt-in HTTP Basic Auth to the Flask app so it is not open to anyone on the local network. A `require_auth` decorator protects all four routes (`/`, `/setting`, `/download`, `/sleep`): when `APP_PASSWORD` is set, requests need username `admin` + the password (constant-time compared via `hmac.compare_digest`); missing/wrong credentials get `401` + `WWW-Authenticate: Basic realm="EPF"`, triggering the browser's native dialog. When `APP_PASSWORD` is empty/absent, all routes stay open (backward compatible). The ESP32 firmware sends matching credentials via `HTTPClient.setAuthorization("admin", APP_PASSWORD)` on its `/download` and `/sleep` calls. Documented in `compose.yml`, `.env.example`, and README.

**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10

**Depends on:** Phase 7

**Plans:** 1/3 plans executed

Plans:
- [x] 08-01-PLAN.md — Wave 0 (TDD RED): tests/test_auth.py with 8 failing contract tests (AUTH-01..AUTH-08)
- [x] 08-02-PLAN.md — TDD GREEN: require_auth decorator + APP_PASSWORD + protect 4 routes; document in compose.yml/.env.example/README (AUTH-01..05, 07, 08)
- [ ] 08-03-PLAN.md — Firmware setAuthorization() on http + sleepHttp clients + config.h constant; human verify browser dialog + device fetch (AUTH-06, AUTH-09, AUTH-10)

### Phase 9: Blurred background behind image when using fit-width or fit-height modes

**Goal:** Replace the plain white letterbox/pillarbox bars in fit mode with a fill-scaled, heavily Gaussian-blurred version of the same photo as the background layer. The sharp fit-scaled photo is pasted centered on top. Implemented in cpy_fallback.py (canonical pure-Python) and mirrored into cpy.pyx (Cython production path). A new blur_radius config key (default 30) is persisted to config.yaml and exposed via a slider in the settings UI.

**Requirements:** BG-01, BG-02, BG-03, BG-04, BG-05, BG-06

**Depends on:** Phase 8

**Plans:** 3/3 plans complete

Plans:
- [x] 09-01-PLAN.md — Wave 1 (TDD RED): tests/test_blur_background.py with 6 failing contract tests (BG-01..BG-06)
- [x] 09-02-PLAN.md — Wave 2 (TDD GREEN): blur-fill fit branch in cpy_fallback.py + blur_radius wired through app.py (DEFAULT_CONFIG, update_app_config, scale_img_in_memory, POST handler)
- [x] 09-03-PLAN.md — Wave 3: mirror blur logic into cpy.pyx + blur_radius slider in settings.html + human visual verify checkpoint

### Phase 10: Battery optimization

**Goal:** Reduce active-period battery drain on the XIAO ESP32-S3 firmware. Switch image transport from hex-CSV text (~2.8 MB) to raw binary (960000 bytes, application/octet-stream) on the server to cut WiFi-on time ~3x. On firmware: gate the 3 s USB-CDC boot delay on wakeup cause (skip on deep-sleep wakeups), set CPU to 80 MHz and WiFi TX power to 8.5 dBm before connecting, decode the frame as raw binary directly into PSRAM, and isolate the BAT_ADC/ADC_EN GPIOs before deep sleep. Estimated ~4.4 mAh/day saved.

**Requirements:** BATT-01, BATT-02, BATT-03, BATT-04, BATT-05, BATT-06

**Depends on:** Phase 9

**Plans:** 2/2 plans complete

Plans:
- [x] 10-01-PLAN.md — Wave 1 (TDD): binary image transport server-side — convert_to_binary_in_memory() + octet-stream /download responses; contract tests BATT-01..04
- [x] 10-02-PLAN.md — Wave 2 (firmware): gated boot delay + CPU 80 MHz + WiFi TX 11 dBm + binary frame decode + GPIO isolation; human-verify on device (BATT-05, BATT-06)

### Phase 999.1: Set SPI/display GPIO pins to INPUT before deep sleep

**Goal:** Set SPI and display control pins (DC GPIO10, CS GPIO44, CS1 GPIO41, RST GPIO38) to INPUT mode — and release SCLK GPIO8 / MOSI GPIO9 via `SPI.end()` — before `esp_deep_sleep_start()` in the battery path of `hibernate()`, to eliminate leakage current through the e-paper protection diodes. These are digital-only ESP32-S3 pins (NOT RTC-capable), so `rtc_gpio_isolate()` does not apply and `gpio_reset_pin()` is avoided (can block deep-sleep entry); use `pinMode(pin, INPUT)`. The Seeed_GFX `epaper.sleep()` call only sends a software command and does NOT tri-state these lines. Measure deep-sleep current before/after — impact may be small or zero if the T133A01 already tri-states its own SPI inputs on sleep, in which case the change remains as defensive engineering.

**Requirements:** SLEEP-01, SLEEP-02, SLEEP-03

**Depends on:** Phase 10

**Plans:** 1/1 plans complete

Plans:
- [x] 999.1-01-PLAN.md — Measure baseline current, add SPI.end() + pinMode(INPUT) on DC/CS/CS1/RST to hibernate() battery path, human-verify wake cycle + measure after-change current (SLEEP-01..03)
