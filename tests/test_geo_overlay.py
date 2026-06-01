"""Tests for Phase 7: Geolocation Overlay (GEO-01..GEO-12) and language switching (GEO-LANG-01..GEO-LANG-02).

These tests target interfaces that Plans 07-02 and 07-03 will create.
They MUST fail (RED) until those plans land — that is the TDD contract.

GEO-01: extract_gps_from_exif() returns correct (lat, lon) from synthetic EXIF
GEO-02: extract_gps_from_exif() returns None for image without GPS tag
GEO-03: extract_gps_from_exif() returns None for image with no _getexif (non-JPEG)
GEO-04: parse_photo_location() returns city+country from Immich exifInfo dict
GEO-05: parse_photo_location() returns None when Immich exifInfo has no city/country
GEO-06: parse_photo_location() calls geocoder (mocked) for local image with GPS
GEO-07: reverse_geocode_cached() uses cache on second call (no Nominatim call)
GEO-08: reverse_geocode_cached() stores null on Nominatim exception
GEO-09: scale_img_in_memory() renders geo+date combined overlay text
GEO-10: scale_img_in_memory() renders date-only when no geo available
GEO-11: scale_img_in_memory() renders location-only when no date available
GEO-12: Overlay hidden when neither geo nor date available
GEO-LANG-01: reverse_geocode_cached() passes overlay_language='de' to Nominatim and stores under language-keyed entry
GEO-LANG-02: 'en'-keyed cache entry is NOT returned when overlay_language='de' (cache miss triggers fresh lookup)
"""

import json

from PIL import Image

# --- GPS extraction (GEO-01..GEO-03) ----------------------------------------


def test_extract_gps_from_exif(synthetic_gps_image):
    """GEO-01: extract_gps_from_exif() returns correct (lat, lon) for Munich."""
    from app import extract_gps_from_exif

    coords = extract_gps_from_exif(synthetic_gps_image)
    assert coords is not None
    lat, lon = coords
    assert abs(lat - 48.1351) < 0.01
    assert abs(lon - 11.5820) < 0.01


def test_extract_gps_no_gps_tag(blank_rgb_image):
    """GEO-02: extract_gps_from_exif() returns None for image without GPS tag."""
    from app import extract_gps_from_exif

    blank_rgb_image._getexif = lambda: {36867: '2022:01:05 10:00:00'}  # noqa: SLF001
    assert extract_gps_from_exif(blank_rgb_image) is None


def test_extract_gps_no_exif_method():
    """GEO-03: extract_gps_from_exif() returns None when _getexif returns None."""
    from app import extract_gps_from_exif

    img = Image.new('RGB', (10, 10))
    img._getexif = lambda: None  # noqa: SLF001
    assert extract_gps_from_exif(img) is None


# --- Location parsing (GEO-04..GEO-06) ---------------------------------------


def test_location_from_immich_exif():
    """GEO-04: parse_photo_location() returns 'City, Country' from Immich exifInfo dict."""
    from app import parse_photo_location

    assert parse_photo_location(immich_exif={'city': 'Munich', 'country': 'Germany'}) == 'Munich, Germany'


def test_location_immich_empty_fields():
    """GEO-05: parse_photo_location() returns None when Immich exifInfo has empty city/country."""
    from app import parse_photo_location

    assert parse_photo_location(immich_exif={'city': '', 'country': ''}) is None
    assert parse_photo_location(immich_exif={}) is None


def test_location_from_local_gps(synthetic_gps_image, monkeypatch):
    """GEO-06: parse_photo_location() calls geocoder (mocked) for local image with GPS."""
    import app

    monkeypatch.setattr(app, 'reverse_geocode_cached', lambda lat, lon: 'Munich, Germany')
    assert app.parse_photo_location(local_image=synthetic_gps_image) == 'Munich, Germany'


# --- Geocoding cache (GEO-07..GEO-08) ----------------------------------------


def test_geocache_hit_no_network_call(mock_geo_cache_dir, monkeypatch):
    """GEO-07: reverse_geocode_cached() uses pre-seeded cache without calling Nominatim."""
    import app

    cache_file = mock_geo_cache_dir / 'geo_cache.json'
    cache_file.write_text(json.dumps({'48.135,11.582:en': 'Munich, Germany'}))

    def _nominatim_must_not_be_called(*a, **k):
        raise AssertionError('network called')

    monkeypatch.setattr(app, 'Nominatim', _nominatim_must_not_be_called)
    monkeypatch.setattr(app, 'overlay_language', 'en', raising=False)
    assert app.reverse_geocode_cached(48.1351, 11.5820) == 'Munich, Germany'


