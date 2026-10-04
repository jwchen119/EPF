#-*- coding:utf8 -*-
"""
The Flask app and its HTTP routes.

Everything else lives in the epf package: see epf/__init__.py for the map. The
contract with the firmware is /download and /sleep; the rest serves the settings
page. Run with `python app.py`, or `docker compose up -d`.
"""
import io
import os
import threading
import time
from datetime import datetime, timedelta

import ntplib
from flask import (Flask, jsonify, redirect, render_template, request, send_file,
                   url_for)
from epf import (battery, config, credentials, eventlog, imaging, immich, notify,
                 state, tracking)

app = Flask(__name__)

# ---------------------------------------------------------------- template glue

@app.context_processor
def inject_current_year():
    """ Expose the current year to every template, so the footer never goes stale """
    return {'current_year': datetime.now().year}

@app.context_processor
def inject_static_url():
    """
    static_url('css/settings.css') with the file's modification time appended, so
    a browser cannot keep serving a stale stylesheet or script after an update.
    """
    def static_url(filename):
        try:
            version = int(os.path.getmtime(os.path.join(app.static_folder, filename)))
        except OSError:
            version = 0
        return url_for('static', filename=filename, v=version)

    return {'static_url': static_url}

@app.context_processor
def inject_current_photo():
    """ Expose the photo the frame is showing, or None before the first check-in """
    if not state.last_photo['asset_id']:
        return {'photo': None}

    shown_at = state.last_photo['shown_at']
    return {'photo': {
        'asset_id': state.last_photo['asset_id'],
        'taken_at': state.last_photo['taken_at'] or '',
        # The configured server rather than my.immich.app, so the link opens the
        # web UI on the LAN instead of needing an internet round trip
        'link': immich.photo_link(state.last_photo['asset_id']),
        'shown_at': shown_at.strftime('%Y-%m-%d %H:%M') if shown_at else '',
    }}

def _no_store(response):
    """ Status, previews and the log change constantly: never cache them """
    response.headers['Cache-Control'] = 'no-store'
    return response

def _flat_defaults():
    """
    Every default in one flat dict.

    The page's reset button looks fields up by form-field name, which is unique
    across the sections, so it does not need the nesting.
    """
    flat = {}
    for values in config.DEFAULT_CONFIG.values():
        flat.update(values)
    return flat

def _fresh_battery():
    """ The last reported voltage, or 0 once it is more than an hour old """
    if time.time() - state.battery['updated'] < 3600:
        return state.battery['voltage']
    return 0

# --------------------------------------------------------------- settings page

@app.route('/setting', methods=['GET', 'POST'])
def settings():
    voltage = _fresh_battery()
    percentage = battery.percentage(voltage) if voltage > 0 else 0

    if voltage > 0:
        print(f"Battery: {voltage:.0f}mV ({percentage:.1f}%)")
    else:
        print("No battery information available")

    def render(error=None):
        return render_template('settings.html',
                               config=config.current,
                               defaults=_flat_defaults(),
                               battery_voltage=voltage,
                               battery_percentage=percentage,
                               error=error)

    if request.method != 'POST':
        return render()

    # Field name -> how to read it. Anything absent is treated as text.
    number = {'rotation': int, 'enhanced': float, 'contrast': float, 'strength': float,
              'sleep_start_hour': int, 'sleep_start_minute': int,
              'sleep_end_hour': int, 'sleep_end_minute': int, 'wakeup_interval': int,
              'battery_threshold': int, 'min_interval_hours': int}
    boolean = {'enabled'}
    # Tick boxes: an unticked box is simply absent from the form, so its absence
    # has to mean False rather than "unchanged"
    checkbox = {'use_telegram', 'use_line'}

    submitted = {}
    for section in config.sections():
        live = config.current[section]
        submitted[section] = {}
        for key, previous in live.items():
            if key in checkbox:
                submitted[section][key] = key in request.form
                continue
            if key in boolean:
                # A select rather than a checkbox, because an unchecked checkbox
                # is simply absent from the form and would look like "unchanged"
                submitted[section][key] = request.form.get(key, str(previous)) == 'true'
                continue
            raw = request.form.get(key, previous)
            try:
                submitted[section][key] = number[key](raw) if key in number else raw
            except (TypeError, ValueError):
                return render(error=f"'{key}' is not a valid number")

    if submitted['immich']['rotation'] not in [0, 90, 180, 270]:
        return render(error="Rotation must be 0, 90, 180, or 270 degrees")

    try:
        config.write_file(submitted)
    except Exception as error:
        return render(error=f"Error saving configuration: {error}")

    # Record only the fields that actually moved, so the log stays useful
    changes = {}
    for section, values in submitted.items():
        for key, value in values.items():
            if config.current[section].get(key) != value:
                changes[key] = [config.current[section].get(key), value]

    config.apply(submitted)
    eventlog.record('settings_saved', ip=eventlog.client_ip(), changes=changes or None)

    # A new look or album makes the prepared image stale; prepare again
    state.clear_rendered()
    start_preparing()

    return redirect(url_for('settings'))

