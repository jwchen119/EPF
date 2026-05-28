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
