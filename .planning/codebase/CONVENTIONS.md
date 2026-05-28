# Coding Conventions

**Analysis Date:** 2026-05-27

## Naming Patterns

**Files:**
- Lowercase with underscores: `app.py`, `cpy.pyx`
- HTML templates: lowercase: `templates/settings.html`
- C++ header/source files: CamelCase: `WifiCaptive.h`, `WifiCaptive.cpp`, `epd7in3e.h`
- Arduino sketch: lowercase with extension: `epd7in3e.ino`

**Functions:**
- Snake_case for Python functions: `load_downloaded_images()`, `save_downloaded_image()`, `convert_raw_or_dng_to_jpg()`
- Followed consistently in `app.py` and `cpy.pyx`
- Descriptive function names indicating operation: `depalette_image()`, `scale_img_in_memory()`, `calculate_battery_percentage()`

**Variables:**
- Snake_case for local and global variables: `tracking_file`, `rotationAngle` (mostly snake_case with one exception: `rotationAngle`, `img_enhanced`)
- Global module-level variables use descriptive names: `ALLOWED_EXTENSIONS`, `BATTERY_LEVELS`, `DEFAULT_CONFIG`
- Single-letter variables in loops: `x`, `y`, `c`, `i` (acceptable in algorithmic code)

**Constants:**
- UPPERCASE with underscores: `ALLOWED_EXTENSIONS`, `BATTERY_LEVELS`, `DEFAULT_CONFIG`, `EPD_W`, `EPD_H`
- Defined at module level for reusability

**Types (Cython):**
- CamelCase for Cython type definitions: `FLOAT_TYPE`, `UINT8_TYPE`, `float32_t`, `uint8_t`
- Descriptive names for arrays and typed variables

## Code Style

**Formatting:**
- Python: 4-space indentation (PEP 8 compliant)
- No automated formatter detected (black, autopep8, etc.)
- Line length varies: generally under 100 characters, some lines approach 120 characters
- Blank lines: 2 blank lines between top-level functions (observed in `app.py`)

**Linting:**
- No linting configuration detected (no `.eslintrc`, `.pylintrc`, `setup.cfg`)
- Code does not enforce strict linting rules
- Import statements not fully organized by type (see Import Organization below)

**Operator Spacing:**
- Standard spacing around operators: `x = y + z`
- Cython arithmetic operations: tightly spaced in performance-critical code: `1063 * sqDiff(...) / 5000`

## Import Organization

**Order:**
Python imports in `app.py` (lines 2-18):
1. Standard library imports: `flask`, `yaml`, `requests`, `os`, `io`, `random`, `rawpy`, `numpy`, `PIL`, `datetime`, `watchdog`, `threading`, `ntplib`, `time`
2. Relative imports from Cython: `from cpy import convert_image, load_scaled`
3. No clear grouping between standard library and third-party packages

**Path Aliases:**
- No path aliases detected
- Full import paths used throughout: `from PIL import Image`, `from flask import Flask`
- Direct relative imports for compiled modules: `from cpy import convert_image, load_scaled`

**Cython Imports:**
- Cython `cimport` statements for performance: `cimport numpy as np`, `from libc.math cimport pow`
- C-level imports for fast operations: `cimport cython`

## Error Handling

**Patterns:**
- Try-except blocks with broad exception catching:
  ```python
  try:
      exif = image._getexif()
  except:
      date_time = None
  ```
- Generic exception handlers without specific error types (lines 195-196, 249-250)
- Specific exception handling in file I/O:
  ```python
  except PermissionError:
      print(f"Permission denied when writing to {tracking_file}")
  except IOError as e:
      print(f"IO Error when writing to tracking file: {e}")
  except Exception as e:
      print(f"Unexpected error writing to tracking file: {e}")
  ```
- Error responses via Flask `jsonify()`: Returns dict with `{"error": "message"}` structure (lines 694, 702, 708, 717, 757, 787)
- HTTP status codes: 500 (server error), 404 (not found) for Flask routes

**Global Variables as State:**
- Configuration stored in global variables (lines 41-55): `url`, `albumname`, `rotationAngle`, `img_enhanced`, `img_contrast`, `strength`, `display_mode`, `image_order`, `sleep_start_hour`, `sleep_end_hour`, `sleep_start_minute`, `sleep_end_minute`
- Global battery state: `last_battery_voltage`, `last_battery_update` (lines 91-92)
- Functions modify globals with `global` declaration (line 463): `global current_config, url, albumname...`

