---
phase: 10-battery-optimization
verified: 2026-06-28T00:00:00Z
status: human_needed
score: 4/6 must-haves verified automatically
human_verification:
  - test: "On-device: timer/EXT1 wakeup boots without the 3 s delay; cold boot/reset keeps it"
    expected: "Serial log shows 'Wakeup caused by timer' with no 3 s pause; a reset shows the full 3 s CDC wait"
    why_human: "Requires physical XIAO ESP32-S3, serial monitor observation — not pytest-testable"
  - test: "On-device: e-paper renders the binary frame with correct colors and no random-color noise; serial log shows no byte-count warning"
    expected: "Display shows the expected photo cleanly; 'Warning: expected 960000 bytes, received N' never appears"
    why_human: "Requires compiled firmware on device, visual display inspection, and serial log review"
notes:
  - "WIFI_POWER_8_5dBm was changed to WIFI_POWER_11dBm during hardware verification (connection drops at 8.5 dBm on 960 KB transfers). This is a documented, intentional deviation — the acceptance criterion spirit (lowest confirmed-working TX power) is satisfied."
---

# Phase 10: Battery Optimization Verification Report

**Phase Goal:** Reduce per-cycle energy consumption by eliminating avoidable overheads in the WiFi download path and ESP32 active time — binary transport, CPU/radio tuning, boot delay gating, and GPIO isolation before deep sleep.
**Verified:** 2026-06-28
**Status:** human_needed (4/6 auto-verified; 2 require physical device)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `/download` returns the e-paper frame as raw binary (`application/octet-stream`), not hex-CSV text | VERIFIED | `test_download_mimetype` passes; `grep application/octet-stream app.py` hits both `serve_local_image` (line 1060) and `serve_immich_image` (line 1154); `text/plain` is absent from all serve-function download paths |
| 2 | Binary frame is exactly 960000 bytes and Content-Length matches | VERIFIED | `test_binary_output_length` + `test_download_content_length` both pass; `convert_to_binary_in_memory()` returns `BytesIO` of exactly 960000 bytes |
| 3 | Binary bytes are nibble-identical to the legacy hex-CSV encoding | VERIFIED | `test_binary_nibble_parity` passes — same nibble_map, same depalette_image(), byte-for-byte comparison confirmed against multicolor 1200x1600 image |
| 4 | CPU set to 80 MHz and WiFi TX power set to confirmed-minimum before WiFi connect | VERIFIED | `setCpuFrequencyMhz(CPU_FREQ_MHZ)` at line 365 and `WiFi.setTxPower(WIFI_TX_POWER)` at line 367, both before `autoConnect()`; constants `CPU_FREQ_MHZ 80U` and `WIFI_TX_POWER WIFI_POWER_11dBm` defined in config.h lines 35–36 |
| 5 | On a deep-sleep timer/EXT1 wakeup the device skips the 3 s boot delay; cold boot keeps it | ? HUMAN | Code verified: `esp_sleep_get_wakeup_cause()` called before `delay()` (line 513); `isDevelopmentBoot` gate at line 516 with 3 s vs 50 ms branches. Behavioral confirmation requires physical device. |
| 6 | Device renders downloaded photo correctly with no corruption; GPIO isolation prevents ADC leakage | ? HUMAN | Code verified: binary readBytes loop at lines 250–265, `rtc_gpio_isolate(GPIO_NUM_1)` and `GPIO_NUM_6` at lines 298–299 (after `WiFi.mode(WIFI_OFF)`, before `esp_deep_sleep_start()`). On-device render test required. Hardware verification documented in 10-02-SUMMARY.md as completed, but verifier cannot independently confirm physical device output. |

**Score:** 4/6 truths verifiable automatically, both pass; 2/6 require human/device confirmation

---

## Required Artifacts

### Plan 10-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_battery_optimization.py` | RED contract tests BATT-01..BATT-04 | VERIFIED | 107 lines; contains `test_binary_output_length`, `test_binary_nibble_parity`, `test_download_mimetype`, `test_download_content_length`; all 4 pass |
| `app.py` | `convert_to_binary_in_memory()` + binary `/download` responses | VERIFIED | `def convert_to_binary_in_memory` at line 641; `application/octet-stream` in both `serve_local_image` (line 1060) and `serve_immich_image` (line 1154) |

