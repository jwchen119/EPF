"""
Panel colour calibration from photos of the calibration card.

imaging.calibration_card() fills the panel with a 3x3 grid: the six colours
and three fine checkerboards (imaging.CARD_LAYOUT). The user photographs the
panel showing it and marks the card's four corners on the settings page, and
measure() reads every cell: its middle, in linear light, blurred so a
checkerboard averages the way the eye sees it, then the median per channel so
dust and small highlights drop out. Every colour is divided by the white cell,
which cancels the phone's exposure and white balance: the palette comes out as
the panel shows it, with its own white as 255,255,255. The black/white and
red/white checkerboards give the dot gain (see dither.DOT_GAIN).

The corners may be marked in any order and the photo taken at any rotation:
of the eight ways the card can lie in the marked quadrilateral, the one whose
colours look most like a panel's is taken. Each photo is checked for
exposure, glare and colours that make no sense; several are combined by
median, and one that disagrees with the rest is left out.

The photos are never written anywhere. The result is kept in
/config/calibration.json beside config.yaml; until one is saved, the values
measured on the panel this was developed with are used.
"""
import io
import json
import math
import os
import threading
from datetime import datetime

import numpy as np
from PIL import Image, ImageCms, ImageOps

from . import config, dither, imaging

CALIBRATION_PATH = os.path.join(os.path.dirname(config.CONFIG_PATH), 'calibration.json')

# Palette order, as everywhere else: imaging.palette and the firmware's codes
NAMES = ('black', 'white', 'yellow', 'red', 'blue', 'green')

# Photos are averaged down, in linear light, to about this many pixels on the
# long side before measuring; a cell still covers thousands of them
MAX_SIDE = 1600
# Share of a cell's width and height that is read, centred, so a corner
# marked a little off or a mat covering the panel's edge does not matter
CELL_CORE = 0.4
SAMPLES = 24    # per cell and axis

# Checks, see _read_photo():
# a white cell brighter than CLIPPED (linear) has lost its highlights, one
# darker than DARK is too underexposed to trust; a solid cell whose middle
# varies by more than GLARE of the white's brightness has a reflection on it;
# when even the best of the eight placements of the card is further than
# UNRECOGNISED (mean CIELAB difference from the default palette) the corners
# are not on the card, and a single colour further than UNEXPECTED is not
# something a panel shows; a photo further than OUTLIER from the others'
# median is left out
CLIPPED = 0.97
DARK = 0.03
GLARE = 0.12
UNRECOGNISED = 25.0
UNEXPECTED = 30.0
OUTLIER = 8.0
DOT_GAIN_RANGE = (0.03, 0.25)
# A photo with any of these is not used at all
BLOCKING = ('unreadable', 'corners', 'unrecognised', 'overexposed', 'too_dark', 'glare', 'unexpected')

_lock = threading.Lock()
_SRGB = ImageCms.createProfile('sRGB')
_TO_LINEAR = dither._to_linear(np.arange(256) / 255.0).astype(np.float32)


# ------------------------------------------------------------------ storage

def defaults():
    """ The values measured on the panel this was developed with """
    return {'palette': [list(colour) for colour in imaging.CALIBRATED_PALETTE],
            'dot_gain': dither.DOT_GAIN, 'measured_at': None, 'photos_used': 0, 'default': True}

def current():
    """ The calibration in use: the saved one, or the defaults """
    with _lock:
        try:
            with open(CALIBRATION_PATH, 'r', encoding='utf-8') as handle:
                stored = json.load(handle)
        except FileNotFoundError:
            return defaults()
        except Exception as error:
            print(f"Could not read the calibration: {error}")
            return defaults()
    try:
        palette = [[int(value) for value in colour] for colour in stored['palette']]
        dot_gain = float(stored['dot_gain'])
        if not math.isfinite(dot_gain):
            raise ValueError('dot_gain')
        if len(palette) != len(NAMES) or any(
                len(colour) != 3 or not all(0 <= value <= 255 for value in colour) for colour in palette):
            raise ValueError('palette')
    except (KeyError, TypeError, ValueError) as error:
        print(f"Ignoring a malformed calibration: {error}")
        return defaults()
    return {'palette': palette, 'dot_gain': dot_gain, 'measured_at': stored.get('measured_at'),
            'photos_used': stored.get('photos_used', 0), 'default': False}

def version():
    """
    Changes whenever the calibration in use does, to tell that a prepared image
    is stale: the values themselves, so that a hand edit of calibration.json
    that keeps measured_at counts too
    """
    measured = current()
    return json.dumps([measured['palette'], measured['dot_gain']])

