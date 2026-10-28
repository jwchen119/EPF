/*
 * Part of the e-paper photo frame settings page.
 * Behaviour: language, theme, header status, previews and the log.
 * Loaded after i18n.js, which defines TRANSLATIONS.
 */
/*
 * Client-side translations. Adding a language means adding one block here
 * plus one <option> to #langSelect; no server-side change is required.
 * English is the fallback for any key a translation is missing.
 */

/*
 * DEFAULT_CONFIG['immich'], handed over by the page. The reset button
 * reads its values from here so it cannot drift away from the defaults
 * the server itself falls back to.
 */
const DEFAULT_SETTINGS = window.EPF_DEFAULTS || {};

const FALLBACK_LANG = 'en';
const LANG_STORAGE_KEY = 'epf_lang';
const THEME_STORAGE_KEY = 'epf_theme';
const THEME_MODES = ['auto', 'light', 'dark'];
let currentLang = FALLBACK_LANG;
let themeMode = 'auto';

// localStorage throws in some privacy modes, so every access is guarded
function readStoredLang() {
    try {
        return localStorage.getItem(LANG_STORAGE_KEY);
    } catch (e) {
        return null;
    }
}

function storeLang(lang) {
    try {
        localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch (e) {
        /* preference simply will not persist */
    }
}

// Stored choice wins; otherwise fall back to the browser's preferred languages.
// A bare 'zh' tag is treated as Simplified, matching CLDR.
function detectLanguage() {
    const stored = readStoredLang();
    if (stored && TRANSLATIONS[stored]) {
        return stored;
    }

    const preferred = navigator.languages || [navigator.language || ''];
    for (const raw of preferred) {
        const tag = raw.toLowerCase();
        if (tag.startsWith('ja')) {
            return 'ja';
        }
        if (tag.startsWith('zh')) {
            return /hant|tw|hk|mo/.test(tag) ? 'zh-Hant' : 'zh-Hans';
        }
        if (tag.startsWith('en')) {
            return 'en';
        }
    }
    return FALLBACK_LANG;
}

function t(key) {
    const dict = TRANSLATIONS[currentLang] || {};
    if (key in dict) {
        return dict[key];
    }
    return TRANSLATIONS[FALLBACK_LANG][key] || key;
}

function applyTranslations() {
    document.documentElement.lang = currentLang;
    document.title = t('page.title');

    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-value]').forEach(el => {
        el.value = t(el.dataset.i18nValue);
    });
    document.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
        el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        el.setAttribute('title', t(el.dataset.i18nTitle));
    });

    // Header status and log rows are generated rather than marked up,
    // so redo them by hand instead of leaving text in the old language
    renderStatus();
    renderLog();
    renderChannels();
    renderCalibration();
}

/*
 * The photo the frame will get next. It is chosen server-side in advance so
 * this can show it; swapping asks the server to pick a different one.
 */
function renderNext(info) {
    const slot = document.getElementById('nextSlot');
    if (!info || !info.asset_id) {
        slot.hidden = true;
        return;
    }
    document.getElementById('nextLink').href = info.link;
    document.getElementById('nextTaken').textContent = info.taken_at || '';
    // The URL is stable, so a swap needs a cache-buster to actually reload
    document.getElementById('nextPreview').src = 'preview/next?t=' + Date.now();
    slot.hidden = false;
    // The card starts hidden when the frame has not been sent a photo yet; a
    // chosen next photo is reason enough to reveal it.
    document.getElementById('photoCard').hidden = false;
}

function loadNext(method) {
    fetch('next', { method: method || 'GET', cache: 'no-store' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error(response.status)))
        .then(renderNext)
        .catch(() => renderNext(null));
}

function swapNextPhoto() {
    loadNext('POST');
}

/*
 * Linking a notification service.
 *
 * The credentials are never sent to the page - it is only told which channels are
 * linked - and a channel only counts as linked once a test message has arrived,
 * so "linked" means "known to work".
 */
const CHANNEL_LABELS = { telegram: 'Telegram', line: 'LINE' };
let channelFields = {};
let channelState = {};
let bindingChannel = null;

