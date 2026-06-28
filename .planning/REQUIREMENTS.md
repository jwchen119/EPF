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

---

## Phase 12 — More Color Options: Gray Shades (CLR-01..CLR-04)

Add three gray shade options (Dark Gray, Gray, Light Gray) to the overlay color palette so
they can be selected for background, text, and border colors. Overlay-only — the T133A01
hardware quantization palette is unchanged; grays nearest-neighbor to black/white on the
e-paper. See `.planning/phases/12-more-color-options-expand-text-and-border-color-palette-with-gray-shades/12-CONTEXT.md`.

| ID | Requirement | Acceptance Criteria | Verification |
|----|-------------|---------------------|--------------|
| CLR-01 | OVERLAY_COLORS gains three gray RGBA entries | `OVERLAY_COLORS` contains `'dark_gray': (64, 64, 64, 255)`, `'gray': (128, 128, 128, 255)`, `'light_gray': (192, 192, 192, 255)` in addition to the existing 6 colors | unit — `python -c "import app; assert app.OVERLAY_COLORS['dark_gray']==(64,64,64,255) and app.OVERLAY_COLORS['gray']==(128,128,128,255) and app.OVERLAY_COLORS['light_gray']==(192,192,192,255)"` |
| CLR-02 | Existing overlay-color contract test reflects the 9-color set | `tests/test_overlay_customization.py::test_overlay_colors_dict` asserts the key set is exactly the 9 colors (black, white, dark_gray, gray, light_gray, yellow, red, blue, green) and the three new RGBA values; full test suite passes | unit — `pytest tests/test_overlay_customization.py::test_overlay_colors_dict -x` |
| CLR-03 | All three settings dropdowns offer the grays in the correct order | Each of `overlay_bg_color`, `overlay_text_color`, `overlay_border_color` `<select>` in `templates/settings.html` has `<option>` entries for `dark_gray`/`gray`/`light_gray` placed after White and before Yellow (order: Black, White, Dark Gray, Gray, Light Gray, Yellow, Red, Blue, Green) with labels "Dark Gray"/"Gray"/"Light Gray" and the existing `.get()` selected-state pattern | code review — `grep -c 'value="dark_gray"' templates/settings.html` returns 3 |
| CLR-04 | Gray selections persist round-trip and render without error | Selecting a gray for any of the three colors saves to config.yaml and re-renders selected on reload; the date overlay renders using the gray RGBA without exceptions; old config.yaml lacking gray values still loads (`.get` fallback) | manual — human-verify (12-01 Task 3) |

---

## Phase 13 — Battery Indicator Icon: Low Battery Warning (BATIND-01..BATIND-05)

Render a PIL-drawn battery warning icon onto the display image (server-side, before binary
encoding) only when the device's reported battery level is low or empty. Warning-only — no
icon when battery is healthy or when there is no battery data (USB-only). Position is
user-configurable via the same POSITIONS system as the date overlay. Server-only; no firmware
changes. See `.planning/phases/13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display/13-CONTEXT.md`.

| ID | Requirement | Acceptance Criteria | Verification |
|----|-------------|---------------------|--------------|
| BATIND-01 | `draw_battery_indicator()` renders a PIL battery icon (body + nub + state-based fill) | A new function `draw_battery_indicator(output_img, battery_pct, position_str, rotation, font_size, color)` exists in `app.py`; for `battery_pct=10` it mutates a white 1200×1600 image (non-white pixels present) drawing a battery body (2:1) + right-side nub at the requested viewer-space position; icon height ≈ `font_size`; stroke width 2 (D-01, D-04, D-12, D-13) | unit — `tests/test_battery_indicator.py` (draw produces non-white pixels at low state) |
| BATIND-02 | Three discrete fill states keyed to thresholds | `BATTERY_LOW_THRESHOLD == 20` and `BATTERY_FLAT_THRESHOLD == 5` constants exist; `battery_pct > 20` draws nothing (no-op), `5 < battery_pct <= 20` draws a partially-filled body, `battery_pct <= 5` draws an empty (no-fill) outline (D-02, D-06) | unit — `tests/test_battery_indicator.py` (above-threshold no-op byte-identical to blank; flat vs low produce different pixel counts) |
| BATIND-03 | Icon is warning-only and suppressed when there is no battery data | `draw_battery_indicator()` returns immediately (no pixel change) when `battery_pct > 20`; the `scale_img_in_memory()` call site computes `battery_pct` from `last_battery_voltage` only when `last_battery_voltage > 0` and passes 0 otherwise so USB/no-data devices never show a false flat icon (D-05, D-07, D-19) | unit — `tests/test_battery_indicator.py::test_above_threshold_is_noop`; code review — `grep "last_battery_voltage > 0" app.py` |
| BATIND-04 | `battery_indicator_enabled` / `battery_indicator_position` are persisted config keys | `DEFAULT_CONFIG['immich']` contains `'battery_indicator_enabled': 'on'` and `'battery_indicator_position': 'topRight'`; both round-trip through `update_app_config()` and the POST handler with `.get()` fallback; `scale_img_in_memory()` calls `draw_battery_indicator()` after `draw_date_overlay()`, gated on `battery_indicator_enabled == 'on'` (D-08, D-09, D-16, D-17, D-18) | unit — `python -c "import app; assert app.DEFAULT_CONFIG['immich']['battery_indicator_enabled']=='on' and app.DEFAULT_CONFIG['immich']['battery_indicator_position']=='topRight'"`; code review — `grep "draw_battery_indicator(" app.py` |
| BATIND-05 | Settings UI exposes a Battery Indicator card | `templates/settings.html` has a new "Battery Indicator" card (separate from Date Overlay and Power Management cards) with an Enable `select` (on/off, default on) named `battery_indicator_enabled` and a Position `select` named `battery_indicator_position` offering the 9 POSITIONS keys (default topRight); both use the `.get()` selected-state pattern; old config.yaml without the keys still renders (D-14, D-15) | code review — `grep -c 'name="battery_indicator_position"' templates/settings.html` returns 1; manual — human-verify (13-02 Task) |
