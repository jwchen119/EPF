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
