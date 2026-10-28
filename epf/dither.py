"""
Floyd-Steinberg dithering to the panel's six colours, compiled with Numba.

Two algorithms, both returning the image in the six *pure* colours, which is
what the packing step maps onto the panel's colour codes:

classic   The former Cython module's convert_image (cpy.pyx), line for line:
          nearest colour and error measured against the pure palette, each
          error share truncated to an int and stored back into 8-bit pixels.
          The output is byte-identical to the Cython version's.

classic_cc
          Classic, unchanged, with a colour-correction table in front of it,
          built the way a printer profile is. Classic measures its error
          against pure primaries and mixes sRGB numbers, so on this panel
          skin turns yellow; its lightness and texture are what people
          prefer, though. The table is made from the panel model: a uniform
          patch of every colour on a 17^3 grid is dithered with classic and
          its look on the panel worked out (calibrated colours, dot gain,
          linear-light mixing); then for every grid colour the input is
          found whose patch has classic's own lightness for that colour but
          the colour's hue and chroma. Hue and chroma are measured from the
          grey classic shows at the same lightness, since the panel's greys
          are purplish and neutralising them would only sprinkle green dots
          into the shadows. Built once per setting (about four seconds) and
          kept. The palette and dot gain come from the panel's calibration
          (epf/calibration.py), and four adjustments fine-tune it without
          one: the share of the correction applied, a chroma multiplier, and
          CIELAB b* (warmth) and a* (tint) offsets; see dither().

Numba compiles each function on first use (about a second) and caches the
machine code in __pycache__, so later processes start quickly.
"""
import numpy as np
from numba import njit

# Index order shared with imaging.palette and the firmware's colour codes:
# black, white, yellow, red, blue, green
PURE = np.array([
    [0, 0, 0],
    [1, 1, 1],
    [1, 1, 0],
    [1, 0, 0],
    [0, 0, 1],
    [0, 1, 0],
], dtype=np.float64)
PURE8 = (PURE * 255).astype(np.uint8)

WHITE = 1
# Share of a pixel's area a black or coloured dot takes from a white dot it
# shares an edge with, measured on the calibration card's black/white and
# red/white checkerboards (2026-10-06; 0.11-0.16 across the two cleanest shots,
# the same for black and red). Edges between two non-white dots showed no
# consistent effect and are left out.
DOT_GAIN = 0.13

# classic_cc: points per channel in the correction table, and how strongly an
# input is held near the photo's own colour where the panel cannot reach the
# wanted one (squared CIELAB units per squared sRGB step)
CC_GRID = 17
CC_STAY = 0.01
# classic_cc's adjustments when none are given: the whole correction, chroma
# as in the photo, no shift in warmth or tint
CC_NEUTRAL = {'strength': 1.0, 'chroma': 1.0, 'warmth': 0.0, 'tint': 0.0}
# Tables kept, newest last; moving a slider back and forth reuses them
CC_TABLES_KEPT = 4
_cc_tables = {}


@njit(cache=True)
def _classic(px, pal, strength):
    """ The former cpy.pyx convert_image, translated. px is int64 0..255, modified in place. """
    h, w, _ = px.shape
    idx = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            min_diff = 1e10
            best = 0
            for c in range(pal.shape[0]):
                diff = 0.0
                for i in range(3):
                    diff += (px[y, x, i] / 255.0 - pal[c, i]) ** 2
                if diff < min_diff:
                    min_diff = diff
                    best = c
            idx[y, x] = best
            for c in range(3):
                scaled = (px[y, x, c] / 255.0 - pal[best, c]) * strength
                if x + 1 < w:
                    px[y, x + 1, c] = min(max(px[y, x + 1, c] + int(scaled * 7 / 16 * 255), 0), 255)
                if x - 1 >= 0 and y + 1 < h:
                    px[y + 1, x - 1, c] = min(max(px[y + 1, x - 1, c] + int(scaled * 3 / 16 * 255), 0), 255)
                if y + 1 < h:
                    px[y + 1, x, c] = min(max(px[y + 1, x, c] + int(scaled * 5 / 16 * 255), 0), 255)
                if x + 1 < w and y + 1 < h:
                    px[y + 1, x + 1, c] = min(max(px[y + 1, x + 1, c] + int(scaled * 1 / 16 * 255), 0), 255)
    return idx