def save(result):
    """ Keep a measurement from measure() as the calibration in use """
    record = {key: result[key] for key in ('palette', 'dot_gain', 'measured_at', 'photos_used')}
    with _lock:
        os.makedirs(os.path.dirname(CALIBRATION_PATH), exist_ok=True)
        # one line per key, so the palette can be read and edited by hand
        lines = (f' {json.dumps(key)}: {json.dumps(value)}' for key, value in record.items())
        with open(CALIBRATION_PATH, 'w', encoding='utf-8') as handle:
            handle.write('{\n' + ',\n'.join(lines) + '\n}\n')

def reset():
    """ Go back to the defaults """
    with _lock:
        try:
            os.remove(CALIBRATION_PATH)
        except FileNotFoundError:
            pass


# -------------------------------------------------------------- measurement

def open_photo(data):
    """
    Decode an uploaded photo: upright, converted to sRGB from its colour profile
    (iPhones save Display P3), then to linear light and averaged down to about
    MAX_SIDE pixels. Averaging has to happen in linear light: a checkerboard
    the camera resolved would otherwise come out too dark.
    """
    image = Image.open(io.BytesIO(data))
    profile = image.info.get('icc_profile')
    image = ImageOps.exif_transpose(image).convert('RGB')
    if profile:
        try:
            ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                                      _SRGB, outputMode='RGB', inPlace=True)
        except (ImageCms.PyCMSError, OSError, ValueError) as error:
            print(f"Colour profile not applied, reading the photo as sRGB: {error}")
    pixels = np.asarray(image)
    step = max(1, -(-max(pixels.shape[:2]) // MAX_SIDE))
    if step == 1:
        return _TO_LINEAR[pixels]
    # A band of rows at a time: the whole photo in float32 is four times its
    # decoded size, 580 MB for a 48 MP one
    h, w = pixels.shape[0] // step * step, pixels.shape[1] // step * step
    band = step * max(1, 64 // step)
    return np.concatenate([
        _TO_LINEAR[pixels[y:min(y + band, h), :w]].reshape(-1, step, w // step, step, 3).mean(axis=(1, 3))
        for y in range(0, h, band)])

def _homography(src, dst):
    """ The 3x3 projective map taking four points src to dst """
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(rows, dtype=np.float64))
    return vt[-1].reshape(3, 3) / vt[-1, -1]

def _around(points):
    """ The four points in order around their centre """
    centre = points.mean(axis=0)
    return points[np.argsort(np.arctan2(points[:, 1] - centre[1], points[:, 0] - centre[0]))]

def _cells(lin, card_to_photo):
    """ Median and spread of the middle of each card cell, keyed by its layout entry """
    lo, hi = 0.5 - CELL_CORE / 2, 0.5 + CELL_CORE / 2
    offsets = np.linspace(lo, hi, SAMPLES)
    du, dv = np.meshgrid(offsets, offsets)
    found = {}
    for r, row in enumerate(imaging.CARD_LAYOUT):
        for c, cell in enumerate(row):
            uv = np.stack([(c + du.ravel()) / 3, (r + dv.ravel()) / 3, np.ones(du.size)])
            xyw = card_to_photo @ uv
            x = np.round(xyw[0] / xyw[2]).astype(int)
            y = np.round(xyw[1] / xyw[2]).astype(int)
            if x.min() < 0 or y.min() < 0 or x.max() >= lin.shape[1] or y.max() >= lin.shape[0]:
                return None
            values = lin[y, x]
            spread = np.percentile(values, 90, axis=0) - np.percentile(values, 10, axis=0)
            found[cell] = (np.median(values, axis=0), spread.max())
    return found

def _dot_gain(rel):
    """
    The dot gain that best explains the two checkerboards with white: each
    pixel has two edges to the other colour, each moving the gain's share of
    a pixel from white to that colour, on top of the plain mix in linear light
    """
    measured, spread = [], []
    for colour in ('black', 'red'):
        measured.append(rel[(colour, 'white')] - (rel[colour] + rel['white']) / 2)
        spread.append(2 * (rel[colour] - rel['white']))
    measured, spread = np.concatenate(measured), np.concatenate(spread)
    return float((measured * spread).sum() / (spread * spread).sum())

def _to_srgb8(lin):
    lin = np.clip(lin, 0, 1)
    return np.round(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055) * 255).astype(int)

def _expected_lab():
    return dither._lab(dither._to_linear(np.asarray(imaging.CALIBRATED_PALETTE, dtype=np.float64) / 255.0))

def _read_photo(lin, corners):
    """
    Measure one photo. corners are the card's four corners as fractions of the
    photo's width and height, in any order. Returns the photo's palette (linear
    light, relative to its white), dot gain and the problems found.
    """
    report = {'problems': []}
    h, w = lin.shape[:2]
    try:
        points = np.array(corners, dtype=np.float64).reshape(4, 2) * [w, h]
    except (TypeError, ValueError):
        points = None
    if points is None or not np.isfinite(points).all():
        report['problems'].append('corners')
        return report
    points = _around(points)
    # blur each panel pixel's worth, so checkerboards are read as the eye mixes them
    x0, y0 = np.floor(points.min(axis=0)).astype(int)
    x1, y1 = np.ceil(points.max(axis=0)).astype(int)
    d1, d2 = points[2] - points[0], points[3] - points[1]
    area = abs(d1[0] * d2[1] - d1[1] * d2[0]) / 2
    pixels_per_dot = np.sqrt(area / (imaging.EPD_W * imaging.EPD_H))
    sigma = max(1.0, 1.2 * pixels_per_dot)
    pad = int(3 * sigma) + 1
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    if x1 - x0 < 30 or y1 - y0 < 30:
        report['problems'].append('corners')
        return report
    crop = lin[y0:y1, x0:x1]
    blurred = np.stack([dither._blur(crop[..., i].astype(np.float64), sigma) for i in range(3)], axis=-1)
    points -= [x0, y0]

    card = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=np.float64)
    expected = _expected_lab()
    best = None
    for start in range(4):
        for turn in (1, -1):
            placed = points[[(start + turn * i) % 4 for i in range(4)]]
            cells = _cells(blurred, _homography(card, placed))
            if cells is None:
                continue
            white = np.maximum(cells['white'][0], 1e-6)
            rel = {cell: value / white for cell, (value, _) in cells.items()}
            solids = dither._lab(np.array([rel[name] for name in NAMES]))
            differences = np.sqrt(((solids - expected) ** 2).sum(axis=1))
            if best is None or differences.mean() < best[0]:
                best = (differences.mean(), differences, cells, rel)
    if best is None:
        report['problems'].append('corners')
        return report

    fit, differences, cells, rel = best
    white = cells['white'][0]
    white_level = float(white @ [0.2126, 0.7152, 0.0722])
    glare = max(cells[name][1] for name in NAMES) / max(white_level, 1e-6)
    report.update({
        'palette_lin': np.array([rel[name] for name in NAMES]),
        'dot_gain': _dot_gain(rel),
        'fit': round(float(fit), 1),
        'white_level': round(white_level, 3),
        'glare': round(float(glare), 3),
    })
    if fit > UNRECOGNISED:
        report['problems'].append('unrecognised')
    elif differences.max() > UNEXPECTED:
        report['problems'].append('unexpected')
    if white.max() > CLIPPED:
        report['problems'].append('overexposed')
    if white_level < DARK:
        report['problems'].append('too_dark')
    if glare > GLARE:
        report['problems'].append('glare')
    if not DOT_GAIN_RANGE[0] <= report['dot_gain'] <= DOT_GAIN_RANGE[1]:
        report['problems'].append('dot_gain_range')
    return report

def _mean_difference(a, b):
    return float(np.sqrt(((dither._lab(a) - dither._lab(b)) ** 2).sum(axis=-1)).mean())

def measure(photos):
    """
    Measure photos of the calibration card: a list of (name, bytes, corners).
    Returns the combined palette and dot gain, ready for save(), with a report
    per photo; 'usable' is False when no photo could be used.
    """
    reports = []
    for name, data, corners in photos:
        try:
            report = _read_photo(open_photo(data), corners)
        except Exception as error:
            print(f"Calibration photo {name} unreadable: {error}")
            report = {'problems': ['unreadable']}
        report['name'] = name
        reports.append(report)

    used = [r for r in reports if not set(r['problems']) & set(BLOCKING)]
    warnings = []
    if len(used) >= 3:
        middle = np.median([r['palette_lin'] for r in used], axis=0)
        for r in used:
            if _mean_difference(r['palette_lin'], middle) > OUTLIER:
                r['problems'].append('outlier')
        used = [r for r in used if 'outlier' not in r['problems']]
    elif len(used) == 2 and _mean_difference(used[0]['palette_lin'], used[1]['palette_lin']) > OUTLIER:
        warnings.append('disagree')

    result = {'usable': bool(used), 'palette': None, 'dot_gain': None, 'warnings': warnings,
              'measured_at': datetime.now().isoformat(timespec='seconds'), 'photos_used': len(used)}
    if used:
        result['palette'] = _to_srgb8(np.median([r['palette_lin'] for r in used], axis=0)).tolist()
        gains = [r['dot_gain'] for r in used if 'dot_gain_range' not in r['problems']]
        if gains:
            result['dot_gain'] = round(float(np.median(gains)), 3)
        else:
            result['dot_gain'] = dither.DOT_GAIN
            warnings.append('dot_gain_default')
    result['photos'] = [{
        'name': r['name'],
        'used': any(r is u for u in used),
        'problems': r['problems'],
        'palette': _to_srgb8(r['palette_lin']).tolist() if 'palette_lin' in r else None,
        'dot_gain': round(r['dot_gain'], 3) if 'dot_gain' in r else None,
        **{key: r[key] for key in ('fit', 'white_level', 'glare') if key in r},
    } for r in reports]
    return result
