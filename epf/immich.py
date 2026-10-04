"""
Talking to Immich, and deciding which photo comes next.

Every call reads the live configuration, so a URL or album changed on the
settings page takes effect on the next request without a restart.
"""
import os
import random
import time
from datetime import datetime

import requests

from . import config, state, tracking

# Read once at import, like the original: changing the key means a restart.
# Note the README's docker run example spells it IMMICH-API-KEY, which is not
# what this reads.
apikey = os.getenv('IMMICH_API_KEY')

headers = {
    'Accept': 'application/json',
    'x-api-key': apikey,
}

class ImmichError(Exception):
    """ Carries the message and HTTP status the caller should report """

    def __init__(self, message, status=500):
        super().__init__(message)
        self.message = message
        self.status = status

# Immich on the LAN answers in well under a second; these only matter when it
# is down. Without them a request to an Immich that accepts the connection but
# never answers would hang the handler, and the frame would give up at its own
# 50-second limit without ever learning why. They have to stay inside that
# limit so the device gets a status code it can act on.
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 20
# The original can be a RAW file of tens of megabytes. The read timeout only
# covers each chunk, so a trickling connection could outlast the frame: the
# whole download also gets a deadline.
DOWNLOAD_TIMEOUT = (CONNECT_TIMEOUT, 15)
DOWNLOAD_DEADLINE = 25

def _call(method, url, **kwargs):
    """
    requests.request() with the API key and timeouts, reporting a transport
    failure as an ImmichError the routes can return: 504 when Immich did not
    answer in time, 502 when it could not be reached at all.
    """
    kwargs.setdefault('timeout', (CONNECT_TIMEOUT, READ_TIMEOUT))
    try:
        return requests.request(method, url, headers=headers, **kwargs)
    except requests.Timeout as error:
        raise ImmichError(f"Immich did not answer in time: {error}", 504)
    except requests.RequestException as error:
        raise ImmichError(f"Could not reach Immich: {error}", 502)

def base_url():
    return config.immich()['url']

def album_name():
    return config.immich()['album']

def photo_link(asset_id):
    """ The asset in the configured server's web UI, so the link works on the LAN """
    return f"{base_url().rstrip('/')}/photos/{asset_id}"

def resolve_album_id():
    """ Look up the configured album, raising ImmichError if it cannot be used """
    response = _call('GET', f"{base_url()}/api/albums")
    if response.status_code != 200:
        raise ImmichError(f"Failed to fetch albums (Immich returned {response.status_code})", 502)

    wanted = album_name()
    albumid = next((item['id'] for item in response.json()
                    if item['albumName'] == wanted), None)
    if not albumid:
        raise ImmichError("Album not found", 404)
    return albumid

def list_album_assets(albumid):
    """
    Every asset in the album.

    Immich v3 breaking change: GET /api/albums/{id} no longer returns the
    'assets' property, so this goes through the paginated search endpoint.

    Videos are left out: an album may hold them, and handing one to the image
    pipeline only fails later, where PIL can say no more than "cannot identify
    image file".
    """
    assets = []
    page = 1
    while True:
        search_body = {
            "albumIds": [albumid],
            "type": "IMAGE",
            "size": 1000,
            "page": page,
            "withExif": True,
        }
        response = _call('POST', f"{base_url()}/api/search/metadata", json=search_body)
        if response.status_code != 200:
            raise ImmichError(f"Failed to fetch album details (Immich returned {response.status_code})", 502)

        result = response.json().get('assets', {})
        # Filtered again here in case an older server ignores the type above
        assets.extend(item for item in result.get('items', [])
                      if item.get('type', 'IMAGE') == 'IMAGE')

        next_page = result.get('nextPage')
        if not next_page:
            break
        page = int(next_page)

    if not assets:
        raise ImmichError("No images found in album", 404)
    return assets

