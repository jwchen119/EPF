---
phase: 10
slug: battery-optimization
status: draft
nyquist_compliant: false
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
| **Config file** | pytest.ini or pyproject.toml |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | Binary transport | unit | `pytest tests/test_binary_transport.py -v` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | Boot delay gate | integration | `pytest tests/test_boot_delay.py -v` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 2 | CPU freq tuning | unit | `pytest tests/test_power_config.py -v` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 2 | TX power tuning | unit | `pytest tests/test_power_config.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_binary_transport.py` — stubs for binary image transport server side
- [ ] `tests/test_boot_delay.py` — stubs for wakeup-gated delay logic
- [ ] `tests/test_power_config.py` — stubs for CPU freq / TX power settings
- [ ] `tests/conftest.py` — shared fixtures if not already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ESP32-S3 deep sleep current draw | Power reduction | Requires hardware measurement | Measure current with USB ammeter during deep sleep before and after changes |
| Binary image display quality | Correct rendering | Requires physical device | Display test image and verify no corruption or color shift |
| WiFi TX power reduction | Connectivity maintained | Requires RF environment | Verify WiFi still connects reliably at reduced TX power |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
