# Phase 6: Text Customization — Colors, Styles, and Border Mode - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the timestamp overlay's visual appearance configurable: background color, text color, overlay style (filled background vs outline-only), stroke color for outline mode, stroke thickness (outline mode only), and font size. All settings exposed in the web Configuration UI and persisted in config.yaml.

The rendering logic lives in `draw_date_overlay()` at `app.py:95`. All new parameters are added to `DEFAULT_CONFIG`, read by `update_app_config()`, and wired into the HTML form + POST handler following the established Phase 2 config pattern.

</domain>

<decisions>
## Implementation Decisions

### Color Selection
- **D-01:** Colors are selected from a **6-color dropdown `<select>`** matching the T133A01 e-paper palette: Black, White, Yellow, Red, Blue, Green. No free hex input — the display can only render these 6 colors anyway, so arbitrary hex would silently snap to the nearest palette color.
- **D-02:** All 6 palette colors are available for both background color and text color. No validation enforcing text ≠ background — if the user picks white-on-white, the overlay becomes invisible; that is their choice.
- **D-03:** Palette RGB values (from `app.py:196-201`):
  - Black: `(0, 0, 0)`
  - White: `(255, 255, 255)`
  - Yellow: `(255, 216, 0)`
  - Red: `(229, 57, 53)`
  - Blue: `(0, 76, 255)`
  - Green: `(29, 185, 84)`

### Overlay Style
- **D-04:** A **`<select>` dropdown** with two options controls the overlay style:
  - `"background"` — solid filled rectangle behind text (current behavior)
  - `"outline"` — no filled background; text rendered with a colored stroke/outline around each letter
- **D-05:** Using a `<select>` (not a checkbox) follows the Phase 2 pattern (STATE.md key decision: select on/off avoids unchecked-field omission in HTML POST).

### Colors per Mode
- **D-06:** In `"background"` style: `overlay_bg_color` (background rectangle fill) + `overlay_text_color` (text fill) are both active.
- **D-07:** In `"outline"` style: `overlay_text_color` (text fill) + `overlay_border_color` (stroke) are active. `overlay_bg_color` is ignored (no rectangle drawn).
- **D-08:** `overlay_border_color` is a **separate config key** (not reused from text color). Allows white text + black outline or black text + white outline — maximum contrast in either mode.

### Stroke Thickness (Outline Mode Only)
- **D-09:** `overlay_stroke_width` is a **slider from 1–5 px**, matching the contrast/enhancement slider pattern in settings.html.
- **D-10:** Thickness applies **only in outline mode**. In background mode, there is no border stroke, so the slider is not relevant.
- **D-11:** Default: **2 px**.

### Font Size
- **D-12:** `overlay_font_size` is a **slider from 16–48 px**, matching the slider pattern.
- **D-13:** Default: **26 px** (preserves current hardcoded value at `app.py:371`).

### Defaults and Backward Compatibility
- **D-14:** New config key defaults preserve the exact current visual behavior — existing deployments that upgrade see **zero visual change** until they configure it:
  - `overlay_style`: `"background"`
  - `overlay_bg_color`: `"black"`
  - `overlay_text_color`: `"white"`
  - `overlay_border_color`: `"white"` (only relevant in outline mode; default chosen to match text color)
  - `overlay_stroke_width`: `2`
  - `overlay_font_size`: `26`
- **D-15:** All new keys use `.get()` fallback in `update_app_config()` (same pattern as D-02 in Phase 2 / STATE.md: `.get() fallback for backward compat with old config.yaml`).

