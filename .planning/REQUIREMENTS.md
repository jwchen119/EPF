# EPF Requirements

> Canonical requirement definitions referenced by ROADMAP.md and phase plans.
> Requirement IDs are phase-prefixed (e.g., BATT-* belongs to Phase 10).

---

## Phase 10 — Battery Optimization (BATT-01..BATT-06)

Reduce active-period battery drain on the XIAO ESP32-S3 firmware by switching image
transport to raw binary and tuning the firmware wake cycle. See
`.planning/phases/10-battery-optimization/10-RESEARCH.md` for the full impact analysis.

| ID | Requirement | Acceptance Criteria | Verification |
|----|-------------|---------------------|--------------|
| BATT-01 | Server encodes the e-paper frame as raw binary | `convert_to_binary_in_memory()` returns a `BytesIO` whose contents are exactly `960000` bytes (1200×1600 / 2), with no ASCII hex formatting | unit — `tests/test_battery_optimization.py::test_binary_output_length` |
| BATT-02 | Binary encoding is nibble-identical to the legacy hex-CSV encoding | For the same image, the bytes from `convert_to_binary_in_memory()` equal the byte values parsed from `convert_to_c_code_in_memory()`, element for element | unit — `tests/test_battery_optimization.py::test_binary_nibble_parity` |
| BATT-03 | `/download` returns binary content type | `GET /download` (with a local image present) returns HTTP 200 with `Content-Type: application/octet-stream` | integration — `tests/test_battery_optimization.py::test_download_mimetype` |
| BATT-04 | `/download` advertises the exact frame length | `GET /download` returns `Content-Length: 960000` | integration — `tests/test_battery_optimization.py::test_download_content_length` |
| BATT-05 | Firmware skips the boot delay on production wakeups | On a deep-sleep timer/EXT1 wakeup the device renders the new image quickly (no 3 s serial-monitor pause); cold boot/reset still waits 3 s for the serial monitor | manual — human-verify on device (`10-02` Task 3) |
| BATT-06 | Firmware decodes the binary frame and renders it correctly | After deploying the binary server and firmware together, the e-paper renders the downloaded photo with correct colors and no random-color noise; serial log shows no byte-count mismatch | manual — human-verify on device (`10-02` Task 3) |

**Atomicity note (BATT-02/BATT-06):** the server binary protocol (Phase 10-01) and the
firmware binary decode (Phase 10-02) must ship together. A binary server with a hex-decoding
firmware (or vice versa) corrupts the frame buffer (see 10-RESEARCH Pitfall 3).

---

## Phase 999.1 — SPI/Display GPIO Tri-State Before Deep Sleep (SLEEP-01..SLEEP-03)

Eliminate leakage current through the e-paper protection diodes during deep sleep by
tri-stating the SPI/display control pins before `esp_deep_sleep_start()`. Firmware-only;
see `.planning/phases/999.1-set-spi-display-gpio-pins-to-input-before-deep-sleep/999.1-RESEARCH.md`.

| ID | Requirement | Acceptance Criteria | Verification |
|----|-------------|---------------------|--------------|
| SLEEP-01 | Firmware tri-states SPI/display pins before deep sleep | In `hibernate()` battery path, `SPI.end()` is called and `pinMode(INPUT)` is set on DC_PIN/CS_PIN/CS1_PIN/RST_PIN, after `rtc_gpio_isolate(GPIO_NUM_6)` and before `fs_deinit()`; `gpio_reset_pin` is NOT used | code review — `grep "SPI.end();" epd7in3e/epd7in3e.ino` |
| SLEEP-02 | The change does not regress the wake cycle | After flashing, the device wakes from deep sleep, downloads, and re-renders the photo with correct colors and no noise (proves `SPI.end()` does not break SPI re-init on wake) | manual — human-verify on device (`999.1-01` Task 3) |
| SLEEP-03 | Deep-sleep current impact is measured | Before/after deep-sleep current is recorded (µA) and the delta documented, or explicitly noted as unmeasurable when no probe is available | manual — human-verify on device (`999.1-01` Task 3) |

---

## Phase 11 — Margin for Text on Image (MARGIN-01..MARGIN-05)

Add a configurable inset margin so the date/location overlay text is pushed away from the
display edges, keeping it visible inside a passe-partout window mat. Additive to the existing
`padding=6` text-box breathing room. Server-only; see
`.planning/phases/11-margin-for-text-on-image-configurable-inset-margin-to-keep-text-visible-behind-passe-partout/11-CONTEXT.md`.

| ID | Requirement | Acceptance Criteria | Verification |
|----|-------------|---------------------|--------------|
| MARGIN-01 | POSITIONS lambdas inset edge text by margin_h/margin_v additive to padding | All 9 POSITIONS lambdas accept `(w, h, tw, th, p, mh, mv)`; corner/edge positions add `mh`/`mv` to the relevant axis; `center` ignores both; `centerLeft`/`centerRight` apply only `mh`; `topCenter`/`bottomCenter` apply only `mv` | unit — `tests/test_overlay_margin.py` (position math) |
| MARGIN-02 | draw_date_overlay default margins reproduce prior output | `draw_date_overlay(..., margin_h=0, margin_v=0)` produces byte-identical pixels to the call omitting margins; signature defaults are 0 | unit — `tests/test_overlay_margin.py::test_draw_overlay_zero_margin_matches_omitted` |
| MARGIN-03 | overlay_margin_h/overlay_margin_v are persisted config keys defaulting to 0 | Both keys exist in `DEFAULT_CONFIG['immich']` with value 0; loaded into module globals; round-trip through `update_app_config()` with `int()` cast and `.get()` fallback | unit — `python -c "import app; assert app.DEFAULT_CONFIG['immich']['overlay_margin_h']==0"` |
| MARGIN-04 | scale_img_in_memory() passes configured margins to draw_date_overlay() | The `draw_date_overlay()` call site includes `margin_h=overlay_margin_h, margin_v=overlay_margin_v` | code review — `grep "margin_h=overlay_margin_h" app.py` |
| MARGIN-05 | Settings UI exposes Horizontal/Vertical Margin sliders | `templates/settings.html` has two sliders (`overlay_margin_h`, `overlay_margin_v`), range 0–200 step 10, in the Date Overlay card; values persist via the POST handler; old config.yaml without the keys still renders (`.get` fallback) | code review — `grep "overlay_margin_h" templates/settings.html` |
