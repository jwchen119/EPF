---
phase: 6
slug: text-customization-colors-styles-and-border-mode
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — test discovery defaults from project root |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TC-01 | 01 | 0 | D-03 | unit | `pytest tests/test_overlay_customization.py::test_overlay_colors_dict -x` | ❌ W0 | ⬜ pending |
| TC-02 | 01 | 0 | D-14 | unit | `pytest tests/test_overlay_customization.py::test_default_config_new_keys -x` | ❌ W0 | ⬜ pending |
| TC-03 | 01 | 0 | D-06 | unit | `pytest tests/test_overlay_customization.py::test_background_mode_uses_bg_color -x` | ❌ W0 | ⬜ pending |
| TC-04 | 01 | 0 | D-07 | unit | `pytest tests/test_overlay_customization.py::test_outline_mode_no_rect -x` | ❌ W0 | ⬜ pending |
| TC-05 | 01 | 0 | D-08 | unit | `pytest tests/test_overlay_customization.py::test_outline_mode_border_color -x` | ❌ W0 | ⬜ pending |
| TC-06 | 01 | 0 | D-14 | unit | `pytest tests/test_overlay_customization.py::test_default_params_match_current -x` | ❌ W0 | ⬜ pending |
| TC-07 | 01 | 0 | D-09 | unit | `pytest tests/test_overlay_customization.py::test_stroke_width_zero -x` | ❌ W0 | ⬜ pending |
| TC-08 | 01 | 0 | D-15 | integration | `pytest tests/test_overlay_customization.py::test_update_config_new_keys -x` | ❌ W0 | ⬜ pending |
| TC-09 | 01 | 0 | D-12 | integration | `pytest tests/test_overlay_customization.py::test_post_handler_font_size_int -x` | ❌ W0 | ⬜ pending |
| TC-10 | — | — | Phase 2 regression | regression | `.venv/bin/python -m pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_overlay_customization.py` — stubs for TC-01 through TC-09

*Existing infrastructure covers TC-10; `tests/conftest.py` fixtures reused.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Overlay visually invisible when text color = bg color | D-02 | Pixel-level color identity requires visual inspection or precise pixel sampling | Set both dropdowns to same color, trigger a render, confirm overlay is not visually distinct |
| Stroke visible at all 6 palette colors in outline mode | D-07/D-08 | Color contrast varies — automated test checks pixel presence, visual test confirms readability | Select each color combo for outline, render, confirm stroke contrast is as expected |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
