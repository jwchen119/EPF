# Codebase Concerns

**Analysis Date:** 2026-05-27

## Tech Debt

**Global State Management:**
- Issue: Extensive use of global variables in `app.py` (url, albumname, rotationAngle, img_enhanced, img_contrast, strength, display_mode, image_order, sleep_start_hour, sleep_end_hour, sleep_start_minute, sleep_end_minute) makes the application difficult to test and maintain
- Files: `app.py` (lines 44-55, 483-494)
- Impact: Race conditions possible in multithreaded environment, tests cannot isolate state, configuration changes require global updates instead of dependency injection
- Fix approach: Refactor to use a configuration object/class, pass config to functions instead of relying on globals, use context managers or dependency injection

**Bare Except Clauses:**
- Issue: Multiple bare `except:` blocks catching all exceptions indiscriminately throughout `app.py`
- Files: `app.py` (lines 195-196, 249-250, 345)
- Impact: Hides bugs, makes debugging difficult, can catch system-critical exceptions like KeyboardInterrupt
- Fix approach: Replace with specific exception types (e.g., `except PIL.UnidentifiedImageError`, `except ValueError`)

**Inconsistent Error Handling:**
- Issue: EXIF data extraction uses bare except, date format parsing uses nested try-except with bare except at outer level
- Files: `app.py` (lines 184-196, 253-261)
- Impact: Silent failures, no logging for debugging, user receives no feedback when EXIF reading fails
- Fix approach: Log specific exceptions, provide meaningful error messages, document expected EXIF formats

**Broken/Incomplete Features:**
- Issue: Text overlay on images is commented out (WIP - Work In Progress)
- Files: `app.py` (line 346-347)
- Impact: Date/time display feature for photos doesn't work, users expect metadata display
- Fix approach: Complete the `draw_text_with_background()` implementation or remove commented code

**Cython Color Conversion Algorithm:**
- Issue: In `cpy.pyx`, the main color quantization loop (lines 141-154) iterates through colors but doesn't actually apply Floyd-Steinberg dithering - the dithering code (lines 156-189) is never executed
- Files: `cpy.pyx` (lines 141-193)
- Impact: Images are quantized to 6 colors but without dithering, resulting in banding and poor image quality
- Fix approach: Move dithering code inside the pixel iteration loop, or verify if dithering should be applied

**Unused/Commented Code:**
- Issue: Large commented-out block of old wakeup calculation logic (lines 875-907 in `app.py`)
- Files: `app.py` (lines 875-907)
- Impact: Increases file size, confuses maintainers, unclear if it's deprecated or for reference
- Fix approach: Remove or move to git history, document why old approach was replaced

## Known Bugs

**Typo in Flask Configuration Key:**
- Symptoms: Strength setting stored under wrong key name in Flask app config
- Files: `app.py` (line 473)
- Trigger: Any code accessing `app.config['IMMICH_STRENGH']`
- Workaround: Current code uses global variable directly, not Flask config, so bug is masked
- Details: Key is `IMMICH_STRENGH` (missing 't') instead of `IMMICH_STRENGTH`

**Image Quantization Not Applied Correctly:**
- Symptoms: Images sent to ESP32 may show color banding instead of smooth dithering
- Files: `cpy.pyx` (lines 141-193)
- Trigger: Every image download
- Details: Floyd-Steinberg dithering setup is present but loop structure prevents it from executing

**Potential Race Condition on Tracking File:**
- Symptoms: Multiple concurrent requests could corrupt `tracking.txt`
- Files: `app.py` (lines 94-152)
- Trigger: When ESP32 requests image while tracking file is being written
- Workaround: File locking not implemented
- Details: No file locking mechanism between `load_downloaded_images()` and `save_downloaded_image()`

**Bare `except` in Image Loading:**
- Symptoms: If `PIL.UnidentifiedImageError` occurs for invalid image data, caught silently
- Files: `app.py` (line 345)
- Trigger: When image file is corrupted or format is not supported
- Details: Error is swallowed, execution continues with potentially None data

## Security Considerations

**Missing Input Validation on Configuration:**
- Risk: Float values for enhancement and contrast parameters are not validated for reasonable ranges (could be negative or extremely large)
- Files: `app.py` (lines 583-585)
- Current mitigation: Flask form parsing, no min/max bounds enforced
- Recommendations: Add validation for 0.0-3.0 range for enhancement/contrast, log invalid attempts

