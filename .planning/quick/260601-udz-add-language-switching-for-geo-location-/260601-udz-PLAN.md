---
phase: quick-260601-udz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app.py
  - templates/settings.html
  - tests/test_geo_overlay.py
autonomous: true
requirements: [GEO-LANG-01, GEO-LANG-02, GEO-LANG-03]
must_haves:
  truths:
    - "User can select an overlay language (English/German) in the settings page"
    - "Selected language persists across restarts via config.yaml"
    - "Reverse-geocoded location names render in the selected language (e.g. 'Germany' vs 'Deutschland')"
    - "The geo cache is keyed per language so switching language does not return stale localized names"
  artifacts:
    - path: "app.py"
      provides: "overlay_language config key, language-aware reverse_geocode_cached, global wiring"
      contains: "overlay_language"
    - path: "templates/settings.html"
      provides: "Overlay Language dropdown (English/German)"
      contains: "overlay_language"
    - path: "tests/test_geo_overlay.py"
      provides: "Tests for language passthrough and per-language cache keying"
  key_links:
    - from: "templates/settings.html overlay_language select"
      to: "POST handler request.form.get('overlay_language')"
      via: "form field name overlay_language"
      pattern: "overlay_language"
    - from: "reverse_geocode_cached"
      to: "Nominatim.reverse(language=...)"
      via: "overlay_language global"
      pattern: "language="
    - from: "reverse_geocode_cached cache key"
      to: "geo_cache.json"
      via: "language-suffixed key"
      pattern: "round\\(float\\(lat\\), 3\\)"
---

<objective>
Add an overlay language setting (English / German) so the geo-location overlay renders place names in the user's chosen language. The language controls Nominatim reverse-geocoding (`language='en'` is currently hardcoded at app.py:157). The geo cache key gains a language dimension so switching language does not surface a stale localized result.

Purpose: User wants "Germany" vs "Deutschland" depending on app settings.
Output: New `overlay_language` config key, language-aware `reverse_geocode_cached`, settings dropdown, and tests.

IMPORTANT CAVEAT (document, do not "fix"): Immich's `exifInfo.city`/`country` values are pre-localized by the Immich server and are NOT re-translatable here. `parse_photo_location` returns those Immich strings directly when present (app.py:177-185), so the language setting only affects photos that fall back to local-GPS reverse geocoding. This is correct and expected — note it in the settings help text rather than attempting to translate Immich-supplied strings.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app.py
@templates/settings.html
@tests/test_geo_overlay.py

<interfaces>
Current geo helper (app.py:148-168) — language is hardcoded, cache key has no language dimension:
```python
def reverse_geocode_cached(lat, lon):
    key = f'{round(float(lat), 3)},{round(float(lon), 3)}'
    cache = _load_geo_cache()
    if key in cache:
        return cache[key]
    ...
    geolocator = Nominatim(user_agent='epf-photo-frame/1.0', timeout=5)
    location = geolocator.reverse((lat, lon), exactly_one=True, language='en')
    ...
```

Config defaults block (app.py:37-62) holds all `immich.*` overlay keys (e.g. `overlay_font_size`).
`update_app_config()` (app.py ~690-748) declares overlay globals and reads them with `.get()` fallback.
POST handler (app.py ~840-880) maps `request.form.*` -> new config dict.
`reverse_geocode_cached` is called from `parse_photo_location` (app.py:189) on the local-GPS fallback path only.