function renderChannels() {
    Object.keys(CHANNEL_LABELS).forEach(channel => {
        const tile = document.getElementById('tile-' + channel);
        if (!tile) {
            return;
        }
        const info = channelState[channel] || {};
        tile.dataset.bound = info.bound ? 'true' : 'false';
        const state = tile.querySelector('.channel-state');
        state.dataset.i18n = info.bound ? 'bind.bound' : 'bind.unbound';
        state.textContent = t(state.dataset.i18n);

        // Warnings cannot go to a service that is not linked
        const use = document.getElementById('use_' + channel);
        if (use) {
            use.disabled = !info.bound;
        }
    });

    // Warnings have nowhere to go until something is linked
    const none = document.getElementById('notifyNoChannel');
    if (none) {
        none.hidden = Object.values(channelState).some(info => info.bound);
    }
}

function loadChannels() {
    fetch('notify/channels', { cache: 'no-store' })
        .then(response => response.json())
        .then(payload => {
            channelFields = payload.fields || {};
            channelState = payload.channels || {};
            renderChannels();
        })
        .catch(() => { /* the tiles simply stay as they are */ });
}

function openBinding(channel) {
    bindingChannel = channel;
    const bound = (channelState[channel] || {}).bound;

    document.getElementById('bindTitle').textContent = CHANNEL_LABELS[channel] || channel;
    document.getElementById('bindHelp').textContent = t('bind.help.' + channel);
    document.getElementById('bindError').hidden = true;
    document.getElementById('bindForget').hidden = !bound;
    document.getElementById('bindSave').textContent =
        t(bound ? 'btn.bindAgain' : 'btn.bindSave');

    // Always blank: the stored values are never sent to the browser
    const holder = document.getElementById('bindFields');
    holder.textContent = '';
    (channelFields[channel] || []).forEach(field => {
        const group = document.createElement('div');
        group.className = 'form-group';

        const label = document.createElement('label');
        label.setAttribute('for', 'bind-' + field);
        label.textContent = t('bind.field.' + field);

        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'bind-' + field;
        input.autocomplete = 'off';
        input.spellcheck = false;

        group.append(label, input);
        holder.appendChild(group);
    });

    document.getElementById('bindModal').style.display = 'flex';
}

function closeBinding() {
    document.getElementById('bindModal').style.display = 'none';
    bindingChannel = null;
}

function submitBinding() {
    const channel = bindingChannel;
    const body = new FormData();
    body.append('channel', channel);
    (channelFields[channel] || []).forEach(field => {
        body.append(field, document.getElementById('bind-' + field).value.trim());
    });

    const error = document.getElementById('bindError');
    const save = document.getElementById('bindSave');
    error.hidden = true;
    save.disabled = true;
    save.textContent = t('bind.testing');

    fetch('notify/bind', { method: 'POST', body: body, cache: 'no-store' })
        .then(response => response.json().then(payload => ({ ok: response.ok, payload })))
        .then(({ ok, payload }) => {
            save.disabled = false;
            if (!ok) {
                save.textContent = t('btn.bindSave');
                error.textContent = t('bind.failed.' + payload.error) !== 'bind.failed.' + payload.error
                    ? t('bind.failed.' + payload.error)
                    : (payload.detail || payload.error);
                error.hidden = false;
                loadLog();
                return;
            }
            channelState = payload.channels || channelState;
            renderChannels();
            closeBinding();
            showNotification(t('bind.succeeded'));
            loadLog();
        })
        .catch(() => {
            save.disabled = false;
            save.textContent = t('btn.bindSave');
            error.textContent = t('bind.failed.unreachable');
            error.hidden = false;
        });
}

function unbindChannel() {
    const body = new FormData();
    body.append('channel', bindingChannel);
    fetch('notify/unbind', { method: 'POST', body: body, cache: 'no-store' })
        .then(response => response.json())
        .then(payload => {
            channelState = payload.channels || channelState;
            renderChannels();
            closeBinding();
            loadLog();
        })
        .catch(() => closeBinding());
}

function testNotification() {
    fetch('notify/test', { method: 'POST', cache: 'no-store' })
        .then(response => response.json().then(payload => ({ ok: response.ok, payload })))
        .then(({ ok, payload }) => {
            showNotification(ok ? t('notify.testSent')
                : t('notify.testFailed') + ' ' + JSON.stringify(payload.detail || payload.error));
            loadLog();
        })
        .catch(() => showNotification(t('notify.testFailed')));
}

function clearLog() {
    fetch('log/clear', { method: 'POST', cache: 'no-store' })
        .then(() => loadLog())
        .catch(() => loadLog());
}

