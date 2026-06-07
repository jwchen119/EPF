---
phase: 9
slug: blurred-background-behind-image-when-using-fit-width-or-fit-height-modes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest.ini or pyproject.toml (check project root) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | blur-bg | unit | `python -m pytest tests/ -k "blur" -x -q` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 1 | fit-width blur | unit | `python -m pytest tests/ -k "fit_width_blur" -x -q` | ❌ W0 | ⬜ pending |
| 9-01-03 | 01 | 1 | fit-height blur | unit | `python -m pytest tests/ -k "fit_height_blur" -x -q` | ❌ W0 | ⬜ pending |
| 9-01-04 | 01 | 2 | cython sync | integration | `python -m pytest tests/ -k "cpy" -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_blur_background.py` — stubs for blur background behavior in fit-width and fit-height modes
- [ ] Verify existing `tests/` infrastructure covers image processing tests

*If existing test infrastructure covers all requirements, Wave 0 only adds new stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual blur quality | blur-bg | Subjective visual check | Load image in fit-width mode, verify background is blurred and sharp image overlaid |
| Cython production path | cython-sync | Requires compiled .so | Build Cython extension and verify same blur result as fallback |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
