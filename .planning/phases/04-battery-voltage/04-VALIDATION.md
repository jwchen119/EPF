---
phase: 4
slug: battery-voltage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual hardware test + Serial Monitor verification (no unit test framework for `.ino` firmware) |
| **Config file** | none |
| **Quick run command** | `arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 epd7in3e/` |
| **Full suite command** | Flash to device, observe Serial Monitor output |
| **Estimated runtime** | ~30 seconds (compile), ~5 minutes (flash + observe) |

---

## Sampling Rate

- **After every task commit:** Compile with zero errors/warnings
- **After every plan wave:** Flash to device and run Serial Monitor smoke test
- **Before `/gsd:verify-work`:** All 5 manual hardware checks pass
- **Max feedback latency:** 30 seconds (compile gate)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | BV-01 | compile | `arduino-cli compile ...` | ✅ | ⬜ pending |
| 4-01-02 | 01 | 1 | BV-01 | compile | `arduino-cli compile ...` | ✅ | ⬜ pending |
| 4-02-01 | 02 | 1 | BV-02, BV-03 | compile | `arduino-cli compile ...` | ✅ | ⬜ pending |
| 4-02-02 | 02 | 1 | BV-04 | compile | `arduino-cli compile ...` | ✅ | ⬜ pending |
| 4-02-03 | 02 | 1 | BV-05 | compile | `arduino-cli compile ...` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Verification checklist document for hardware testing (optional — no automated unit tests possible for `.ino` firmware)

*All verification is manual hardware testing with Serial Monitor — no test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Battery voltage read returns 3400–4200 mV on charged battery | BV-01 | Requires hardware with battery connected | Flash → Serial Monitor shows `Battery voltage: XXXX mV` |
| ADC reads ~0 mV on USB-only (no battery) | BV-01 | Requires hardware without battery | Flash USB-only → Serial Monitor shows `Battery voltage: 0 mV` |
| `batteryCap` header = 0 on USB-only, mV value on battery | BV-02, BV-04 | Requires HTTP traffic capture | `curl -v <server>/download` or check server settings UI `last_battery_voltage` |
| Deep sleep entered when on battery | BV-03 | Requires hardware observation | Connect battery → device deep sleeps after display refresh |
| Idle loop (wait + restart) when USB-only | BV-03 | Requires hardware observation | USB-only → device stays awake, refreshes after `sleepDuration` seconds |
| Low-battery guard: device sleeps 24h if voltage < 3050 mV | BV-05 | Requires bench power supply or threshold mock | Temporarily lower `MIN_BATTERY_VOLTAGE` to trigger, confirm 24h sleep |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` compile verify (zero errors/warnings)
- [ ] Sampling continuity: compile after every task
- [ ] Wave 0 complete (checklist doc created if desired)
- [ ] No watch-mode flags
- [ ] All 5 manual hardware checks pass
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