function setLanguage(lang) {
    currentLang = TRANSLATIONS[lang] ? lang : FALLBACK_LANG;
    storeLang(currentLang);
    document.getElementById('langSelect').value = currentLang;
    applyTranslations();
}

/*
 * Theme: 'auto' follows the OS, 'light' and 'dark' override it. The mode
 * is resolved to an explicit data-theme here rather than in a media query,
 * so the dark palette exists in exactly one place in the stylesheet.
 */
function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
}

function applyTheme() {
    const dark = themeMode === 'dark' || (themeMode === 'auto' && systemPrefersDark());
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');

    const button = document.getElementById('themeToggle');
    button.dataset.mode = themeMode;
    // Keep the i18n keys current so a later language switch relabels it
    button.dataset.i18nAriaLabel = 'theme.' + themeMode;
    button.dataset.i18nTitle = 'theme.' + themeMode;
    button.setAttribute('aria-label', t('theme.' + themeMode));
    button.setAttribute('title', t('theme.' + themeMode));
}

function setTheme(mode) {
    themeMode = THEME_MODES.indexOf(mode) !== -1 ? mode : 'auto';
    try {
        if (themeMode === 'auto') {
            localStorage.removeItem(THEME_STORAGE_KEY);
        } else {
            localStorage.setItem(THEME_STORAGE_KEY, themeMode);
        }
    } catch (e) {
        /* preference simply will not persist */
    }
    applyTheme();
}

function cycleTheme() {
    setTheme(THEME_MODES[(THEME_MODES.indexOf(themeMode) + 1) % THEME_MODES.length]);
}

function readStoredTheme() {
    try {
        return localStorage.getItem(THEME_STORAGE_KEY);
    } catch (e) {
        return null;
    }
}

function showNotification(message) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.style.display = 'block';

    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.style.display = 'none';
        }, 300);
    }, 3000);
}

// data-format on the slider picks how its value reads: a percentage, a
// signed whole number, or one decimal
function formatSliderValue(slider, value) {
    if (slider.dataset.format === 'percent') {
        return Math.round(value * 100) + '%';
    }
    if (slider.dataset.format === 'signed') {
        return (value > 0 ? '+' : '') + value.toFixed(0);
    }
    return value.toFixed(1);
}

/*
 * Show only the controls the chosen dithering method uses: each lists them in
 * data-modes. Hidden inputs are still submitted, so their values are kept.
 */
function updateModeControls() {
    const mode = document.getElementById('dither_mode').value;
    document.querySelectorAll('[data-modes]').forEach(el => {
        el.hidden = el.dataset.modes.split(' ').indexOf(mode) === -1;
    });
}

function updateSliderValue(slider) {
    const value = parseFloat(slider.value);
    const output = slider.nextElementSibling;
    output.textContent = formatSliderValue(slider, value);

    // Paint the filled portion of the track up to the thumb
    const min = parseFloat(slider.min);
    const max = parseFloat(slider.max);
    const pct = max > min ? ((value - min) / (max - min)) * 100 : 0;
    slider.style.setProperty('--fill', pct + '%');
}

/*
 * Header status. /status reports codes rather than sentences so the text
 * can be produced in whichever language is active; the last payload is
 * kept so a language switch can re-render it without refetching.
 */
const STATUS_LABELS = {
    connected: 'status.connected',
    album_missing: 'status.albumMissing',
    unauthorized: 'status.unauthorized',
    unreachable: 'status.unreachable',
    not_configured: 'status.notConfigured',
    server_error: 'status.serverError',
};
let lastStatus = null;

function relativeTime(minutes) {
    if (minutes < 1) {
        return t('status.justNow');
    }
    if (minutes < 60) {
        return t('status.minutesAgo').replace('{n}', minutes);
    }
    if (minutes < 60 * 24) {
        return t('status.hoursAgo').replace('{n}', Math.floor(minutes / 60));
    }
    return t('status.daysAgo').replace('{n}', Math.floor(minutes / 1440));
}