@app.route('/')
def index():
    return redirect(url_for('settings'))

# ------------------------------------------------------------------- page data

@app.route('/status')
def status():
    """
    Live health for the header: can we reach Immich, and is the frame checking in.

    Returns machine-readable codes rather than sentences, so the page can render
    them in whichever language it is showing.
    """
    # The device is silent between wake-ups, so "connected" can only mean
    # "checked in recently enough", measured against its own wake-up interval.
    last_seen = (datetime.fromtimestamp(state.battery['updated'])
                 if state.battery['updated'] else None)
    shown_at = state.last_photo['shown_at']
    if shown_at and (last_seen is None or shown_at > last_seen):
        last_seen = shown_at

    if last_seen is None:
        frame = {'state': 'unknown', 'code': 'never', 'minutes_ago': None}
    else:
        minutes_ago = max(0, int((datetime.now() - last_seen).total_seconds() // 60))
        interval = int(config.immich()['wakeup_interval'])
        frame = {
            'state': 'ok' if minutes_ago <= interval * 2 else 'warn',
            'code': 'seen',
            'minutes_ago': minutes_ago,
            'last_seen': last_seen.strftime('%Y-%m-%d %H:%M'),
        }

    voltage = _fresh_battery()
    return _no_store(jsonify({
        'immich': immich.check_health(),
        'frame': frame,
        'battery': {
            'voltage': voltage,
            'percentage': battery.percentage(voltage) if voltage > 0 else None,
        },
    }))

@app.route('/log')
def read_log():
    """ Recent events, newest first """
    try:
        limit = min(max(int(request.args.get('limit', 50)), 1), 500)
    except ValueError:
        limit = 50
    return _no_store(jsonify({'entries': eventlog.recent(limit)}))

@app.route('/notify/bind', methods=['POST'])
def bind_notification():
    """
    Store credentials for a channel, but only once a test message has arrived.

    Nothing is written unless the send succeeds, so "bound" always means "known
    to work" rather than "something was typed in".
    """
    channel = request.form.get('channel')
    if channel not in credentials.FIELDS:
        return _no_store(jsonify({"error": "unknown_channel", "detail": channel})), 400

    values = {field: (request.form.get(field) or '').strip()
              for field in credentials.FIELDS[channel]}
    missing = [field for field, value in values.items() if not value]
    if missing:
        return _no_store(jsonify({"error": "not_configured",
                                  "detail": ', '.join(missing)})), 400

    try:
        notify.send("E-paper frame: notifications are set up", channel, values)
    except notify.NotifyError as error:
        eventlog.record('error', where='notify', message=error.code,
                        detail=error.detail, channel=channel)
        return _no_store(jsonify({"error": error.code, "detail": error.detail})), 502

    credentials.save_verified(channel, values)
    eventlog.record('notify_bound', channel=channel, ip=eventlog.client_ip())
    return _no_store(jsonify({'bound': True, 'channel': channel,
                              'channels': credentials.summary()}))

@app.route('/notify/unbind', methods=['POST'])
def unbind_notification():
    """ Forget a channel's credentials """
    channel = request.form.get('channel')
    if channel not in credentials.FIELDS:
        return _no_store(jsonify({"error": "unknown_channel", "detail": channel})), 400

    credentials.forget(channel)
    eventlog.record('notify_unbound', channel=channel, ip=eventlog.client_ip())
    return _no_store(jsonify({'channels': credentials.summary()}))

@app.route('/notify/channels')
def notification_channels():
    """ Whether each channel is bound. Never the credentials themselves. """
    return _no_store(jsonify({'channels': credentials.summary(),
                              'fields': {c: list(f) for c, f in credentials.FIELDS.items()}}))

@app.route('/notify/test', methods=['POST'])
def test_notification():
    """
    Send where a real warning would go, so the test proves the actual path.

    That means linked and ticked, not merely linked: testing a service the page
    has unticked would be reporting on something that will never be used.
    """
    channels = notify.send_channels()
    if not channels:
        return _no_store(jsonify({"error": "not_configured", "detail": "no channel bound"})), 400

    failures = {}
    for channel in channels:
        try:
            notify.send("E-paper frame: test notification", channel)
            eventlog.record('notified', channel=channel, reason='test')
        except notify.NotifyError as error:
            failures[channel] = error.detail or error.code
            eventlog.record('error', where='notify', message=error.code,
                            detail=error.detail, channel=channel)

    if failures:
        return _no_store(jsonify({"error": "rejected", "detail": failures})), 502
    return _no_store(jsonify({'sent': True, 'channels': channels}))

@app.route('/log/clear', methods=['POST'])
def clear_log():
    """ Empty the event log, then record that it happened """
    try:
        eventlog.clear()
    except Exception as error:
        return _no_store(jsonify({"error": str(error)})), 500

    eventlog.record('log_cleared', ip=eventlog.client_ip())
    return _no_store(jsonify({'cleared': True}))

def _serve_thumbnail(asset_id):
    try:
        content, content_type = immich.fetch_thumbnail(asset_id)
    except immich.ImmichError as error:
        return _no_store(jsonify({"error": error.message})), error.status
    return _no_store(send_file(io.BytesIO(content), mimetype=content_type))

@app.route('/preview/original')
def preview_original():
    """ The photo the frame is showing now """
    if not state.last_photo['asset_id']:
        return jsonify({"error": "No photo has been sent to the frame yet"}), 404
    return _serve_thumbnail(state.last_photo['asset_id'])

@app.route('/preview/next')
def preview_next():
    """ The photo the frame will be given on its next wake-up """
    if not state.next_photo['asset']:
        return jsonify({"error": "No photo has been chosen yet"}), 404
    return _serve_thumbnail(state.next_photo['asset']['id'])

@app.route('/next', methods=['GET', 'POST'])
def upcoming_photo():
    """
    What the frame will show next. GET chooses one only if none is remembered;
    POST always picks again, which is what the "swap" button uses.
    """
    album = config.immich()['album']
    try:
        # Wait for a preparation already under way rather than choosing a second
        # photo in parallel and overwriting the one it is rendering
        with _prepare_lock:
            needs_choice = request.method == 'POST' or not state.next_photo['asset'] \
                or state.next_photo['album'] != album
            if needs_choice:
                immich.refresh_next_photo()
        if needs_choice:
            start_preparing()
    except immich.ImmichError as error:
        eventlog.record('error', where='next', message=error.message, ip=eventlog.client_ip())
        return _no_store(jsonify({"error": error.message})), error.status

    asset = state.next_photo['asset']
    if not asset:
        return _no_store(jsonify({"error": "No photo could be chosen"})), 404

    if request.method == 'POST':
        eventlog.record('photo_swapped', ip=eventlog.client_ip(),
                        asset_id=asset['id'], album=album)

    return _no_store(jsonify({
        'asset_id': asset['id'],
        'link': immich.photo_link(asset['id']),
        'taken_at': immich.taken_at_text(asset),
        # Whether the packed image is already waiting for the frame
        'prepared': bool(state.next_photo['rendered']),
    }))

# ------------------------------------------------ preparing the next photo

RENDER_KEYS = ('rotation', 'display_mode', 'enhanced', 'contrast', 'strength')

def render_settings():
    """ The settings a rendered image depends on, to tell whether a prepared one is still right """
    settings_now = config.immich()
    return {key: settings_now[key] for key in RENDER_KEYS}

def render_asset(selected):
    """
    Fetch, process and pack one asset for the panel.

    Returns (BytesIO of C-array text, timing) where timing holds the
    milliseconds of each step and the size of the original.
    """
    timing = {}
    clock = time.perf_counter()

    def lap(name):
        nonlocal clock
        now = time.perf_counter()
        timing[name] = int((now - clock) * 1000)
        clock = now

    original = immich.fetch_original(selected['id'])
    timing['original_bytes'] = len(original)
    lap('fetch_ms')
    image = imaging.open_asset(io.BytesIO(original), selected.get('originalPath'))
    lap('decode_ms')

    settings_now = config.immich()
    processed = imaging.scale_img_in_memory(
        image,
        rotation=settings_now['rotation'],
        display_mode=settings_now['display_mode'],
        enhanced=settings_now['enhanced'],
        contrast=settings_now['contrast'],
        strength=settings_now['strength'],
    )
    lap('process_ms')
    c_code = imaging.pack_bmp_for_panel(processed)
    lap('pack_ms')
    return c_code, timing

_prepare_lock = threading.Lock()

def prepare_next_photo():
    """
    Choose the next photo if none is remembered, then render it, so /download
    can answer from memory. Listing a large album takes around ten seconds and
    rendering one or two more, and the frame otherwise spends all of it awake
    with the radio on. Runs on a thread and never raises; one run at a time.
    """
    if not _prepare_lock.acquire(blocking=False):
        return
    try:
        # A swap or a settings change while rendering makes the result stale,
        # so go round again rather than leave nothing prepared.
        for _ in range(3):
            settings_now = config.immich()
            album = settings_now['album']
            if not settings_now['url'] or not album:
                return
            if not state.next_photo['asset'] or state.next_photo['album'] != album:
                immich.refresh_next_photo()
            asset = state.next_photo['asset']
            if not asset or state.next_photo['rendered']:
                return

            settings_used = render_settings()
            c_code, timing = render_asset(asset)
            if state.next_photo['asset'] is asset and settings_used == render_settings():
                state.next_photo['rendered'] = {
                    'asset_id': asset['id'],
                    'c_code': c_code.getvalue(),
                    'settings': settings_used,
                    'timing': timing,
                }
                total = sum(value for key, value in timing.items() if key.endswith('_ms'))
                print(f"Prepared next photo {asset['id']} in {total} ms")
                return
    except Exception as error:
        # Only a convenience: the next /download renders on the spot instead
        print(f"Could not prepare the next photo: {error}")
    finally:
        _prepare_lock.release()

def start_preparing():
    threading.Thread(target=prepare_next_photo, daemon=True).start()

# ------------------------------------------------- the contract with the frame

def _int_header(name):
    """ A numeric request header, or None when absent or malformed """
    try:
        return int(request.headers.get(name))
    except (TypeError, ValueError):
        return None

@app.route('/download', methods=['GET'])
def process_and_download():
    """
    The panel image, as C-array source text: "XX,XX,..." terminated by "};".

    The device sends its battery voltage in the batteryCap request header, in
    millivolts, and reads the X-Photo-Url response header for the NFC tag.
    """
    reported_mv = 0
    try:
        reported_mv = float(request.headers.get('batteryCap', '0'))
        if reported_mv > 0:
            state.battery.update({'voltage': reported_mv, 'updated': time.time()})
    except (TypeError, ValueError):
        reported_mv = 0

    album = config.immich()['album']
    if not config.immich()['url'] or not album:
        message = "Immich URL or Album not configured"
        eventlog.record('error', where='download', message=message, ip=eventlog.client_ip())
        return jsonify({"error": message}), 500

    try:
        # Timed per phase and reported in the check-in event: the frame stays
        # awake, radio on, for the whole of this, so it is worth watching.
        clock = time.perf_counter()
        timing = {}

        def lap(name):
            nonlocal clock
            now = time.perf_counter()
            timing[name] = int((now - clock) * 1000)
            clock = now

        # Use the photo already chosen for this wake-up when there is one, so the
        # frame gets exactly what the settings page was showing as "next".
        rendered = None
        if state.next_photo['asset'] and state.next_photo['album'] == album:
            selected = state.next_photo['asset']
            albumid = state.next_photo['album_id']
            rendered = state.next_photo['rendered']
        else:
            albumid = immich.resolve_album_id()
            selected = immich.select_asset(immich.list_album_assets(albumid))

        # Handed over, so it is no longer "next"
        state.clear_next_photo()

        asset_id = selected['id']
        tracking.mark_shown(asset_id)
        lap('select_ms')

        # Prepared on a thread after the previous hand-over; good to send
        # unless the picture settings have changed since it was rendered.
        if rendered and rendered['asset_id'] == asset_id \
                and rendered['settings'] == render_settings():
            c_code = io.BytesIO(rendered['c_code'])
            timing['prerendered'] = True
        else:
            c_code, render_timing = render_asset(selected)
            timing.update(render_timing)
            timing['prerendered'] = False

        state.last_photo.update({'asset_id': asset_id, 'shown_at': datetime.now(),
                                 'taken_at': immich.taken_at_text(selected)})

        response = send_file(c_code, mimetype='text/plain', as_attachment=True,
                             download_name=f"image_{asset_id}.c")
        # Deep link the firmware writes to the ST25DV NFC tag (Arduino/nfc_writer.cpp)
        response.headers['X-Photo-Url'] = \
            f"https://my.immich.app/albums/{albumid}/photos/{asset_id}"

        # MAC and signal strength are only here if the firmware sends them: HTTP
        # carries no MAC and the container cannot read the LAN's ARP table.
        eventlog.record('checkin', ip=eventlog.client_ip(), asset_id=asset_id, album=album,
                        battery_mv=int(reported_mv) if reported_mv else None,
                        battery_pct=battery.percentage(reported_mv) if reported_mv else None,
                        mac=request.headers.get('X-Device-Mac'),
                        rssi=request.headers.get('X-Device-Rssi'),
                        agent=request.headers.get('User-Agent'),
                        # Sent by firmware from October 2026 on: milliseconds
                        # awake before this request, and what woke the frame
                        uptime_ms=_int_header('X-Uptime-Ms'),
                        wake=request.headers.get('X-Wake'),
                        timing=timing)

        if reported_mv:
            # Sent on a thread: the frame gives up after 50 seconds and must not
            # wait on Telegram or LINE
            notify.check_battery(battery.percentage(reported_mv), reported_mv)

        # Choose and render the following photo now, while the frame sleeps
        start_preparing()

        return response

    except immich.ImmichError as error:
        eventlog.record('error', where='download', message=error.message, ip=eventlog.client_ip())
        return jsonify({"error": error.message}), error.status
    except Exception as error:
        eventlog.record('error', where='download', message=str(error), ip=eventlog.client_ip())
        return jsonify({"error": str(error)}), 500

@app.route('/sleep', methods=['GET'])
def get_sleep_duration():
    """
    How long the frame should sleep, in milliseconds. Derived from local time, so
    TZ has to be set or the quiet hours land at the wrong time of day.
    """
    now = datetime.now()
    settings_now = config.immich()
    interval = int(settings_now['wakeup_interval'])

    def next_interval(base_time, intervals=1):
        total_minutes = base_time.hour * 60 + base_time.minute
        upcoming = interval * ((total_minutes // interval) + intervals)
        upcoming = upcoming % (24 * 60)  # wrap around midnight

        candidate = base_time.replace(hour=upcoming // 60, minute=upcoming % 60,
                                      second=0, microsecond=0)
        if candidate < base_time:
            candidate = candidate + timedelta(days=1)
        return candidate

    next_wakeup = next_interval(now)

    sleep_start = now.replace(hour=settings_now['sleep_start_hour'],
                              minute=settings_now['sleep_start_minute'],
                              second=0, microsecond=0)
    sleep_end = now.replace(hour=settings_now['sleep_end_hour'],
                            minute=settings_now['sleep_end_minute'],
                            second=0, microsecond=0)

    # The window crosses midnight when the end is before the start
    if sleep_end < sleep_start:
        if now >= sleep_start:
            sleep_end = sleep_end + timedelta(days=1)
        elif now < sleep_end:
            sleep_start = sleep_start - timedelta(days=1)

    if sleep_start <= next_wakeup < sleep_end:
        next_wakeup = sleep_end

    sleep_ms = int((next_wakeup - now).total_seconds() * 1000)

    # Waking again in under ten minutes is not worth the radio; skip a slot
    if sleep_ms < 600000:
        next_wakeup = next_interval(now, intervals=2)
        if sleep_start <= next_wakeup < sleep_end:
            next_wakeup = sleep_end
        sleep_ms = int((next_wakeup - now).total_seconds() * 1000)

    # Deliberately not logged: /sleep runs on every wake-up and its answer is
    # implied by the check-in, so it only crowded out the entries that matter.
    return jsonify({
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "next_wakeup": next_wakeup.strftime("%Y-%m-%d %H:%M:%S"),
        "sleep_duration": sleep_ms,
    })

# -------------------------------------------------------------------- start-up

def sync_time_with_ntp():
    """
    The time according to NTP.

    Note this only *reports* the time: nothing sets the system clock from it, so
    a wrong clock in the container stays wrong. TZ is what matters in practice.
    """
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', timeout=5)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as error:
        print(f"NTP sync failed: {error}")
        return datetime.now()

def run_daily_ntp_sync():
    """ Report the NTP time once a day, a little after 04:00 """
    while True:
        try:
            now = datetime.now()
            next_sync = now.replace(hour=4, minute=11, second=0, microsecond=0)
            if now >= next_sync:
                next_sync = next_sync + timedelta(days=1)

            time.sleep((next_sync - now).total_seconds())

            synced = sync_time_with_ntp()
            print(f"Daily NTP sync completed at {synced.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as error:
            print(f"Error in daily NTP sync: {error}")
            time.sleep(3600)

def main():
    observer = config.start_watcher(config.apply)

    try:
        config.apply(config.read_file())
        eventlog.record('startup')
        start_preparing()

        threading.Thread(target=run_daily_ntp_sync, daemon=True).start()

        app.run(host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
