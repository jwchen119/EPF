# EPF — E-paper Photo Frame

EPF is a battery-powered e-paper photo frame driven by an ESP32. A Flask server (running on a NAS or any always-on host) selects a photo from your Immich library or a local folder, downscales and dithers it to the display's 6-color palette, and serves it to the ESP32 over HTTP. The ESP32 streams the pre-processed image straight to the panel and returns to deep sleep, so a single Li-Po charge lasts months.

## Table of Contents

- [Features](#features)
- [Components](#components)
- [Installation](#installation)
- [Firmware (Arduino)](#firmware-arduino)
- [Development](#development)
- [License](#license)

## Features

- **Immich integration** — Pulls photos from a named Immich album. Tracks which assets have been shown in `tracking.txt` to avoid repeats; resets the tracker once the album cycle completes.
- **Local photo source** — If the `local_photos/` directory contains at least one supported image, it takes priority over Immich. Supports JPEG, BMP, HEIC, and RAW formats (DNG, ARW, CR2, NEF) via `rawpy` and `pillow-heif`.
- **Display modes** — Choose `fit` (letterbox, preserves full image) or `fill` (crop to fill panel) per your taste. Configurable from the web UI.
- **Image order** — `random` (shuffle through the album) or `newest` (always show the most recent un-shown photo first).
- **Date overlay** — Optionally render the photo's capture date (parsed from EXIF or Immich metadata) as a white-on-black label in any of 9 positions (topLeft, topCenter, topRight, centerLeft, center, centerRight, bottomLeft, bottomCenter, bottomRight). Rotation-aware so the label always reads upright. Off by default.
- **Sleep schedule** — Configurable quiet hours (start/end HH:MM) during which the device sleeps through and skips refreshes. Crosses midnight correctly.
- **Wake interval** — Configurable refresh cadence in minutes; the server computes the next aligned wake time and returns it to the ESP32 in the `/sleep` response.
- **Battery monitoring** — The ESP32 reports its battery voltage (mV, 50-sample averaged) in the `batteryCap` HTTP header on every `/download` call. The server stores it and shows percentage on the settings page using a Li-Po voltage table. When running on USB power the device reports `0` and skips deep sleep (uses `delay() + ESP.restart()` instead).
- **Low-battery guard** — If battery voltage falls below 3050 mV the device clears the display and enters a 24-hour deep sleep.
- **Server-side image processing** — All scaling, color enhancement (Pillow `ImageEnhance`), contrast adjustment, and Floyd–Steinberg dithering to the 6-color Seeed T133A01 palette happen on the server. The ESP32 receives a hex-CSV byte stream already in the panel's native nibble format. A Cython-accelerated path (`cpy.convert_image`) speeds up dithering ~5x where available; a pure-Python fallback (`cpy_fallback`) is used otherwise.
- **HTTPS support** — The ESP32 client supports both `http://` and `https://` server URLs (insecure mode — self-signed certs accepted).
- **Captive portal Wi-Fi setup** — Long-press the config button (~3s) during boot to enter setup mode. Stores up to five SSIDs. Adapted from [TRMNL WiFiCaptive](https://github.com/usetrmnl/firmware/tree/main/lib/wificaptive).
- **One-button operation** — Short press while sleeping wakes the device and triggers a refresh. Long press at boot enters captive-portal config mode.

## Components

- **Microcontroller** — [XIAO ESP32-S3 Plus](https://www.seeedstudio.com/XIAO-ESP32S3-Plus-p-6361.html) (16 MB flash, 8 MB PSRAM — PSRAM is REQUIRED for the 1200×1600 frame buffer).
- **Display + HAT** — [Seeed Studio 13.3" Color E-Paper Display + EE02 Driver Board (T133A01)](https://www.seeedstudio.com/13-3-Color-E-Paper-Display-and-EE02-Driver-Board-p-6420.html). 1200×1600 native resolution, 6-color palette (black, white, yellow, red, blue, green).
- **Battery** — Li-Po with PH2.0 connector (any capacity; the EE02 board has a BQ24070 charger circuit). The board's green charge LEDs (D5, D16) are controlled by the PMIC and cannot be suppressed from firmware — they will blink when no battery is connected.
- **Frame** — Any picture frame deep enough to hold the display + EE02 board + battery.
- **Optional** — Tactile button wired to the XIAO's `D0` (GPIO2) pin for wake/setup. The EE02 board exposes this pin on its header.

### Pin layout (XIAO ESP32-S3 Plus on EE02)

| Signal  | XIAO pin | GPIO   |
|---------|----------|--------|
| BUSY    | D3       | GPIO5  |
| RST     | (internal, wired by EE02 board) | GPIO38 |
| DC      | —        | GPIO10 |
| CS      | D7 + CS1 | GPIO44 + GPIO41 |
| SCLK    | D8       | GPIO8  |
| MOSI    | —        | GPIO9  |
| WAKEUP / CONFIG | D0 | GPIO2 |
| BAT_ADC | A0/D0    | GPIO1  |
| ADC_EN  | —        | GPIO5  |

Wiring is fixed by the EE02 HAT — no manual wiring needed beyond seating the XIAO on the board and (optionally) soldering a button to D0.

## Installation

Two supported paths: pull the prebuilt image (recommended) or build locally.

### Prerequisites

- Docker + Docker Compose
- (Optional) An Immich server reachable from the host where you run EPF
- (Optional) An Immich API key — required only if you want to pull photos from Immich; the local-photos source works without one

### Quick start — pull from GitHub Container Registry

The CI/CD pipeline publishes a multi-arch image to `ghcr.io/laennart/epf` on every tagged release (`v<MAJOR>.<MINOR>.<PATCH>`). To use it, edit `compose.yml` and replace the `build: .` line with:

```yaml
image: ghcr.io/laennart/epf:latest
```

(Substitute the lowercase `OWNER/REPO` path matching wherever this repo lives; the Deploy workflow derives the image name from `${GITHUB_REPOSITORY,,}`.)

Then:

```bash
git clone <this-repo-url>
cd EPF
# Edit compose.yml: set IMMICH_API_KEY (or remove the env var if using local photos only)
docker compose up -d
```

The server listens on port `15151` on the host (mapped to container port 5000). Open `http://<host>:15151/setting` to configure.

### Build locally

The default `compose.yml` already specifies `build: .` so simply:

```bash
git clone <this-repo-url>
cd EPF
# Edit compose.yml: set IMMICH_API_KEY
docker compose up -d --build
```

### Configuration

All configuration happens through the web UI at `http://<host>:15151/setting`. There is no need to write `config.yaml` by hand — it is created on first run with defaults from `app.py` (`DEFAULT_CONFIG`) and persisted to the `./config` volume on every save.

Settings exposed in the UI (matching the keys in `DEFAULT_CONFIG`):

| Setting | Description | Default |
|---------|-------------|---------|
| `url` | Immich server URL (NOT `localhost` — must be reachable from the EPF container) | `http://192.168.1.10` |
| `album` | Immich album name to pull from | `default_album` |
| `rotation` | Display rotation: 0, 90, 180, or 270 | `270` |
| `enhanced` | Pillow color saturation (1.0 = unchanged) | `1.3` |
| `contrast` | Pillow contrast (1.0 = unchanged) | `0.9` |
| `strength` | Floyd–Steinberg dithering strength 0.0–1.0 | `0.8` |
| `display_mode` | `fit` or `fill` | `fill` |
| `image_order` | `random` or `newest` | `random` |
| `sleep_start_hour` / `sleep_start_minute` | Quiet-hours start | `23:00` |
| `sleep_end_hour` / `sleep_end_minute` | Quiet-hours end | `06:00` |
| `wakeup_interval` | Refresh interval in minutes | `60` |
| `date_overlay_enabled` | Show date overlay | `false` |
| `date_overlay_position` | One of the 9 anchor positions | `bottomRight` |

### Local photos

Drop image files into the `./local_photos/` directory on the host (mapped to `/data/local_photos` inside the container). Supported extensions: `.jpg`, `.jpeg`, `.bmp`, `.heic`, `.dng`, `.arw`, `.cr2`, `.nef`, `.raw`. When at least one file is present, the local source takes priority over Immich.

### Volumes

The default `compose.yml` mounts three directories:

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `./photos` | `/data/photos` | Immich download cache + `tracking.txt` (which assets have been shown) |
| `./local_photos` | `/data/local_photos` | User-supplied images (takes priority over Immich when non-empty) |
| `./config` | `/data/config` | Persistent `config.yaml` written by the web UI |

## Firmware (Arduino)

### Required hardware

- XIAO ESP32-S3 Plus seated on the Seeed EE02 driver board with the T133A01 13.3" panel attached. No additional wiring required.
- (Optional) Tactile button between `D0` and GND for wake / config-mode entry.

### Arduino IDE setup

1. Install the Arduino IDE (2.x recommended).
2. Add the Espressif board manager URL under **Preferences → Additional boards manager URLs**:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. **Boards Manager** → install **esp32 by Espressif Systems** (version 3.x).
4. Select board: **Tools → Board → esp32 → XIAO_ESP32S3**.
5. **CRITICAL:** **Tools → PSRAM → OPI PSRAM**. The 1200×1600×4bpp frame buffer (960,000 bytes) is allocated with `ps_malloc()` and the firmware will refuse to start if PSRAM is disabled.
6. Select the correct serial port under **Tools → Port**.

### Required libraries

Install these from **Tools → Manage Libraries…**:

- **TFT_eSPI** (Bodmer) — graphics library; used as the dependency of Seeed_GFX.
- **Seeed_GFX** — Seeed's fork providing the `EPaper` class for the T133A01 panel. Available from Seeed's library index or via Git: `https://github.com/Seeed-Studio/Seeed_GFX`.
- **ArduinoJson** (Benoit Blanchon) — used to parse the `/sleep` JSON response.
- **Preferences** — bundled with the ESP32 core; no separate install needed.

The captive-portal code under `lib/WifiCaptive/` is bundled with this repo and compiles automatically when the sketch is opened.

### Build and flash

1. Open `epd7in3e/epd7in3e.ino` (the folder is already named `epd7in3e` — no renaming required).
2. Click **Verify** to confirm the toolchain finds all libraries, then **Upload**.
3. Open the serial monitor at 115200 baud. The first boot will log `e-Paper initialized successfully (Seeed_GFX)` and then enter captive-portal mode (no WiFi credentials stored).
4. Connect to the Wi-Fi AP named `ESP32_ePAPER` from a phone or laptop.
5. The captive portal opens automatically. Enter:
   - Your Wi-Fi SSID + password (up to five networks can be stored).
   - The EPF server URL, including port — e.g. `http://192.168.1.20:15151`. HTTPS URLs are supported.
6. After saving, the device reboots, fetches the first photo, and enters deep sleep.

To re-enter the captive portal later, **long-press** the config button (~3s) during boot, or short-press `D0` while the device is sleeping to wake it (it will refresh; long-press to re-enter setup).

### Known hardware limitation

The EE02 board has two green charge-status LEDs (D5, D16) wired to the BQ24070 PMIC's `STAT1`/`STAT2` open-drain outputs. They are NOT connected to any XIAO GPIO and cannot be suppressed from firmware. When no battery is connected the PMIC enters a no-battery fault state and the LEDs blink. This is documented hardware behavior, not a firmware bug.

## Development

### Running the test suite

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest tests/ -v
```

System dependencies required for the full test run: `libraw-dev`, `fonts-dejavu-core` (Debian/Ubuntu names — see `.github/workflows/ci.yml` for the exact `apt-get` invocation used in CI).

### Lint and typecheck

```bash
ruff check .
ruff format --check .
pyright
```

These three commands match the gates enforced by the PR workflow.

### CI/CD

Two GitHub Actions workflows live under `.github/workflows/`:

- **`ci.yml`** — runs on every pull request to `main`. Three parallel jobs:
  - `Lint (ruff)` — `ruff check` + `ruff format --check`
  - `Typecheck (pyright)` — `pyright` over the full repo
  - `Test (pytest)` — installs system deps + Python deps and runs `pytest tests/ -v`
- **`deploy.yml`** — manual `workflow_dispatch` with a `version` input (`MAJOR.MINOR.PATCH`, numeric only). Validates the semver, creates a `v<VERSION>` git tag, builds the Docker image, pushes `ghcr.io/<owner>/<repo>:<version>` and `:latest`, and creates a GitHub Release with auto-generated notes.

To cut a release: **Actions → Deploy → Run workflow**, enter a version like `1.2.0`, click **Run workflow**.

### Contributing

Pull requests are welcome. The CI gates must pass before a PR can be merged. Please keep PRs focused and include test coverage for any new server-side behavior.

## License

This project is licensed under the MIT License.