function updateBatteryChip(percentage) {
    const chip = document.getElementById('batteryChip');
    const fill = document.getElementById('batteryFill');
    const label = document.getElementById('batteryPercent');

    // null means the device has never reported in, which is not 0%
    if (percentage === null || percentage === undefined) {
        chip.dataset.state = 'unknown';
        fill.setAttribute('width', '0');
        label.textContent = '—';
        chip.setAttribute('title', t('battery.unknown'));
        return;
    }

    const clamped = Math.max(0, Math.min(100, percentage));
    chip.dataset.state = clamped >= 50 ? 'good' : clamped >= 20 ? 'low' : 'critical';
    // 15.5 is the usable width inside the battery outline
    fill.setAttribute('width', (clamped / 100 * 15.5).toFixed(2));
    label.textContent = clamped.toFixed(1) + '%';
    chip.removeAttribute('title');
}

function renderStatus() {
    const immich = document.getElementById('immichStatus');
    const frame = document.getElementById('frameStatus');
    const immichDetail = document.getElementById('immichDetail');
    const frameDetail = document.getElementById('frameDetail');

    if (lastStatus === null || lastStatus === 'failed') {
        const pending = lastStatus === null;
        immich.dataset.state = frame.dataset.state = pending ? 'pending' : 'error';
        immichDetail.textContent = frameDetail.textContent =
            t(pending ? 'status.checking' : 'status.statusFailed');
        updateBatteryChip(null);
        return;
    }

    immich.dataset.state = lastStatus.immich.state;
    immichDetail.textContent = t(STATUS_LABELS[lastStatus.immich.code] || 'status.serverError');

    // The frame is asleep most of the time, so "ok" means it checked in
    // within a couple of its own wake-up intervals
    frame.dataset.state = lastStatus.frame.state === 'unknown' ? 'pending' : lastStatus.frame.state;
    frameDetail.textContent = lastStatus.frame.minutes_ago === null
        ? t('status.never')
        : relativeTime(lastStatus.frame.minutes_ago);

    updateBatteryChip(lastStatus.battery.percentage);
}

/*
 * System log. Rows are built with createElement rather than innerHTML,
 * because album names, IP addresses and error text all come from outside.
 */
const LOG_EVENTS = {
    checkin: 'event.checkin',
    settings_saved: 'event.settingsSaved',
    photo_swapped: 'event.photoSwapped',
    log_cleared: 'event.logCleared',
    notify_bound: 'event.notifyBound',
    notify_unbound: 'event.notifyUnbound',
    notified: 'event.notified',
    config_reloaded: 'event.configReloaded',
    tracking_reset: 'event.trackingReset',
    error: 'event.error',
    startup: 'event.startup',
    calibrated: 'event.calibrated',
    calibration_reset: 'event.calibrationReset',
};
let logEntries = null;

function logDetail(entry) {
    const parts = [];
    if (entry.event === 'checkin') {
        if (typeof entry.battery_pct === 'number') {
            parts.push(entry.battery_pct.toFixed(1) + '%');
        }
        if (entry.battery_mv) {
            parts.push(entry.battery_mv + ' mV');
        }
        if (entry.album) {
            parts.push(entry.album);
        }
        if (entry.ip) {
            parts.push(entry.ip);
        }
        if (entry.mac) {
            parts.push(entry.mac);
        }
        if (entry.rssi) {
            parts.push(entry.rssi + ' dBm');
        }
        if (typeof entry.uptime_ms === 'number') {
            // How long the frame had been awake when it asked
            parts.push('awake ' + (entry.uptime_ms / 1000).toFixed(1) + ' s before request'
                + (entry.wake ? ' (' + entry.wake + ' wake)' : ''));
        }
        if (entry.timing) {
            // How long the frame waited for the server, by phase
            const t = entry.timing;
            const total = ['select_ms', 'fetch_ms', 'decode_ms', 'process_ms', 'pack_ms']
                .reduce((sum, key) => sum + (t[key] || 0), 0);
            parts.push('server ' + (total / 1000).toFixed(1) + ' s'
                + (t.prerendered
                    ? ' (prepared in advance)'
                    : ' (fetch ' + ((t.fetch_ms || 0) / 1000).toFixed(1)
                        + ', decode ' + ((t.decode_ms || 0) / 1000).toFixed(1)
                        + ', process ' + ((t.process_ms || 0) / 1000).toFixed(1) + ')'));
        }
        if (entry.dither) {
            // Which algorithm made the image now on the panel; older entries
            // may name a method since removed, shown as recorded
            const method = t('dither.' + entry.dither);
            parts.push(t('label.ditherMode').replace(/[:：]\s*$/, '') + ': '
                + (method === 'dither.' + entry.dither ? entry.dither : method));
        }
        if (entry.preview_fallback) {
            // The photo was shown, but from Immich's preview; the reason says why
            parts.push(t('log.previewFallback') + ': ' + entry.preview_fallback);
        }
    } else if (entry.event === 'settings_saved') {
        if (entry.changes) {
            parts.push(Object.keys(entry.changes)
                .map(key => key + ': ' + entry.changes[key][0] + ' \u2192 ' + entry.changes[key][1])
                .join(', '));
        }
        if (entry.ip) {
            parts.push(entry.ip);
        }
    } else if (entry.event === 'calibrated') {
        parts.push(t('calib.photos').replace('{n}', entry.photos_used));
        parts.push(t('calib.dotGain') + ' ' + entry.dot_gain);
        if (entry.ip) {
            parts.push(entry.ip);
        }
    } else if (entry.event === 'tracking_reset' && entry.reason) {
        parts.push(entry.reason);
    } else if (entry.event === 'error' && entry.message) {
        parts.push(entry.message);
        if (entry.asset_id) {
            // Enough of the id to find the photo in Immich
            parts.push(entry.asset_id.slice(0, 8));
        }
    }
    return parts.join(' \u00b7 ');
}

