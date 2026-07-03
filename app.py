# -*- coding:utf8 -*-
import hmac
import io
import json
import os
import random
import threading
from datetime import datetime, timedelta
from functools import wraps

import numpy as np
import rawpy
import requests
import yaml
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_file, url_for
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
from pillow_heif import register_heif_opener
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    from cpy import convert_image, load_scaled
except ImportError as exc:
    from cpy_fallback import convert_image, load_scaled

    print(f'Using pure Python image processing fallback: {exc}')
import time

import ntplib

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)


DEFAULT_CONFIG = {
    'immich': {
        'url': 'http://192.168.1.10',  # Immich server URL ("localhost" is forbidden)
        'album': 'default_album',  # Album name
        'rotation': 270,  # 0/90/180/270
        'enhanced': 1.3,  # From 0.0 .. 1.0
        'contrast': 0.9,  # From 0.0 .. 1.0
        'strength': 0.8,  # From 0.0 .. 1.0
        'display_mode': 'fill',  # Add display mode setting (fit/fill)
        'image_order': 'random',  # Add image display order setting (random/newest)
        'sleep_start_hour': 23,  # Sleep start time 23:00 (11:00 PM)
        'sleep_start_minute': 0,  # Sleep start time 23:00 (11:00 PM)
        'sleep_end_hour': 6,  # Sleep end time 6:00 (6:00 AM)
        'sleep_end_minute': 0,  # Sleep end time 6:00 (6:00 AM)
        'wakeup_interval': 60,  # Default 60 minutes (1 hour)
        'date_overlay_enabled': False,  # D-01: overlay off by default
        'geo_overlay_enabled': True,  # location visible by default when date overlay is on
        'date_overlay_position': 'bottomRight',  # D-05: default position
        'overlay_style': 'background',  # D-04/D-14: "background" | "outline"
        'overlay_bg_color': 'black',  # D-06/D-14: rect fill (background mode)
        'overlay_text_color': 'white',  # D-06/D-07/D-14: text glyph fill (both modes)
        'overlay_border_color': 'white',  # D-08/D-14: stroke color (outline mode)
        'overlay_stroke_width': 2,  # D-09/D-11/D-14: stroke px (outline mode), int
        'overlay_font_size': 26,  # D-12/D-13/D-14: font px, int
        'overlay_language': 'en',  # 'en' | 'de' — Nominatim reverse-geocode language (GEO-LANG)
        'blur_radius': 30,  # px, int — GaussianBlur radius for fit mode blurred background
        'overlay_margin_h': 0,  # D-02/D-08: horizontal passe-partout inset (px), int
        'overlay_margin_v': 0,  # D-02/D-08: vertical passe-partout inset (px), int
        'battery_indicator_enabled': 'on',        # D-15/D-16: show low-battery icon; select on/off
        'battery_indicator_position': 'topRight',  # D-08/D-09/D-16: POSITIONS key, default topRight
    }
}


