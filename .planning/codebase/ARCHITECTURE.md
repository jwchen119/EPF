# Architecture

**Analysis Date:** 2026-05-27

## Pattern Overview

**Overall:** Client-Server with IoT Device Integration

**Key Characteristics:**
- Two-tier architecture: Flask backend server handling image processing and serving a web-based admin interface, with an ESP32-C6 microcontroller firmware as the client
- Asynchronous server-side image processing and quantization using Cython for performance
- RESTful API endpoints for device communication and configuration management
- Real-time configuration updates via file watching and event-based reload
- Integration with Immich photo management service for album management and retrieval

## Layers

**Firmware Layer (ESP32-C6):**
- Purpose: Hardware abstraction and device management on the microcontroller
- Location: `epd7in3e/` (includes `.ino`, `.cpp`, `.h` files)
- Contains: HAT driver code (`epd7in3e.cpp/h`), WiFi captive portal (`WifiCaptive.cpp/h`), filesystem operations (`filesystem.cpp/h`), e-paper display driver, button handling, battery monitoring
- Depends on: Arduino libraries (WiFi, HTTPClient, ArduinoJson, Preferences), SPI for display communication
- Used by: Main firmware logic in `epd7in3e.ino`

**HTTP Communication Layer:**
- Purpose: Device-to-server communication with battery reporting and image download
- Location: Requests made from `epd7in3e.ino` to Flask endpoints (`/download`, `/sleep`), and configuration sent via captive portal
- Contains: HTTP/HTTPS client implementations with battery voltage headers, JSON configuration payloads
- Depends on: HTTPClient library, WiFi connectivity
- Used by: Device wake-up flow and configuration setup

**Flask API Layer:**
- Purpose: REST endpoints for image serving and device synchronization
- Location: `app.py` (routes section: lines 556-865)
- Contains: `/download` endpoint (image processing and serving), `/sleep` endpoint (sleep duration calculation), `/setting` endpoint (configuration management), `/` root index
- Depends on: Immich API integration, file I/O operations, configuration system
- Used by: ESP32 firmware and web browser for admin interface

**Image Processing Layer:**
- Purpose: High-performance color quantization, dithering, and format conversion
- Location: Core logic in `cpy.pyx` (Cython), Python wrappers in `app.py` (lines 162-388)
- Contains: Floyd-Steinberg dithering with strength control, image scaling/rotation, HEIC/RAW format conversion, color palette matching
- Depends on: NumPy, PIL/Pillow, rawpy, pillow_heif
- Used by: `/download` endpoint to process images before sending to device

**Configuration Management Layer:**
- Purpose: Dynamic configuration loading, validation, and file watching
- Location: `app.py` (lines 461-533), file system observer pattern using watchdog
- Contains: DEFAULT_CONFIG dictionary, `ConfigFileHandler` class (lines 475-533), YAML file reading, config validation
- Depends on: YAML parsing, watchdog filesystem events, threading for async updates
- Used by: All application layers that need runtime configuration values

**Data Access Layer:**
- Purpose: Immich album and image retrieval
- Location: `app.py` (lines 670-750 shows album/asset API calls)
- Contains: Album lookup via `/api/albums`, asset retrieval via `/api/albums/{id}`, downloaded image tracking via `tracking.txt`
- Depends on: HTTP requests to Immich server, local filesystem for tracking state
- Used by: `/download` endpoint to fetch and serve images

## Data Flow

**Image Download and Display Flow:**

1. ESP32 wakes from deep sleep and calls `/download` endpoint with battery voltage in headers
2. Flask retrieves configured album name from global state (`current_config`)
3. Queries Immich API to get albums list and find target album by name
4. Fetches all assets in album; applies image ordering logic (random or newest-first)
5. Selects image (skipping already-downloaded ones via `tracking.txt`)
6. Downloads raw image file from Immich to `/photos` directory
7. Converts format if needed (RAW/DNG to JPG, HEIC to JPG) using `rawpy` and `pillow_heif`
8. Scales and rotates image using `load_scaled()` from `cpy.pyx`
9. Applies color enhancement and contrast adjustments via PIL `ImageEnhance`
10. Quantizes to 6-color palette using Cython `convert_image()` with Floyd-Steinberg dithering
11. Encodes to PNG and returns via Flask HTTP response
12. Records image ID in `tracking.txt` to prevent re-sending

**Sleep Duration Calculation Flow:**

1. ESP32 calls `/sleep` endpoint after displaying image
2. Flask calculates next wake-up time based on interval (default 60 minutes) and sleep schedule
3. If next wake time falls in sleep period (configurable hours), shifts to sleep end time
4. Returns sleep duration in milliseconds to ESP32
5. ESP32 enters deep sleep via RTC timer for specified duration

**Configuration Update Flow:**

1. User modifies settings via web UI (`/setting` POST)
2. Validation checks parameters (rotation 0/90/180/270, ranges for contrast/enhanced/strength)
3. YAML written to `/config/config.yaml`
4. Watchdog file observer detects change (lines 516-530)
5. `ConfigFileHandler` callback triggers `update_app_config()`
6. Global variables updated: `url`, `albumname`, `rotationAngle`, `img_enhanced`, `img_contrast`, etc.
7. All subsequent requests use updated values

