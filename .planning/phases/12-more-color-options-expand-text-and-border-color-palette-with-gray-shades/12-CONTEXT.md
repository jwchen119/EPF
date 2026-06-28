# Phase 12: More Color Options — Expand Text and Border Color Palette with Gray Shades - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add three gray shade options (Dark Gray, Gray, Light Gray) to the `OVERLAY_COLORS` dict and
all three color `<select>` dropdowns (`overlay_bg_color`, `overlay_text_color`,
`overlay_border_color`) in the date overlay settings UI. No changes to the T133A01 hardware
palette used for image quantization — gray shades are overlay-only.

</domain>

<decisions>
## Implementation Decisions

### Gray Shades to Add
- **D-01:** Three gray shades added to `OVERLAY_COLORS`:
  - `'dark_gray'`: `(64, 64, 64, 255)` — nearest-neighbor quantizes to black on the e-paper display
  - `'gray'`: `(128, 128, 128, 255)` — mid-point; quantizes to black or white depending on surrounding pixels
  - `'light_gray'`: `(192, 192, 192, 255)` — nearest-neighbor quantizes to white on the e-paper display
- **D-02:** All three grays are drawn in RGB space before palette quantization. Their appearance on the actual e-paper display will be black or white pixels (nearest-neighbor to the 6 hardware colors). This is expected and acceptable behavior.

### Naming and Ordering in UI
- **D-03:** Labels in the dropdown: `"Dark Gray"`, `"Gray"`, `"Light Gray"`.
- **D-04:** The three grays appear **after White and before Yellow** in all three dropdowns. Final order: Black, White, Dark Gray, Gray, Light Gray, Yellow, Red, Blue, Green. Keeps achromatic tones grouped at the top.

### Scope
- **D-05:** Changes are limited to:
  1. `OVERLAY_COLORS` dict in `app.py` — add three new entries
  2. All three `<select>` elements in `templates/settings.html` — add three new `<option>` entries each
  3. `.get()` fallback read-back in the Jinja template (already uses `.get()` — no code change needed for backward compat)
- **D-06:** The T133A01 hardware palette (`palette` list in `app.py:367`) is **not changed**. Grays are not e-paper colors and adding them there would break image quantization.

### Claude's Discretion
- Which existing callers of `OVERLAY_COLORS.get()` to verify still work with the new keys (should be transparent — they're additive entries, not modifications).
- Whether any test fixtures that enumerate `OVERLAY_COLORS` need updating.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Color definitions (primary targets)
- `app.py:377–383` — `OVERLAY_COLORS` dict: authoritative string → RGBA mapping for overlay colors. New gray entries go here.
- `app.py:367–375` — `palette` list: T133A01 hardware colors. **Do not add grays here.**

### Settings UI (primary target)
- `templates/settings.html:529–559` — Three `<select>` dropdowns for `overlay_bg_color`, `overlay_text_color`, `overlay_border_color`. New `<option>` entries go into each dropdown.

### Config pattern (established in Phase 6, carried from Phase 2)
- `app.py:58–60` — `DEFAULT_CONFIG['immich']` entries for `overlay_bg_color`, `overlay_text_color`, `overlay_border_color`. Defaults remain `'black'` / `'white'` / `'white'` — no change needed.
- `app.py:813–815` — `update_app_config()` reads color keys via `.get()` with fallbacks. No change needed.
- `app.py:941–947` — POST handler reads color keys. No change needed.

### Prior phase decisions
- `.planning/phases/06-text-customization-colors-styles-and-border-mode/06-CONTEXT.md` — D-01: original 6-color palette rationale; D-05: select dropdown pattern; D-14: defaults.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OVERLAY_COLORS` (`app.py:377`): dict already in place — Phase 12 adds 3 entries, no structural change.
- `<select>` HTML pattern (`settings.html:529–559`): existing `<option value="X" {% if ... %}selected{% endif %}>Label</option>` pattern to replicate for each new gray in each of the three dropdowns.

### Established Patterns
- Color string → RGBA lookup: `OVERLAY_COLORS.get(key, fallback_rgba)` at `app.py:605–607`. Adding entries is transparent to existing callers.
- Jinja read-back: `config['immich'].get('overlay_bg_color', 'black')` — `.get()` already present; no code change required for old `config.yaml` without the gray keys (old configs simply won't show gray selected).

### Integration Points
- Only `OVERLAY_COLORS` dict and `settings.html` dropdowns need changes. No call-site changes in `draw_date_overlay()`, `scale_img_in_memory()`, `update_app_config()`, or POST handler — new color keys are drop-in additions to the existing lookup table.

</code_context>

<specifics>
## Specific Ideas

- Exact RGB values chosen to create an even perceptual spread: 64/128/192 (25%/50%/75% of 255).
- mid-gray (128,128,128) quantization behavior is technically indeterminate (equidistant from black and white in the nearest-neighbor distance); in practice the quantization will pick one or the other based on `np.argmin` tie-breaking in `depalette_image()`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-more-color-options-expand-text-and-border-color-palette-with-gray-shades*
*Context gathered: 2026-06-28*
