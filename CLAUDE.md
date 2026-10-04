# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An e-paper photo frame split across two codebases that talk over HTTP:

- **Server** (`app.py`, `epf/`, `cpy.pyx`, `templates/`, `static/`) — a Flask app, normally run in Docker on a NAS. Pulls photos from an [Immich](https://immich.app) album, crops/enhances/dithers them to the panel's 6-color palette, and serves the result already packed for the display.
- **Firmware** (`Arduino/`) — an ESP32-C6 sketch (`epd7in3e.ino`) for a Waveshare 7.3" Spectra 6 (E6) panel, 800x480. It does no image processing: it streams bytes straight into the panel and goes back into deep sleep.
- **CAD** (`CAD/*.STEP`) — enclosure parts, not built by any toolchain here.

There are no tests, no linter config, and no build system for the Python side.

## Server: build and run

`docker compose up -d`, with a `.env` alongside holding `IMMICH_API_KEY`. Or directly: `python app.py` (serves on `0.0.0.0:5000`).

`docker-compose.yml` exists because two things are easy to get wrong and both fail silently:

- Two paths are **hardcoded**, not configurable: `/config/config.yaml` (written by the settings page, watched by `watchdog` for external edits, created from `DEFAULT_CONFIG` if missing) and `/photos` (override with `IMMICH_PHOTO_DEST`; holds only `tracking.txt` — no photos are ever written to disk). A plain `docker restart` keeps them, but recreating the container — which is what updating the image requires — discards anything not bind-mounted, so settings revert to `DEFAULT_CONFIG` without any error.
- **`TZ` must be set.** The base image has no timezone, so `datetime.now()` returns UTC. `/sleep` derives both the sleep window and the wake-up schedule from local time, so an unset `TZ` shifts the frame's quiet hours by the whole UTC offset. Zone data is already in the image, so the env var alone is enough — no `tzdata` install and no `/etc/localtime` mount.

`IMMICH_API_KEY` is read once at import into the module-level `headers` dict. Note the README's `docker run` example writes `IMMICH-API-KEY` with hyphens, which the app does not read.

## Server: how the code is laid out

`app.py` holds the Flask app and every route; everything else is in `epf/`:

| module | holds |
| --- | --- |
| `config.py` | `DEFAULT_CONFIG`, the live settings, `config.yaml` read/write, the watchdog observer |
| `state.py` | in-memory runtime state: battery reading, current photo, pre-chosen next photo and its pre-rendered panel image (`next_photo['rendered']`) |
| `eventlog.py` | the JSONL event log and `client_ip()` |
| `tracking.py` | `tracking.txt` |
| `immich.py` | album/asset queries, `select_asset()`, health check, thumbnail fetch; the `/download` path (`resolve_album_id`, `list_album_assets`, `fetch_original`) goes through `_call()`, which applies `CONNECT_TIMEOUT`/`READ_TIMEOUT` and turns transport failures into `ImmichError` 502/504 — the timeouts must stay under the firmware's 50s `HTTP_TIMEOUT` |
| `imaging.py` | the pipeline; takes its settings as arguments and reads no globals |
| `battery.py` | voltage → percentage |
| `notify.py` | low-battery push over Telegram or LINE |
| `credentials.py` | the notification tokens, in `/config/credentials.json` |

**The live settings are one dict that is only ever updated in place** (`config.apply()` calls `.update()`; it never rebinds `config.current`). Modules call `config.immich()` at the point of use. Copying a value out at import time — `from epf.config import current; url = current['immich']['url']` — would freeze it at start-up, which is the one way to break this layout. `config.current` is a `deepcopy` of `DEFAULT_CONFIG` for the same reason a shallow copy was wrong: the two would share the inner dict, and saving settings would rewrite the defaults the reset button restores.

The front end is split the same way: `templates/settings.html` is markup only, with `static/css/settings.css`, `static/js/i18n.js` (the translation dictionary) and `static/js/settings.js` (behaviour). Two things stay inline in the template and must: the theme bootstrap has to run before the stylesheet or the wrong theme flashes, and `window.EPF_DEFAULTS` is how the server's defaults reach the static JS. Assets are linked through `static_url()`, which appends the file's mtime so a browser cannot serve a stale one after an update.

## Server: HTTP contract with the firmware

This contract is the thing to be careful about — both sides must change together.

- `GET /download` — the device sends its battery voltage in a `batteryCap` **request header** (millivolts), plus `X-Uptime-Ms` (milliseconds awake before the request) and `X-Wake` (`manual`/`timer`), which the server only records in the check-in event (`uptime_ms`, `wake`) — the way to see where a battery-powered wake-up spends its time, since there is no serial port then. Response is `text/plain`: ASCII hex bytes as `"XX,XX,..."` terminated by `};`, i.e. C-array source text, not binary. The `X-Photo-Url` response header carries the Immich web URL of the chosen photo — the firmware reads it with `collectHeaders` and writes it to the ST25DV NFC tag (`Arduino/nfc_writer.cpp`) before streaming the image.
- `GET /sleep` — returns `{current_time, next_wakeup, sleep_duration}` where `sleep_duration` is **milliseconds**. The firmware divides by 1000 and passes it to `esp_deep_sleep`. If `/sleep` fails after a successful download the firmware falls back to `SLEEP_INTERVAL` (1h). If `/download` fails — any non-200 after up to `MAX_RETRIES` attempts on a 500, or a transport error — it never calls `/sleep`; `failAndSleep()` counts the failure in Preferences and sleeps with back-off (`MIN_SLEEP_TIME` doubled per failure for `QUIET_RETRIES`, then `ERROR_SLEEP_TIME`), so a server-side change to the failure status code changes nothing on the device beyond whether it retries first. `/download` and `/sleep` are two separate requests per wake cycle.
- `GET /setting` (GET renders, POST saves) — the config UI; `/` redirects here. Battery percentage shown here comes from the last `/download` request's header, cached in module globals for one hour, so it reads 0% until the device has checked in.
- `GET /log?limit=N` — the system-log card, newest first (limit clamped to 500). Events are appended as JSONL to `events.jsonl` beside `tracking.txt`, so the mount that keeps the settings keeps the history; `log_event()` never raises and is guarded by a lock, because the threaded dev server means the device and a browser can write at once. The file is trimmed to `LOG_MAX_ENTRIES` once it passes `LOG_TRIM_BYTES`. Events: `checkin` (ip, battery, asset, album, plus `mac`/`rssi` **only if the firmware sends `X-Device-Mac`/`X-Device-Rssi`** — HTTP carries no MAC and the container cannot read the LAN's ARP table), `settings_saved` (with a before/after diff), `config_reloaded`, `tracking_reset`, `notified`, `notify_bound`, `notify_unbound`, `log_cleared`, `error`, `startup`. `/sleep` deliberately writes nothing: it fires every wake-up and its answer is implied by the check-in. `POST /log/clear` empties the file.
- `POST /notify/bind` / `POST /notify/unbind` / `GET /notify/channels` / `POST /notify/test` — linking a notification service. **Nothing is stored until a test message is actually delivered**, so "linked" always means "known to work". Credentials live in `/config/credentials.json` (`credentials.py`), not the environment, so a token can be changed without recreating the container, and **`/notify/channels` reports only whether each channel is linked — never the values**, since the settings page has no authentication. The low-battery warning is triggered from `/download`, the only place a reading arrives, and sent **on a thread** because the frame gives up after 50s. It goes to every channel that is both linked and ticked on the settings page (`use_telegram`/`use_line`, on by default), so linking two services does not force both to be messaged; rate limiting lives in `state.notify['last_sent']`, in memory, so a restart allows one extra message. LINE needs the Messaging API — LINE Notify was discontinued in 2025.
- `GET /status` — fills the header indicators, fetched by the page after load rather than blocking the render. Reports Immich health by calling `GET /api/albums` (one request covers reachability, whether the key is accepted, and whether the configured album still exists), plus how long ago the frame checked in, derived from `last_battery_update`/`last_photo['shown_at']` and judged stale past two `wakeup_interval`s. Returns codes such as `unauthorized` or `album_missing` rather than sentences, so the page renders them in the active language.
- `GET /preview/original` and `GET /preview/next` — the two images in the "photos" card: what the frame is showing, and what it will be given next. Both proxy Immich's `/api/assets/{id}/thumbnail?size=preview` through `proxy_thumbnail`, because the API key never reaches the browser and originals may be HEIC or RAW that browsers cannot display. `/preview/original` 404s until the device has fetched an image at least once; `/preview/next` 404s until something has been chosen.
- `GET /next` (choose only if nothing is remembered) and `POST /next` (always choose again, which is the swap button) — the frame is handed exactly the asset `/next` reported, so the page and the device cannot disagree. Under `random` ordering there was previously no such thing as "next": it did not exist until the device asked. The response's `prepared` flag says whether the packed image is already waiting.
- **The next photo is prepared in advance.** Listing a large album through `/api/search/metadata` costs ~0.6 s per 1000 assets (17,600 assets → 10 s) and rendering 1-2 s more, all of which the frame used to spend awake with the radio on. `start_preparing()` runs `prepare_next_photo()` on a thread at start-up, after every `/download` hand-over, after a swap and after a settings save: it chooses if nothing is chosen and renders into `state.next_photo['rendered']` together with the `RENDER_KEYS` settings it used. `/download` serves that when the asset and settings still match (`timing.prerendered` in the check-in event), otherwise renders on the spot. Measured on the frame: server wait 0.2 s instead of 14 s.

## Server: image pipeline

`/download` → pick asset → `scale_img_in_memory()` → `convert_to_c_code_in_memory()`. Everything is in-memory `BytesIO`.

1. **Asset selection.** Album assets are fetched via paginated `POST /api/search/metadata` filtered by `albumIds` — *not* `GET /api/albums/{id}`, which stopped returning `assets` in Immich v3. `tracking.txt` records which assets have been shown: line 1 is the album name (changing albums resets the file), remaining lines are asset IDs. `image_order` is `random` (reset when exhausted) or `newest` (reset when a newer photo appears).
2. **Scale + enhance.** `cpy.load_scaled()` rotates and either letterboxes (`fit`) or center-crops (`fill`) to 800x480, then PIL `ImageEnhance` applies `enhanced` (saturation) and `contrast`.
3. **Quantize.** `cpy.convert_image()` does Floyd-Steinberg dithering to six pure-RGB colors, with `strength` scaling the error diffusion. The commented-out PIL `.quantize()` block in `scale_img_in_memory` is the superseded version.
4. **Pack.** `depalette_image()` nearest-matches each pixel against the module-level `palette` (the *measured* panel colors, e.g. yellow is `(255,243,56)`) and applies `indices[indices > 3] += 1` to line up with the panel's color codes in `Arduino/epd7in3e.h`. Then two 4-bit indices are packed per byte.

Three palettes must stay consistent: the pure-RGB one inside `cpy.pyx:convert_image`, the measured one at the top of `app.py`, and the `EPD_7IN3E_*` codes in the firmware header.

## cpy: the Cython module

**`cpy.so` is a prebuilt Linux x86-64 binary committed to the repo, and there is no `setup.py` or build step anywhere — not in the Dockerfile, not in `requirements.txt`.** Editing `cpy.pyx` therefore has no effect until you compile it yourself and replace `cpy.so`; on Windows you cannot load the committed `.so` at all, so `import app` fails locally. Assume any `.pyx` change needs a Linux build (`cython` + `numpy` headers) plus a note to the user that the binary must be regenerated.

`EPD_W`/`EPD_H` are duplicated as module constants in `cpy.pyx`; the target size is not passed in. `scale_img_in_memory`'s `target_width`/`target_height` arguments only affect the (currently disabled) date-overlay positioning.

## Firmware: build and flow

Arduino IDE, board FireBeetle 2 ESP32-C6. The folder must be renamed to `epd7in3e` to match the `.ino`. Libraries: ArduinoJson 7, AsyncTCP and ESPAsyncWebServer (ESP32Async forks), STM32duino ST25DV, QRCode (ricmoo). `Arduino/platformio.ini` (pioarduino platform fork, `min_spiffs` partition table) is the PlatformIO alternative. The USB Serial/JTAG port exists only while the ESP32 is awake (it vanishes in deep sleep), and `pio run -t upload` spends ~90 s in its build check before esptool runs, so to flash a sleeping frame wake it and call esptool directly; writing `firmware.factory.bin` at 0x0 wipes NVS (Wi-Fi/server settings), writing `firmware.bin` at 0x10000 keeps it. On a cp950 Windows console set `PYTHONIOENCODING=utf-8` or esptool's progress bar crashes mid-flash. `Serial` is HWCDC (USB Serial/JTAG): with the frame plugged into a PC that has no terminal open, the host driver stops reading once its buffer is full and every `Serial` write then blocks up to 20 × `tx_timeout_ms` — measured 92 s awake instead of 37 s — so `setup()` calls `Serial.setTxTimeoutMs(2)`; keep it. Opening or closing the port from the PC also resets the chip (`rst:0x15 USB_UART_HPSYS`), so a serial monitor attaching mid-cycle restarts the wake-up. Pin map is in the comment block at the top of `epd7in3e.ino`; NFC (ST25DV) uses I2C on GPIO 19/20 and is powered from GPIO 4, which is held LOW through deep sleep. The captive-portal HTML lives in `Arduino/AP_webpage_src/index.html`; run `AP_webpage_src/compress_html.py` to regenerate `WifiCaptivePage.h`. The text screens (`status_screen.*`) draw with `fonts/spleen_8x16.h`, generated from the BSD-licensed Spleen BDF by `fonts/gen_font.py`; they render row by row straight into the panel stream, so there is no framebuffer, and every `show()` is a full 15-25 s refresh — the caller decides whether a redraw is worth it.

`setup()` runs once per wake and never returns to `loop()`:

1. Read battery on ADC pin 0 (×2 for the divider, 50-sample average kept in `batteryMv`). Below 3050 mV: draw the low-battery screen and sleep 24h. `manualWake` records whether the timer woke us.
2. `epd.Init()`, mount SPIFFS, open the `data` Preferences namespace.
3. `Button(CONFIG_PIN).result()` — blocks ~3.5s watching GPIO 2. A ~3s hold enters the captive portal; a short press just proceeds (that's the wake-and-refresh path).
4. Connect via `WifiCaptivePortal` (up to 5 saved SSIDs, AP `ESP32_ePAPER` at `http://4.3.2.1`), or start the portal if nothing is saved.
5. `downloadImage()`: read `SERVER_BASE_URL` from Preferences, GET `/download`, stream-parse the hex text and `epd.SendData()` each byte after `SendCommand(0x10)`, then `TurnOnDisplay()`; GET `/sleep`; `hibernate()`. It returns only on failure, with `failReason` set; `update()` then calls `failAndSleep()`, which increments `retry_count`, draws `showErrorScreen()` only on a manual wake or the first failure past `QUIET_RETRIES`, and sleeps with back-off; a manual wake restarts the count. `setup()` waits `SERIAL_WAIT_BOOT_MS` for a monitor after power-on/flash but only `SERIAL_WAIT_WAKE_MS` after deep sleep, and not at all when `Serial.isPlugged()` is false (battery). `begin()` failing (no Wi-Fi, portal abandoned, panel dead) takes the same path — it used to `ESP.restart()` every 30 s without ever sleeping. The long-press and no-saved-network paths draw `showSetupScreen()` (SSID, portal URL, two QR codes) before `startPortal()`.

State lives in two Preferences namespaces: `data` (`SERVER_BASE_URL`, `retry_count` = consecutive failed wake-ups, reset by a successful download) and `wificaptive` (SSIDs/passwords, last-used index). `WifiCaptive.cpp` writes `SERVER_BASE_URL` on portal save; the `SERVER_BASE_URL` `#define` in `config.h` is a leftover and is not the value used at runtime.

Deep sleep wakes on the timer or on GPIO 2 going low (`ext1`). `epd.Sleep()` before hibernating matters for the ~16µA target — dropping it leaves the panel drawing current.

`WifiCaptive*` files are adapted from [TRMNL firmware](https://github.com/usetrmnl/firmware/tree/main/lib/wificaptive); `epd7in3e.*` and `epdif.*` are Waveshare vendor drivers. Prefer keeping local edits minimal and obvious in all of these.

## Web installer (`docs/`)

`docs/` is served by GitHub Pages at https://jwchen119.github.io/EPF/ (Settings → Pages → `main` / `docs`). `index.html` is a static, self-contained page (zh-TW/en strings in one dictionary, `?lang=` or the toggle, stored in `localStorage`) around two [ESP Web Tools](https://esphome.github.io/esp-web-tools/) install buttons whose `manifest` attribute is switched by the version selector. `firmware/versions.json` lists releases (newest first, `latest`); `firmware/v<version>/` holds `app.bin` (application, 0x10000), `factory.bin` (combined image, 0x0), `SHA256SUMS.txt` and the two manifests. **ESP Web Tools treats a board that does not speak Improv as a new install and erases the whole flash first unless the manifest sets `new_install_prompt_erase: true`**, so `update.json` prompts (the page tells the user to leave "Erase device" unticked, which keeps NVS) while `factory.json` does not; both set `new_install_improv_wait_time: 0` because the firmware has no Improv. Publish a release with `python docs/firmware/add_version.py <version> --notes-en ... --notes-zh ...` after `pio run`; `.dockerignore` keeps `docs/` out of the server image. `README.zh-TW.md` is a translation of `README.md` and must be updated together with it.

## Conventions

Everything committed to this repo is written in **English** — code, comments, identifiers, commit messages, docs — because changes may be submitted upstream as merge requests. Pre-existing Traditional Chinese comments in `cpy.pyx` and `Arduino/button.h` are the original author's; leave them alone, but write new comments in English.
