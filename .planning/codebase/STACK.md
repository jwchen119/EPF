# Technology Stack

**Analysis Date:** 2026-05-27

## Languages

**Primary:**
- Python 3.9 - Backend web server, image processing, Immich integration
- Arduino/C++ - ESP32-C6 firmware, e-paper display controller
- Cython - Image quantization and color processing optimization

**Secondary:**
- HTML/CSS/JavaScript - Web UI for settings configuration

## Runtime

**Environment:**
- Python 3.9 (containerized via Docker)
- Arduino IDE 2.x (for ESP32-C6 firmware compilation)
- ESP32-C6 microcontroller (FireBeetle 2 ESP32-C6)

**Package Managers:**
- pip (Python) - Lockfile: `requirements.txt` present
- Arduino Library Manager - For ESP32 libraries

## Frameworks

**Core:**
- Flask 3.1.0 - RESTful API server for image processing and device management
- Arduino framework - for ESP32-C6 firmware

**Image Processing:**
- Pillow 11.0.0 - PIL image manipulation, color enhancement, quantization
- pillow_heif 0.21.0 - HEIC/HEIF image format support
- rawpy 0.23.2 - RAW photo processing (DNG, ARW, CR2, NEF, CRW)
- NumPy 2.0.2 - Numerical operations for image processing

**Utilities:**
- Watchdog 6.0.0 - File system event monitoring
- PyYAML 6.0.2 - YAML configuration parsing
- DateTime 5.5 - Date/time handling
- ntplib - NTP time synchronization

**ESP32 Libraries:**
- ArduinoJson - JSON parsing and serialization
- Async TCP - Asynchronous TCP communication
- ESP Async Web Server - Asynchronous HTTP server for captive portal
- WiFiClientSecure - HTTPS support

## Key Dependencies

**Critical:**
- Flask 3.1.0 - Web framework for API endpoints, serves image processing pipeline
- requests 2.32.3 - HTTP client for Immich API communication
- pillow 11.0.0 - Image manipulation, color space conversions, dithering
- rawpy 0.23.2 - RAW file decoding (essential for professional camera formats)
- numpy 2.0.2 - Numerical computation for image data processing

**Infrastructure:**
- pillow_heif 0.21.0 - HEIC format support (modern iOS photos)
- Cython (compiled as `cpy.so`) - Performance-critical image quantization (5x speedup)
- watchdog 6.0.0 - File system monitoring for configuration changes

## Configuration

**Environment:**
- Docker containerized deployment
- Environment variables:
  - `IMMICH_API_KEY` - API key for Immich server authentication (REQUIRED)
  - `IMMICH_PHOTO_DEST` - Photo storage directory (default: `/photos`)

**Build:**
- `Dockerfile` - Multi-layer Python 3.9-slim container
- `.nvmrc` or version files - Not detected
- `setup.py` or build config - Not detected (pip-only)

**Runtime Configuration:**
- Configuration stored in SQLite preferences via Preferences library (ESP32)
- Web UI for settings: `templates/settings.html`
- Server URL, album name, rotation, color enhancement, contrast, dithering strength all configurable via web interface

## Platform Requirements

**Development:**
- macOS/Linux/Windows with Docker
- Arduino IDE 2.x for ESP32-C6 firmware development
- Python 3.9+ with pip
- C/C++ compiler for Cython compilation (`cpy.pyx` compiled to `cpy.so`)

**Production:**
- Docker container runtime
- ESP32-C6 microcontroller with e-paper display (WaveShare 7.3-inch Spectra E6)
- Li-Po battery
- Network connectivity (WiFi via ESP32)
- Immich server (self-hosted photo management platform)

**Hardware Requirements:**
- FireBeetle 2 ESP32-C6 microcontroller
- WaveShare 7.3-inch E Ink Spectra 6 (E6) Full Color e-paper display
- Li-Po battery with PH2.0 header
- Standard picture frame

---

*Stack analysis: 2026-05-27*
