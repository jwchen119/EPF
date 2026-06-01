# Phase 6: Text Customization — Colors, Styles, and Border Mode - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 06-text-customization-colors-styles-and-border-mode
**Areas discussed:** Color picker approach, Border mode meaning, Defaults and backward compat, Border thickness, Font size

---

## Color picker approach

| Option | Description | Selected |
|--------|-------------|----------|
| 6-color dropdown | A `<select>` showing 6 e-paper palette names: Black, White, Yellow, Red, Blue, Green. Stays consistent with all other controls, no surprises from dithering. | ✓ |
| Native color picker | `<input type="color">` — user can pick any RGB, display snaps to nearest of 6 palette colors. More flexible but potentially confusing. | |

**User's choice:** 6-color dropdown  
**Notes:** The display can only show these 6 colors anyway; free hex input would silently snap to the nearest palette color.

---

## All 6 colors selectable?

| Option | Description | Selected |
|--------|-------------|----------|
| All 6 palette colors | Black, White, Yellow, Red, Blue, Green — full freedom, no validation. | ✓ |
| Exclude same-color combos | Validate text ≠ background. Adds logic. | |

**User's choice:** All 6, no validation.

---

## Border mode meaning

| Option | Description | Selected |
|--------|-------------|----------|
| Outline-only mode (no filled background) | Text has a colored stroke/outline; no background rectangle. Useful when you don't want a box blocking the photo. | ✓ |
| Bordered rectangle (stroke around box) | Keep filled background AND add a border stroke around it. | |
| Shape style option (rectangle vs pill) | Choose between sharp rectangle and rounded pill. | |

**User's choice:** Outline-only mode (no filled background)

---

## Border color: separate key or reuse text color?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate border_color key | Independent text fill + stroke color. Enables white text + black outline. Matches STATE.md intent. | ✓ |
| Reuse text color for stroke | Simpler, fewer keys, but limits contrast options. | |

**User's choice:** Separate `overlay_border_color` config key.

---

## Border mode activation in UI

| Option | Description | Selected |
|--------|-------------|----------|
| Style dropdown (Background / Outline only) | Consistent with select pattern; avoids unchecked-field HTML POST issue. | ✓ |
| Checkbox for border mode | Simpler but inconsistent with Phase 2 decision (select on/off preferred). | |

**User's choice:** `<select>` with two options: "Background (filled)" and "Outline only".

---

## Border/stroke thickness

| Option | Description | Selected |
|--------|-------------|----------|
| Preset dropdown (thin/medium/thick) | Maps to fixed px values. Simple. | |
| Numeric slider (1–5 px) | Range slider like contrast/enhancement sliders. More flexible. | ✓ |

**User's choice:** Slider, 1–5 px.  
**Notes:** Default 2 px. Applies only in outline mode.

---

## Defaults and backward compat

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve existing look | Default: style=background, bg=black, text=white, border=white, stroke=2, font=26. Zero visual change on upgrade. | ✓ |
| Start fresh with recommended settings | New color combination on upgrade — more surprising. | |

**User's choice:** Preserve existing look.

---

## Font size

| Option | Description | Selected |
|--------|-------------|----------|
| Slider (16–48 px) | Matches contrast/enhancement slider pattern. 26px is current hardcoded default. | ✓ |
| Preset dropdown (Small/Medium/Large) | Simpler, fewer choices. | |

**User's choice:** Slider, 16–48 px. Default: 26 px (preserves current hardcoded value).

---

## Claude's Discretion

- PIL stroke implementation (`draw.text(stroke_width=N, stroke_fill=...)`)
- Where the 6-color name-to-RGB dict lives in app.py
- Whether new config keys go under existing `immich` section or new `overlay` subsection
- UI organization (new controls appended to existing "Date Overlay" card)
- Whether to show/hide irrelevant controls per mode (no JS required per Phase 6 scope)

## Deferred Ideas

None — discussion stayed within phase scope.