### Claude's Discretion
- PIL text stroke implementation: use `draw.text(..., stroke_width=N, stroke_fill=(R,G,B,255))` (Pillow ≥ 8.0) for outline mode.
- Where the 6-color name-to-RGB mapping lives: a small dict in `app.py` near the existing `palette` list at line 196, or inline in `draw_date_overlay()`.
- Whether to add new config keys under `immich` (existing section) or a new `overlay` subsection — consistency with Phase 2 pattern favors `immich`.
- UI organization: new controls appended to the existing "Date Overlay" card in settings.html rather than a new card.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core rendering function (primary target)
- `app.py:95-148` — `draw_date_overlay()`: current implementation with hardcoded colors and hardcoded stroke-free rendering. All new parameters added here.
- `app.py:196-201` — T133A01 palette RGB values (authoritative color list for the dropdown).
- `app.py:366-374` — Call site in `scale_img_in_memory()`: font loading + `draw_date_overlay()` call. Font size will be parameterized here.

### Config pattern (established in Phase 2)
- `app.py:43-56` — `DEFAULT_CONFIG['immich']` section: all new keys added here with defaults.
- `app.py:505-544` — `update_app_config()`: reads new keys into module globals.
- `app.py:649-660` — POST handler in `settings()`: reads form fields for date overlay.

### Settings UI
- `templates/settings.html:460-485` — Existing "Date Overlay" card with enable/position controls. New controls appended to this card.
- `templates/settings.html:121-145` — Existing slider pattern (`input[type="range"]` + `.slider-container`) to replicate for font size and stroke width.

### Prior phase decisions
- Phase 2 CONTEXT.md (`.planning/phases/02-date-overlay/02-CONTEXT.md`) — D-02: select on/off pattern; D-05: date_overlay_position default; Claude's Discretion on visual style (now being made configurable in Phase 6).
- STATE.md key decision: "date_overlay_enabled uses select on/off not checkbox to avoid unchecked-field omission in HTML POST" — applies to `overlay_style` dropdown too.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `draw_date_overlay()` (`app.py:95`): accepts `output_img`, `text`, `font`, `position_str`, `padding`, `rotation`. Will receive new params: `bg_color`, `text_color`, `style`, `border_color`, `stroke_width`.
- `POSITIONS` dict (`app.py:81-91`): 9-position anchor lookup — unchanged by Phase 6.
- Slider CSS + HTML pattern (`settings.html:121-145`): `input[type="range"]` with `.slider-container` class — replicate for font size and stroke width sliders.

### Established Patterns
- **6 hardcoded values to parameterize:**
  - Background fill: `(0, 0, 0, 255)` at `app.py:135` → `overlay_bg_color`
  - Text fill: `(255, 255, 255, 255)` at `app.py:136` → `overlay_text_color`
  - Font size: `26` at `app.py:371` → `overlay_font_size`
  - Style: implicit "background" → `overlay_style`
  - Border color: none currently → `overlay_border_color`
  - Stroke width: none currently → `overlay_stroke_width`
- **PIL stroke API:** `ImageDraw.Draw.text(..., stroke_width=N, stroke_fill=color)` — available since Pillow 8.0; no rectangle drawn in outline mode (skip `draw.rectangle()`).

### Integration Points
- `scale_img_in_memory()` (`app.py:286`): reads `date_overlay_enabled` and `date_overlay_position` globals. Will also read `overlay_style`, `overlay_bg_color`, `overlay_text_color`, `overlay_border_color`, `overlay_stroke_width`, `overlay_font_size` globals.
- `update_app_config()` (`app.py:505`): new globals must be declared here and in the `global` statement at the top of the function.

</code_context>

<specifics>
## Specific Ideas

- The color name-to-RGBA mapping must use the exact palette RGB values from `app.py:196-201`, not approximations.
- Pillow `stroke_width` draws the stroke as an outward expansion. At 2px stroke on a 26px font, the stroke is clearly visible without overwhelming the text.
- The `overlay_bg_color` control should be **hidden or greyed out** in outline mode, and `overlay_border_color` + `overlay_stroke_width` controls should only be **relevant** in outline mode — but the simplest implementation just always shows all controls and lets the user understand which apply per mode (no JS show/hide required).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-text-customization-colors-styles-and-border-mode*
*Context gathered: 2026-05-29*