### Plan 10-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `epd7in3e/epd7in3e.ino` | gated boot delay, CPU/TX power tuning, binary stream decode, GPIO isolation | VERIFIED | All four patterns present at lines 513–521 (boot gate), 365–367 (CPU/TX), 250–265 (readBytes), 298–299 (rtc_gpio_isolate) |
| `epd7in3e/config.h` | `CPU_FREQ_MHZ` + `WIFI_TX_POWER` documentation constants | VERIFIED | Line 35: `CPU_FREQ_MHZ 80U`; line 36: `WIFI_TX_POWER WIFI_POWER_11dBm` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py serve_local_image()` | `convert_to_binary_in_memory` | `send_file` with `mimetype application/octet-stream` | WIRED | Lines 1055–1063: `frame = convert_to_binary_in_memory(...)` then `send_file(frame, mimetype='application/octet-stream', ...)` |
| `app.py serve_immich_image()` | `convert_to_binary_in_memory` | `send_file` with `mimetype application/octet-stream` | WIRED | Lines 1151–1158: same pattern |
| `setup() delay` | `esp_sleep_get_wakeup_cause()` | gate the 3 s delay on wakeup reason | WIRED | `wakeup_reason` read at line 513, `isDevelopmentBoot` at line 514, conditional delay at lines 516–521 — wakeup cause evaluated BEFORE any `delay()` |
| `processImageData()` | `frame_buf` | `stream.readBytes(frame_buf + totalRead, ...)` | WIRED | Lines 250–265: binary readBytes loop fills PSRAM frame buffer directly; `strtol`/`String hexBuffer` fully absent |
| `hibernate()` | deep sleep | `rtc_gpio_isolate` before `esp_deep_sleep_start` | WIRED | `rtc_gpio_isolate(GPIO_NUM_1)` line 298, `rtc_gpio_isolate(GPIO_NUM_6)` line 299 — both appear after `WiFi.mode(WIFI_OFF)` (line 297) and before `esp_deep_sleep_start()` (line 315) |
| `processImageData() readBytes(frame_buf)` | `app.py /download (application/octet-stream, 960000 bytes)` | shared binary frame protocol (plan 10-01 + 10-02 atomic) | WIRED | Server emits exactly 960000 raw bytes (BATT-03/04 verified); firmware reads exactly 960000 bytes via readBytes loop — protocol contract held |

---

## Data-Flow Trace (Level 4)

Server-side: `convert_to_binary_in_memory()` computes the frame from `depalette_image(pixels, palette)` on the actual PIL image data — no static returns, no empty stubs. Both serve functions call it on the real processed image. BATT-02 nibble parity test confirms output is substantive (byte-for-byte matches the legacy encoder on a multicolor test image).

Firmware-side: `processImageData()` reads the binary HTTP response body directly into PSRAM `frame_buf` via `stream.readBytes()`, then calls `epaper.pushImage(0, 0, EPD_WIDTH, EPD_HEIGHT, (uint16_t*)frame_buf)`. Data path is continuous from HTTP socket to display. No hollow props or disconnected state.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `convert_to_binary_in_memory()` returns 960000 bytes | `pytest test_binary_output_length` | PASS | PASS |
| Binary bytes are nibble-identical to legacy encoder | `pytest test_binary_nibble_parity` | PASS | PASS |
| `/download` returns `application/octet-stream` | `pytest test_download_mimetype` | PASS | PASS |
| `/download` returns `Content-Length: 960000` | `pytest test_download_content_length` | PASS | PASS |
| Full suite — no regressions | `python -m pytest tests/ -q` | 61 passed, 10 warnings | PASS |
| Boot delay gate on physical device | MANUAL — requires XIAO ESP32-S3 | N/A | SKIP (human verify) |
| Binary render with no corruption | MANUAL — requires XIAO ESP32-S3 | N/A | SKIP (human verify) |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BATT-01 | 10-01 | `convert_to_binary_in_memory()` returns exactly 960000 bytes | SATISFIED | `test_binary_output_length` passes; function at app.py line 641 returns `BytesIO(bytes(bytes_array))` with `len == 960000` |
| BATT-02 | 10-01 | Binary encoding nibble-identical to legacy hex-CSV | SATISFIED | `test_binary_nibble_parity` passes; same `nibble_map` and `depalette_image()` used in both encoders |
| BATT-03 | 10-01 | `/download` returns `Content-Type: application/octet-stream` | SATISFIED | `test_download_mimetype` passes; both serve functions wired with `mimetype='application/octet-stream'` |
| BATT-04 | 10-01 | `/download` returns `Content-Length: 960000` | SATISFIED | `test_download_content_length` passes |
| BATT-05 | 10-02 | Firmware skips boot delay on timer/EXT1 wakeup | NEEDS HUMAN | Code verified correct (wakeup cause evaluated before delay, gate logic present). Hardware behavior documented as confirmed in 10-02-SUMMARY.md |
| BATT-06 | 10-02 | Firmware decodes binary frame and renders correctly; no byte-count mismatch | NEEDS HUMAN | Code verified (binary readBytes loop, hex decode removed). Hardware verification documented in 10-02-SUMMARY.md as confirmed |

All 6 BATT-* requirement IDs from REQUIREMENTS.md are accounted for. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `epd7in3e/config.h` | 36 | `WIFI_TX_POWER WIFI_POWER_11dBm` — plan specified `8.5dBm` | Info | Intentional deviation documented in 10-02-SUMMARY.md; hardware testing showed 8.5 dBm caused connection drops on 960 KB transfers; 11 dBm is confirmed minimum. Not a stub or regression. |

No TODO/FIXME/placeholder patterns found in any phase 10 files. No empty return stubs. No hex-decode remnants (`strtol`/`String hexBuffer` fully absent from firmware).

---

## Human Verification Required

### 1. Boot Delay Gate — Timer Wakeup Path

**Test:** Flash `epd7in3e/epd7in3e.ino` + `config.h` to the XIAO ESP32-S3. Let the device complete one cycle and wake from the deep-sleep timer. Open serial monitor.
**Expected:** Serial log shows "Wakeup caused by timer" with no multi-second pause before `checkVoltage` or WiFi connect. Then reset the device (press reset or power-cycle). Expected: full 3 s USB-CDC enumeration pause visible before any other log output.
**Why human:** Requires physical XIAO ESP32-S3, USB serial monitor, and real-time observation of boot sequence timing. Not simulatable in pytest.

### 2. Binary Render Correctness — On-Device

**Test:** With the binary server (`app.py`) running and returning `Content-Type: application/octet-stream, Content-Length: 960000`, flash the firmware and let a full wake cycle complete.
**Expected:** The 13.3" T133A01 e-paper displays the photo with correct colors and no random-color noise or corrupted tiles. Serial log shows no "Warning: expected 960000 bytes, received N" byte-count mismatch.
**Why human:** Requires physical e-paper display inspection and serial monitor review. Visual correctness of a 6-color e-paper render cannot be verified programmatically.

*Note: Both tests are documented as completed in 10-02-SUMMARY.md (hardware verification performed 2026-06-28 by the executing agent). The outstanding status here reflects that a verifier cannot independently confirm physical device output without re-running hardware tests.*

---

## Gaps Summary

No code gaps found. All automated must-haves verified:

- `convert_to_binary_in_memory()` exists, is substantive (matches legacy encoder byte-for-byte), and is wired into both serve functions
- Both `/download` paths return `application/octet-stream` with `Content-Length: 960000`
- Firmware has all four optimizations correctly wired: boot delay gate, CPU 80 MHz + TX power set before WiFi, binary `readBytes` loop replacing hex decode, GPIO isolation before deep sleep
- `strtol`/`String hexBuffer` fully removed (hex decode path eliminated)
- `rtc_gpio_isolate` calls correctly positioned after `WiFi.mode(WIFI_OFF)` and before `esp_deep_sleep_start()`
- Full test suite: 61 tests pass, 0 failures, no regressions
- TX power deviation from plan (8.5 dBm → 11 dBm) is a legitimate hardware-tested fix, not a gap

The two human verification items (BATT-05, BATT-06) are behavioral — they verify on-device timing and visual render correctness. The 10-02-SUMMARY.md records them as hardware-verified by the executing agent on 2026-06-28.

---

_Verified: 2026-06-28_
_Verifier: Claude (gsd-verifier)_