**API Key Exposure via Environment Variable:**
- Risk: Immich API key passed via `IMMICH_API_KEY` environment variable - visible in process list on some systems
- Files: `app.py` (line 58)
- Current mitigation: Used in headers for requests
- Recommendations: Consider using secret manager, document that this is a security concern for deployment

**Missing HTTPS Validation:**
- Risk: When connecting to Immich server via HTTPS, no certificate verification enforced
- Files: `app.py` (lines 700, 711, 755)
- Current mitigation: None - `requests` library will verify by default but code doesn't explicitly confirm
- Recommendations: Add explicit `verify=True` to requests calls, document HTTPS requirement

**Album Name User Input Not Escaped:**
- Risk: Album name and URL from form are written directly to tracking file without sanitization
- Files: `app.py` (lines 580-581, 112-113)
- Current mitigation: File-based storage, not executed as code
- Recommendations: Add whitelist validation for album names, validate URLs are properly formatted

**No Rate Limiting:**
- Risk: `/download` endpoint can be called repeatedly without rate limiting
- Files: `app.py` (line 670)
- Current mitigation: None
- Recommendations: Add rate limiting per IP address, implement caching of last downloaded image

## Performance Bottlenecks

**Inefficient Battery Level Table Lookup:**
- Problem: `calculate_battery_percentage()` iterates linearly through voltage table on every request
- Files: `app.py` (lines 534-554)
- Cause: O(n) linear search through `BATTERY_LEVELS` dict
- Improvement path: Use binary search with sorted list, cache results, or pre-compute interpolation coefficients

**Numpy Array Allocation in Cython Loop:**
- Problem: `convert_image()` function allocates large numpy arrays (EPD_H x EPD_W x 3) multiple times
- Files: `cpy.pyx` (lines 125-126)
- Cause: Two full-size output arrays allocated, could reuse single output buffer
- Improvement path: Allocate once, reuse buffers, profile actual allocation overhead

**Image Download Full Content in Memory:**
- Problem: `response.content` loads entire image into memory before processing
- Files: `app.py` (line 760)
- Cause: Not using streaming for large image files
- Improvement path: Use `stream=True` and process image chunks, implement memory-efficient image handling

**Global Configuration Watcher Thread:**
- Problem: Observer thread watches config file continuously even when config rarely changes
- Files: `app.py` (lines 498-507)
- Cause: File system events monitored on every startup
- Improvement path: Consider polling on-demand instead of continuous watching, implement debouncing

**Blocking NTP Sync in Thread:**
- Problem: Daily NTP sync sleeps main thread for potentially hours
- Files: `app.py` (lines 626-647)
- Cause: Sleep time calculated and blocks thread until sync time
- Improvement path: Use scheduler library (APScheduler), implement non-blocking async scheduling

## Fragile Areas

**Date/Time Parsing from EXIF:**
- Files: `app.py` (lines 184-196, 253-261)
- Why fragile: Multiple EXIF tag numbers checked, multiple date formats attempted, bare except clause hides failures
- Safe modification: Add logging for which format was matched, document expected EXIF formats, add test cases for various date formats
- Test coverage: No test cases visible for EXIF parsing

**Sleep Schedule Calculation:**
- Files: `app.py` (lines 789-863)
- Why fragile: Complex logic for handling sleep period crossing midnight, multiple conditional branches
- Safe modification: Add comprehensive unit tests for edge cases (sleep period crossing midnight, current time in sleep period, etc.), add logging for calculated times
- Test coverage: No unit tests visible

**Image Rotation and Display Mode Logic:**
- Files: `cpy.pyx` (lines 60-108), `app.py` (lines 263-318)
- Why fragile: Position calculations for text overlay assume specific rotations, magic numbers for coordinates hardcoded
- Safe modification: Extract coordinate calculations to separate functions, add test cases for all 4 rotation angles, document coordinate system
- Test coverage: No test cases for image rotation variants

**Configuration File Watching:**
- Files: `app.py` (lines 407-507)
- Why fragile: Filesystem events may be missed, no atomic file write guarantee, race condition between file read and app state update
- Safe modification: Add logging for config reloads, use file locking, test with concurrent writes
- Test coverage: No integration tests for config file changes

## Scaling Limits