function renderLog() {
    const body = document.getElementById('logBody');
    body.textContent = '';

    if (logEntries === null || logEntries === 'failed' || !logEntries.length) {
        const note = document.createElement('p');
        note.className = 'log-note';
        note.textContent = t(logEntries === 'failed' ? 'log.failed'
            : logEntries === null ? 'status.checking' : 'log.empty');
        body.appendChild(note);
        return;
    }

    logEntries.forEach(entry => {
        const row = document.createElement('div');
        row.className = 'log-row';
        row.dataset.event = entry.event;

        const time = document.createElement('span');
        time.className = 'log-time';
        // 2026-08-14T11:30:02 -> 08-14 11:30
        time.textContent = (entry.ts || '').slice(5, 16).replace('T', ' ');

        const tag = document.createElement('span');
        tag.className = 'log-tag';
        tag.textContent = LOG_EVENTS[entry.event] ? t(LOG_EVENTS[entry.event]) : entry.event;

        const detail = document.createElement('span');
        detail.className = 'log-detail';
        detail.textContent = logDetail(entry);

        row.append(time, tag, detail);
        body.appendChild(row);
    });
}

function loadLog() {
    fetch('log?limit=60', { cache: 'no-store' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error(response.status)))
        // Treat an unexpected shape as a failure rather than letting
        // renderLog() trip over an undefined list
        .then(payload => {
            logEntries = Array.isArray(payload.entries) ? payload.entries : 'failed';
        })
        .catch(() => { logEntries = 'failed'; })
        .then(renderLog);
}

function fetchStatus() {
    fetch('status', { cache: 'no-store' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error(response.status)))
        .then(payload => { lastStatus = payload; })
        .catch(() => { lastStatus = 'failed'; })
        .then(renderStatus);
}

document.addEventListener('DOMContentLoaded', () => {
    setLanguage(detectLanguage());
    setTheme(readStoredTheme() || 'auto');

    // While on 'auto', follow the OS if it flips (e.g. a night schedule)
    const darkQuery = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
    if (darkQuery && darkQuery.addEventListener) {
        darkQuery.addEventListener('change', () => {
            if (themeMode === 'auto') {
                applyTheme();
            }
        });
    }

    document.querySelectorAll('input[type="range"]').forEach(updateSliderValue);
    updateModeControls();
    fetchStatus();
    loadLog();
    loadNext();
    loadChannels();
    loadCalibration();

    const calibImage = document.getElementById('calibImage');
    calibImage.addEventListener('pointerdown', onCalibrationPointerDown);
    calibImage.addEventListener('pointermove', onCalibrationPointerMove);
    calibImage.addEventListener('pointerup', onCalibrationPointerUp);
    calibImage.addEventListener('pointercancel', onCalibrationPointerUp);
    calibImage.addEventListener('load', drawCorners);
    calibImage.addEventListener('error', () => {
        // Most likely HEIC, which only Safari can show
        if (calibSession) {
            const message = document.getElementById('calibError');
            message.textContent = t('calib.cannotShow');
            message.hidden = false;
        }
    });
    window.addEventListener('resize', drawCorners);

    // Both previews are proxied from Immich, so a failure there is the
    // likely cause; say so rather than leaving a broken image.
    document.querySelectorAll('.photo-preview').forEach(image => {
        image.addEventListener('error', () => {
            image.removeAttribute('src');
            showNotification(t('photo.originalFailed'));
        });
    });
});