def parse_photo_date(raw_str):
    """Return 'DD.MM.YYYY' string from a date input, or None if unparseable.

    Accepts:
      - EXIF format: 'YYYY:MM:DD HH:MM:SS'   (PIL exif tag 36867)
      - ISO 8601:   'YYYY-MM-DDTHH:MM:SS.sssZ' or 'YYYY-MM-DD...'  (Immich exifInfo.dateTimeOriginal)
    Returns None for None, empty string, or unparseable input.
    """
    if not raw_str or not isinstance(raw_str, str) or len(raw_str) < 10:
        return None
    # EXIF format: separator is ':' at index 4
    if raw_str[4] == ':':
        try:
            return datetime.strptime(raw_str[:10], '%Y:%m:%d').strftime('%d.%m.%Y')
        except ValueError:
            return None
    # ISO 8601: separator is '-' at index 4
    if raw_str[4] == '-':
        try:
            return datetime.strptime(raw_str[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Geolocation helpers (Phase 7 — D-10..D-16)
# ---------------------------------------------------------------------------

_GEO_CACHE = None  # lazily-loaded geo_cache.json dict


def extract_gps_from_exif(image):
    """Return (lat_float, lon_float) tuple or None. Never raises."""
    try:
        exif = image._getexif()
        if not exif:
            return None
        gps_info = exif.get(34853)
        if not gps_info:
            return None
        lat_dms = gps_info.get(2)
        lat_ref = gps_info.get(1, 'N')
        lon_dms = gps_info.get(4)
        lon_ref = gps_info.get(3, 'E')
        if not lat_dms or not lon_dms:
            return None
        lat = float(lat_dms[0]) + float(lat_dms[1]) / 60.0 + float(lat_dms[2]) / 3600.0
        lon = float(lon_dms[0]) + float(lon_dms[1]) / 60.0 + float(lon_dms[2]) / 3600.0
        if lat_ref == 'S':
            lat = -lat
        if lon_ref == 'W':
            lon = -lon
        return (lat, lon)
    except (AttributeError, Exception):
        return None


def _geo_cache_path():
    dest = os.environ.get('IMMICH_PHOTO_DEST', '')
    base = dest if dest else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'geo_cache.json')


def _load_geo_cache():
    global _GEO_CACHE
    if _GEO_CACHE is None:
        try:
            with open(_geo_cache_path(), 'r', encoding='utf-8') as f:
                _GEO_CACHE = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _GEO_CACHE = {}
    return _GEO_CACHE


def _save_geo_cache(cache):
    try:
        with open(_geo_cache_path(), 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[WARN] Could not save geo_cache.json: {e}')


def reverse_geocode_cached(lat, lon):
    """Return 'City, Country' string or None. Persistent JSON cache; null cached on failure.

    Cache key is language-suffixed (e.g. '48.135,11.582:en') so 'en' and 'de' results coexist.
    Language is read from the module-level `overlay_language` global (default 'en').
    """
    key = f'{round(float(lat), 3)},{round(float(lon), 3)}:{overlay_language}'
    cache = _load_geo_cache()
    if key in cache:
        return cache[key]
    result = None
    try:
        geolocator = Nominatim(user_agent='epf-photo-frame/1.0', timeout=5)  # type: ignore[arg-type]
        location = geolocator.reverse((lat, lon), exactly_one=True, language=overlay_language)  # type: ignore[arg-type]
        if location:
            addr = location.raw.get('address', {})  # type: ignore[union-attr]
            city = addr.get('city') or addr.get('town') or addr.get('village')
            country = addr.get('country')
            if city and country:
                result = f'{city}, {country}'
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        print(f'[WARN] Nominatim geocoding failed for ({lat},{lon}): {e}')
    cache[key] = result
    _save_geo_cache(cache)
    return result


def parse_photo_location(local_image=None, immich_exif=None):
    """Return 'City, Country' string or None.

    Priority: Immich exifInfo city/country first; local GPS EXIF second.
    Follows parse_photo_date() None-propagation contract.
    """
    if immich_exif:
        city = immich_exif.get('city') or ''
        country = immich_exif.get('country') or ''
        if city and country:
            return f'{city}, {country}'
        if city:
            return city
        if country:
            return country
    if local_image is not None:
        coords = extract_gps_from_exif(local_image)
        if coords:
            return reverse_geocode_cached(coords[0], coords[1])
    return None


# Battery indicator warning thresholds (percent). Hardcoded, not configurable (D-06).
BATTERY_LOW_THRESHOLD = 20   # battery_pct <= this and > FLAT -> partial-fill warning icon
BATTERY_FLAT_THRESHOLD = 5   # battery_pct <= this -> empty (flat) battery outline

# 9-position anchor lookup for date overlay (DO-04).
# Each lambda returns (x, y) of the text's top-left given image w/h, text bbox w/h,
# padding p, and optional inset margins mh (horizontal) and mv (vertical).
# mh and mv are additive to p for edge positions; center ignores both;
# axis-center positions (topCenter/bottomCenter/centerLeft/centerRight) use only
# the relevant axis margin.
POSITIONS = {
    'topLeft': lambda w, h, tw, th, p, mh, mv: (p + mh, p + mv),
    'topCenter': lambda w, h, tw, th, p, mh, mv: ((w - tw) // 2, p + mv),
    'topRight': lambda w, h, tw, th, p, mh, mv: (w - tw - p - mh, p + mv),
    'centerLeft': lambda w, h, tw, th, p, mh, mv: (p + mh, (h - th) // 2),
    'center': lambda w, h, tw, th, p, mh, mv: ((w - tw) // 2, (h - th) // 2),
    'centerRight': lambda w, h, tw, th, p, mh, mv: (w - tw - p - mh, (h - th) // 2),
    'bottomLeft': lambda w, h, tw, th, p, mh, mv: (p + mh, h - th - p - mv),
    'bottomCenter': lambda w, h, tw, th, p, mh, mv: ((w - tw) // 2, h - th - p - mv),
    'bottomRight': lambda w, h, tw, th, p, mh, mv: (w - tw - p - mh, h - th - p - mv),
}


def draw_date_overlay(
    output_img,
    text,
    font,
    position_str,
    padding=6,
    rotation=0,
    style='background',
    bg_color=(0, 0, 0, 255),
    text_color=(255, 255, 255, 255),
    border_color=(255, 255, 255, 255),
    stroke_width=2,
    margin_h=0,
    margin_v=0,
):
    """Draw a date overlay (filled-background or outline style) at position_str.

    Accounts for display rotation so that position_str refers to the viewer's
    visual corner (e.g. 'bottomRight' always appears at the viewer's bottom-right
    regardless of rotationAngle), and text is rendered upright from the viewer's
    perspective.

    Args:
        output_img:   PIL.Image (RGB mode). Mutated in place.
        text:         String to render (e.g. '05.01.2022').
        font:         PIL ImageFont instance.
        position_str: One of POSITIONS keys; unknown values fall back to 'bottomRight'.
        padding:      Pixels of background around the text on all sides.
        rotation:     Display rotation angle in degrees (0, 90, 180, 270).
                      Must match the rotationAngle used by load_scaled so that
                      the overlay is placed correctly in viewer space.
        style:        "background" (filled rect + text) or "outline" (stroke text only).
        bg_color:     RGBA tuple for the filled rectangle in background mode.
        text_color:   RGBA tuple for the text glyph fill in both modes.
        border_color: RGBA tuple for the stroke in outline mode.
        stroke_width: Stroke width in pixels used in outline mode.
        margin_h:     Extra horizontal inset (px) from left/right display edge, additive to padding.
        margin_v:     Extra vertical inset (px) from top/bottom display edge, additive to padding.
    """
    bw, bh = output_img.size  # buffer dimensions (always 1200x1600)

    # Viewer canvas dimensions depend on rotation: 90° and 270° CCW transpose W and H.
    if rotation in (90, 270):
        vw, vh = bh, bw  # viewer perceives a transposed (landscape) display
    else:
        vw, vh = bw, bh  # viewer perceives same dimensions as buffer

    # --- Step 1: measure text in viewer space ---
    _probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    sw = stroke_width if style == 'outline' else 0
    bbox = _probe.textbbox((0, 0), text, font=font, stroke_width=sw)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # --- Step 2: compute overlay position in viewer space ---
    get_xy = POSITIONS.get(position_str, POSITIONS['bottomRight'])
    x, y = get_xy(vw, vh, tw, th, padding, margin_h, margin_v)

    # --- Step 3: draw upright text on a viewer-oriented RGBA canvas ---
    viewer_canvas = Image.new('RGBA', (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(viewer_canvas)
    rect = [x - padding, y - padding, x + tw + padding, y + th + padding]
    if style == 'background':
        draw.rectangle(rect, fill=bg_color)
        draw.text((x - bbox[0], y - bbox[1]), text, fill=text_color, font=font)
    else:  # outline — no rectangle, stroke provides separation (D-07)
        draw.text(
            (x - bbox[0], y - bbox[1]),
            text,
            fill=text_color,
            font=font,
            stroke_width=stroke_width,
            stroke_fill=border_color,
        )

    # --- Step 4: rotate viewer canvas into buffer orientation ---
    # load_scaled rotated the image content by `rotation`° CCW; apply the same
    # rotation to the overlay canvas so it lands in the matching buffer location.
    if rotation != 0:
        viewer_canvas = viewer_canvas.rotate(rotation, expand=True)

    # --- Step 5: paste overlay onto output_img using alpha mask ---
    # viewer_canvas is now buffer-sized; paste only where alpha > 0.
    overlay_rgb = viewer_canvas.convert('RGB')
    mask = viewer_canvas.split()[3]  # alpha channel as mask
    output_img.paste(overlay_rgb, mask=mask)


def draw_battery_indicator(output_img, battery_pct, position_str, rotation, font_size, color):
    """Draw a battery warning icon onto output_img (PIL RGB Image, mutated in place).

    Warning-only: only renders when battery level is low or flat.

    Three states (BATIND-01, D-02):
      - battery_pct > BATTERY_LOW_THRESHOLD (20): no-op — image is left byte-identical (D-19)
      - BATTERY_FLAT_THRESHOLD < battery_pct <= BATTERY_LOW_THRESHOLD: body outline + nub + partial fill bar
      - battery_pct <= BATTERY_FLAT_THRESHOLD (5): body outline + nub only, no fill (empty/flat icon)

    Icon is rotation-aware via the same viewer-space coordinate technique as draw_date_overlay():
    'topRight' always means the viewer's top-right regardless of rotationAngle (D-11).

    Args:
        output_img:   PIL.Image (RGB mode). Mutated in place.
        battery_pct:  Battery percentage (0-100 float or int).
        position_str: One of POSITIONS keys; unknown values fall back to 'topRight' (D-09).
        rotation:     Display rotation angle in degrees (0, 90, 180, 270).
        font_size:    Icon height in pixels (derived from overlay_font_size, default 26) (D-12).
        color:        RGBA tuple for the icon (D-03, default white).
    """
    # --- Warning-only no-op guard (D-05 / D-19) ---
    if battery_pct > BATTERY_LOW_THRESHOLD:
        return

    # --- Step 1: Compute icon geometry from font_size (D-12, D-13) ---
    icon_h = int(font_size)
    body_w = icon_h * 2
    nub_w = max(1, int(icon_h * 0.2))   # ~20% of height
    nub_h = max(1, int(icon_h * 0.5))   # ~50% of height, vertically centered
    stroke = 2                            # 2px stroke (D-13)
    icon_w = body_w + nub_w              # total footprint including nub

    # --- Step 2: Viewer canvas dims (mirror draw_date_overlay Step 1) ---
    bw, bh = output_img.size  # buffer dimensions (always 1200x1600)
    if rotation in (90, 270):
        vw, vh = bh, bw
    else:
        vw, vh = bw, bh

    # --- Step 3: Position in viewer space (mirror Step 2), default 'topRight' (D-09) ---
    padding = 10  # fixed inset from display edge
    get_xy = POSITIONS.get(position_str, POSITIONS['topRight'])
    x, y = get_xy(vw, vh, icon_w, icon_h, padding, 0, 0)

    # --- Step 4: Draw battery icon on an RGBA viewer canvas (mirror Step 3) ---
    viewer_canvas = Image.new('RGBA', (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(viewer_canvas)

    # Battery body outline (left part of footprint):
    body = [x, y, x + body_w, y + icon_h]
    draw.rectangle(body, outline=color, width=stroke)

    # Nub on the right end (conventional orientation), vertically centered:
    nub_top = y + (icon_h - nub_h) // 2
    nub = [x + body_w, nub_top, x + body_w + nub_w, nub_top + nub_h]
    draw.rectangle(nub, outline=color, width=stroke)

    # Partial fill bar ONLY in the low (non-flat) state (D-02):
    if battery_pct > BATTERY_FLAT_THRESHOLD:
        inset = stroke + 2
        fill_frac = max(0.15, min(1.0, battery_pct / BATTERY_LOW_THRESHOLD))
        fill_w = int((body_w - 2 * inset) * fill_frac)
        if fill_w > 0:
            fill_rect = [x + inset, y + inset, x + inset + fill_w, y + icon_h - inset]
            draw.rectangle(fill_rect, fill=color)
    # battery_pct <= FLAT_THRESHOLD -> no fill (empty outline)

    # --- Step 5: Rotate viewer canvas into buffer orientation (mirror Step 4) ---
    if rotation != 0:
        viewer_canvas = viewer_canvas.rotate(rotation, expand=True)

    # --- Step 6: Paste overlay onto output_img using alpha mask (mirror Step 5) ---
    overlay_rgb = viewer_canvas.convert('RGB')
    mask = viewer_canvas.split()[3]
    output_img.paste(overlay_rgb, mask=mask)


current_config = DEFAULT_CONFIG.copy()

# Initialize configuration
url = DEFAULT_CONFIG['immich']['url']
albumname = DEFAULT_CONFIG['immich']['album']
rotationAngle = DEFAULT_CONFIG['immich']['rotation']  # noqa: N816
img_enhanced = DEFAULT_CONFIG['immich']['enhanced']
img_contrast = DEFAULT_CONFIG['immich']['contrast']
strength = DEFAULT_CONFIG['immich']['strength']
display_mode = DEFAULT_CONFIG['immich']['display_mode']
image_order = DEFAULT_CONFIG['immich']['image_order']
sleep_start_hour = DEFAULT_CONFIG['immich']['sleep_start_hour']
sleep_start_minute = DEFAULT_CONFIG['immich']['sleep_start_minute']
sleep_end_hour = DEFAULT_CONFIG['immich']['sleep_end_hour']
sleep_end_minute = DEFAULT_CONFIG['immich']['sleep_end_minute']
date_overlay_enabled = DEFAULT_CONFIG['immich']['date_overlay_enabled']
geo_overlay_enabled = DEFAULT_CONFIG['immich']['geo_overlay_enabled']
date_overlay_position = DEFAULT_CONFIG['immich']['date_overlay_position']
overlay_style = DEFAULT_CONFIG['immich']['overlay_style']
overlay_bg_color = DEFAULT_CONFIG['immich']['overlay_bg_color']
overlay_text_color = DEFAULT_CONFIG['immich']['overlay_text_color']
overlay_border_color = DEFAULT_CONFIG['immich']['overlay_border_color']
overlay_stroke_width = DEFAULT_CONFIG['immich']['overlay_stroke_width']
overlay_font_size = DEFAULT_CONFIG['immich']['overlay_font_size']
overlay_language = DEFAULT_CONFIG['immich']['overlay_language']
blur_radius = DEFAULT_CONFIG['immich']['blur_radius']
overlay_margin_h = DEFAULT_CONFIG['immich']['overlay_margin_h']
overlay_margin_v = DEFAULT_CONFIG['immich']['overlay_margin_v']
battery_indicator_enabled = DEFAULT_CONFIG['immich']['battery_indicator_enabled']
battery_indicator_position = DEFAULT_CONFIG['immich']['battery_indicator_position']

# Retrieve environment variables with error handling
apikey = os.getenv('IMMICH_API_KEY')
base_dir = os.path.dirname(os.path.abspath(__file__))
photodir = os.getenv('IMMICH_PHOTO_DEST', os.path.join(base_dir, 'photos'))
tracking_file = os.path.join(photodir, 'tracking.txt')
localdir = os.getenv('LOCAL_PHOTO_DIR', os.path.join(base_dir, 'local_photos'))
config_file = os.getenv('CONFIG_FILE', os.path.join(base_dir, 'config.yaml'))
APP_PASSWORD = os.getenv('APP_PASSWORD', '')

# Ensure directory exists
os.makedirs(photodir, exist_ok=True)
os.makedirs(localdir, exist_ok=True)

# Ensure tracking.txt exists
if not os.path.exists(tracking_file):
    open(tracking_file, 'w').close()

headers = {'Accept': 'application/json', 'x-api-key': apikey}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.jpeg', '.raw', '.jpg', '.bmp', '.dng', '.heic', '.arw', '.cr2', '.dng', '.nef', '.raw'}

# Set up the directory for the downloaded images
os.makedirs(photodir, exist_ok=True)
register_heif_opener()

# Seeed T133A01 color primaries (from Seeed_GFX dither.cpp kE6Rgb table)
# Order: black, white, yellow, red, blue, green
palette = [
    (0, 0, 0),  # index 0 → T133A01 nibble 0xF (black)
    (255, 255, 255),  # index 1 → T133A01 nibble 0x0 (white)
    (255, 216, 0),  # index 2 → T133A01 nibble 0xB (yellow)
    (229, 57, 53),  # index 3 → T133A01 nibble 0x6 (red)
    (0, 76, 255),  # index 4 → T133A01 nibble 0xD (blue)
    (29, 185, 84),  # index 5 → T133A01 nibble 0x2 (green)
]

# Source: palette above (authoritative). String name -> RGBA for overlay color resolution.
OVERLAY_COLORS = {
    'black': (0, 0, 0, 255),
    'white': (255, 255, 255, 255),
    'grey_100': (25, 25, 25, 255),
    'grey_200': (50, 50, 50, 255),
    'grey_300': (75, 75, 75, 255),
    'grey_400': (100, 100, 100, 255),
    'grey_500': (128, 128, 128, 255),
    'grey_600': (153, 153, 153, 255),
    'grey_700': (178, 178, 178, 255),
    'grey_800': (204, 204, 204, 255),
    'grey_900': (230, 230, 230, 255),
    'yellow': (255, 216, 0, 255),
    'red': (229, 57, 53, 255),
    'blue': (0, 76, 255, 255),
    'green': (29, 185, 84, 255),
}

# Battery telemetry persistence — stored alongside config.yaml in the persisted
# /data/config volume so the last reading (and the full history) survive
# container restarts. battery_state.json holds only the most recent reading;
# battery_history.csv accumulates one timestamped row per report so the
# discharge curve can be plotted to compare firmware versions objectively.
battery_state_file = os.path.join(os.path.dirname(config_file), 'battery_state.json')
battery_history_file = os.path.join(os.path.dirname(config_file), 'battery_history.csv')


def load_battery_state():
    """Return (voltage_mv, epoch_seconds) from the last persisted report, or (0, 0)."""
    try:
        with open(battery_state_file, 'r') as f:
            data = json.load(f)
        return float(data.get('voltage', 0)), float(data.get('updated', 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0.0, 0.0


def persist_battery_reading(voltage_mv, timestamp):
    """Atomically persist the latest reading and append a history row.

    The latest-value file is written via a temp file + os.replace so a crash
    mid-write can never corrupt it. The history file is append-only.
    """
    try:
        os.makedirs(os.path.dirname(battery_state_file), exist_ok=True)
        tmp_path = f'{battery_state_file}.tmp'
        with open(tmp_path, 'w') as f:
            json.dump({'voltage': voltage_mv, 'updated': timestamp}, f)
        os.replace(tmp_path, battery_state_file)

        write_header = not os.path.exists(battery_history_file)
        with open(battery_history_file, 'a') as f:
            if write_header:
                f.write('iso_time,epoch,voltage_mv,percent\n')
            iso_time = datetime.fromtimestamp(timestamp).isoformat(timespec='seconds')
            percent = calculate_battery_percentage(voltage_mv)
            f.write(f'{iso_time},{int(timestamp)},{voltage_mv:.0f},{percent}\n')
    except OSError as e:
        print(f'[WARN] Could not persist battery reading: {e}')


last_battery_voltage, last_battery_update = load_battery_state()


def require_auth(f):
    """Enforce HTTP Basic Auth when APP_PASSWORD is set.

    Opt-in: when APP_PASSWORD is empty/absent, all requests pass through.
    Returns 401 + WWW-Authenticate header on missing or wrong credentials.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        if not APP_PASSWORD:
            return f(*args, **kwargs)
        auth = request.authorization
        if auth and auth.username == 'admin' and hmac.compare_digest(auth.password or '', APP_PASSWORD):
            return f(*args, **kwargs)
        app.logger.warning('Auth failed from %s', request.remote_addr)
        response = make_response('Unauthorized', 401)
        response.headers['WWW-Authenticate'] = 'Basic realm="EPF"'
        return response

    return decorated


def load_downloaded_images():
    """Load downloaded image ID from tracking.txt"""
    global albumname
    try:
        # Ensure file exists and is readable/writable
        if not os.path.exists(tracking_file):
            open(tracking_file, 'w').close()

        # Ensure file has correct permissions
        os.chmod(tracking_file, 0o666)

        with open(tracking_file, 'r+') as f:
            lines = f.readlines()

            # If file is empty or first line is not current album name, return empty set
            if not lines or lines[0].strip() != albumname:
                # Rewrite album name
                f.seek(0)
                f.truncate()
                f.write(f'{albumname}\n')
                return set()

            # Return all lines except the first as downloaded image IDs
            return set(line.strip() for line in lines[1:] if line.strip())
    except Exception as e:
        print(f'Error reading tracking file: {e}')
        return set()


def save_downloaded_image(asset_id):
    """Save downloaded image ID from tracking.txt"""
    global albumname
    try:
        # Check the file exists and is writable
        if not os.path.exists(tracking_file):
            open(tracking_file, 'w').close()

        # Check the permission of the file
        os.chmod(tracking_file, 0o666)

        with open(tracking_file, 'r+') as f:
            # Read all lines
            lines = f.readlines()

            # If file is empty or first line is not current album name, reset file
            if not lines or lines[0].strip() != albumname:
                f.seek(0)
                f.truncate()
                f.write(f'{albumname}\n')
            else:
                f.seek(0, 2)  # Move to the end of the file

            # Add new image ID
            f.write(f'{asset_id}\n')
    except PermissionError:
        print(f'Permission denied when writing to {tracking_file}')
    except IOError as e:
        print(f'IO Error when writing to tracking file: {e}')
    except Exception as e:
        print(f'Unexpected error writing to tracking file: {e}')


def reset_tracking_file():
    """Reset tracking.txt file"""
    try:
        open(tracking_file, 'w').close()
    except Exception as e:
        print(f'Error resetting tracking file: {e}')


def depalette_image(pixels, palette):
    palette_array = np.array(palette)
    diffs = np.sqrt(np.sum((pixels[:, :, None, :] - palette_array[None, None, :, :]) ** 2, axis=3))
    indices = np.argmin(diffs, axis=2)
    return indices


def scale_img_in_memory(
    image, target_width=1200, target_height=1600, bg_color=(255, 255, 255), immich_date_raw=None, immich_exif_raw=None
):
    """
    Process image in memory, return BytesIO object

    :param image: PIL Image object
    :param target_width: width of epaper
    :param target_height: height of epaper
    :param bg_color: background color
    :param immich_date_raw: raw date string from Immich exifInfo.dateTimeOriginal (ISO 8601), or None
    :param immich_exif_raw: full Immich exifInfo dict (city/country/lat/lon), or None
    :return: BytesIO object
    """

    # Update the angle
    rotation = rotationAngle

    # Extract EXIF date from local image as fallback (DO-01 local path)
    date_time_raw = None
    try:
        exif = image._getexif()
        if exif:
            date_time_raw = exif.get(36867) or exif.get(306)
    except (AttributeError, Exception):
        date_time_raw = None

    # Preserve pre-transpose image reference for GPS EXIF extraction (GPS survives transpose in metadata)
    pre_transpose_image = image

    # Read correct photo orientation from EXIF
    image = ImageOps.exif_transpose(image)
    # output_img = Image.new('RGB', (target_width, target_height), bg_color)

    # # calculate position
    # paste_x = (target_width - new_width) // 2
    # paste_y = (target_height - new_height) // 2
    img = load_scaled(image, rotation, display_mode, blur_radius=blur_radius)
    # Enhance color and contrast
    enhanced_img = ImageEnhance.Color(img).enhance(img_enhanced)
    enhanced_img = ImageEnhance.Contrast(enhanced_img).enhance(img_contrast)

    # Palette definition (Seeed T133A01 color primaries)
    palette = [
        0,
        0,
        0,  # Black
        255,
        255,
        255,  # White
        255,
        216,
        0,  # Yellow (Seeed)
        229,
        57,
        53,  # Red (Seeed)
        0,
        76,
        255,  # Blue (Seeed)
        29,
        185,
        84,  # Green (Seeed)
    ]

    # Prepare palette image (similar to previous code)
    e = len(palette)
    assert e > 0, 'Palette unexpectedly short'
    assert e <= 768, 'Palette unexpectedly long'
    assert e % 3 == 0, 'Palette not multiple of 3, so not RGB'

    # Create temporary palette image
    pal_image = Image.new('P', (1, 1))

    # Zero-pad palette to 768 values
    palette += (768 - e) * [0]
    pal_image.putpalette(palette)

    # Quantize image
    # output_img = enhanced_img.convert("RGB").quantize(
    #     palette=pal_image,
    #     dither=Image.Dither.FLOYDSTEINBERG
    # ).convert("RGB")

    output_img = convert_image(enhanced_img, dithering_strength=strength)
    output_img = Image.fromarray(output_img, mode='RGB')

    # Date/geo overlay (D-07/D-19 fallback chain). Off by default (D-01); silently hidden when neither available (D-03).
    if date_overlay_enabled:
        location_str = (
            parse_photo_location(local_image=pre_transpose_image, immich_exif=immich_exif_raw)
            if geo_overlay_enabled
            else None
        )
        date_str = parse_photo_date(immich_date_raw) or parse_photo_date(date_time_raw)
        if location_str and date_str:
            overlay_text = f'{location_str} • {date_str}'
        elif location_str:
            overlay_text = location_str
        else:
            overlay_text = date_str  # may be None -> overlay hidden
        if overlay_text:
            try:
                font = ImageFont.truetype(
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                    overlay_font_size,
                )
            except (IOError, OSError):
                font = ImageFont.load_default()
            draw_date_overlay(
                output_img,
                overlay_text,
                font,
                date_overlay_position,
                padding=6,
                rotation=rotation,
                style=overlay_style,
                bg_color=OVERLAY_COLORS.get(overlay_bg_color, (0, 0, 0, 255)),
                text_color=OVERLAY_COLORS.get(overlay_text_color, (255, 255, 255, 255)),
                border_color=OVERLAY_COLORS.get(overlay_border_color, (255, 255, 255, 255)),
                stroke_width=overlay_stroke_width,
                margin_h=overlay_margin_h,
                margin_v=overlay_margin_v,
            )

    # Low-battery warning icon (BATIND-03/04; warning-only, D-05/D-19).
    # battery_pct comes from the live ADC voltage; 0 (USB/no data) suppresses the icon (D-07).
    if battery_indicator_enabled == 'on':
        battery_pct = (
            calculate_battery_percentage(last_battery_voltage)
            if last_battery_voltage > 0
            else 0
        )
        draw_battery_indicator(
            output_img,
            battery_pct,
            battery_indicator_position,
            rotation,
            overlay_font_size,
            OVERLAY_COLORS.get('white', (255, 255, 255, 255)),
        )

    # Save image into ram
    img_io = io.BytesIO()
    output_img.save(img_io, 'BMP')
    img_io.seek(0)
    return img_io


def convert_to_c_code_in_memory(image_data):
    """Convert image to C code in memory — T133A01 nibble encoding"""
    pixels = np.array(image_data)

    # Nearest-neighbor palette quantization
    indices = depalette_image(pixels, palette)

    # T133A01 nibble codes indexed by palette position:
    # palette[0]=black→0xF, [1]=white→0x0, [2]=yellow→0xB,
    # [3]=red→0x6, [4]=blue→0xD, [5]=green→0x2
    nibble_map = [0xF, 0x0, 0xB, 0x6, 0xD, 0x2]

    height, width = indices.shape
    bytes_array = [
        (nibble_map[indices[y, x]] << 4) | nibble_map[indices[y, x + 1]]
        if x + 1 < width
        else (nibble_map[indices[y, x]] << 4)
        for y in range(height)
        for x in range(0, width, 2)
    ]

    # Generate hex CSV output
    output = io.StringIO()
    for i, byte_value in enumerate(bytes_array):
        output.write(f'{byte_value:02X},')
        if (i + 1) % 16 == 0:
            output.write('\n')
    output.write('};\n')

    result = output.getvalue().encode('utf-8')
    output_bytes = io.BytesIO(result)
    output_bytes.seek(0)
    return output_bytes


def convert_to_binary_in_memory(image_data):
    """Convert image to raw binary nibble frame — T133A01 4bpp, 960000 bytes."""
    pixels = np.array(image_data)
    indices = depalette_image(pixels, palette)
    nibble_map = [0xF, 0x0, 0xB, 0x6, 0xD, 0x2]
    height, width = indices.shape
    bytes_array = [
        (nibble_map[indices[y, x]] << 4) | nibble_map[indices[y, x + 1]]
        if x + 1 < width
        else (nibble_map[indices[y, x]] << 4)
        for y in range(height)
        for x in range(0, width, 2)
    ]
    output_bytes = io.BytesIO(bytes(bytes_array))
    output_bytes.seek(0)
    return output_bytes


def convert_raw_or_dng_to_jpg(input_file_path, output_dir):
    """Convert RAW or DNG files to JPG using rawpy."""
    with rawpy.imread(input_file_path) as raw:
        rgb = raw.postprocess(use_camera_wb=True, use_auto_wb=False)
        base_name = os.path.splitext(os.path.basename(input_file_path))[0]
        jpg_file_path = os.path.join(output_dir, f'{base_name}.jpg')
        Image.fromarray(rgb).save(jpg_file_path, 'JPEG')
        return jpg_file_path


def convert_heic_to_jpg(input_file_path, output_dir):
    """Convert heic files to JPG using rawpy."""
    img = Image.open(input_file_path)
    img = img.convert('RGB')
    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    jpg_file_path = os.path.join(output_dir, f'{base_name}.jpg')
    img.save(jpg_file_path, 'JPEG', quality=95)
    # print(f"Successfully converted {input_file_path} to {output_dir}")
    return jpg_file_path


class ConfigFileHandler(FileSystemEventHandler):
    """Reload configuration and notify application when config.yaml changes"""

    def __init__(self, config_path, config_update_callback):
        self.config_path = config_path
        self.config_update_callback = config_update_callback

        # Ensure directory and config file exist
        self.ensure_config_exists()

        # Load configuration
        self.config = self.load_config()

    def ensure_config_exists(self):
        """
        Ensure the config directory and config file exist.
        Create them if they don't exist.
        """
        # Get the directory path
        config_dir = os.path.dirname(self.config_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
                print(f'Created config directory: {config_dir}')
            except Exception as e:
                print(f'Error creating config directory: {e}')

        # Create the config file if it doesn't exist
        if not os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'w') as file:
                    yaml.dump(DEFAULT_CONFIG, file)
                print(f'Created default configuration file: {self.config_path}')
            except Exception as e:
                print(f'Error creating config file: {e}')

    def on_modified(self, event):
        if event.src_path == self.config_path:
            print('File modification detected, reloading configuration...')
            new_config = self.load_config()
            # Use callback function to update configuration
            self.config_update_callback(new_config)

    def load_config(self):
        """Load config"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            return config if config is not None else DEFAULT_CONFIG
        except Exception as e:
            print(f'Error reading config file: {e}')
            return DEFAULT_CONFIG


def update_app_config(new_config):
    """Update global configuration and Flask application configuration"""
    global \
        current_config, \
        url, \
        albumname, \
        rotationAngle, \
        img_enhanced, \
        img_contrast, \
        strength, \
        display_mode, \
        image_order, \
        sleep_start_hour, \
        sleep_end_hour, \
        sleep_start_minute, \
        sleep_end_minute, \
        date_overlay_enabled, \
        geo_overlay_enabled, \
        date_overlay_position, \
        overlay_style, \
        overlay_bg_color, \
        overlay_text_color, \
        overlay_border_color, \
        overlay_stroke_width, \
        overlay_font_size, \
        overlay_language, \
        blur_radius, \
        overlay_margin_h, \
        overlay_margin_v, \
        battery_indicator_enabled, \
        battery_indicator_position

    current_config = new_config

    # Update Flask application configuration
    app.config['IMMICH_URL'] = new_config['immich']['url']
    app.config['IMMICH_ALBUM'] = new_config['immich']['album']
    app.config['IMMICH_ROTATION'] = new_config['immich']['rotation']
    app.config['IMMICH_ENHANCED'] = new_config['immich']['enhanced']
    app.config['IMMICH_CONTRAST'] = new_config['immich']['contrast']
    app.config['IMMICH_STRENGH'] = new_config['immich']['strength']
    app.config['IMMICH_DISPLAY_MODE'] = new_config['immich']['display_mode']
    app.config['IMMICH_IMAGE_ORDER'] = new_config['immich']['image_order']
    app.config['IMMICH_SLEEP_START_HOUR'] = new_config['immich']['sleep_start_hour']
    app.config['IMMICH_SLEEP_END_HOUR'] = new_config['immich']['sleep_end_hour']
    app.config['IMMICH_SLEEP_START_MINUTE'] = new_config['immich']['sleep_start_minute']
    app.config['IMMICH_SLEEP_END_MINUTE'] = new_config['immich']['sleep_end_minute']

    # Update global variables
    url = new_config['immich']['url']
    albumname = new_config['immich']['album']
    rotationAngle = new_config['immich']['rotation']
    img_enhanced = new_config['immich']['enhanced']
    img_contrast = new_config['immich']['contrast']
    strength = new_config['immich']['strength']
    display_mode = new_config['immich']['display_mode']
    image_order = new_config['immich']['image_order']
    sleep_start_hour = new_config['immich']['sleep_start_hour']
    sleep_end_hour = new_config['immich']['sleep_end_hour']
    sleep_start_minute = new_config['immich']['sleep_start_minute']
    sleep_end_minute = new_config['immich']['sleep_end_minute']
    date_overlay_enabled = new_config['immich'].get('date_overlay_enabled', False)
    geo_overlay_enabled = new_config['immich'].get('geo_overlay_enabled', True)
    date_overlay_position = new_config['immich'].get('date_overlay_position', 'bottomRight')
    overlay_style = new_config['immich'].get('overlay_style', 'background')
    overlay_bg_color = new_config['immich'].get('overlay_bg_color', 'black')
    overlay_text_color = new_config['immich'].get('overlay_text_color', 'white')
    overlay_border_color = new_config['immich'].get('overlay_border_color', 'white')
    overlay_stroke_width = int(new_config['immich'].get('overlay_stroke_width', 2))
    overlay_font_size = int(new_config['immich'].get('overlay_font_size', 26))
    overlay_language = new_config['immich'].get('overlay_language', 'en')
    blur_radius = int(new_config['immich'].get('blur_radius', 30))
    overlay_margin_h = int(new_config['immich'].get('overlay_margin_h', 0))
    overlay_margin_v = int(new_config['immich'].get('overlay_margin_v', 0))
    battery_indicator_enabled = new_config['immich'].get('battery_indicator_enabled', 'on')
    battery_indicator_position = new_config['immich'].get('battery_indicator_position', 'topRight')

    print(
        f'Configuration updated: URL = {url}, Album = {albumname}, angle = {rotationAngle}, enhance = {img_enhanced}, contrast = {img_contrast}, strength = {strength}, display_mode = {display_mode}, image_order = {image_order}'
    )


def start_config_watcher(config_path):
    """Start configuration file monitoring"""
    config_handler = ConfigFileHandler(config_path, update_app_config)

    # Start monitoring file changes
    observer = Observer()
    observer.schedule(config_handler, path=os.path.dirname(config_path), recursive=False)
    observer.start()

    return observer


# Add lithium battery voltage table (voltage: battery percentage)
BATTERY_LEVELS = {
    4200: 100,
    4150: 95,
    4110: 90,
    4080: 85,
    4020: 80,
    3980: 75,
    3950: 70,
    3910: 65,
    3870: 60,
    3850: 55,
    3840: 50,
    3820: 45,
    3800: 40,
    3790: 35,
    3770: 30,
    3750: 25,
    3730: 20,
    3710: 15,
    3690: 10,
    3610: 5,
    3400: 0,
}


def calculate_battery_percentage(voltage):
    """
    Calculate actual battery percentage based on battery voltage
    Use piecewise linear interpolation for more accurate battery estimation
    """
    if voltage >= 4200:
        return 100
    if voltage <= 3400:
        return 0

    # Find the two closest reference points
    voltages = list(BATTERY_LEVELS.keys())
    for i in range(len(voltages) - 1):
        if voltages[i] >= voltage >= voltages[i + 1]:
            v1, v2 = voltages[i], voltages[i + 1]
            p1, p2 = BATTERY_LEVELS[v1], BATTERY_LEVELS[v2]
            # Linear interpolation
            percentage = p2 + (voltage - v2) * (p1 - p2) / (v1 - v2)
            return round(percentage, 1)

    return 0


@app.route('/setting', methods=['GET', 'POST'])
@require_auth
def settings():
    global current_config, last_battery_voltage, last_battery_update

    # Use stored battery voltage (if updated within the last hour)
    current_time = time.time()
    if current_time - last_battery_update < 3600:  # 1 hour = 3600 seconds
        battery_voltage = last_battery_voltage
    else:
        battery_voltage = 0

    # Use new battery calculation method
    battery_percentage = calculate_battery_percentage(battery_voltage) if battery_voltage > 0 else 0

    if battery_voltage > 0:
        print(f'Battery: {battery_voltage:.0f}mV ({battery_percentage:.1f}%)')
    else:
        print('No battery information available')

    if request.method == 'POST':
        # Collect form data
        new_config = {
            'immich': {
                'url': request.form.get('url', current_config['immich']['url']),
                'album': request.form.get('album', current_config['immich']['album']),
                'rotation': int(request.form.get('rotation', current_config['immich']['rotation'])),
                'enhanced': float(request.form.get('enhanced', current_config['immich']['enhanced'])),
                'contrast': float(request.form.get('contrast', current_config['immich']['contrast'])),
                'strength': float(request.form.get('strength', current_config['immich']['strength'])),
                'display_mode': request.form.get('display_mode', current_config['immich']['display_mode']),
                'image_order': request.form.get('image_order', current_config['immich']['image_order']),
                'sleep_start_hour': int(
                    request.form.get('sleep_start_hour', current_config['immich']['sleep_start_hour'])
                ),
                'sleep_start_minute': int(
                    request.form.get('sleep_start_minute', current_config['immich']['sleep_start_minute'])
                ),
                'sleep_end_hour': int(request.form.get('sleep_end_hour', current_config['immich']['sleep_end_hour'])),
                'sleep_end_minute': int(
                    request.form.get('sleep_end_minute', current_config['immich']['sleep_end_minute'])
                ),
                'wakeup_interval': int(
                    request.form.get('wakeup_interval', current_config['immich']['wakeup_interval'])
                ),
                'date_overlay_enabled': request.form.get('date_overlay_enabled', 'off') == 'on',
                'geo_overlay_enabled': request.form.get('geo_overlay_enabled', 'off') == 'on',
                'date_overlay_position': request.form.get('date_overlay_position', 'bottomRight'),
                'overlay_style': request.form.get(
                    'overlay_style', current_config['immich'].get('overlay_style', 'background')
                ),
                'overlay_bg_color': request.form.get(
                    'overlay_bg_color', current_config['immich'].get('overlay_bg_color', 'black')
                ),
                'overlay_text_color': request.form.get(
                    'overlay_text_color', current_config['immich'].get('overlay_text_color', 'white')
                ),
                'overlay_border_color': request.form.get(
                    'overlay_border_color', current_config['immich'].get('overlay_border_color', 'white')
                ),
                'overlay_stroke_width': int(
                    request.form.get('overlay_stroke_width', current_config['immich'].get('overlay_stroke_width', 2))
                ),
                'overlay_font_size': int(
                    request.form.get('overlay_font_size', current_config['immich'].get('overlay_font_size', 26))
                ),
                'overlay_language': request.form.get(
                    'overlay_language', current_config['immich'].get('overlay_language', 'en')
                ),
                'blur_radius': int(request.form.get('blur_radius', current_config['immich'].get('blur_radius', 30))),
                'overlay_margin_h': int(
                    request.form.get('overlay_margin_h', current_config['immich'].get('overlay_margin_h', 0))
                ),
                'overlay_margin_v': int(
                    request.form.get('overlay_margin_v', current_config['immich'].get('overlay_margin_v', 0))
                ),
                'battery_indicator_enabled': request.form.get(
                    'battery_indicator_enabled', current_config['immich'].get('battery_indicator_enabled', 'on')
                ),
                'battery_indicator_position': request.form.get(
                    'battery_indicator_position', current_config['immich'].get('battery_indicator_position', 'topRight')
                ),
            }
        }

        # Validate rotation values
        if new_config['immich']['rotation'] not in [0, 90, 180, 270]:
            return render_template(
                'settings.html', config=current_config, error='Rotation must be 0, 90, 180, or 270 degrees'
            )

        try:
            # Write to config file
            with open(config_file, 'w') as file:
                yaml.safe_dump(new_config, file)

            # Update current configuration
            update_app_config(new_config)

            return redirect(url_for('settings'))

        except Exception as e:
            return render_template(
                'settings.html', config=current_config, error=f'Error saving configuration: {str(e)}'
            )

    local_mode = os.path.isdir(localdir) and any(
        os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS for f in os.listdir(localdir)
    )
    return render_template(
        'settings.html',
        config=current_config,
        battery_voltage=battery_voltage,
        battery_percentage=battery_percentage,
        local_mode=local_mode,
    )


@app.route('/')
@require_auth
def index():
    return redirect(url_for('settings'))


def run_daily_ntp_sync():
    """Daily NTP sync task"""
    while True:
        try:
            # Get current time
            now = datetime.now()
            # Calculate next 4:00 AM
            next_sync = now.replace(hour=4, minute=11, second=0, microsecond=0)
            if now >= next_sync:
                next_sync = next_sync + timedelta(days=1)

            # Calculate wait time
            wait_seconds = (next_sync - now).total_seconds()
            time.sleep(wait_seconds)

            # Perform NTP sync
            synced_time = sync_time_with_ntp()
            print(f"Daily NTP sync completed at {synced_time.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f'Error in daily NTP sync: {e}')
            time.sleep(3600)  # Retry after 1 hour if error occurs


def main():
    # Start configuration file monitoring
    config_observer = start_config_watcher(config_file)

    try:
        # Initialize configuration
        initial_config = ConfigFileHandler(config_file, update_app_config).config
        update_app_config(initial_config)

        # Start daily NTP sync thread
        ntp_sync_thread = threading.Thread(target=run_daily_ntp_sync, daemon=True)
        ntp_sync_thread.start()

        # Run Flask application in a separate thread
        app.run(host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        config_observer.stop()
    config_observer.join()


def open_image_from_path(filepath):
    """Open a local image file into a PIL Image, handling RAW/HEIC formats."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {'.raw', '.dng', '.arw', '.cr2', '.nef'}:
        with rawpy.imread(filepath) as raw:
            rgb = raw.postprocess(use_camera_wb=True, use_auto_wb=False)
            return Image.fromarray(rgb)
    elif ext == '.heic':
        return Image.open(filepath).convert('RGB')
    else:
        return Image.open(filepath)


def serve_local_image():
    """Pick a random image from localdir, process it, and return a send_file response."""
    if not os.path.isdir(localdir):
        return jsonify({'error': f'Local photo directory not found: {localdir}'}), 500

    candidates = [f for f in os.listdir(localdir) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS]
    if not candidates:
        return jsonify({'error': 'No supported images found in local directory'}), 404

    filename = random.choice(candidates)
    filepath = os.path.join(localdir, filename)
    image = open_image_from_path(filepath)

    processed_image = scale_img_in_memory(image)
    processed_image.seek(0)
    frame = convert_to_binary_in_memory(Image.open(processed_image))

    stem = os.path.splitext(filename)[0]
    return send_file(
        frame,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=f'image_{stem}.bin',
    )


def serve_immich_image():
    """Pick an image from Immich, process it, and return a send_file response."""
    current_url = url
    current_albumname = albumname

    if not current_url or not current_albumname:
        return jsonify({'error': 'Immich URL or Album not configured'}), 500

    downloaded_images = load_downloaded_images()

    response = requests.get(f'{current_url}/api/albums', headers=headers, params={'withoutAssets': 'true'})
    if response.status_code != 200:
        print(f'[ERROR] GET /api/albums → HTTP {response.status_code}: {response.text[:500]}')
        return jsonify(
            {'error': 'Failed to fetch albums', 'status': response.status_code, 'detail': response.text[:500]}
        ), 500

    data = response.json()
    albumid = next((item['id'] for item in data if item['albumName'] == current_albumname), None)
    if not albumid:
        return jsonify({'error': 'Album not found'}), 404

    response = requests.get(f'{url}/api/albums/{albumid}', headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch album details'}), 500

    data = response.json()
    if 'assets' not in data or not data['assets']:
        return jsonify({'error': 'No images found in album'}), 404

    current_image_order = current_config['immich']['image_order']

    if current_image_order == 'newest':
        latest_photo = max(
            data['assets'], key=lambda x: x.get('exifInfo', {}).get('dateTimeOriginal', '1970-01-01T00:00:00')
        )
        latest_id = latest_photo['id']

        downloaded_images = load_downloaded_images()
        if not downloaded_images or latest_id not in downloaded_images:
            reset_tracking_file()
            sorted_assets = sorted(
                data['assets'],
                key=lambda x: x.get('exifInfo', {}).get('dateTimeOriginal', '1970-01-01T00:00:00'),
                reverse=True,
            )
            remaining_images = sorted_assets
        else:
            remaining_images = [img for img in data['assets'] if img['id'] not in downloaded_images]
            remaining_images.sort(
                key=lambda x: x.get('exifInfo', {}).get('dateTimeOriginal', '1970-01-01T00:00:00'), reverse=True
            )
    else:  # random order
        remaining_images = [img for img in data['assets'] if img['id'] not in downloaded_images]
        if not remaining_images:
            reset_tracking_file()
            remaining_images = data['assets']

    selected_image = remaining_images[0] if current_image_order == 'newest' else random.choice(remaining_images)
    asset_id = selected_image['id']
    save_downloaded_image(asset_id)

    print(f'{url}/api/assets/{asset_id}/original')
    response = requests.get(f'{url}/api/assets/{asset_id}/original', headers=headers, stream=True)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to download image'}), 500

    image_data = io.BytesIO(response.content)
    if selected_image['originalPath'].lower().endswith(('.raw', '.dng', '.arw', '.cr2', '.nef')):
        with rawpy.imread(image_data) as raw:
            rgb = raw.postprocess(use_camera_wb=True, use_auto_wb=False)
            image = Image.fromarray(rgb)
    elif selected_image['originalPath'].lower().endswith('.heic'):
        image = Image.open(image_data).convert('RGB')
    else:
        image = Image.open(image_data)

    immich_date_raw = selected_image.get('exifInfo', {}).get('dateTimeOriginal')
    processed_image = scale_img_in_memory(
        image,
        immich_date_raw=immich_date_raw,
        immich_exif_raw=selected_image.get('exifInfo', {}),
    )
    processed_image.seek(0)
    frame = convert_to_binary_in_memory(Image.open(processed_image))

    return send_file(
        frame,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=f'image_{asset_id}.bin',
    )


@app.route('/download', methods=['GET'])
@require_auth
def process_and_download():
    global last_battery_voltage, last_battery_update

    # Update battery information when received
    try:
        battery_voltage = float(request.headers.get('batteryCap', '0'))
        if battery_voltage > 0:
            last_battery_voltage = battery_voltage
            last_battery_update = time.time()
            persist_battery_reading(last_battery_voltage, last_battery_update)
    except (TypeError, ValueError):
        pass

    try:
        # Local folder takes priority when it contains at least one image.
        # Fall back to Immich when IMMICH_API_KEY is present.
        local_has_images = os.path.isdir(localdir) and any(
            os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS for f in os.listdir(localdir)
        )
        if local_has_images:
            return serve_local_image()
        elif apikey:
            return serve_immich_image()
        else:
            return jsonify(
                {'error': 'No image source configured. Add images to local_photos/ or set IMMICH_API_KEY.'}
            ), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/sleep', methods=['GET'])
@require_auth
def get_sleep_duration():
    # Use system time instead of NTP sync
    current_time = datetime.now()

    # Get wake interval from config (in minutes)
    interval = int(current_config['immich']['wakeup_interval'])

    def calculate_next_interval_time(base_time, intervals=1):
        # Calculate next interval time
        total_minutes = base_time.hour * 60 + base_time.minute
        next_total_minutes = interval * ((total_minutes // interval) + intervals)

        # Handle case where next_total_minutes exceeds 24 hours
        next_total_minutes = next_total_minutes % (24 * 60)  # Wrap around to next day

        # Create next wake time
        next_time = base_time.replace(
            hour=next_total_minutes // 60, minute=next_total_minutes % 60, second=0, microsecond=0
        )

        # If we crossed into the next day, add a day
        if next_time < base_time:
            next_time = next_time + timedelta(days=1)

        return next_time

    # Get initial next wake time
    next_wakeup = calculate_next_interval_time(current_time)

    # Check if next wake time is in sleep period
    sleep_start = current_time.replace(
        hour=current_config['immich']['sleep_start_hour'],
        minute=current_config['immich']['sleep_start_minute'],
        second=0,
        microsecond=0,
    )

    sleep_end = current_time.replace(
        hour=current_config['immich']['sleep_end_hour'],
        minute=current_config['immich']['sleep_end_minute'],
        second=0,
        microsecond=0,
    )

    # Adjust sleep end time if it's less than start time (crosses midnight)
    if sleep_end < sleep_start:
        if current_time >= sleep_start:
            sleep_end = sleep_end + timedelta(days=1)
        elif current_time < sleep_end:
            sleep_start = sleep_start - timedelta(days=1)

    # If next wake time is in sleep period, set to sleep end time
    if sleep_start <= next_wakeup < sleep_end:
        next_wakeup = sleep_end

    # Calculate sleep duration in milliseconds
    sleep_ms = int((next_wakeup - current_time).total_seconds() * 1000)

    # If sleep duration is less than 10 minutes, calculate next interval
    if sleep_ms < 600000:  # 10 minutes = 600,000 milliseconds
        next_wakeup = calculate_next_interval_time(current_time, intervals=2)
        # Check again for sleep period
        if sleep_start <= next_wakeup < sleep_end:
            next_wakeup = sleep_end
        sleep_ms = int((next_wakeup - current_time).total_seconds() * 1000)

    return jsonify(
        {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'next_wakeup': next_wakeup.strftime('%Y-%m-%d %H:%M:%S'),
            'sleep_duration': sleep_ms,
        }
    )


def sync_time_with_ntp():
    """Sync time with NTP server"""
    try:
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request('pool.ntp.org', timeout=5)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        print(f'NTP sync failed: {e}')
        return datetime.now()


# def calculate_next_wakeup(current_time, wakeup_hour, wakeup_minute):
#     """Calculate next wakeup time, considering sleep time range"""
#     # Get sleep time range
#     sleep_start = current_time.replace(
#         hour=current_config['immich']['sleep_start_hour'],
#         minute=current_config['immich']['sleep_start_minute'],
#         second=0,
#         microsecond=0
#     )

#     sleep_end = current_time.replace(
#         hour=current_config['immich']['sleep_end_hour'],
#         minute=current_config['immich']['sleep_end_minute'],
#         second=0,
#         microsecond=0
#     )

#     # If current time is before sleep end time but after midnight
#     if sleep_end < sleep_start and current_time < sleep_end:
#         sleep_start = sleep_start - timedelta(days=1)
#     # If current time is after sleep start time
#     elif sleep_end < sleep_start and current_time >= sleep_start:
#         sleep_end = sleep_end + timedelta(days=1)

#     # Calculate next wake up time
#     interval_minutes = int(current_config['immich']['wakeup_interval'])
#     next_wakeup = current_time + timedelta(minutes=interval_minutes)

#     # Adjust next wake up time if it falls within sleep period
#     if sleep_start <= next_wakeup < sleep_end:
#         next_wakeup = sleep_end

#     return next_wakeup

if __name__ == '__main__':
    main()
