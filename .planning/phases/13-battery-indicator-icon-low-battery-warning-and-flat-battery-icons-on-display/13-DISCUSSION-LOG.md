# Phase 13: Battery Indicator Icon — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display
**Areas discussed:** Icon appearance, Display trigger, Position & sizing, Settings & toggles

---

## Icon Appearance

### Q1: What should the battery icon look like?

| Option | Description | Selected |
|--------|-------------|----------|
| PIL-drawn battery shape | Classic battery outline (rectangle + nub) with fill bar showing charge level — drawn with PIL rectangles/lines. No external files. | ✓ |
| Text percentage only | Just '83%' or 'LOW' text drawn like the date overlay — reuses text rendering path. | |
| Distinct state icons | 4 distinct shapes: full, medium, low, flat/empty. More expressive but more code. | |

**User's choice:** PIL-drawn battery shape (Recommended)
**Notes:** Consistent with the "icon" framing in the phase name.

---

### Q2: Should the fill bar show actual charge level or discrete states?

| Option | Description | Selected |
|--------|-------------|----------|
| Proportional fill | Fill width = battery %. Continuous feedback. | |
| Three steps: full / low / empty | Bar shows full, partial (low warning), or empty — three discrete states. | ✓ |
| Just outline — filled or empty only | Binary: either fully filled or completely empty. | |

**User's choice:** Three steps: full / low / empty
**Notes:** Chosen over continuous fill for simplicity. The "flat battery" icon (empty state) is the key deliverable per the phase name.

---

### Q3: What color should the battery icon use?

| Option | Description | Selected |
|--------|-------------|----------|
| White icon | Same as default date text — visible on most photos, consistent with overlays. | ✓ |
| Red for low/empty, white otherwise | Color changes by state: red when warning/flat, white when OK. | |
| Inherit from date overlay text color | Uses whatever overlay_text_color is configured — no new color config. | |

**User's choice:** White icon (Recommended)
**Notes:** Single color keeps implementation simple. Red was considered but rejected in favor of simplicity.

---

## Display Trigger

### Q4: When should the battery icon appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Always — every image refresh | Always show in corner; disappears when on USB. | |
| Warning-only — below threshold | Icon only appears below a threshold. | ✓ |
| Never on USB, always on battery | Same as 'always' but explicitly hides when batteryCap=0. | |

**User's choice:** Warning-only — below threshold
**Notes:** Clean approach — icon only appears when user needs to know about battery state.

---

### Q5: Which states trigger the icon?

| Option | Description | Selected |
|--------|-------------|----------|
| Low + empty only | Icon appears for both 'low' and 'empty' states. Full = no icon. | ✓ |
| Empty only | Icon only appears when completely flat (e.g., below 5%). | |

**User's choice:** Low + empty only (Recommended)

---

### Q6: What percentage thresholds?

| Option | Description | Selected |
|--------|-------------|----------|
| Low ≤ 20%, empty ≤ 5% | Standard phone-style thresholds. | ✓ |
| Low ≤ 30%, empty ≤ 10% | More conservative / earlier warning. | |
| Configurable in settings | User sets thresholds via sliders. | |

**User's choice:** Low ≤ 20%, empty ≤ 5% (Recommended)
**Notes:** Hardcoded thresholds — no settings UI needed for this.

---

## Position & Sizing

### Q7: Where should the icon appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed top-right corner | Always top-right — no config needed. | |
| Configurable — same POSITIONS system | User picks corner/edge in settings, like date overlay. | ✓ |
| Same corner as date overlay, stacked | Adjacent to date text in configured corner. | |

**User's choice:** Configurable — same POSITIONS system as date overlay
**Notes:** Consistent with the settings-driven approach used throughout the project.

---

### Q8: How large should the icon be?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed small size — ~24×48px | Compact, always the same regardless of font size. | |
| Proportional to font size — match date text height | Icon height = overlay_font_size; pairs visually with text overlay. | ✓ |
| Configurable size | User sets icon size in settings. | |

**User's choice:** Proportional to font size — match date text height
**Notes:** Derives from `overlay_font_size` (default 26px). No new config key needed for size.

---

## Settings & Toggles

### Q9: Should the battery icon be toggleable?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — enabled by default, user can disable | Toggle in settings, default on. Consistent with date/geo overlays. | ✓ |
| Always on — no toggle needed | Warning-only means it rarely shows. | |
| Disabled by default, user can enable | Opt-in. | |

**User's choice:** Yes — enabled by default, user can disable (Recommended)

---

### Q10: Where in settings UI?

| Option | Description | Selected |
|--------|-------------|----------|
| New 'Battery Indicator' card/section | Dedicated card with toggle and position dropdown. | ✓ |
| Inside existing Date Overlay card | Fewer sections but mixes concerns. | |
| In the Battery Consumption card | Minimal new UI surface but wrong grouping. | |

**User's choice:** New 'Battery Indicator' card/section (Recommended)

---

## Claude's Discretion

- Exact PIL drawing sequence for battery outline + nub + fill (rectangle calls, line vs rect for nub).
- Padding/margin from display edge (apply `overlay_margin_h`/`overlay_margin_v` or fixed 10px).
- Test strategy for `draw_battery_indicator()` function.

## Deferred Ideas

None — discussion stayed within phase scope.
