# Phase 11: Margin for text on image — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 11 — margin-for-text-on-image
**Areas discussed:** Margin range & default, Uniform vs directional, Center position behavior, Implementation approach

---

## Margin range & default

### Slider range

| Option | Description | Selected |
|--------|-------------|----------|
| 0–200 px | Covers all realistic passe-partout widths on a 1200×1600 display. Step=10. | ✓ |
| 0–150 px | Tighter range, step=5 or 10. | |
| 0–300 px | Very wide range; most users won't go past 150 px. | |

**User's choice:** 0–200 px (step=10)
**Notes:** Recommended default accepted without modification.

### Default value

| Option | Description | Selected |
|--------|-------------|----------|
| 0 px | Zero is backward-compatible — existing deployments see no visual change. | ✓ |
| 50 px | Useful out-of-the-box default but changes existing behavior. | |

**User's choice:** 0 px
**Notes:** Backward-compatibility is important — default 0 px.

---

## Uniform vs directional

| Option | Description | Selected |
|--------|-------------|----------|
| Single uniform value | One slider, all sides equal. Simple UI. | |
| Two values: horizontal + vertical | Separate sliders for left/right and top/bottom. | ✓ |
| Four values: per side | Individual sliders for top, right, bottom, left. | |

**User's choice:** Two values — `overlay_margin_h` (horizontal) and `overlay_margin_v` (vertical)
**Notes:** Covers asymmetric passe-partout mats (portrait vs landscape frames) without cluttering UI.

---

## Center position behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Silently ignore margin for center | Center always at geometric center; no margin effect. | ✓ |
| Show a UI note | Static text explaining center ignores margin. | |

**User's choice:** Silently ignore
**Notes:** No UI note needed — behavior is self-evident.

---

## Implementation approach

| Option | Description | Selected |
|--------|-------------|----------|
| Separate: margin added on top of padding | POSITIONS lambdas get `mh, mv` args; padding=6 unchanged. | ✓ |
| Replace: margin becomes the new edge offset | `p` parameter absorbs both concerns. | |

**User's choice:** Separate — margin is additive to existing padding=6
**Notes:** Keeps `padding` (text box breathing room) conceptually distinct from `margin` (display-edge inset). Cleanest API.

---

## Claude's Discretion

- POSITIONS lambda signature extension: `(w, h, tw, th, p, mh, mv)` across all 9 lambdas
- `center` lambda ignores `mh` and `mv`; axis-center lambdas use only the relevant axis
- `draw_date_overlay()` receives `margin_h=0, margin_v=0` as backward-compatible kwargs

## Deferred Ideas

None raised during discussion.
