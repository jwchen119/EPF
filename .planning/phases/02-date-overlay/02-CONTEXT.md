# Phase 2: Date Overlay - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract the date a photo was taken (from Immich API metadata or local file EXIF) and render it as a configurable text overlay on the processed image before it is sent to the e-paper display.

The overlay position must be one of 9 configurable alignments (topLeft, topCenter, topRight, centerLeft, center, centerRight, bottomLeft, bottomCenter, bottomRight), settable via `config.yaml` and the web settings UI.

</domain>

<decisions>
## Implementation Decisions

### Overlay Enable/Disable
- **D-01:** Overlay is **off by default**. The default config value for `date_overlay_enabled` should be `false` so existing deployments are unaffected until the user explicitly enables it in settings.
- **D-02:** The settings UI must include an on/off toggle for the overlay.

### Missing Date Fallback
- **D-03:** When no date can be extracted (no EXIF tags, no Immich `exifInfo.dateTimeOriginal`, no fallback), the overlay is **silently hidden**. No placeholder text ("Unknown date") is shown. The image renders without any text overlay.

### Overlay Position
- **D-04:** 9 configurable positions: `topLeft`, `topCenter`, `topRight`, `centerLeft`, `center`, `centerRight`, `bottomLeft`, `bottomCenter`, `bottomRight`. These are **positions on the final rendered image** (after rotation is applied), so `bottomRight` always means the bottom-right corner of what the viewer sees on the display.
- **D-05:** The config key is `date_overlay_position` with default value `bottomRight`.

### Claude's Discretion
- Date format: Use `DD.MM.YYYY` (e.g. `05.01.2022`) as the default. This is a readable European format and avoids the ambiguous YYYY/MM/DD in the existing partial code.
- Font size: 24–28px bold, auto-detected from DejaVuSans-Bold or fallback to PIL default.
- Visual style: White text with a semi-transparent/solid black background pill/rectangle (matching the existing partial implementation in `draw_text_with_background()`). Not configurable — keep the UI simple.
- Padding around text: 5–8px on all sides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Relevant code to read before implementing
- `app.py` lines 180–365 — `scale_img_in_memory()`: contains the existing partial date overlay implementation (`draw_text_with_background()`) that is commented out at line 357. The refactored implementation should replace this dead code.
- `app.py` lines 722–801 — `serve_immich_image()`: Immich `exifInfo.dateTimeOriginal` is already available on the selected asset dict (line 753 uses it for sorting). This field should be passed through or re-used for the overlay.
- `app.py` lines 568–631 — `settings()` route: shows the config read/write pattern for adding new settings fields.
- `app.py` lines 23–46 — `DEFAULT_CONFIG`: all new config keys must be added here with defaults.
- `app.py` lines 473–508 — `update_app_config()`: new config keys must be extracted here into globals.
- `app.py` lines 587–604 — POST handler in `settings()`: new form fields must be read here.
- `templates/settings.html` — existing settings UI, new controls must match the card/form-group/select pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `draw_text_with_background()` (nested in `scale_img_in_memory()`, lines 274–357): exists but handles position as rotation-dependent hardcoded offsets. Must be refactored to accept an explicit `position` parameter (one of 9 string values) and compute x/y coordinates from that, independent of rotation.
- `ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)` with PIL default fallback: existing font loading pattern to reuse.
- `ImageDraw.Draw(output_img)`: already used in the partial overlay code.

### Established Patterns
- Config pattern: add key to `DEFAULT_CONFIG` → `update_app_config()` reads it into a global → HTML form has matching input → POST handler reads `request.form.get(...)`.
- Global state: new settings become module-level globals (e.g. `date_overlay_enabled`, `date_overlay_position`).
- Image pipeline: `scale_img_in_memory()` is called for both local and Immich images. Date injection should happen inside this function so it works for both paths.

### Integration Points
- `scale_img_in_memory()` is called from both `serve_local_image()` and `serve_immich_image()`. The Immich path already has `exifInfo.dateTimeOriginal` on the asset; this must be passed into `scale_img_in_memory()` so the overlay can use it as a fallback or primary source.
- `serve_local_image()` relies on EXIF extracted inside `scale_img_in_memory()` — this path already works for local files.
- Settings HTML uses `.card` + `.form-group` + `label` + `select` or `input[type="range"]` pattern. A new "Date Overlay" card section should follow this pattern.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for font rendering and position calculation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-date-overlay*
*Context gathered: 2026-05-27*
