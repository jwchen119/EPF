# Phase 11: Margin for text on image — Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a configurable inset margin so the date/location overlay text is pushed away from the display edges, keeping it visible through a passe-partout (window mat/frame). Two separate config values control horizontal margin (left/right offset) and vertical margin (top/bottom offset).

The margin is purely additive — it is applied on top of the existing `padding=6` text box breathing room. The rendering logic lives in `draw_date_overlay()` and the POSITIONS lambdas at `app.py:201–213`. New config keys follow the established Phase 2/6 pattern.

</domain>

<decisions>
## Implementation Decisions

### Margin Values
- **D-01:** Two separate config keys: `overlay_margin_h` (horizontal — left/right) and `overlay_margin_v` (vertical — top/bottom). Supports asymmetric passe-partout mats without adding four individual controls.
- **D-02:** Both default to **0 px** — zero margin means no visual change for existing deployments (backward-compatible).
- **D-03:** Both sliders range **0–200 px**, step=10. This covers all realistic passe-partout widths on a 1200×1600 display.

### Relationship to Existing Padding
- **D-04:** The margin is **separate from and additive to** the existing `padding=6`. `padding` remains the text box breathing room (background rectangle inset around text). The margin is the additional display-edge inset. POSITIONS lambdas receive `margin_h` and `margin_v` as separate arguments alongside `p`.
- **D-05:** The POSITIONS lambdas are extended to accept `margin_h` and `margin_v`. Edge positions incorporate them into the x/y calculation:
  - Left-edge positions: x offset = `p + margin_h`
  - Right-edge positions: x offset from right = `p + margin_h`
  - Top-edge positions: y offset = `p + margin_v`
  - Bottom-edge positions: y offset from bottom = `p + margin_v`

### Center Position Behavior
- **D-06:** The `center` position silently ignores both margins — it always places text at the geometric center of the viewer canvas. No special UI note is needed.
- **D-07:** `centerLeft` and `centerRight` ignore `margin_v` (vertical has no effect); they do apply `margin_h`. `topCenter` and `bottomCenter` ignore `margin_h`; they apply `margin_v`. This follows naturally from the lambda structure.

### Config & UI
- **D-08:** New config keys under `DEFAULT_CONFIG['immich']`:
  - `overlay_margin_h`: default `0` (int)
  - `overlay_margin_v`: default `0` (int)
- **D-09:** Both keys use `.get()` fallback with int() cast in `update_app_config()` — same pattern as `overlay_font_size` (Phase 6 D-15, STATE.md).
- **D-10:** Settings UI: two sliders appended to the existing "Date Overlay" card in settings.html, following the `slider-container` pattern. Labels: "Horizontal Margin (px)" and "Vertical Margin (px)".
- **D-11:** `int()` cast applied to both values in `update_app_config()` and the POST handler (STATE.md key decision).

### Claude's Discretion
- Lambda signature change: update all 9 POSITIONS lambdas to accept `(w, h, tw, th, p, mh, mv)` — `mh` = margin_h, `mv` = margin_v. The `center` lambda ignores both; axis-center lambdas (`topCenter`, `bottomCenter`, `centerLeft`, `centerRight`) use only the relevant margin axis.
- Where to pass margin in `draw_date_overlay()`: add `margin_h=0, margin_v=0` parameters, pass them through to the POSITIONS lambda call at line 268.
- Whether the `draw_date_overlay()` signature change is backward-compatible: yes — default `margin_h=0, margin_v=0` preserves existing behavior for all callers.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Core overlay positioning (primary target)
- `app.py:201–213` — `POSITIONS` dict: 9 lambdas that compute text x/y. All 9 lambdas receive new `mh, mv` args. `center` ignores both; axis-center positions use one axis only.
- `app.py:216–297` — `draw_date_overlay()`: receives new `margin_h=0, margin_v=0` params, passes them to the POSITIONS lambda at line 268.
- `app.py:585–597` — Call site in `scale_img_in_memory()`: passes `overlay_margin_h` and `overlay_margin_v` globals to `draw_date_overlay()`.

### Config pattern (established in Phase 2, extended in Phase 6)
- `app.py:43–58` — `DEFAULT_CONFIG['immich']`: add `overlay_margin_h: 0` and `overlay_margin_v: 0`.
- `app.py:505–544` — `update_app_config()`: read new keys into module globals with int() cast and .get() fallback.
- `app.py:649–660` — POST handler in `settings()`: read `request.form.get('overlay_margin_h', 0)` and `overlay_margin_v`.

### Settings UI
- `templates/settings.html:560–576` — Existing font-size and stroke-width sliders in the "Date Overlay" card. New margin sliders follow the same `slider-container` pattern immediately after.
- `templates/settings.html:115–145` — Slider CSS + `updateSliderValue` JS function (referenced pattern).

### Prior phase decisions
- `.planning/phases/06-text-customization-colors-styles-and-border-mode/06-CONTEXT.md` — D-12/D-13: slider range/step patterns; D-14/D-15: backward-compat defaults and .get() fallback.
- `.planning/phases/02-date-overlay/02-CONTEXT.md` — D-02: .get() fallback pattern; D-05: default position.
- `.planning/STATE.md` key decision: "int() cast on slider values in both update_app_config() and POST handler".

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `POSITIONS` dict (`app.py:203`): 9 lambdas with signature `(w, h, tw, th, p)`. Will be extended to `(w, h, tw, th, p, mh, mv)`.
- `draw_date_overlay()` (`app.py:216`): `padding=6` default parameter. Will receive `margin_h=0, margin_v=0` additional kwargs.
- Slider HTML/CSS pattern (`settings.html:429–432`, `564–568`): `input[type="range"]` with `.slider-container` + `oninput="updateSliderValue(this)"` + `output.slider-value`. Copy verbatim for new margin sliders.

### Established Patterns
- Two new module-level globals: `overlay_margin_h = 0`, `overlay_margin_v = 0` (initialized from `DEFAULT_CONFIG`, read in `scale_img_in_memory()`).
- All slider values cast with `int()` before assignment — avoids type errors when YAML loads as strings (established in Phase 6 STATE.md note).
- `.get(key, default)` in `update_app_config()` for all new keys — backward compat with old config.yaml files.

### Integration Points
- `draw_date_overlay()` call at `app.py:585`: add `margin_h=overlay_margin_h, margin_v=overlay_margin_v` kwargs.
- `update_app_config()` global statement: add `overlay_margin_h`, `overlay_margin_v` to the existing list.
- No changes needed to `serve_local_image()` or `serve_immich_image()` — margins are read from globals inside `scale_img_in_memory()`.

</code_context>

<specifics>
## Specific Ideas

- The passe-partout use case: a physical mat/frame sits on top of the display with a window cut-out. The overlay text needs to be inside the visible window, so the user sets margins matching the physical mat border width (e.g., 80px horizontal + 80px vertical for a typical A4 mat on a 1200×1600 display).
- The margin does NOT affect the text box padding (6px rectangle inset) — it only affects where on the canvas the text box is anchored.
- Lambda refactor example for `bottomRight`:
  ```python
  'bottomRight': lambda w, h, tw, th, p, mh, mv: (w - tw - p - mh, h - th - p - mv),
  ```
- Lambda for `center` (unchanged behavior):
  ```python
  'center': lambda w, h, tw, th, p, mh, mv: ((w - tw) // 2, (h - th) // 2),
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-margin-for-text-on-image-configurable-inset-margin-to-keep-text-visible-behind-passe-partout*
*Context gathered: 2026-06-28*