**State Management:**

- **Global mutable state:** `app.py` maintains globals like `current_config`, `url`, `albumname`, `rotationAngle` (lines 23-56, 91-92)
- **Persistent state:** Downloaded image tracking via `tracking.txt` file (album name as header, asset IDs as rows)
- **Temporary state:** Battery voltage cached in `last_battery_voltage` and `last_battery_update` (lines 91-92)
- **Configuration state:** Loaded from YAML on startup, reloaded on file changes via watchdog observer

## Key Abstractions

**ConfigFileHandler Class:**
- Purpose: Encapsulate YAML file reading and change detection
- Location: `app.py` (lines 475-533, defined in main() context)
- Pattern: File watcher with callback on modification; lazy initialization with file lock handling
- Decouples configuration source (YAML) from application logic

**EpaperManager Class:**
- Purpose: Encapsulate device lifecycle and image download logic (firmware side)
- Location: `epd7in3e/epd7in3e.ino` (lines 32+)
- Pattern: State machine handling WiFi connection, image download, error retry, deep sleep
- Decouples device hardware from application flow

**Image Processing Pipeline:**
- Purpose: Chain format conversion → scaling → enhancement → quantization
- Location: `app.py` (lines 388-420 shows convert_heic_to_jpg, scale_img_in_memory, convert_image sequence)
- Pattern: Composition of transformation functions with PIL Image objects as data carriers
- Allows format-agnostic processing by normalizing all input to PIL Image

**Floyd-Steinberg Dithering:**
- Purpose: Distribute quantization error to nearby pixels for visual quality on limited color palette
- Location: `cpy.pyx` (lines 166-189)
- Pattern: Cython for performance; parameterized dithering strength for user control
- Critical for visual fidelity on 6-color e-paper display

## Entry Points

**Device Firmware Entry:**
- Location: `epd7in3e/epd7in3e.ino` (setup() and loop())
- Triggers: Device power-on, button wake from sleep, configuration button press
- Responsibilities: WiFi connection, captive portal if in setup mode, HTTP requests to server, display image, deep sleep

**Flask Server Entry:**
- Location: `app.py` (lines 649-668, main() function)
- Triggers: Docker container start or direct Python execution
- Responsibilities: Load config from YAML, start file watcher thread, start NTP sync thread, run Flask app on 0.0.0.0:5000

**Configuration API Entry:**
- Location: `app.py` (lines 556-620, /setting route)
- Triggers: GET shows settings page, POST saves new settings
- Responsibilities: Render settings.html template, validate form inputs, write YAML, redirect on success

**Image Download Entry:**
- Location: `app.py` (lines 670-785, /download route)
- Triggers: GET request from ESP32 after wake
- Responsibilities: Query Immich, select image, process image, return PNG response

**Sleep Duration Entry:**
- Location: `app.py` (lines 789-858, /sleep route)
- Triggers: GET request from ESP32 after displaying image
- Responsibilities: Calculate next wake time, apply sleep schedule logic, return JSON with duration

## Error Handling

**Strategy:** Defensive programming with try-catch at key boundaries; errors logged or returned to caller

**Patterns:**
- **File I/O errors:** `load_downloaded_images()` and `save_downloaded_image()` wrap file ops in try-except, return empty set or log on failure (lines 94-160)
- **Immich API errors:** `/download` checks HTTP status codes and returns JSON error with HTTP status (lines 700-717)
- **Configuration validation:** `/setting` validates rotation angle, ranges for numeric parameters before saving (lines 574-600)
- **Device communication:** Firmware includes retry loop with `retryOnError` flag (lines 96-100 in epd7in3e.ino)
- **NTP sync:** Falls back to system time on failure (lines 865-868 in app.py, line ~37 in epdif.cpp)

## Cross-Cutting Concerns

**Logging:** 
- Python: Uses print() statements (lines 119, 148-151 for file errors; line 643 for NTP sync status)
- Firmware: Uses Serial.print/println for debugging
- No centralized logging framework; output goes to stdout/serial console

**Validation:**
- Settings form: Client-side (JavaScript in settings.html likely) + server-side range/format checks (lines 580-600)
- Immich API response: Checks JSON structure for presence of required fields (lines 716-717)
- Image format: Validates file extensions against ALLOWED_EXTENSIONS set (line 75)

**Authentication:**
- Immich: API key via `x-api-key` header in every Immich API call (lines 69-72)
- API endpoints (`/download`, `/sleep`): No authentication required (stateless, device-based access)
- Web UI (`/setting`): No authentication; assumes local network access only

**Battery Monitoring:**
- ESP32 sends voltage in `batteryCap` header with every request (line 91-92 in epd7in3e.ino)
- Flask extracts and caches voltage (lines 677-682 in app.py)
- Battery percentage calculated from voltage curve (lines 534-554, not shown in excerpt)
- Displayed on settings page for user awareness

**Time Synchronization:**
- Daily NTP sync thread started in main() (lines 661-662)
- Syncs to pool.ntp.org at 4:11 AM daily (line 633)
- Retry every 1 hour on failure (line 647)
- Used for accurate sleep scheduling on server side

---

*Architecture analysis: 2026-05-27*
