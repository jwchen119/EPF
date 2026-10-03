# EPF - E-paper Photo Frame

A battery-powered photo frame built around a Waveshare 7.3" Spectra 6 (E6) colour e-paper panel and an ESP32-C6. Photos are managed in an [Immich](https://immich.app) album; a small Flask server (normally run in Docker on a NAS) picks the next photo, crops, enhances and dithers it to the panel's six colours, and hands the ESP32 a stream of bytes it can push straight into the display. The ESP32 does no image processing, so it is awake for well under a minute per photo and spends the rest of its time in deep sleep.

Two parts live in this repository and talk over HTTP:

| Part | Where | What it does |
| --- | --- | --- |
| Server | `app.py`, `epf/`, `cpy.pyx`, `templates/`, `static/` | Flask app in Docker. Talks to Immich, processes photos, serves the settings page, logs check-ins, sends low-battery notifications. |
| Firmware | `Arduino/` | ESP32-C6 sketch. WiFi captive portal, image download, panel driver, optional NFC tag writing, deep sleep. |
| Enclosure | `CAD/` | STEP files for the frame parts. |

## How it works

1. The ESP32 wakes up (timer, or a press on the button) and connects to WiFi.
2. It calls `GET /download` on the server, sending its battery voltage in a request header.
3. The server picks a photo from the configured Immich album, scales and rotates it to 800x480, applies saturation and contrast, dithers it to the six panel colours and packs two 4-bit pixels per byte.
4. The firmware streams the response directly into the panel over SPI, without holding the full image in RAM, and refreshes the display.
5. If an ST25DV NFC tag is fitted, the firmware writes the photo's Immich link (from the `X-Photo-Url` response header) to the tag, so tapping the frame with a phone opens the original photo.
6. It calls `GET /sleep` to learn when to wake up next, which respects the configured quiet hours, then goes back to deep sleep.

## Features

