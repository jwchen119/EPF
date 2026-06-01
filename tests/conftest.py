"""Shared pytest fixtures for the EPF test suite."""
import pytest
from PIL import Image, ImageFont


@pytest.fixture
def blank_rgb_image():
    """Return a fresh 200x100 white RGB PIL Image."""
    return Image.new("RGB", (200, 100), (255, 255, 255))


@pytest.fixture
def large_rgb_image():
    """Return a fresh 1200x1600 white RGB PIL Image (display dimensions)."""
    return Image.new("RGB", (1200, 1600), (255, 255, 255))


@pytest.fixture
def dejavu_or_default_font():
    """Return DejaVuSans-Bold 26 if available, else PIL default font."""
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except (IOError, OSError):
        return ImageFont.load_default()


@pytest.fixture
def synthetic_gps_image():
    """A PIL RGB image whose _getexif() returns a GPSInfo dict for Munich (~48.1351, 11.5820).

    GPSInfo sub-tags (EXIF spec):
      1 = GPSLatitudeRef ('N'/'S'), 2 = GPSLatitude DMS tuple,
      3 = GPSLongitudeRef ('E'/'W'), 4 = GPSLongitude DMS tuple.
    Munich 48.1351 N -> (48, 8, 6.36); 11.5820 E -> (11, 34, 55.2).
    """
    img = Image.new("RGB", (200, 100), (255, 255, 255))
    gps_dict = {
        1: 'N',
        2: (48.0, 8.0, 6.36),
        3: 'E',
        4: (11.0, 34.0, 55.2),
    }
    exif_dict = {34853: gps_dict, 36867: '2022:01:05 10:00:00'}
    img._getexif = lambda: exif_dict  # noqa: SLF001 — test stub
    return img


@pytest.fixture
def mock_geo_cache_dir(tmp_path, monkeypatch):
    """Point geo cache at an isolated tmp dir via IMMICH_PHOTO_DEST; reset app module cache."""
    monkeypatch.setenv('IMMICH_PHOTO_DEST', str(tmp_path))
    import app
    monkeypatch.setattr(app, '_GEO_CACHE', None, raising=False)
    return tmp_path