def dither(image, mode='classic', strength=1.0, measured_palette=None, dot_gain=DOT_GAIN,
           correction=None):
    """
    Dither a PIL image to the panel's six colours.

    Returns an HxWx3 uint8 array holding only the six pure colours.
    measured_palette is the panel's measured colours as 0..255 RGB triples, in
    PURE's index order; required for classic_cc. dot_gain is the
    panel's (see DOT_GAIN). correction holds classic_cc's adjustments, any of
    CC_NEUTRAL's keys: 'strength' the share of the correction applied (0 is
    plain classic), 'chroma' a multiplier on the photo's chroma, 'warmth' and
    'tint' CIELAB b* and a* offsets (positive is warmer, more magenta).
    """
    rgb = np.asarray(image.convert('RGB'))
    if mode == 'classic_cc':
        adjust = dict(CC_NEUTRAL, **(correction or {}))
        px = rgb.astype(np.int64)
        if adjust['strength'] > 0:
            table = _classic_table(strength, measured_palette, dot_gain,
                                   adjust['chroma'], adjust['warmth'], adjust['tint'])
            rgb_f = rgb.astype(np.float64)
            corrected = rgb_f + adjust['strength'] * (_trilinear(table, rgb_f) - rgb_f)
            px = np.clip(np.round(corrected), 0, 255).astype(np.int64)
        idx = _classic(px, PURE, float(strength))
    else:
        idx = _classic(rgb.astype(np.int64), PURE, float(strength))
    return PURE8[idx]


def _to_linear(c):
    """ sRGB 0..1 to linear light 0..1 """
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# Linear sRGB to CIE XYZ, and the D65 white, for the CIELAB conversions
_XYZ = np.array([[0.4124, 0.3576, 0.1805],
                 [0.2126, 0.7152, 0.0722],
                 [0.0193, 0.1192, 0.9505]])
_D65 = np.array([0.95047, 1.0, 1.08883])


def _lab(lin):
    """ CIELAB of linear-light RGB """
    xyz = lin @ _XYZ.T / _D65
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def _panel_mean(idx, pal_lin, gain, crop):
    """
    Mean linear light of patches idx (P, h, w) as the panel shows them: each
    edge between a white dot and another colour moves gain of a pixel's area
    to that colour (see DOT_GAIN). crop trims the dither's first rows and
    columns, where its error has not built up yet.
    """
    lin = pal_lin[idx]
    white = idx == WHITE
    for axis in (1, 2):
        n = idx.shape[axis]
        a = np.take(idx, np.arange(n - 1), axis=axis)
        b = np.take(idx, np.arange(1, n), axis=axis)
        wa = np.take(white, np.arange(n - 1), axis=axis)
        wb = np.take(white, np.arange(1, n), axis=axis)
        to_first = (wa & ~wb)[..., None] * gain * (pal_lin[b] - pal_lin[WHITE])
        to_second = (wb & ~wa)[..., None] * gain * (pal_lin[a] - pal_lin[WHITE])
        first, second = [(0, 0)] * 4, [(0, 0)] * 4
        first[axis], second[axis] = (0, 1), (1, 0)
        lin = lin + np.pad(to_first, first) + np.pad(to_second, second)
    return lin[:, crop:-crop, crop:-crop].mean(axis=(1, 2))


def _trilinear(table, rgb):
    """ Look a (G, G, G, k) table up at 0..255 colours rgb (..., 3) """
    g = table.shape[0]
    t = np.clip(rgb / 255.0 * (g - 1), 0, g - 1 - 1e-9)
    i = t.astype(np.int64)
    f = t - i
    out = 0.0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = ((f[..., 0] if dr else 1 - f[..., 0])
                     * (f[..., 1] if dg else 1 - f[..., 1])
                     * (f[..., 2] if db else 1 - f[..., 2]))
                out = out + w[..., None] * table[i[..., 0] + dr, i[..., 1] + dg, i[..., 2] + db]
    return out