- **Immich as the photo source.** Drop photos into an album and they appear on the frame; nothing has to be copied or converted by hand. HEIC and RAW originals are handled on the server.
- **Server-side processing.** Scaling, rotation, fit or fill, saturation, contrast and Floyd-Steinberg dithering all run on the server. The dithering core is written in Cython.
- **Low power.** The ESP32 only wakes to fetch and show a photo, and the server chooses and renders the following photo right after handing one over, so a wake-up is about 36 seconds, 30 of which are the panel refreshing. The panel is put to sleep before hibernating; the original author measured around 16 uA in deep sleep.
- **Settings page.** Immich URL and album, rotation, fit or fill, random or newest-first ordering, enhancement sliders, quiet hours and wake-up interval, all saved from the browser. Shows the current and the next photo, with a button to swap the next one. Available in English, Traditional Chinese, Simplified Chinese and Japanese.
- **Status and history.** The page shows whether Immich is reachable, whether the album still exists, when the frame last checked in and its battery level, plus a system log of check-ins, settings changes and errors.
- **Low-battery notifications** over Telegram or LINE Messaging API, linked from the settings page. A service only counts as linked once a test message has actually been delivered.
- **Captive portal.** Hold the button at boot and the ESP32 opens a WiFi access point with a setup page for up to five saved networks and the server URL. Adapted from the [TRMNL firmware](https://github.com/usetrmnl/firmware/tree/main/lib/wificaptive).
- **HTTPS.** The firmware can talk to a server behind HTTPS (certificate validation is skipped).
- **NFC tag (optional).** With an ST25DV tag the frame advertises a link to the photo currently on display.
- **One button.** Short press while asleep: wake up and fetch a new photo. Hold for about 3 seconds while booting: enter the captive portal.

## Hardware

- [DFRobot FireBeetle 2 ESP32-C6](https://www.dfrobot.com/product-2771.html)
- [Waveshare 7.3" E Ink Spectra 6 (E6) e-paper module with HAT](https://www.waveshare.com/7.3inch-e-paper-hat-e.htm), 800x480
- Li-Po battery with a PH2.0 connector (the FireBeetle charges it over USB)
- A momentary push button for wake-up and setup
- Optional: ST25DV16 NFC tag breakout (I2C)
- A picture frame deep enough for the panel; STEP files for the internal parts are in `CAD/`

### Wiring

| Function | ESP32-C6 GPIO | Notes |
| --- | --- | --- |
| E-paper BUSY | 18 | input, internal pull-up |
| E-paper RST | 14 | |
| E-paper DC | 8 | |
| E-paper CS | 1 | |
| E-paper SCLK | 23 | SPI clock |
| E-paper DIN | 22 | SPI MOSI |
| E-paper VCC / GND | 3V3 / GND | |
| Button | 2 | to GND, internal pull-up; wake-up and setup |
| Battery sense | 0 (ADC) | through a 1:2 divider |
| NFC SDA | 19 | I2C, optional |
| NFC SCL | 20 | I2C, optional |
| NFC VCC | 4 | the GPIO powers the tag directly and is held low during sleep |

## Server

### Run with Docker Compose (recommended)

```bash
git clone https://github.com/jwchen119/EPF.git
cd EPF
cp .env.example .env        # then put your Immich API key in it
docker compose up -d
```

The settings page is then at `http://<host>:15001/`. The compose file bind-mounts `./config` and `./photos` so the settings, the shown-photo history, the event log and the notification credentials survive `docker compose pull` and a container rebuild. It also sets `TZ`, which matters: quiet hours and the wake-up schedule are evaluated in local time.

Everything else is configured from the settings page; there is no config file to edit by hand.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `IMMICH_API_KEY` | required | Immich web UI, Account Settings, API Keys. Read once at start-up. |
| `EPF_PORT` | `15001` | Host port for the settings page and for the frame. Must match the server URL saved in the frame's captive portal. |
| `TZ` | `Asia/Taipei` | Local timezone. Without it the container runs in UTC and the quiet hours shift by the UTC offset. |
| `IMMICH_PHOTO_DEST` | `/photos` | Where `tracking.txt` and `events.jsonl` are kept. No photos are written to disk. |

### Run without Compose

```bash
docker run --name epf \
    -e IMMICH_API_KEY='<your-immich-api-key>' \
    -e TZ=Asia/Taipei \
    -v "$(pwd)/config:/config" \
    -v "$(pwd)/photos:/photos" \
    -d -p 15001:5000 jwchen119/epf
```

The prebuilt image is on [Docker Hub](https://hub.docker.com/r/jwchen119/epf). To build it yourself, run `docker build -t jwchen119/epf .` in the repository root, or uncomment `build: .` in `docker-compose.yml`.

### What is stored where

| Path in the container | Contents |
| --- | --- |
| `/config/config.yaml` | Settings saved from the web page. Created with defaults on first start and watched for external edits. |
| `/config/credentials.json` | Telegram and LINE tokens, written only after a successful test message. |
| `/photos/tracking.txt` | Which photos of the current album have already been shown. |
| `/photos/events.jsonl` | The system log shown on the settings page. |

### HTTP endpoints

The two the firmware uses:

| Endpoint | Used by | Purpose |
| --- | --- | --- |
| `GET /download` | frame | The next photo as a hex byte stream, prepared in advance so the frame is not kept awake while the album is listed and the image processed. Request header `batteryCap` carries the battery voltage in millivolts; response header `X-Photo-Url` carries the photo's Immich link for the NFC tag. |
| `GET /sleep` | frame | `{current_time, next_wakeup, sleep_duration}`; `sleep_duration` is in milliseconds and already accounts for the quiet hours. |

The rest serve the settings page: `/setting` (GET renders, POST saves), `/status`, `/log`, `/log/clear`, `/next` (GET shows, POST re-chooses), `/preview/original`, `/preview/next`, and `/notify/bind`, `/notify/unbind`, `/notify/channels`, `/notify/test`. The settings page has no authentication, so keep the port on your LAN or behind a reverse proxy that adds some.

### Notes for developers

- `cpy.so` is a prebuilt Linux x86-64 Cython module committed to the repository. Changing `cpy.pyx` has no effect until you rebuild it on Linux (`cython` plus the NumPy headers) and replace the binary. The module cannot be loaded on Windows, so `python app.py` only runs on Linux or in Docker.
- The server-side module layout, the image pipeline and the exact HTTP contract are documented in `CLAUDE.md`.
- Three palettes must agree: the pure-RGB palette inside `cpy.pyx`, the measured panel colours in `epf/imaging.py`, and the `EPD_7IN3E_*` colour codes in `Arduino/epd7in3e.h`.

## Firmware

### Build with PlatformIO (recommended)

Open the `Arduino` folder in VS Code with the PlatformIO or pioarduino extension, or from a shell:

```bash
cd Arduino
pio run                 # build
pio run -t upload       # flash over USB
pio device monitor      # serial output at 115200 baud
```

`platformio.ini` pulls in the ESP32-C6 board support (the pioarduino fork of the Espressif platform, since the upstream one does not support the C6 yet), the `min_spiffs` partition table and all libraries: ArduinoJson 7, AsyncTCP and ESPAsyncWebServer (ESP32Async forks), NTPClient, STM32duino ST25DV and QRCode.

`pio run -t upload` writes only the bootloader, partition table and application, so the Wi-Fi and server settings stored in NVS survive an update. The build also produces `firmware.factory.bin`, a single image for tools that flash from address 0 such as [web.esphome.io](https://web.esphome.io/); flashing it erases the whole flash including those settings, and the frame comes up in setup mode afterwards. The frame's USB port only exists while it is awake, so press the button (or hold it for the setup screen) right before uploading.

### Build with the Arduino IDE

1. Install the ESP32 board package (3.x) and select **DFRobot FireBeetle 2 ESP32-C6**.
2. Copy the `Arduino` folder somewhere and rename it to `epd7in3e`, so it matches `epd7in3e.ino`.
3. Install from the Library Manager: ArduinoJson (7.x), Async TCP and ESP Async WebServer (the ESP32Async versions), STM32duino ST25DV, QRCode (Richard Moore).
4. Choose a partition scheme with at least 1.9 MB of app space (for example "Minimal SPIFFS"), then upload.

The NFC library is required to compile even if no tag is fitted; at runtime the firmware simply skips NFC writes when it cannot find one.

### First-time setup

1. Power the frame and hold the button for about 3 seconds while it boots. The serial monitor prints `long press`, the panel shows a setup screen with the network name, the address and two QR codes, and the ESP32 starts an access point named `ESP32_ePAPER`. A frame with no saved network shows the same screen on its own.
2. Connect to it (scan the first QR code, or pick the network by hand); the setup page opens automatically. If it does not, scan the second code or browse to `http://4.3.2.1`. The access point closes after 5 minutes.
3. Pick your WiFi network, enter its password, and enter the server URL, for example `http://192.168.1.10:15001`. Up to five networks are remembered and tried in turn.
4. Save. The frame connects, fetches the first photo and goes to sleep.

To change the settings later, hold the button during a reboot the same way. Saved networks are listed on the page and can be selected without retyping their password.

### Day-to-day behaviour

- Wakes on the schedule the server returns, or immediately on a short button press.
- Below 3.05 V the frame clears the screen and sleeps for 24 hours to protect the battery.
- A server error (HTTP 500) is retried up to five times, ten seconds apart within the same wake-up. If the photo arrives but no schedule does, the frame sleeps for an hour.
- When a wake-up ends without a new photo (no Wi-Fi, server unreachable, download rejected), the frame keeps the current photo and quietly tries again after 15, 30 and then 60 minutes. If the fourth attempt also fails it draws an error screen explaining what went wrong, with the server address, network, battery level and when it will try next, and from then on checks every 6 hours to spare the battery. A button press always retries at once, restarts the schedule from 15 minutes, and shows the error screen if that attempt fails too. The first successful photo clears the count.
- Right after first setup the server answers with an error until an album is configured on the settings page. Once it is, either wait for the next retry or press the button to fetch the first photo immediately.
- When the battery is empty the panel shows a charging reminder instead of going blank.
- If the panel does not respond within 60 seconds the firmware gives up on the refresh instead of hanging.
- With an NFC tag fitted, the tag reads "Updating..." while a new photo is being fetched and then carries the link to the photo on display. The tag is powered off during deep sleep.

### Editing the captive portal page

`WifiCaptivePage.h` is the portal's HTML, gzip-compressed into a C array. The source is `Arduino/AP_webpage_src/index.html`. After editing it, run:

```bash
python Arduino/AP_webpage_src/compress_html.py
```

`decompress_html.py` does the reverse if you need to recover the HTML from the header.

## Credits

- `WifiCaptive*` is adapted from the [TRMNL firmware](https://github.com/usetrmnl/firmware/tree/main/lib/wificaptive).
- `epd7in3e.*` and `epdif.*` are based on the Waveshare driver for the 7.3" E6 panel.

## License

MIT. See `LICENSE`.