def test_geocache_stores_null_on_error(mock_geo_cache_dir, monkeypatch):
    """GEO-08: reverse_geocode_cached() stores null in cache when Nominatim raises."""
    import app

    class _BadNominatim:
        def __init__(self, *a, **k):
            pass

        def reverse(self, *a, **k):
            raise Exception('network failure')

    monkeypatch.setattr(app, 'Nominatim', _BadNominatim)
    monkeypatch.setattr(app, 'overlay_language', 'en', raising=False)

    result = app.reverse_geocode_cached(10.0, 20.0)
    assert result is None

    cache_file = mock_geo_cache_dir / 'geo_cache.json'
    cache = json.loads(cache_file.read_text())
    assert '10.0,20.0:en' in cache
    assert cache['10.0,20.0:en'] is None


# --- scale_img_in_memory overlay assembly (GEO-09..GEO-12) -------------------


def test_scale_img_geo_plus_date_overlay(large_rgb_image, monkeypatch):
    """GEO-09: scale_img_in_memory() renders 'Location • DD.MM.YYYY' when both are available."""
    import app

    monkeypatch.setattr(app, 'date_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'parse_photo_location', lambda **k: 'Munich, Germany')

    captured = []
    monkeypatch.setattr(app, 'draw_date_overlay', lambda img, text, *a, **k: captured.append(text))

    app.scale_img_in_memory(
        large_rgb_image,
        immich_date_raw='2022-01-05T10:00:00.000Z',
        immich_exif_raw={'city': 'Munich', 'country': 'Germany'},
    )
    assert captured == ['Munich, Germany • 05.01.2022']


def test_scale_img_date_fallback(large_rgb_image, monkeypatch):
    """GEO-10: scale_img_in_memory() renders date-only when no geo available."""
    import app

    monkeypatch.setattr(app, 'date_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'parse_photo_location', lambda **k: None)

    captured = []
    monkeypatch.setattr(app, 'draw_date_overlay', lambda img, text, *a, **k: captured.append(text))

    app.scale_img_in_memory(
        large_rgb_image,
        immich_date_raw='2022-01-05T10:00:00.000Z',
        immich_exif_raw=None,
    )
    assert captured == ['05.01.2022']


def test_scale_img_location_only(large_rgb_image, monkeypatch):
    """GEO-11: scale_img_in_memory() renders location-only when no date available."""
    import app

    monkeypatch.setattr(app, 'date_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'parse_photo_location', lambda **k: 'Munich, Germany')
    large_rgb_image._getexif = lambda: None  # noqa: SLF001

    captured = []
    monkeypatch.setattr(app, 'draw_date_overlay', lambda img, text, *a, **k: captured.append(text))

    app.scale_img_in_memory(
        large_rgb_image,
        immich_date_raw=None,
        immich_exif_raw={'city': 'Munich', 'country': 'Germany'},
    )
    assert captured == ['Munich, Germany']


def test_scale_img_no_overlay(large_rgb_image, monkeypatch):
    """GEO-12: Overlay hidden when neither geo nor date available."""
    import app

    monkeypatch.setattr(app, 'date_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'parse_photo_location', lambda **k: None)
    large_rgb_image._getexif = lambda: None  # noqa: SLF001

    captured = []
    monkeypatch.setattr(app, 'draw_date_overlay', lambda img, text, *a, **k: captured.append(text))

    app.scale_img_in_memory(
        large_rgb_image,
        immich_date_raw=None,
        immich_exif_raw=None,
    )
    assert captured == []


# --- geo_overlay_enabled toggle (GEO-13..GEO-15) --------------------------------


def test_scale_img_geo_disabled_shows_date_only(large_rgb_image, monkeypatch):
    """GEO-13: geo_overlay_enabled=False produces date-only overlay even when location is available."""
    import app

    monkeypatch.setattr(app, 'date_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'geo_overlay_enabled', False, raising=False)
    monkeypatch.setattr(app, 'parse_photo_location', lambda **k: 'Munich, Germany')

    captured = []
    monkeypatch.setattr(app, 'draw_date_overlay', lambda img, text, *a, **k: captured.append(text))

    app.scale_img_in_memory(
        large_rgb_image,
        immich_date_raw='2022-01-05T10:00:00.000Z',
        immich_exif_raw={'city': 'Munich', 'country': 'Germany'},
    )
    assert captured == ['05.01.2022']


def test_scale_img_geo_enabled_shows_full_overlay(large_rgb_image, monkeypatch):
    """GEO-14: geo_overlay_enabled=True with location available shows 'City • date' format."""
    import app

    monkeypatch.setattr(app, 'date_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'geo_overlay_enabled', True, raising=False)
    monkeypatch.setattr(app, 'parse_photo_location', lambda **k: 'Munich, Germany')

    captured = []
    monkeypatch.setattr(app, 'draw_date_overlay', lambda img, text, *a, **k: captured.append(text))

    app.scale_img_in_memory(
        large_rgb_image,
        immich_date_raw='2022-01-05T10:00:00.000Z',
        immich_exif_raw={'city': 'Munich', 'country': 'Germany'},
    )
    assert captured == ['Munich, Germany • 05.01.2022']


def test_update_app_config_geo_overlay_defaults_to_true(monkeypatch):
    """GEO-15: update_app_config with config missing geo_overlay_enabled key defaults global to True."""
    import app

    config_without_geo = {
        'immich': {
            'url': 'http://localhost',
            'album': 'test',
            'rotation': 0,
            'enhanced': 1.0,
            'contrast': 1.0,
            'strength': 1.0,
            'display_mode': 'fill',
            'image_order': 'random',
            'sleep_start_hour': 23,
            'sleep_start_minute': 0,
            'sleep_end_hour': 6,
            'sleep_end_minute': 0,
            'wakeup_interval': 60,
            'date_overlay_enabled': False,
            # geo_overlay_enabled intentionally absent
        }
    }

    app.update_app_config(config_without_geo)
    assert app.geo_overlay_enabled is True


# --- Language switching (GEO-LANG-01..GEO-LANG-02) ---------------------------


def test_geocache_uses_language_kwarg_de(mock_geo_cache_dir, monkeypatch):
    """GEO-LANG-01: reverse_geocode_cached passes language='de' to Nominatim and stores under ':de' key."""
    import app

    captured_kwargs = {}

    class _FakeNominatim:
        def __init__(self, *a, **k):
            pass

        def reverse(self, coords, **k):
            captured_kwargs.update(k)

            class _FakeLoc:
                raw = {'address': {'city': 'München', 'country': 'Deutschland'}}

            return _FakeLoc()

    monkeypatch.setattr(app, 'Nominatim', _FakeNominatim)
    monkeypatch.setattr(app, 'overlay_language', 'de', raising=False)

    result = app.reverse_geocode_cached(48.1351, 11.5820)

    assert result == 'München, Deutschland'
    assert captured_kwargs.get('language') == 'de'

    cache_file = mock_geo_cache_dir / 'geo_cache.json'
    cache = json.loads(cache_file.read_text())
    assert '48.135,11.582:de' in cache
    assert cache['48.135,11.582:de'] == 'München, Deutschland'


def test_geocache_en_entry_not_returned_for_de(mock_geo_cache_dir, monkeypatch):
    """GEO-LANG-02: An 'en'-keyed entry is NOT returned when overlay_language='de' (cache miss)."""
    import app

    cache_file = mock_geo_cache_dir / 'geo_cache.json'
    cache_file.write_text(json.dumps({'48.135,11.582:en': 'Munich, Germany'}))

    nominatim_called = []

    class _FakeNominatim:
        def __init__(self, *a, **k):
            pass

        def reverse(self, coords, **k):
            nominatim_called.append(k.get('language'))

            class _FakeLoc:
                raw = {'address': {'city': 'München', 'country': 'Deutschland'}}

            return _FakeLoc()

    monkeypatch.setattr(app, 'Nominatim', _FakeNominatim)
    monkeypatch.setattr(app, 'overlay_language', 'de', raising=False)

    result = app.reverse_geocode_cached(48.1351, 11.5820)

    # Must NOT return stale 'en' result; must trigger a fresh lookup
    assert result == 'München, Deutschland'
    assert nominatim_called == ['de']