Existing per-language cache test seed format (test_geo_overlay.py:89): `{'48.135,11.582': 'Munich, Germany'}` — adding a language suffix changes this key, so GEO-07/08 seeds must be updated in the same task.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make reverse_geocode_cached language-aware</name>
  <files>app.py, tests/test_geo_overlay.py</files>
  <behavior>
    - Add module-level global `overlay_language` defaulting to 'en'.
    - `reverse_geocode_cached(lat, lon)` reads the `overlay_language` global and passes it as `language=` to `geolocator.reverse(...)` instead of the hardcoded 'en'.
    - Cache key becomes language-suffixed: `f'{round(float(lat),3)},{round(float(lon),3)}:{overlay_language}'` so 'en' and 'de' results coexist without collision.
    - GEO-07 (cache hit, no network): update the pre-seeded cache key to `'48.135,11.582:en'` and assert no Nominatim call.
    - GEO-08 (null on error): assert the stored key is `'10.0,20.0:en'` with value None.
    - New test GEO-LANG-01: with `overlay_language` monkeypatched to 'de', `reverse_geocode_cached` passes `language='de'` to a fake Nominatim (capture the kwarg) and stores under key `...:de`.
    - New test GEO-LANG-02: an 'en'-seeded cache entry is NOT returned when `overlay_language='de'` (cache miss triggers a fresh lookup).
  </behavior>
  <action>
    1. In app.py DEFAULT_CONFIG['immich'] (app.py:37-61) add `'overlay_language': 'en',  # 'en' | 'de' — Nominatim reverse-geocode language (GEO-LANG)` near the other overlay keys.
    2. Add `overlay_language = DEFAULT_CONFIG['immich']['overlay_language']` to the global-init block alongside `overlay_font_size` (~app.py:315).
    3. Rewrite `reverse_geocode_cached` (app.py:148-168): reference the module global `overlay_language` (no signature change — keep `(lat, lon)` to preserve the parse_photo_location call site at app.py:189 and GEO-06/07/08 contracts). Build the language-suffixed cache key and pass `language=overlay_language` to `geolocator.reverse(...)`. Keep the `# type: ignore` comments already present.
    4. Update tests/test_geo_overlay.py GEO-07 seed to `'48.135,11.582:en'` and GEO-08 assertion to `'10.0,20.0:en'`.
    5. Add GEO-LANG-01 and GEO-LANG-02 tests per the behavior block. Use a fake Nominatim that records the `language` kwarg and returns an object whose `.raw` yields a known city/country, following the `_BadNominatim` pattern at test_geo_overlay.py:102.
  </action>
  <verify>
    <automated>cd /Users/lennart/Dev/privat/EPF && python -m pytest tests/test_geo_overlay.py -q</automated>
  </verify>
  <done>All geo tests pass; reverse_geocode_cached uses the overlay_language global for both the Nominatim call and the cache key; new GEO-LANG-01/02 tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Wire overlay_language through config load/save and settings UI</name>
  <files>app.py, templates/settings.html</files>
  <action>
    1. In `update_app_config()` (app.py ~690-748): add `overlay_language` to the `global` declaration (after `overlay_font_size`, app.py:709) and add `overlay_language = new_config['immich'].get('overlay_language', 'en')` alongside the other overlay reads (~app.py:748). Backward compat: `.get()` default 'en' for old config.yaml files.
    2. In the POST handler config dict (app.py ~860-880): add `'overlay_language': request.form.get('overlay_language', current_config['immich'].get('overlay_language', 'en')),` next to the other overlay_* form reads.
    3. In templates/settings.html, after the "Show Location" form-group (settings.html:470-477), add an Overlay Language dropdown:
       ```html
       <div class="form-group">
           <label for="overlay_language">Location Language:</label>
           <select id="overlay_language" name="overlay_language">
               <option value="en" {% if config['immich'].get('overlay_language', 'en') == 'en' %}selected{% endif %}>English</option>
               <option value="de" {% if config['immich'].get('overlay_language', 'en') == 'de' %}selected{% endif %}>Deutsch</option>
           </select>
           <div class="small-text">Language for GPS-derived place names (e.g. "Germany" / "Deutschland"). Note: locations supplied directly by Immich keep Immich's language.</div>
       </div>
       ```
    Match the existing select/small-text markup style used for geo_overlay_enabled.
  </action>
  <verify>
    <automated>cd /Users/lennart/Dev/privat/EPF && python -c "import ast; ast.parse(open('app.py').read())" && python -m pytest tests/test_geo_overlay.py -q && grep -q overlay_language templates/settings.html</automated>
  </verify>
  <done>overlay_language round-trips through DEFAULT_CONFIG, update_app_config (with 'en' fallback), and the POST handler; the settings page shows an English/Deutsch dropdown reflecting the saved value; all geo tests pass.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/test_geo_overlay.py -q` passes (existing GEO-01..15 plus new GEO-LANG-01/02).
- `grep -n "language=overlay_language" app.py` shows the Nominatim call uses the global.
- `grep -n ":{overlay_language}\|:en'\|:de'" app.py` confirms the cache key is language-suffixed.
- Settings page renders a "Location Language" dropdown with English/Deutsch options.
</verification>

<success_criteria>
- User selects English or Deutsch in settings; choice persists in config.yaml as `immich.overlay_language`.
- GPS-fallback location names reverse-geocode in the chosen language; cache is keyed per language so switching does not return stale strings.
- Immich-supplied city/country behavior is unchanged and the UI help text explains this limitation.
- Full geo test suite green.
</success_criteria>

<output>
After completion, create `.planning/quick/260601-udz-add-language-switching-for-geo-location-/260601-udz-SUMMARY.md`
</output>