## Logging

**Framework:** Python `print()` statements only

**Patterns:**
- Console output for status: `print(f"Error reading tracking file: {e}")`
- Informational logging: `print(f"Created config directory: {config_dir}")`
- Battery status: `print(f"Battery: {battery_voltage:.0f}mV ({battery_percentage:.1f}%)")`
- NTP sync results: `print(f"Daily NTP sync completed at {synced_time.strftime('%Y-%m-%d %H:%M:%S')}")`
- Configuration updates: `print(f"Configuration updated: URL = {url}, Album = {albumname}...")`
- No structured logging framework (no logging module, no log levels)

## Comments

**When to Comment:**
- Function docstrings present in some cases:
  ```python
  def load_downloaded_images():
      """ Load downloaded image ID from tracking.txt """
  ```
- Inline comments for complex logic:
  ```python
  # Simulate the code from the C
  indices[indices > 3] += 1
  ```
- Comments explaining magic numbers (palette configuration, EXIF tags):
  ```python
  # EXIF time tag is 36867
  date_time = exif.get(36867)
  ```
- Commented-out code sections: Large disabled block (lines 875-907) for `calculate_next_wakeup()` function

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Docstrings: Present but minimal, not comprehensive
- Function-level docstring example:
  ```python
  def scale_img_in_memory(image, target_width=800, target_height=480, bg_color=(255, 255, 255)):
      """
      Process image in memory, return BytesIO object
      
      :param image: PIL Image object
      :param target_width: width of epaper
      ...
      """
  ```

## Function Design

**Size:**
- Range: 5-200+ lines per function
- Notable large functions:
  - `scale_img_in_memory()`: ~185 lines (lines 169-353) - includes nested function `draw_text_with_background()`
  - `process_and_download()`: ~115 lines (lines 671-787) - main business logic
  - `get_sleep_duration()`: ~75 lines (lines 790-863) - complex time calculation
- Most utility functions: 5-30 lines

**Parameters:**
- Typical: 1-3 parameters
- Default parameters used: `scale_img_in_memory(image, target_width=800, target_height=480, bg_color=(255, 255, 255))`
- Flask routes decorated with `@app.route()` extract parameters from `request` object rather than function arguments

**Return Values:**
- Explicit returns: `return set()`, `return img_io`, `jsonify({...})`
- No explicit return statements in some functions (implicitly return None): `print()` statements only in event handlers
- BytesIO objects for image data (lines 350-353)
- Flask response objects: `jsonify()`, `redirect()`, `render_template()`, `send_file()`

## Module Design

**Exports:**
- Flask app object created at module level: `app = Flask(__name__)`
- Routes defined with decorators: `@app.route('/', methods=['GET', 'POST'])`
- Helper functions are module-private (no explicit `__all__` list)
- Entry point: `if __name__ == '__main__': main()`

**Barrel Files:**
- Not applicable (single `app.py` monolithic file)
- Cython extension imported separately: `from cpy import convert_image, load_scaled`

## Configuration Management

**Pattern:**
- Dictionary-based configuration: `DEFAULT_CONFIG` (lines 23-39)
- YAML file-based runtime configuration: `/config/config.yaml` loaded by `ConfigFileHandler`
- Global variable tracking: After loading config, values copied to global variables
- File watching: `watchdog.Observer` monitors config file changes and triggers `update_app_config()` callback
- Environment variables for sensitive data: `IMMICH_API_KEY` via `os.getenv()` (line 58)

**Environment Configuration:**
- `IMMICH_API_KEY`: Required, no default
- `IMMICH_PHOTO_DEST`: Optional, defaults to `/photos` (line 59)
- Flask app config dictionary populated with parsed values (lines 468-479)

## Data Structures

**Immutable Operations:**
- Image processing returns new objects via PIL: `Image.new()`, `image.rotate()`, `image.resize()`
- Configuration updates create new dict: `new_config = {...}` (lines 578-594)
- Global state mutations observed but contained in `update_app_config()` function

**Exception to Immutability:**
- In-memory array modifications: Cython arrays mutated for performance in `convert_image()` (lines 140-189)
- File write operations modify filesystem state

---

*Convention analysis: 2026-05-27*
