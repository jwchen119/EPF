---
phase: quick
plan: 260601-tat
type: execute
wave: 1
depends_on: []
files_modified:
  - app.py
  - templates/settings.html
  - tests/test_geo_overlay.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "geo_overlay_enabled=False suppresses location from the overlay even when GPS/Immich data is present"
    - "date_overlay_enabled=True and geo_overlay_enabled=False shows date-only overlay"
    - "Both toggles On shows 'City, Country • date' overlay as before"
    - "Settings page shows a 'Show Location' select (on/off) inside the Date Overlay card"
    - "Saving settings persists geo_overlay_enabled to config.yaml"
    - "Existing deployments without geo_overlay_enabled in YAML default to True (backward compat)"
  artifacts:
    - path: "app.py"
      provides: "geo_overlay_enabled global, DEFAULT_CONFIG entry, update_app_config wiring, POST handler, scale_img_in_memory guard"
    - path: "templates/settings.html"
      provides: "geo_overlay_enabled select control inside Date Overlay card"
    - path: "tests/test_geo_overlay.py"
      provides: "regression tests for geo_overlay_enabled=False suppression"
  key_links:
    - from: "scale_img_in_memory"
      to: "parse_photo_location"
      via: "geo_overlay_enabled guard"
      pattern: "if geo_overlay_enabled"
    - from: "update_app_config"
      to: "geo_overlay_enabled global"
      via: ".get() with default True"
      pattern: "geo_overlay_enabled = new_config\\['immich'\\].get\\('geo_overlay_enabled', True\\)"
---

<objective>
Add an independent `geo_overlay_enabled` toggle that controls whether location text appears in the date/geo overlay, mirroring the existing `date_overlay_enabled` pattern exactly.

Purpose: Users can now choose date-only, location-only, both, or neither overlay text.
Output: app.py config + pipeline guard + settings.html toggle + regression tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Key decisions already in STATE.md that constrain this work:
- date_overlay_enabled uses select on/off, not checkbox (D per 02-03)
- .get() fallback in update_app_config for all overlay keys (backward compat, 02-03 / 06-03)
- 6 overlay globals use global statement in update_app_config (06-03 pattern)
- parse_photo_location is called inside `if date_overlay_enabled:` block in scale_img_in_memory (~line 527)
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add geo_overlay_enabled config + pipeline guard</name>
  <files>app.py, tests/test_geo_overlay.py</files>
  <behavior>
    - Test GEO-13: scale_img_in_memory with date_overlay_enabled=True and geo_overlay_enabled=False calls draw_date_overlay with date string only (no location prefix)
    - Test GEO-14: scale_img_in_memory with date_overlay_enabled=True and geo_overlay_enabled=True and location available calls draw_date_overlay with "City • date" format
    - Test GEO-15: update_app_config with config missing geo_overlay_enabled key defaults global to True
  </behavior>
  <action>
    Follow the exact `date_overlay_enabled` pattern at every touch-point:

    1. **DEFAULT_CONFIG** (~line 52): Add `'geo_overlay_enabled': True,` immediately after `'date_overlay_enabled': False,`. Default True preserves existing behavior for all current deployments.

    2. **Module-level global** (~line 306): Add `geo_overlay_enabled = DEFAULT_CONFIG['immich']['geo_overlay_enabled']` directly after the `date_overlay_enabled` line.

    3. **update_app_config global statement** (~line 693): Add `geo_overlay_enabled,` to the global declaration list alongside `date_overlay_enabled`.

    4. **update_app_config assignment** (~line 731): Add `geo_overlay_enabled = new_config['immich'].get('geo_overlay_enabled', True)` directly after the `date_overlay_enabled` assignment line.

    5. **scale_img_in_memory overlay block** (~line 527-535): Guard the `parse_photo_location` call with `geo_overlay_enabled`. The block currently builds `location_str` unconditionally when `date_overlay_enabled` is True. Change it to:

    ```python
    if date_overlay_enabled:
        location_str = parse_photo_location(local_image=pre_transpose_image, immich_exif=immich_exif_raw) if geo_overlay_enabled else None
        date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
        ...  # rest of overlay_text assembly unchanged
    ```

    This single-line conditional replaces the bare `parse_photo_location(...)` call — behavior is identical when `geo_overlay_enabled=True`.

    6. **POST handler** (~line 850): Add `'geo_overlay_enabled': request.form.get('geo_overlay_enabled', 'off') == 'on',` directly after the `date_overlay_enabled` line.

    Write TDD tests FIRST (RED), implement until GREEN.
  </action>
  <verify>
    <automated>cd /Users/lennart/Dev/privat/EPF && python -m pytest tests/test_geo_overlay.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All geo overlay tests pass including the three new GEO-13/14/15 cases. `geo_overlay_enabled=False` in a monkeypatched call to scale_img_in_memory produces date-only overlay text.</done>
</task>

<task type="auto">
  <name>Task 2: Add geo_overlay_enabled toggle to settings.html</name>
  <files>templates/settings.html</files>
  <action>
    Inside the "Date Overlay" card, add a new `form-group` div for location toggle immediately after the existing `date_overlay_enabled` form-group (after its closing `</div>`). Mirror the select/on/off pattern exactly:

    ```html
    <div class="form-group">
        <label for="geo_overlay_enabled">Show Location:</label>
        <select id="geo_overlay_enabled" name="geo_overlay_enabled">
            <option value="off" {% if not config['immich'].get('geo_overlay_enabled', true) %}selected{% endif %}>Off</option>
            <option value="on"  {% if config['immich'].get('geo_overlay_enabled', true) %}selected{% endif %}>On</option>
        </select>
        <div class="small-text">Display the city and country from photo GPS or Immich metadata. On by default.</div>
    </div>
    ```

    Note the Jinja2 default is `true` (not `false`) because the server default is True.

    Also update the card description `<p class="small-text">` to clarify that location display is now independently toggleable. Replace the existing paragraph text with:
    "Configure which information appears on the image. Enable the date and/or location overlay below."
  </action>
  <verify>
    <automated>cd /Users/lennart/Dev/privat/EPF && python -c "from flask import Flask; app = Flask(__name__, template_folder='templates'); app.config['TESTING']=True; ctx=app.app_context(); ctx.push(); from flask import render_template_string; open('templates/settings.html').read(); print('template OK')" 2>&1</automated>
  </verify>
  <done>settings.html has a "Show Location" select control inside the Date Overlay card. The select defaults to "on". Saving the form with location=off and date=on shows only the date on the next image render.</done>
</task>

</tasks>

<verification>
Run full test suite to confirm no regressions:
```
cd /Users/lennart/Dev/privat/EPF && python -m pytest tests/ -q 2>&1 | tail -20
```

Manual smoke-test checklist:
1. Load settings page — "Show Location" select appears in Date Overlay section, defaults to On
2. Set date=on, location=off, save — next /image request shows date-only overlay (no city prefix)
3. Set date=on, location=on, save — next /image request shows "City, Country • date" as before
4. Set date=off — overlay hidden regardless of location toggle
</verification>

<success_criteria>
- All existing tests pass (no regressions in test_date_overlay.py, test_geo_overlay.py, test_overlay_customization.py)
- Three new tests GEO-13/14/15 pass
- `geo_overlay_enabled` defaults to True in DEFAULT_CONFIG and in .get() fallback
- settings.html renders the new select without Jinja2 errors
- POST handler correctly maps form value to boolean config key
</success_criteria>

<output>
After completion, create `.planning/quick/260601-tat-add-geo-overlay-toggle-to-settings-allow/260601-tat-SUMMARY.md`
</output>
