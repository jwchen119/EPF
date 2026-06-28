"""Tests for Phase 10: Binary image transport (BATT-01..BATT-04).

BATT-01: convert_to_binary_in_memory() output is exactly 960000 bytes for a 1200x1600 image
BATT-02: binary nibble bytes are identical to the hex-CSV legacy encoder for the same image
BATT-03: GET /download returns HTTP 200 and Content-Type application/octet-stream
BATT-04: GET /download returns Content-Length == '960000'

These tests MUST fail (RED) until plan 10-01 adds convert_to_binary_in_memory and wires
both serve functions to return application/octet-stream.
"""

import re

import pytest
from PIL import Image

import app as app_module
from app import convert_to_binary_in_memory, convert_to_c_code_in_memory  # noqa: F401

FRAME_BYTES = 960000  # 1200 * 1600 / 2


@pytest.fixture
def large_rgb_image():
    """Return a fresh 1200x1600 white RGB PIL Image (display dimensions)."""
    return Image.new('RGB', (1200, 1600), (255, 255, 255))


@pytest.fixture
def multicolor_large_image():
    """1200x1600 image with several T133A01 palette-mapped colours so multiple nibble codes appear."""
    img = Image.new('RGB', (1200, 1600), (255, 255, 255))  # white background
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    # T133A01 palette: black=(0,0,0), white=(255,255,255), yellow=(255,255,0),
    #                  red=(255,0,0), blue=(0,0,255), green=(0,128,0)
    draw.rectangle([0, 0, 300, 400], fill=(0, 0, 0))  # black
    draw.rectangle([300, 0, 600, 400], fill=(255, 255, 0))  # yellow
    draw.rectangle([600, 0, 900, 400], fill=(255, 0, 0))  # red
    draw.rectangle([900, 0, 1200, 400], fill=(0, 0, 255))  # blue
    draw.rectangle([0, 400, 600, 800], fill=(0, 128, 0))  # green
    return img


@pytest.fixture
def local_client(tmp_path, monkeypatch):
    """Test client with a localdir containing one real JPEG (routes /download to serve_local_image)."""
    # Create a small but valid 1200x1600 image in tmp_path
    img = Image.new('RGB', (1200, 1600), (255, 255, 255))
    img_path = tmp_path / 'test_image.jpg'
    img.save(str(img_path), 'JPEG')

    monkeypatch.setattr(app_module, 'localdir', str(tmp_path))
    monkeypatch.setattr(app_module, 'APP_PASSWORD', '')  # disable auth
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# BATT-01: binary output length
# ---------------------------------------------------------------------------


def test_binary_output_length(large_rgb_image):
    """BATT-01: convert_to_binary_in_memory() produces exactly 960000 bytes for a 1200x1600 image."""
    result = convert_to_binary_in_memory(large_rgb_image)
    assert len(result.getvalue()) == FRAME_BYTES


# ---------------------------------------------------------------------------
# BATT-02: nibble parity with legacy hex-CSV encoder
# ---------------------------------------------------------------------------


def test_binary_nibble_parity(multicolor_large_image):
    """BATT-02: binary bytes are nibble-identical to the legacy hex-CSV encoder output."""
    img = multicolor_large_image

    # Parse legacy hex-CSV output
    text = convert_to_c_code_in_memory(img).getvalue().decode('utf-8')
    # Strip trailing "};\n" and "};"
    text = text.replace('};\n', '').replace('};', '')
    tokens = [t for t in re.split(r'[,\n]', text) if t.strip()]
    legacy = bytes(int(t, 16) for t in tokens)

    binary_output = convert_to_binary_in_memory(img).getvalue()

    assert binary_output == legacy


# ---------------------------------------------------------------------------
# BATT-03: /download mimetype is application/octet-stream
# ---------------------------------------------------------------------------


def test_download_mimetype(local_client):
    """BATT-03: GET /download returns HTTP 200 and Content-Type application/octet-stream."""
    resp = local_client.get('/download')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/octet-stream'


# ---------------------------------------------------------------------------
# BATT-04: /download Content-Length is 960000
# ---------------------------------------------------------------------------


def test_download_content_length(local_client):
    """BATT-04: GET /download returns Content-Length == '960000'."""
    resp = local_client.get('/download')
    assert resp.headers['Content-Length'] == str(FRAME_BYTES)
