---
phase: 10-battery-optimization
plan: "01"
subsystem: server
tags: [binary-transport, battery-optimization, tdd, octet-stream]
dependency_graph:
  requires: []
  provides: [binary-image-download]
  affects: [app.py, tests/test_battery_optimization.py]
tech_stack:
  added: []
  patterns: [TDD RED-GREEN, BytesIO binary transport, send_file octet-stream]
key_files:
  created:
    - tests/test_battery_optimization.py
  modified:
    - app.py
decisions:
  - convert_to_binary_in_memory() inserted immediately after convert_to_c_code_in_memory so legacy encoder stays in place for BATT-02 nibble parity test
  - serve_local_image download_name changed from image_<stem>.c to image_<stem>.bin
  - serve_immich_image download_name changed from image_<asset_id>.c to image_<asset_id>.bin
  - No X-Image-Format header added in this plan (deferred to 10-02 for firmware-side verification)
metrics:
  duration: "~2 minutes"
  completed: "2026-06-24"
  tasks_completed: 2
  files_modified: 2
---

# Phase 10 Plan 01: Binary Image Transport Summary

Raw binary e-paper frame transport replacing hex-CSV text encoding: `convert_to_binary_in_memory()` in app.py returns a 960000-byte `BytesIO`, both serve functions now respond with `application/octet-stream` and `Content-Length: 960000`, cutting WiFi payload from ~2.8 MB to ~940 KB per wake cycle.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TDD RED — BATT-01..BATT-04 contract tests | f85c1c2 | tests/test_battery_optimization.py |
| 2 | GREEN — convert_to_binary_in_memory() + binary /download responses | b595755 | app.py |

## What Was Built

### convert_to_binary_in_memory() (app.py, after line 638)

New function that reuses `depalette_image()` and the same `nibble_map` as the legacy encoder, but writes `bytes()` directly to a `BytesIO` instead of hex-CSV ASCII. Output is byte-identical to parsing the legacy text output (verified by BATT-02 nibble parity test).

### serve_local_image() — binary response

Changed the final two lines from:
```python
c_code = convert_to_c_code_in_memory(Image.open(processed_image))
return send_file(c_code, mimetype='text/plain', as_attachment=True, download_name=f'image_{stem}.c')
```
to `convert_to_binary_in_memory()` with `mimetype='application/octet-stream'` and `download_name=f'image_{stem}.bin'`.

### serve_immich_image() — binary response

Same change: `convert_to_binary_in_memory()`, `application/octet-stream`, `image_{asset_id}.bin`.

### Legacy encoder retained

`convert_to_c_code_in_memory()` is kept in place so the BATT-02 parity test can compare byte-for-byte against it.

## Contract Tests (BATT-01..BATT-04)

| ID | Test | Result |
|----|------|--------|
| BATT-01 | `test_binary_output_length` — 960000 bytes for 1200x1600 | PASS |
| BATT-02 | `test_binary_nibble_parity` — bytes identical to legacy encoder | PASS |
| BATT-03 | `test_download_mimetype` — GET /download returns application/octet-stream | PASS |
| BATT-04 | `test_download_content_length` — Content-Length == '960000' | PASS |

Full suite: 61/61 tests pass, no regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- tests/test_battery_optimization.py: FOUND
- app.py contains `def convert_to_binary_in_memory`: FOUND
- app.py contains `application/octet-stream` (2 occurrences): FOUND
- app.py still contains `def convert_to_c_code_in_memory`: FOUND
- Commit f85c1c2: FOUND
- Commit b595755: FOUND