**Single File for Image Tracking:**
- Current capacity: Can handle thousands of images, but file grows indefinitely
- Limit: Single tracking.txt file becomes bottleneck if album contains millions of images
- Scaling path: Implement database-backed tracking (SQLite), implement pagination, add pruning strategy for old entries

**In-Memory Image Processing:**
- Current capacity: 800x480 image requires ~4.3MB memory (3 bytes per pixel for RGB)
- Limit: Very large images or concurrent requests could exhaust ESP32 memory
- Scaling path: Implement streaming image processing, add memory pool management, implement request queuing

**Immich API Call Efficiency:**
- Current capacity: Each request fetches all assets in album via API
- Limit: Albums with thousands of images cause slow initial API call
- Scaling path: Use pagination in Immich API, implement local caching of asset list, use websockets for real-time updates

## Dependencies at Risk

**Missing Specific Version Pins:**
- Risk: `requirements.txt` lacks version specifiers for some packages (ntplib)
- Impact: Reproducible builds not guaranteed, potential breaking changes on update
- Migration plan: Add `==X.Y.Z` version pins for all dependencies, test with pinned versions, document major version dependencies

**Pillow Image Format Support:**
- Risk: Reliance on Pillow for multiple formats (JPEG, HEIC, RAW via pillow_heif)
- Impact: Format support depends on Pillow maintenance, security vulnerabilities in image libraries
- Migration plan: Monitor Pillow security advisories, consider alternative image processing pipelines, implement format detection validation

**Cython Compilation:**
- Risk: `cpy.so` is a compiled binary, source (`cpy.pyx`) is primary reference
- Impact: Cannot inspect compiled code, reproducible builds difficult, architecture-specific binary
- Migration plan: Implement build process documentation, consider pure Python fallback, version binary artifacts separately

## Missing Critical Features

**No Error Recovery Mechanism:**
- Problem: If Immich becomes unavailable, ESP32 will sleep without downloading image
- Blocks: Cannot ensure image updates during network outages
- Recommendation: Implement retry logic with exponential backoff, cache last valid image

**No Concurrent Request Handling:**
- Problem: If two ESP32 devices request images simultaneously, tracking file could be corrupted
- Blocks: Cannot scale to multiple devices
- Recommendation: Implement request locking, use database for tracking, implement device-specific tracking

**Missing Image Caching:**
- Problem: Same image may be downloaded multiple times if ESP32 requests retry
- Blocks: Inefficient bandwidth usage
- Recommendation: Implement LRU cache of recent images, add cache-control headers

**No Fallback for Failed API Calls:**
- Problem: If album list API fails, entire request fails with no recovery
- Blocks: Reduces reliability during transient network issues
- Recommendation: Implement circuit breaker pattern, cache album list with TTL, implement timeout handling

## Test Coverage Gaps

**No Unit Tests for Image Processing:**
- What's not tested: `scale_img_in_memory()`, color quantization, rotation logic, EXIF parsing
- Files: `app.py` (lines 169-353), `cpy.pyx`
- Risk: Image processing bugs go unnoticed until production
- Priority: High

**No Integration Tests for API Endpoints:**
- What's not tested: `/download`, `/sleep`, `/setting` endpoints with various configurations
- Files: `app.py` (routes 556-863)
- Risk: Configuration changes may break endpoints
- Priority: High

**No Tests for Configuration Reloading:**
- What's not tested: Configuration file watcher, hot-reloading of config values
- Files: `app.py` (lines 407-507)
- Risk: Config updates may not propagate to running application
- Priority: Medium

**No Edge Case Testing:**
- What's not tested: Empty albums, corrupted images, missing EXIF data, invalid album names
- Files: `app.py` (lines 691-787)
- Risk: Unexpected failures in production edge cases
- Priority: Medium

**No Tests for Sleep Schedule Logic:**
- What's not tested: Sleep period crossing midnight, wakeup interval calculations, sleep duration edge cases
- Files: `app.py` (lines 789-863)
- Risk: Device may sleep at wrong times
- Priority: High

**No Arduino Code Tests:**
- What's not tested: WiFi connection, display rendering, button input handling
- Files: `epd7in3e/` (all C++ files)
- Risk: Hardware integration bugs discovered only during physical testing
- Priority: Medium

---

*Concerns audit: 2026-05-27*