/*
 * Panel colour calibration. The frame shows the calibration card, the user
 * photographs the panel and marks the card's four corners on each photo here,
 * and the server measures them; nothing changes until Apply. The photos are
 * sent only to be measured and are not kept on the server.
 */
const CALIB_MAX_PHOTOS = 6;
const COLOUR_NAMES = ['black', 'white', 'yellow', 'red', 'blue', 'green'];
const SVG_NS = 'http://www.w3.org/2000/svg';
let calibration = null;
let calibSession = null;

function rgbCss(colour) {
    return 'rgb(' + colour.join(',') + ')';
}

function makeSwatch(colour, title) {
    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.backgroundColor = rgbCss(colour);
    swatch.title = title + ' ' + colour.join(', ');
    return swatch;
}

function renderCalibration() {
    const state = document.getElementById('calibState');
    const swatches = document.getElementById('calibSwatches');
    swatches.textContent = '';
    if (!calibration) {
        state.textContent = t('status.checking');
        return;
    }
    state.textContent = calibration.default
        ? t('calib.stateDefault')
        : t('calib.stateMeasured')
            .replace('{date}', (calibration.measured_at || '').slice(0, 16).replace('T', ' '))
            .replace('{n}', calibration.photos_used);
    // The panel's colours as it shows them, against its own white
    calibration.palette.forEach((colour, i) => {
        swatches.appendChild(makeSwatch(colour, t('colour.' + COLOUR_NAMES[i])));
    });
    document.getElementById('calibReset').hidden = calibration.default;
}

function loadCalibration() {
    fetch('calibration', { cache: 'no-store' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error(response.status)))
        .then(payload => { calibration = payload; })
        .catch(() => { calibration = null; })
        .then(renderCalibration);
}

function showCalibrationCard() {
    fetch('calibration/card', { method: 'POST', cache: 'no-store' })
        .then(response => showNotification(t(response.ok ? 'calib.cardQueued' : 'calib.failed')))
        .catch(() => showNotification(t('calib.failed')));
}

function chooseCalibrationPhotos() {
    const input = document.getElementById('calibFiles');
    input.value = '';
    input.click();
}

function startCalibration(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) {
        return;
    }
    if (files.length > CALIB_MAX_PHOTOS) {
        showNotification(t('calib.tooMany'));
        return;
    }
    calibSession = { files: files, corners: files.map(() => []), index: 0, url: null, drag: -1 };
    document.getElementById('calibModal').style.display = 'flex';
    showCalibrationPhoto(0);
}

function showCalibrationPhoto(index) {
    const session = calibSession;
    session.index = index;
    if (session.url) {
        URL.revokeObjectURL(session.url);
    }
    session.url = URL.createObjectURL(session.files[index]);
    document.getElementById('calibMark').hidden = false;
    document.getElementById('calibResult').hidden = true;
    document.getElementById('calibTitle').textContent = t('calib.markTitle')
        .replace('{n}', index + 1).replace('{total}', session.files.length);
    document.getElementById('calibError').hidden = true;
    document.getElementById('calibImage').src = session.url;
    updateCalibrationButtons();
    drawCorners();
}

function updateCalibrationButtons() {
    const session = calibSession;
    const next = document.getElementById('calibNext');
    next.disabled = session.corners[session.index].length < 4;
    next.textContent = t(session.index === session.files.length - 1 ? 'btn.measure' : 'btn.next');
}

// Where the pointer is, as fractions of the photo's width and height
function pointOnPhoto(event) {
    const rect = document.getElementById('calibImage').getBoundingClientRect();
    return [Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1),
        Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1)];
}

// The marker nearest the point, in screen pixels; -1 if none is within reach
function nearestCorner(points, point, reach) {
    const rect = document.getElementById('calibImage').getBoundingClientRect();
    let best = -1;
    let bestDistance = reach;
    points.forEach((p, i) => {
        const distance = Math.hypot((p[0] - point[0]) * rect.width, (p[1] - point[1]) * rect.height);
        if (distance < bestDistance) {
            best = i;
            bestDistance = distance;
        }
    });
    return best;
}