def fetch_original(asset_id):
    """ The asset's original bytes, for the image pipeline """
    deadline = time.monotonic() + DOWNLOAD_DEADLINE
    response = _call('GET', f"{base_url()}/api/assets/{asset_id}/original",
                     timeout=DOWNLOAD_TIMEOUT, stream=True)
    with response:
        if response.status_code != 200:
            raise ImmichError(f"Failed to download image (Immich returned {response.status_code})", 502)
        chunks = []
        try:
            # Small chunks: iter_content only returns once a chunk is full, so the
            # deadline is checked at most one chunk late on a slow connection
            for chunk in response.iter_content(chunk_size=8 * 1024):
                chunks.append(chunk)
                if time.monotonic() > deadline:
                    raise ImmichError("Downloading the original took too long", 504)
        except requests.RequestException as error:
            raise ImmichError(f"Download from Immich failed: {error}", 502)
    return b''.join(chunks)

def fetch_thumbnail(asset_id):
    """
    (bytes, content type) for a browser-friendly rendering of the asset.

    A thumbnail rather than the original because originals may be HEIC or RAW,
    which browsers cannot display, and it has to come through the server at all
    because the API key never reaches the browser.
    """
    try:
        response = requests.get(f"{base_url()}/api/assets/{asset_id}/thumbnail",
                                headers=headers, params={'size': 'preview'}, timeout=15)
    except requests.RequestException as error:
        raise ImmichError(f"Could not reach Immich: {error}", 502)

    if response.status_code != 200:
        raise ImmichError(f"Immich returned {response.status_code}", 502)

    return response.content, response.headers.get('Content-Type', 'image/jpeg')

def check_health():
    """
    One request that settles reachability, credentials and whether the configured
    album exists. Returns the shape /status reports, using codes rather than
    sentences so the page can phrase them in whichever language it is showing.
    """
    if not base_url() or not album_name():
        return {'state': 'error', 'code': 'not_configured'}

    try:
        response = requests.get(f"{base_url()}/api/albums", headers=headers, timeout=6)
    except requests.RequestException:
        return {'state': 'error', 'code': 'unreachable'}

    if response.status_code in (401, 403):
        return {'state': 'error', 'code': 'unauthorized'}
    if response.status_code != 200:
        return {'state': 'error', 'code': 'server_error', 'http': response.status_code}

    wanted = album_name()
    names = [album.get('albumName') for album in response.json()]
    if wanted in names:
        return {'state': 'ok', 'code': 'connected', 'album': wanted}
    return {'state': 'warn', 'code': 'album_missing', 'album': wanted}

def _taken_at(asset):
    return asset.get('exifInfo', {}).get('dateTimeOriginal', '1970-01-01T00:00:00')

def taken_at_text(asset):
    """
    When the photo was taken, for display. Empty when Immich has no EXIF date.

    Already fetched: list_album_assets asks withExif, and 'newest' ordering sorts
    on this very field.
    """
    raw = (asset or {}).get('exifInfo', {}).get('dateTimeOriginal')
    if not raw:
        return ''
    # 2019-08-14T10:23:45.000+08:00 -> 2019-08-14 10:23
    text = str(raw)
    return text[:16].replace('T', ' ') if len(text) >= 16 else text

def select_asset(assets):
    """
    Choose which asset to show next, honouring image_order and the history in
    tracking.txt. The history is reset when the album runs out, or when a newer
    photo turns up while ordering by date.
    """
    order = config.immich()['image_order']
    shown = tracking.shown_ids()

    if order == 'newest':
        latest_id = max(assets, key=_taken_at)['id']
        if not shown or latest_id not in shown:
            tracking.reset(reason='newer_photo')
            remaining = sorted(assets, key=_taken_at, reverse=True)
        else:
            remaining = sorted([a for a in assets if a['id'] not in shown],
                               key=_taken_at, reverse=True)
        if not remaining:
            # Everything has been shown and nothing is newer: begin again rather
            # than indexing an empty list, which used to 500 the device
            tracking.reset(reason='album_exhausted')
            remaining = sorted(assets, key=_taken_at, reverse=True)
        return remaining[0]

    remaining = [a for a in assets if a['id'] not in shown]
    if not remaining:
        tracking.reset(reason='album_exhausted')
        remaining = assets
    return random.choice(remaining)

def refresh_next_photo():
    """ Choose and remember the photo the frame will get next. Raises ImmichError. """
    albumid = resolve_album_id()
    asset = select_asset(list_album_assets(albumid))
    state.next_photo.update({'asset': asset, 'album': album_name(),
                             'album_id': albumid, 'chosen_at': datetime.now(),
                             'rendered': None})
    return asset
