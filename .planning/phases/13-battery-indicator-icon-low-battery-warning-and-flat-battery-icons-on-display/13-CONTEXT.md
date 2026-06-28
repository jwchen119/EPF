# Phase 13: Battery Indicator Icon — Low Battery Warning and Flat Battery Icons on Display - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Render a battery warning icon on the e-paper display image (server-side, composited via PIL
onto the photo before binary encoding). The icon appears only when battery level is low or
empty (warning-only mode). When the server has no battery data (USB-only device, or no
`batteryCap` header yet received), no icon is shown.

This is purely a server-side change — no firmware changes required.

</domain>

<decisions>
## Implementation Decisions

### Icon Appearance
- **D-01:** Battery icon is drawn with PIL shapes — a classic battery outline (rectangle + small nub/terminal on one end) with a fill bar showing charge state. No external image files needed.
- **D-02:** Three discrete fill states based on battery percentage:
  - **Full** (> 20%): Icon does not appear (warning-only trigger)
  - **Low** (5% < battery ≤ 20%): Partially filled bar shown — battery outline with reduced fill
  - **Empty** (battery ≤ 5%): Completely empty battery outline (no fill) — the "flat battery" icon
- **D-03:** Icon color: white (RGBA `(255, 255, 255, 255)`) — consistent with default overlay text color. No color change by state.
- **D-04:** Icon is drawn with PIL `ImageDraw.rectangle()` and `ImageDraw.line()` — no text rendering needed for the icon itself.

### Display Trigger
- **D-05:** Icon is **warning-only** — it only appears when battery is below the low threshold. Normal battery level = no icon on display.
- **D-06:** Thresholds (hardcoded, not configurable):
  - Low warning: battery ≤ 20%
  - Flat/empty: battery ≤ 5%
- **D-07:** When `last_battery_voltage == 0` (USB-only or no data received yet), battery percentage is 0 — treat as "no battery data" and suppress the icon entirely (do not show a false "flat" warning for USB-powered devices). Check: `last_battery_voltage > 0` before drawing.

### Position
- **D-08:** Position is user-configurable via a dropdown in settings — uses the same `POSITIONS` system as the date overlay (keys: `topLeft`, `topRight`, `bottomLeft`, `bottomRight`, `topCenter`, `bottomCenter`, `centerLeft`, `centerRight`, `center`).
- **D-09:** Default position: `topRight`.
- **D-10:** The battery icon position is independent of the date overlay position — they can be placed in the same corner (may overlap) or different corners. No automatic collision avoidance.
- **D-11:** The battery icon respects the same `rotationAngle` as the date overlay, so `topRight` means the viewer's top-right regardless of display rotation. Use the same viewer-space coordinate transformation as `draw_date_overlay()`.

### Sizing
- **D-12:** Icon height is proportional to `overlay_font_size` (the existing config key, defaulting to 26px). Icon height = `overlay_font_size` px. Aspect ratio is 2:1 (width:height) for the battery body, plus a small nub (~20% of height wide, ~50% of height tall) on the right end.
  - Example at 26px font: battery body ≈ 52×26px, nub ≈ 5×13px
- **D-13:** A 2px stroke width for the battery outline (consistent with `overlay_stroke_width` default).

### Settings UI
- **D-14:** New "Battery Indicator" card in `settings.html` (separate from the existing Date Overlay and Battery Consumption cards).
- **D-15:** Card contains:
  - **Enable toggle** (select on/off, defaulting to `'on'`) — key: `battery_indicator_enabled`. Uses the `select` pattern established in Phase 2 (D-03) to avoid HTML POST unchecked-field omission.
  - **Position dropdown** — key: `battery_indicator_position`, same options as `date_overlay_position`, default `topRight`.
- **D-16:** Config keys added to `DEFAULT_CONFIG['immich']`:
  - `'battery_indicator_enabled': 'on'`
  - `'battery_indicator_position': 'topRight'`
- **D-17:** Both keys read via `.get()` with fallback in `update_app_config()` and POST handler — backward compat with old `config.yaml` without these keys.

### New Draw Function
- **D-18:** A new function `draw_battery_indicator(output_img, battery_pct, position_str, rotation, font_size, color)` added to `app.py`, analogous to `draw_date_overlay()`. Called from `scale_img_in_memory()` after the date overlay call.
- **D-19:** `draw_battery_indicator()` is a no-op (returns immediately) when:
  - `battery_indicator_enabled != 'on'`
  - `battery_pct > 20` (above low threshold)
  - `last_battery_voltage == 0` (USB/no data)

