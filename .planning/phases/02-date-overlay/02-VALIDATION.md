---
phase: 2
slug: date-overlay
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no test dir yet — Wave 0 installs) |
| **Config file** | none — Wave 0 creates `tests/conftest.py` |
| **Quick run command** | `pytest tests/test_date_overlay.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_date_overlay.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-W0-01 | 01 | 0 | DO-01 | unit | `pytest tests/test_date_overlay.py::test_parse_exif_date -x` | ❌ W0 | ⬜ pending |
| 2-W0-02 | 01 | 0 | DO-01 | unit | `pytest tests/test_date_overlay.py::test_parse_immich_date -x` | ❌ W0 | ⬜ pending |
| 2-W0-03 | 01 | 0 | DO-01 | unit | `pytest tests/test_date_overlay.py::test_parse_none -x` | ❌ W0 | ⬜ pending |
| 2-W0-04 | 01 | 0 | DO-02 | unit | `pytest tests/test_date_overlay.py::test_draw_overlay_renders -x` | ❌ W0 | ⬜ pending |
| 2-W0-05 | 01 | 0 | DO-03 | unit | `pytest tests/test_date_overlay.py::test_overlay_disabled -x` | ❌ W0 | ⬜ pending |
| 2-W0-06 | 01 | 0 | DO-03 | unit | `pytest tests/test_date_overlay.py::test_overlay_no_date -x` | ❌ W0 | ⬜ pending |
| 2-W0-07 | 01 | 0 | DO-04 | unit | `pytest tests/test_date_overlay.py::test_position_topleft -x` | ❌ W0 | ⬜ pending |
| 2-W0-08 | 01 | 0 | DO-04 | unit | `pytest tests/test_date_overlay.py::test_position_bottomright -x` | ❌ W0 | ⬜ pending |
| 2-W0-09 | 01 | 0 | DO-05 | unit | `pytest tests/test_date_overlay.py::test_default_config -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/test_date_overlay.py` — stubs for DO-01 through DO-05
- [ ] `tests/conftest.py` — shared fixtures (minimal synthetic PIL images)
- [ ] `pip install pytest` — if not present in environment

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Overlay visually renders at correct position on e-paper display | DO-04 | Physical display required | Enable overlay, view on device, confirm position matches config |
| Settings UI toggle persists correctly across page reload | DO-05 | Browser interaction | Set position to `topLeft`, save, reload page, confirm `topLeft` selected |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
