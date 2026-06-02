---
phase: 8
slug: auth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-02
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_auth.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_auth.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 0 | AUTH-01..08 | unit | `pytest tests/test_auth.py -v` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 1 | AUTH-01..05 | unit | `pytest tests/test_auth.py -v` | ✅ W0 | ⬜ pending |
| 8-02-02 | 02 | 1 | AUTH-06..08 | unit | `pytest tests/test_auth.py -v` | ✅ W0 | ⬜ pending |
| 8-03-01 | 03 | 2 | AUTH-09..10 | manual | Browser auth dialog test | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auth.py` — 8 failing contract tests (AUTH-01..AUTH-08)
- [ ] No new conftest.py fixtures needed — existing pytest infrastructure sufficient

*Existing infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser native auth dialog appears | AUTH-09 | Requires a browser to verify WWW-Authenticate triggers dialog | 1. Start app with APP_PASSWORD=test. 2. Open http://localhost:5000/ in browser. 3. Verify native dialog appears. |
| Arduino firmware authenticates to server | AUTH-10 | Requires physical hardware (XIAO ESP32-S3) | 1. Flash firmware with APP_PASSWORD constant set. 2. Ensure server has APP_PASSWORD env var. 3. Verify device fetches image successfully. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