def _smooth_table(table, sigma=0.7):
    """ Gaussian smoothing of a (G, G, G, k) table along its colour axes, edges extended """
    r = 2
    k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma ** 2))
    k /= k.sum()
    g = table.shape[0]
    for axis in range(3):
        pad = [(0, 0)] * 4
        pad[axis] = (r, r)
        p = np.pad(table, pad, mode='edge')
        table = sum(k[j] * np.take(p, np.arange(j, j + g), axis=axis) for j in range(2 * r + 1))
    return table


def _classic_table(strength, measured_palette, dot_gain, chroma, warmth, tint):
    """ The classic_cc correction table for these settings, built on first use """
    key = (round(float(strength), 3), tuple(tuple(int(v) for v in c) for c in measured_palette),
           round(float(dot_gain), 4), round(float(chroma), 3), round(float(warmth), 2),
           round(float(tint), 2))
    if key in _cc_tables:
        return _cc_tables[key]
    pal_lin = _to_linear(np.asarray(measured_palette, dtype=np.float64) / 255.0)
    levels = np.linspace(0, 255, CC_GRID)
    grid = np.stack(np.meshgrid(levels, levels, levels, indexing='ij'), -1).reshape(-1, 3)

    # forward: how classic's patch of each grid colour looks on the panel
    size = 40
    idx = np.empty((len(grid), size, size), dtype=np.uint8)
    patch = np.empty((size, size, 3), dtype=np.int64)
    for k, colour in enumerate(grid):
        patch[:] = np.round(colour).astype(np.int64)
        idx[k] = _classic(patch, PURE, float(strength))
    shown = _lab(_panel_mean(idx, pal_lin, float(dot_gain), 6)).reshape(CC_GRID, CC_GRID, CC_GRID, 3)

    # wanted: classic's own lightness, the colour's hue and chroma measured
    # from the grey classic shows at that lightness, then the adjustments
    want = _lab(_to_linear(grid / 255.0))
    want[:, 0] = shown.reshape(-1, 3)[:, 0]
    want[:, 1:] *= chroma
    diagonal = np.arange(CC_GRID)
    grey = shown[diagonal, diagonal, diagonal]
    grey_l = np.maximum.accumulate(grey[:, 0])
    want[:, 1] += np.interp(want[:, 0], grey_l, grey[:, 1]) + tint
    want[:, 2] += np.interp(want[:, 0], grey_l, grey[:, 2]) + warmth

    # inverse: damped Gauss-Newton on the interpolated forward table
    c = grid.copy()
    for _ in range(40):
        err = want - _trilinear(shown, c)
        jac = np.empty((len(c), 3, 3))
        for k in range(3):
            h = np.zeros(3)
            h[k] = 6.0
            jac[:, :, k] = (_trilinear(shown, c + h) - _trilinear(shown, c - h)) / 12.0
        jt = np.transpose(jac, (0, 2, 1))
        rhs = (jt @ err[..., None])[..., 0] - CC_STAY * (c - grid)
        step = np.linalg.solve(jt @ jac + (CC_STAY + 0.05) * np.eye(3), rhs[..., None])[..., 0]
        c = np.clip(c + np.clip(step, -24, 24), 0, 255)
    table = _smooth_table(c.reshape(CC_GRID, CC_GRID, CC_GRID, 3))
    while len(_cc_tables) >= CC_TABLES_KEPT:
        _cc_tables.pop(next(iter(_cc_tables)))
    _cc_tables[key] = table
    return table


def _blur(a, sigma):
    """ Gaussian blur of a 2-D array, edges extended """
    r = int(3 * sigma)
    k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma ** 2))
    k /= k.sum()
    p = np.pad(a, r, mode='edge')
    rows = sum(k[j] * p[j:j + a.shape[0], :] for j in range(2 * r + 1))
    return sum(k[j] * rows[:, j:j + a.shape[1]] for j in range(2 * r + 1))

