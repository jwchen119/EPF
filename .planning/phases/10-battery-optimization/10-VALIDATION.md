---
phase: 10
slug: battery-optimization
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-24
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

**Single phase test file:** `tests/test_battery_optimization.py` holds all four automatable
contract tests (BATT-01..BATT-04). It is created in Wave 0 (RED) by plan 10-01 Task 1.
Firmware behaviors (BATT-05, BATT-06) are not pytest-testable and are covered by the
human-verify checkpoint in plan 10-02 Task 3.

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01 Task 1 | 01 | 1 | BATT-01..04 (RED) | unit/integration | `python -m pytest tests/test_battery_optimization.py -q` (expect RED) | ✅ created here | ⬜ pending |
| 10-01 Task 2 | 01 | 1 | BATT-01..04 (GREEN) | unit/integration | `python -m pytest tests/test_battery_optimization.py -x -q && python -m pytest tests/ -q` | ✅ tests/test_battery_optimization.py | ⬜ pending |
| 10-02 Task 1 | 02 | 2 | BATT-05 (boot delay + CPU/TX) | firmware grep + regression | `grep ... epd7in3e/* && python -m pytest tests/ -x -q` | ✅ tests/ (regression) | ⬜ pending |
| 10-02 Task 2 | 02 | 2 | BATT-06 (binary decode + GPIO) | firmware grep + regression | `grep ... epd7in3e/* && python -m pytest tests/ -x -q` | ✅ tests/ (regression) | ⬜ pending |
| 10-02 Task 3 | 02 | 2 | BATT-05, BATT-06 | manual (device) | MANUAL — flash + serial + e-paper render | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Note:** 10-02 Tasks 1 and 2 modify only firmware (`epd7in3e/*`) which is not pytest-testable,
so their `<automated>` verify is a firmware grep assertion followed by a `python -m pytest tests/ -x -q`
regression sample to catch any incidental edits to the Python test suite. This keeps every
wave-2 auto task on the pytest sampling cadence rather than deferring all regression detection
to the human checkpoint.

---

## Wave 0 Requirements

- [ ] `tests/test_battery_optimization.py` — four contract tests for binary image transport,
      server-side (BATT-01 length, BATT-02 nibble parity, BATT-03 mimetype, BATT-04 Content-Length).
      Created RED by plan 10-01 Task 1; made GREEN by plan 10-01 Task 2.
- [ ] No new conftest fixtures required — existing `tests/conftest.py` fixtures
      (`blank_rgb_image`/`large_rgb_image`, test_client pattern) suffice.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ESP32-S3 deep sleep current draw | BATT-05 (power reduction) | Requires hardware measurement | Measure current with USB ammeter during deep sleep before and after changes |
| Binary image display quality | BATT-06 (correct rendering) | Requires physical device | Display test image and verify no corruption or color shift |
| Boot-delay gate on timer wakeup | BATT-05 | Requires physical device | Cold boot keeps 3 s delay; timer/EXT1 wakeup skips it (see 10-02 Task 3) |
| WiFi TX power reduction | BATT-05 (connectivity maintained) | Requires RF environment | Verify WiFi still connects reliably at reduced TX power |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (single file: tests/test_battery_optimization.py)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
