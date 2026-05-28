# External Integrations

**Analysis Date:** 2026-05-27

## APIs & External Services

**Immich (Photo Management):**
- Service: Immich - Self-hosted photo management platform
  - SDK/Client: `requests` library (HTTP client)
  - Auth: `x-api-key` header with API key from `IMMICH_API_KEY` env var
  - Base URL: Configurable via web UI (default: `http://192.168.1.10`)

**Immich API Endpoints Used:**
- `GET /api/albums` - Retrieve list of all albums
- `GET /api/albums/{albumId}` - Retrieve specific album and its assets
- `GET /api/assets/{assetId}/original` - Download original photo file

**Implementation:**
- Location: `app.py` lines 670-788 (`/download` endpoint)
- Album lookup: Dynamic by album name (not fixed ID)
- Asset selection: Random or newest-first (configurable)
- Image tracking: Local text file (`tracking.txt`) stores downloaded image IDs to avoid re-downloading

## Data Storage

**Databases:**
- Immich server (external) - All photo metadata and storage
- Local filesystem - Photo cache and tracking
  - Photo directory: `IMMICH_PHOTO_DEST` (default: `/photos`)
  - Tracking file: `{IMMICH_PHOTO_DEST}/tracking.txt` - Downloaded image IDs per album

**File Storage:**
- Immich manages original photo files (RAW, JPEG, HEIC, etc.)
- Flask server processes and quantizes images in-memory
- C code output streamed to ESP32 (no persistent storage)

**Caching:**
- In-memory image processing - No persistent cache layer
- Downloaded image tracking via text file prevents duplicate downloads
- Image metadata cached during album fetch

## Authentication & Identity

**Auth Provider:**
- Custom API key authentication
  - Implementation: `x-api-key` header sent with every Immich API request
  - API Key Source: `IMMICH_API_KEY` environment variable (must be set at container startup)
  - Validation: Checked at runtime; if missing, endpoints return 500 error

**Secrets Location:**
- `.env` file (present) - Contains `IMMICH_API_KEY` (not committed)
- Docker environment variable in deployment command

## Monitoring & Observability

**Error Tracking:**
- None detected - Application logs errors to stdout

**Logs:**
- Standard output logging via Python `print()` statements
- Error messages returned in JSON responses from Flask
- Battery voltage tracking via headers (logged but not persisted)

**Debugging:**
- Serial output from ESP32 for firmware debugging
- Flask debug mode can be enabled (not currently enabled in production)

## CI/CD & Deployment

**Hosting:**
- Docker container (self-hosted)
- Target: NAS or cloud server
- Port exposure: 5000 (Flask development server)

**CI Pipeline:**
- None detected - Manual build via `docker build`
- Pre-built images available on DockerHub: `jwchen119/epf`

**Deployment Commands:**
```bash
docker build -t jwchen119/epf .
docker run --name epf -e IMMICH_API_KEY='<key>' -d -p <port>:5000 jwchen119/epf
```

## Environment Configuration

**Required Environment Variables:**
- `IMMICH_API_KEY` - Immich API key (required, no default)
- `IMMICH_PHOTO_DEST` - Photo storage directory (default: `/photos`)

**Secrets Management:**
- API key passed via Docker environment variable
- No secrets stored in version control
- Dockerfile contains placeholder: `ENV IMMICH_API_KEY="your-api-key"`

## Network Communication

**Incoming (Flask Server):**
- `GET /download` - Image download and processing endpoint
  - Headers: `batteryCap` (battery voltage from ESP32)
  - Response: C code array for e-paper display
- `GET /sleep` - Sleep duration calculation endpoint
- `GET /setting` - Configuration web UI and update
- `GET /` - Settings page HTML

**Outgoing (to Immich Server):**
- `GET /api/albums` - Fetch all album names
- `GET /api/albums/{id}` - Fetch album details and asset list
- `GET /api/assets/{id}/original` - Download photo binary

**ESP32 Communication:**
- HTTP GET requests to Flask server `/download` endpoint
- Receives C code array in response
- Sends battery voltage in request headers
- Supports both HTTP and HTTPS (with certificate validation disabled in code)

## Webhooks & Callbacks

**Incoming:**
- None detected - Polling-based architecture

**Outgoing:**
- None detected - One-way request/response from ESP32 to Flask

## Device Communication

**ESP32 Firmware:**
- WiFi connectivity via ESP32-C6
- HTTP/HTTPS client in firmware makes requests to Flask server
- Captive portal for initial WiFi setup (modified from TRMNL firmware)
- Button-based control:
  - Short press: Wake from sleep
  - Long press (5s at boot): Enter configuration mode

**Configuration Storage (ESP32):**
- Preferences library (ESP32 EEPROM equivalent)
- Persisted keys:
  - `SERVER_BASE_URL` - Flask server URL
  - WiFi credentials (up to 5 SSIDs)

---

*Integration audit: 2026-05-27*