function onCalibrationPointerDown(event) {
    const session = calibSession;
    if (!session) {
        return;
    }
    event.preventDefault();
    const points = session.corners[session.index];
    const point = pointOnPhoto(event);
    let index = nearestCorner(points, point, 28);
    if (index === -1 && points.length < 4) {
        points.push(point);
        index = points.length - 1;
    } else if (index === -1) {
        // All four placed: a tap elsewhere moves the nearest one there
        index = nearestCorner(points, point, Infinity);
        points[index] = point;
    }
    session.drag = index;
    event.currentTarget.setPointerCapture(event.pointerId);
    drawCorners();
    updateCalibrationButtons();
}

function onCalibrationPointerMove(event) {
    const session = calibSession;
    if (!session || session.drag < 0) {
        return;
    }
    session.corners[session.index][session.drag] = pointOnPhoto(event);
    drawCorners();
}

function onCalibrationPointerUp() {
    if (calibSession) {
        calibSession.drag = -1;
    }
}

function drawCorners() {
    const image = document.getElementById('calibImage');
    const overlay = document.getElementById('calibOverlay');
    overlay.textContent = '';
    if (!calibSession || !image.clientWidth) {
        return;
    }
    const w = image.clientWidth;
    const h = image.clientHeight;
    overlay.style.left = image.offsetLeft + 'px';
    overlay.style.top = image.offsetTop + 'px';
    overlay.setAttribute('width', w);
    overlay.setAttribute('height', h);
    overlay.setAttribute('viewBox', '0 0 ' + w + ' ' + h);

    const points = calibSession.corners[calibSession.index].map(p => [p[0] * w, p[1] * h]);
    if (points.length >= 3) {
        // Sorted around their centre, so the outline never crosses itself
        // whatever order the corners were tapped in
        const cx = points.reduce((sum, p) => sum + p[0], 0) / points.length;
        const cy = points.reduce((sum, p) => sum + p[1], 0) / points.length;
        const around = points.slice().sort((a, b) =>
            Math.atan2(a[1] - cy, a[0] - cx) - Math.atan2(b[1] - cy, b[0] - cx));
        const outline = document.createElementNS(SVG_NS, 'polygon');
        outline.setAttribute('points', around.map(p => p.join(',')).join(' '));
        overlay.appendChild(outline);
    }
    points.forEach(p => {
        const marker = document.createElementNS(SVG_NS, 'circle');
        marker.setAttribute('cx', p[0]);
        marker.setAttribute('cy', p[1]);
        marker.setAttribute('r', 10);
        overlay.appendChild(marker);
    });
}

function clearCorners() {
    calibSession.corners[calibSession.index] = [];
    drawCorners();
    updateCalibrationButtons();
}

function nextCalibrationPhoto() {
    const session = calibSession;
    if (session.index < session.files.length - 1) {
        showCalibrationPhoto(session.index + 1);
        return;
    }
    measureCalibration();
}

function measureCalibration() {
    const session = calibSession;
    const body = new FormData();
    session.files.forEach(file => body.append('photo', file, file.name));
    body.append('corners', JSON.stringify(session.corners));

    const next = document.getElementById('calibNext');
    next.disabled = true;
    next.textContent = t('calib.measuring');
    document.getElementById('calibError').hidden = true;

    fetch('calibration/measure', { method: 'POST', body: body, cache: 'no-store' })
        .then(response => {
            if (response.status === 413) {
                throw new Error('calib.tooLarge');
            }
            return response.ok ? response.json() : Promise.reject(new Error('calib.failed'));
        })
        .then(renderCalibrationResult)
        .catch(error => {
            const message = document.getElementById('calibError');
            message.textContent = t(error.message === 'calib.tooLarge' ? 'calib.tooLarge' : 'calib.failed');
            message.hidden = false;
            updateCalibrationButtons();
        });
}