### Claude's Discretion
- Exact PIL drawing sequence for battery outline + nub + fill (rectangle calls, line vs rect for nub).
- Padding/margin from the display edge (apply same `overlay_margin_h`/`overlay_margin_v` globals, or use a fixed 10px inset — Claude decides).
- Whether to write unit tests for the battery draw function (should follow TDD pattern of prior phases).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing overlay infrastructure (primary pattern to follow)
- `app.py:222–320` — `draw_date_overlay()` — the pattern for `draw_battery_indicator()`. Follow the same viewer-space coordinate transformation and POSITIONS lookup.
- `app.py:577–616` — `scale_img_in_memory()` — where `draw_date_overlay()` is called; `draw_battery_indicator()` is called after it.
- `app.py:42–70` — `DEFAULT_CONFIG['immich']` — add new config keys here.
- `app.py:760–830` — `update_app_config()` — add `.get()` reads for new keys here.

### POSITIONS system (used for coordinate mapping)
- `app.py` — `POSITIONS` dict (near `draw_date_overlay`) — maps position strings to lambdas `(vw, vh, tw, th, p, mh, mv) → (x, y)`.

### Battery infrastructure (source of battery % data)
- `app.py:840–882` — `BATTERY_LEVELS` table and `calculate_battery_percentage()`.
- `app.py:386–387` — `last_battery_voltage` and `last_battery_update` globals — the server's live battery state.
- `app.py:892–910` — Where battery % is calculated for the `/` settings page response (pattern for reading battery in `scale_img_in_memory()`).

### Settings UI pattern
- `templates/settings.html:529–559` — Date Overlay card with select/slider patterns to replicate for Battery Indicator card.
- `templates/settings.html:366–371` — Existing Battery Consumption card (do NOT put battery indicator settings here — new card instead).

### Prior phase context (for config and toggle patterns)
- `.planning/phases/02-date-overlay/02-CONTEXT.md` — D-03: `select` on/off toggle pattern avoiding POST omission.
- `.planning/phases/06-text-customization-colors-styles-and-border-mode/06-CONTEXT.md` — D-05: select dropdown pattern; D-14: config defaults.
- `.planning/phases/11-margin-for-text-on-image-configurable-inset-margin-to-keep-text-visible-behind-passe-partout/11-CONTEXT.md` — margin system that battery icon may reuse.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `draw_date_overlay()` (`app.py:222`): Full PIL overlay drawing function with rotation-aware viewer-space coordinate mapping. `draw_battery_indicator()` mirrors this pattern exactly.
- `POSITIONS` dict (`app.py`, near line 222): Position→coordinate lambda system. Battery icon reuses this directly.
- `calculate_battery_percentage()` (`app.py:866`): Already returns float 0–100. Battery icon reads `last_battery_voltage` then calls this.
- `overlay_font_size` global (`app.py:333`): Already loaded into module scope. Battery icon derives its height from this value.

### Established Patterns
- Config keys: `DEFAULT_CONFIG['immich']` → `update_app_config()` `.get()` reads → POST handler reads. All three sites need new keys.
- Toggle pattern: `select` with `on`/`off` values (not `<input type="checkbox">`). Avoids HTML POST omission bug.
- `.get()` fallback everywhere for backward compat with old `config.yaml`.

### Integration Points
- `scale_img_in_memory()` after `draw_date_overlay()` call — add `draw_battery_indicator()` call here.
- `settings.html` — new "Battery Indicator" card between Date Overlay and Battery Consumption cards (or at end of overlay section).
- `update_app_config()` — add 2 new `.get()` reads.
- POST handler — add 2 new form field reads.

</code_context>

<specifics>
## Specific Ideas

- The "flat battery" phrasing in the phase name maps to the empty-state icon (no fill in the battery outline). This is the most visually distinct warning state.
- The battery nub/terminal goes on the right side of the battery body (conventional battery icon orientation), regardless of rotation (it rotates with the icon in viewer space).
- At `overlay_font_size=26` (default), battery body is ~52×26px. At the 1200×1600 display resolution this is small but legible.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-battery-indicator-icon-low-battery-warning-and-flat-battery-icons-on-display*
*Context gathered: 2026-06-28*
