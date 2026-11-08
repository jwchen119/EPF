"""
Regression check of what the server sends the frame.

Renders fixed, generated images through the pipeline and compares a hash of
the packed panel data with the one recorded below, so that an upgrade of
Pillow, NumPy or Numba cannot change the picture on the panel unnoticed. The
classic hashes are those of the former Cython module, which epf/dither.py
reproduces byte for byte. Also checks which file formats are decoded at all,
and which generated photos of the calibration card the measurement accepts.

The dependencies are in the image, not on the host, so run it there:

    docker run --rm -v "$PWD/tests:/app/tests" <image> python -m unittest discover -s tests -v

A hash that changes on purpose (a new dithering, a different palette) is
updated here in the same commit, saying why.
"""
import hashlib
import io
import os
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from epf import calibration, dither, imaging  # noqa: E402


def _sha(data):
    return hashlib.sha256(data).hexdigest()[:16]


def _photos():
    """ A noisy landscape with flat patches, and a portrait of pure noise """
    rng = np.random.default_rng(1)
    h, w = 900, 1200
    y, x = np.mgrid[0:h, 0:w]
    img = np.stack([x * 255 // w, y * 255 // h, (x + y) * 255 // (w + h)], -1).astype(np.int64)
    img[100:300, 100:400] = [200, 150, 120]
    img[500:700, 600:900] = [60, 90, 40]
    noisy = Image.fromarray(np.clip(img + rng.integers(-20, 20, img.shape), 0, 255).astype(np.uint8))
    portrait = Image.fromarray(rng.integers(0, 256, (1600, 1000, 3)).astype(np.uint8))
    return noisy, portrait


def _encoded(image, fmt, **options):
    out = io.BytesIO()
    image.save(out, fmt, **options)
    return out.getvalue()


def _card_photo(palette, exposure=0.5):
    """
    A photo of the calibration card on a panel that shows `palette` (sRGB,
    relative to its own white), exposed so that white is `exposure` in linear
    light: every panel pixel 2x2 photo pixels, as PNG so nothing is lost
    """
    card = imaging.calibration_card().astype(np.int64)
    pure = dither.PURE8.astype(np.int64)
    index = np.argmin(((card[:, :, None] - pure[None, None]) ** 2).sum(-1), -1)
    linear = dither._to_linear(np.asarray(palette, dtype=np.float64) / 255.0) * exposure
    pixels = calibration._to_srgb8(linear).astype(np.uint8)[index]
    image = Image.fromarray(pixels).resize((imaging.EPD_W * 2, imaging.EPD_H * 2), Image.NEAREST)
    return _encoded(image, 'PNG')


# (photo, rotation, display mode, saturation, contrast, strength) -> packed data
CLASSIC = [
    ('noisy', 270, 'fill', 1.3, 0.9, 0.8, '75ce40b92e9f5e91'),
    ('noisy', 0, 'fit', 1.0, 1.0, 1.0, '90a96e2a7b30352a'),
    ('noisy', 90, 'fill', 1.5, 1.2, 0.3, '19ba61164cae19fd'),
    ('portrait', 180, 'fit', 0.8, 0.7, 0.5, '67ebfc5246c48d4e'),
    ('portrait', 270, 'fill', 1.3, 0.9, 0.8, '3c0e558f3457628f'),
]
# Recorded from the 1.4.0 image
CLASSIC_CC = '7e455f7b57b41032'
CARD = '99401c7e204394d1'


class Render(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        noisy, portrait = _photos()
        cls.photos = {'noisy': noisy, 'portrait': portrait}

    def test_classic(self):
        for name, rotation, mode, enhanced, contrast, strength, expected in CLASSIC:
            with self.subTest(photo=name, rotation=rotation, mode=mode):
                bmp = imaging.scale_img_in_memory(self.photos[name], rotation=rotation,
                                                  display_mode=mode, enhanced=enhanced,
                                                  contrast=contrast, strength=strength)
                self.assertEqual(_sha(imaging.pack_bmp_for_panel(bmp).getvalue()), expected)

    def test_classic_cc(self):
        # The developer's panel, as used until a calibration is saved
        measured = calibration.defaults()
        bmp = imaging.scale_img_in_memory(
            self.photos['noisy'], rotation=270, display_mode='fill', enhanced=1.0,
            contrast=1.0, strength=0.8, dither_mode='classic_cc',
            panel_palette=measured['palette'], dot_gain=measured['dot_gain'],
            correction={'strength': 0.8, 'chroma': 1.0, 'warmth': 0.0, 'tint': 0.0})
        self.assertEqual(_sha(imaging.pack_bmp_for_panel(bmp).getvalue()), CLASSIC_CC)

    def test_calibration_card(self):
        card = Image.fromarray(imaging.calibration_card())
        self.assertEqual(_sha(imaging.convert_to_c_code_in_memory(card).getvalue()), CARD)


class Formats(unittest.TestCase):
    """
    Only the formats photos come in are decoded; anything else is shown from
    Immich's preview, so that the decoders of rarely used formats, where most
    of Pillow's published flaws were, are never handed a file.
    """

    @classmethod
    def setUpClass(cls):
        cls.photo = _photos()[0].resize((300, 225))

    def test_photo_formats_open(self):
        for fmt, name in (('JPEG', 'a.jpg'), ('PNG', 'a.png'), ('WEBP', 'a.webp'), ('HEIF', 'a.heic')):
            with self.subTest(format=fmt):
                image = imaging.open_asset(io.BytesIO(_encoded(self.photo, fmt)), name)
                self.assertEqual(image.size, self.photo.size)
        # A camera JPEG with a second picture inside, which PIL calls MPO
        mpo = _encoded(self.photo, 'MPO', save_all=True, append_images=[self.photo])
        image = imaging.open_asset(io.BytesIO(mpo), 'a.jpg')
        self.assertEqual((image.format, image.size), ('MPO', self.photo.size))

    def test_other_formats_refused(self):
        for fmt, name in (('TIFF', 'a.tif'), ('GIF', 'a.gif'), ('BMP', 'a.bmp')):
            with self.subTest(format=fmt):
                with self.assertRaises(ValueError):
                    imaging.open_asset(io.BytesIO(_encoded(self.photo, fmt)), name)

    def test_preview_formats(self):
        for fmt in ('JPEG', 'WEBP'):
            with self.subTest(format=fmt):
                imaging.open_preview(io.BytesIO(_encoded(self.photo, fmt)))
        with self.assertRaises(Exception):
            imaging.open_preview(io.BytesIO(_encoded(self.photo, 'TIFF')))

    def test_calibration_photo_formats(self):
        for fmt in ('JPEG', 'HEIF'):
            with self.subTest(format=fmt):
                calibration.open_photo(_encoded(self.photo, fmt))
        with self.assertRaises(Exception):
            calibration.open_photo(_encoded(self.photo, 'TIFF'))


class Calibration(unittest.TestCase):
    """ The measurement, on generated photos of a panel showing a given palette """

    WHOLE = [[0, 0], [1, 0], [1, 1], [0, 1]]

    def measure(self, palette, corners=WHOLE):
        return calibration.measure([('card', _card_photo(palette), corners)])

    def test_default_panel(self):
        result = self.measure(imaging.CALIBRATED_PALETTE)
        self.assertTrue(result['usable'], result['photos'])
        np.testing.assert_allclose(result['palette'], imaging.CALIBRATED_PALETTE, atol=2)

    def test_vivid_panel(self):
        # What sound photos of another panel and phone measured, refused up to
        # 1.4.1 because the red is 51 (CIELAB) from the default's
        vivid = [(82, 50, 69), (255, 255, 255), (255, 242, 53), (243, 27, 25), (49, 124, 243),
                 (134, 169, 132)]
        result = self.measure(vivid)
        self.assertTrue(result['usable'], result['photos'])
        np.testing.assert_allclose(result['palette'], vivid, atol=2)

    def test_misread_colour(self):
        # A reflection over the whole red cell: it reads as a light grey
        palette = list(imaging.CALIBRATED_PALETTE)
        palette[3] = (200, 200, 200)
        result = self.measure(palette)
        self.assertFalse(result['usable'])
        self.assertIn('unexpected', result['photos'][0]['problems'])

    def test_corners_off_the_card(self):
        for corners, problem in (
                # The mean difference gives it away
                ([[0, 0], [0.5, 0], [0.5, 1], [0, 1]], 'unrecognised'),
                # The mean stays low (16.9) and only the misread colours do
                ([[0, 0], [1, 0], [1, 2 / 3], [0, 2 / 3]], 'unexpected')):
            with self.subTest(corners=corners):
                result = self.measure(imaging.CALIBRATED_PALETTE, corners)
                self.assertFalse(result['usable'])
                self.assertIn(problem, result['photos'][0]['problems'])


if __name__ == '__main__':
    unittest.main()