function renderCalibrationResult(result) {
    document.getElementById('calibMark').hidden = true;
    document.getElementById('calibResult').hidden = false;
    document.getElementById('calibTitle').textContent = t('calib.resultTitle');

    // Each colour as the panel shows it now beside the measurement
    const compare = document.getElementById('calibCompare');
    compare.textContent = '';
    if (result.usable) {
        result.palette.forEach((colour, i) => {
            const cell = document.createElement('div');
            cell.className = 'calib-colour';
            const name = document.createElement('span');
            name.textContent = t('colour.' + COLOUR_NAMES[i]);
            const pair = document.createElement('span');
            pair.className = 'calib-pair';
            if (calibration) {
                pair.appendChild(makeSwatch(calibration.palette[i], t('calib.now')));
            }
            pair.appendChild(makeSwatch(colour, t('calib.measured')));
            cell.append(name, pair);
            compare.appendChild(cell);
        });
    }
    document.getElementById('calibFacts').textContent = result.usable
        ? t('calib.legend') + ' \u00b7 ' + t('calib.dotGain') + ' '
            + (calibration ? calibration.dot_gain : '?') + ' \u2192 ' + result.dot_gain
        : t('calib.nothingUsable');

    const list = document.getElementById('calibPhotos');
    list.textContent = '';
    result.photos.forEach(photo => {
        const row = document.createElement('li');
        const verdict = document.createElement('span');
        verdict.className = photo.used ? 'calib-used' : 'calib-problem';
        verdict.textContent = t(photo.used ? 'calib.used' : 'calib.notUsed');
        const problems = photo.problems.map(code => t('calib.problem.' + code)).join(', ');
        row.append(photo.name + ': ', verdict, problems ? ' \u2014 ' + problems : '');
        list.appendChild(row);
    });
    (result.warnings || []).forEach(code => {
        const row = document.createElement('li');
        row.className = 'calib-problem';
        row.textContent = t('calib.warning.' + code);
        list.appendChild(row);
    });
    document.getElementById('calibApply').hidden = !result.usable;
}

function remarkCalibration() {
    showCalibrationPhoto(0);
}

function closeCalibration() {
    document.getElementById('calibModal').style.display = 'none';
    if (calibSession && calibSession.url) {
        URL.revokeObjectURL(calibSession.url);
    }
    calibSession = null;
    document.getElementById('calibImage').removeAttribute('src');
}

function applyCalibration() {
    fetch('calibration/apply', { method: 'POST', cache: 'no-store' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error(response.status)))
        .then(payload => {
            calibration = payload;
            renderCalibration();
            closeCalibration();
            showNotification(t('calib.applied'));
            loadLog();
        })
        .catch(() => showNotification(t('calib.failed')));
}

function resetCalibration() {
    fetch('calibration/reset', { method: 'POST', cache: 'no-store' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error(response.status)))
        .then(payload => {
            calibration = payload;
            renderCalibration();
            showNotification(t('calib.resetDone'));
            loadLog();
        })
        .catch(() => showNotification(t('calib.failed')));
}

function showResetConfirmation() {
    document.getElementById('confirmModal').style.display = 'flex';
}

function confirmReset() {
    // Reset settings to the server's defaults
    ['url', 'album', 'rotation', 'display_mode', 'image_order', 'dither_mode',
        'sleep_start_hour', 'sleep_start_minute',
        'sleep_end_hour', 'sleep_end_minute', 'wakeup_interval',
        'battery_threshold', 'min_interval_hours'].forEach(id => {
            document.getElementById(id).value = String(DEFAULT_SETTINGS[id]);
        });

    // Stored as a boolean, but presented as a two-option select
    document.getElementById('enabled').value = DEFAULT_SETTINGS.enabled ? 'true' : 'false';

    // Tick boxes carry their state in .checked, not .value
    ['use_telegram', 'use_line'].forEach(id => {
        document.getElementById(id).checked = !!DEFAULT_SETTINGS[id];
    });

    ['enhanced', 'contrast', 'strength', 'cc_strength', 'cc_chroma', 'cc_warmth', 'cc_tint'].forEach(id => {
        const sliderElement = document.getElementById(id);
        sliderElement.value = DEFAULT_SETTINGS[id];
        updateSliderValue(sliderElement);
    });

    showNotification(t('notify.reset'));
    document.getElementById('confirmModal').style.display = 'none';
}

function cancelReset() {
    document.getElementById('confirmModal').style.display = 'none';
}

function handleSubmit(event) {
    event.preventDefault();

    // Submit the form using fetch
    fetch(window.location.href, {
        method: 'POST',
        body: new FormData(document.getElementById('settingsForm'))
    })
        .then(response => {
            if (response.ok) {
                showNotification(t('notify.saved'));
                return;
            }
            throw new Error(t('notify.saveFailed'));
        })
        .catch(error => {
            showNotification(error.message);
        });
}
