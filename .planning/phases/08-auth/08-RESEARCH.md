# Phase 8: Auth - Research

**Researched:** 2026-06-02
**Domain:** HTTP Basic Auth — Flask decorator + Arduino HTTPClient credentials
**Confidence:** HIGH

## Summary

Phase 8 adds opt-in HTTP Basic Auth to the Flask app. All four routes (`/`, `/setting`, `/download`, `/sleep`) gain a `@require_auth` decorator that checks the `Authorization` header. When `APP_PASSWORD` is absent or empty the decorator is a no-op, preserving backward compatibility. When set, unauthenticated requests receive `401 Unauthorized` with a `WWW-Authenticate: Basic realm="EPF"` header, which triggers the browser's native login dialog.

The Flask side requires zero new dependencies. Python's stdlib `hmac.compare_digest` handles constant-time comparison. `request.authorization` (werkzeug `Authorization` object) gives `.username` and `.password` directly from the parsed `Authorization` header. Username is hardcoded as `"admin"`.

The Arduino firmware uses `HTTPClient.setAuthorization("admin", password)` — a single-line addition before each `http.GET()` / `sleepHttp.GET()` call. This is an official ESP32 Arduino HTTPClient API that handles Base64 encoding internally. The password must be stored as a constant in `config.h` (or NVS — planner's call).

**Primary recommendation:** Implement a `require_auth` decorator function inline in `app.py` using `request.authorization`, `hmac.compare_digest`, and a `401` abort. No new Python packages needed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use **HTTP Basic Auth**. Browser shows native username/password dialog — no login page, no `/login` route, no Flask session or secret_key needed. A simple `@require_auth` decorator checks the `Authorization` header on every request.
- **D-02:** Password set via `APP_PASSWORD` environment variable (loaded via `python-dotenv`, consistent with `IMMICH_API_KEY`). No UI controls for the password.
- **D-03:** Username is fixed as `"admin"`. Only `APP_PASSWORD` needs to be set — no `APP_USERNAME` env var.
- **D-04:** `APP_PASSWORD` added to `docker-compose.yml` as a commented-out example (like `IMMICH_API_KEY`). Also documented in README/`.env.example`.
- **D-05:** **All routes** are protected: `/`, `/setting`, `/download`, and `/sleep`. The ESP32 firmware must send HTTP Basic Auth credentials in its requests.
- **D-06:** The Arduino firmware uses `http.setAuthorization("admin", password)` (HTTPClient API) — single-line addition per request. The firmware reads the password from a hardcoded constant or NVS (implementation detail for planner).
- **D-07:** **Auth is opt-in.** When `APP_PASSWORD` is not set (empty string or absent), the decorator passes all requests through without authentication.
- **D-08:** When `APP_PASSWORD` is set and a request arrives without credentials (or with wrong credentials), the server responds with `401 Unauthorized` and a `WWW-Authenticate: Basic realm="EPF"` header.

### Claude's Discretion

- Whether the `@require_auth` decorator lives inline in `app.py` or as a small helper function — `app.py` is consistent with the existing single-file pattern.
- Constant-time comparison for the password check (`hmac.compare_digest`) to avoid timing attacks.
- Whether to log failed auth attempts (recommend yes, at WARN level).
- How the Arduino firmware stores the password (hardcoded constant vs. NVS preferences) — firmware implementation detail.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | `require_auth` decorator checks `Authorization` header; passes when `APP_PASSWORD` is empty | `request.authorization` werkzeug attribute; guard on empty string |
| AUTH-02 | Unauthenticated/wrong-credential requests receive `401` + `WWW-Authenticate: Basic realm="EPF"` | `flask.abort(401)` + `make_response` with `WWW-Authenticate` header |
| AUTH-03 | All four routes protected: `/`, `/setting`, `/download`, `/sleep` | Stack `@require_auth` above each `@app.route` decorator |
| AUTH-04 | `APP_PASSWORD` read from environment via `os.getenv` pattern matching existing env vars | Exact pattern from `app.py:324` (`os.getenv('IMMICH_API_KEY')`) |
| AUTH-05 | `APP_PASSWORD` documented as commented example in `compose.yml` | Matches existing `IMMICH_API_KEY` pattern in `compose.yml:7` |
| AUTH-06 | Arduino firmware sends credentials on `/download` and `/sleep` calls | `http.setAuthorization("admin", PASSWORD)` before each `http.GET()` |
| AUTH-07 | Password comparison uses `hmac.compare_digest` (constant-time) | Python stdlib, no new dependency |
| AUTH-08 | Failed auth attempts logged at WARN level | `app.logger.warning(...)` existing Flask logger |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `hmac` | stdlib | Constant-time string comparison (`hmac.compare_digest`) | Built-in — no install, prevents timing attacks |
| Flask `request.authorization` | Flask 3.1.0 (already installed) | Parse `Authorization: Basic ...` header | Built-in werkzeug support, no extra library |
| `functools.wraps` | stdlib | Preserve decorated function metadata | Required for Flask route introspection |
| `python-dotenv` | already installed | Load `APP_PASSWORD` from `.env` | Already in use for `IMMICH_API_KEY` |

### Supporting (Arduino firmware side)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `HTTPClient.setAuthorization(user, pass)` | ESP32 Arduino Core (already used) | Adds `Authorization: Basic <b64>` header | Before every `http.GET()` and `sleepHttp.GET()` call |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline decorator in `app.py` | `Flask-HTTPAuth` or `Flask-BasicAuth` extensions | Extensions add a dependency for ~10 lines of stdlib code; unnecessary here |
| `@app.before_request` global hook | Per-route `@require_auth` decorator | `before_request` is simpler but less explicit; CONTEXT.md prescribes decorator pattern |
| `hmac.compare_digest` | `==` operator | `==` leaks password length via timing; `compare_digest` is safe even on local network |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure

No new files. All changes land in existing files:
```
app.py               # require_auth() decorator + APP_PASSWORD global + 4 route decorators
compose.yml          # APP_PASSWORD commented-out env var example
epd7in3e/
  config.h           # APP_PASSWORD constant (or planner uses NVS)
  epd7in3e.ino       # setAuthorization() calls on http and sleepHttp clients
README.md            # Document APP_PASSWORD env var
tests/
  test_auth.py       # New: TDD RED contract tests (AUTH-01..AUTH-08)
```

### Pattern 1: `require_auth` Decorator

**What:** A `functools.wraps`-based decorator that reads `request.authorization`, compares the password with `hmac.compare_digest`, and either continues or aborts with 401.

**When to use:** Stack directly below `@app.route` on every protected route.

```python
# Source: Flask 3.1.0 docs + stdlib hmac
import hmac
from functools import wraps
from flask import request, make_response

APP_PASSWORD = os.getenv('APP_PASSWORD', '')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not APP_PASSWORD:
            return f(*args, **kwargs)          # opt-in: no password set → open
        auth = request.authorization
        if auth and auth.username == 'admin' and hmac.compare_digest(
            auth.password or '', APP_PASSWORD
        ):
            return f(*args, **kwargs)
        app.logger.warning('Auth failed: %s', request.remote_addr)
        response = make_response('Unauthorized', 401)
        response.headers['WWW-Authenticate'] = 'Basic realm="EPF"'
        return response
    return decorated


@app.route('/setting', methods=['GET', 'POST'])
@require_auth
def settings():
    ...
```

**Key detail:** `@require_auth` must be placed BELOW `@app.route` so Flask registers the route on the original function name, not the wrapper. This is the standard Flask decorator stacking order.

### Pattern 2: Arduino `setAuthorization` call

**What:** Call `http.setAuthorization("admin", APP_PASSWORD)` immediately after `http.begin(...)` and before `http.GET()`. Applies to both the image download client (`http`) and the sleep client (`sleepHttp`).

```cpp
// Source: espressif/arduino-esp32 HTTPClient Authorization example
// config.h
#define APP_PASSWORD ""  // set to match server APP_PASSWORD env var

// epd7in3e.ino — inside downloadImage(), after http.begin(...)
http.setAuthorization("admin", APP_PASSWORD);
// ...
int httpCode = http.GET();

// same for sleepHttp
sleepHttp.begin(*sleepBasicClient, sleepUrl);
sleepHttp.setAuthorization("admin", APP_PASSWORD);
sleepHttp.GET();
```

`setAuthorization(user, pass)` internally Base64-encodes `"user:pass"` and sets the `Authorization: Basic ...` header. No manual encoding needed.

**Firmware password storage choice (Claude's discretion):**
- **Hardcoded constant in `config.h`**: simplest, consistent with `SERVER_BASE_URL` and other constants in that file. Requires recompile to change password.
- **NVS Preferences**: more flexible, matches `SERVER_BASE_URL` being stored in NVS. Adds NVS read logic.
- **Recommendation:** Hardcoded constant in `config.h` — matches existing pattern for other fixed credentials and is simplest for a local network device.

### Pattern 3: TDD Contract Tests

Following Phase 2–7 patterns: write RED tests first, implement to make them GREEN.

```python
# tests/test_auth.py
import base64
import pytest
import app as app_module

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, 'APP_PASSWORD', 'secret')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c

def auth_header(password='secret'):
    creds = base64.b64encode(f'admin:{password}'.encode()).decode()
    return {'Authorization': f'Basic {creds}'}

def test_protected_route_no_credentials_returns_401(client):
    resp = client.get('/setting')
    assert resp.status_code == 401
    assert 'WWW-Authenticate' in resp.headers

def test_protected_route_correct_credentials_returns_200(client):
    resp = client.get('/setting', headers=auth_header())
    assert resp.status_code == 200

def test_wrong_password_returns_401(client):
    resp = client.get('/setting', headers=auth_header('wrong'))
    assert resp.status_code == 401

def test_no_password_set_allows_access(monkeypatch):
    monkeypatch.setattr(app_module, 'APP_PASSWORD', '')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        resp = c.get('/setting')
        assert resp.status_code == 200
```

### Anti-Patterns to Avoid

- **`@require_auth` above `@app.route`:** Flask will register the wrapper function, potentially breaking routing. Always stack `@app.route` outermost (topmost line).
- **Using `==` for password comparison:** Leaks length via timing. Use `hmac.compare_digest`.
- **Checking `auth.password == APP_PASSWORD`:** Must guard `auth is not None` first or `auth.password or ''` to avoid `AttributeError`.
- **Storing `APP_PASSWORD` in plain text in the git repo `.env`:** Only add to `.env.example` as a placeholder; instruct users to fill in their own value.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Base64 encoding for Basic Auth header (Arduino) | Manual `base64.encode()` + header string assembly | `http.setAuthorization("admin", password)` | HTTPClient handles it natively, correct format guaranteed |
| Constant-time comparison | Custom char-by-char loop | `hmac.compare_digest` | stdlib, FIPS-certified, prevents timing side channels |
| Authorization header parsing | Manually decode `Authorization` header | `request.authorization.username` / `.password` | werkzeug parses and validates the header format |

**Key insight:** Flask + Python stdlib cover the entire server-side implementation. HTTPClient covers the firmware side. No external packages needed in either environment.

---

## Common Pitfalls

### Pitfall 1: Decorator Stacking Order

**What goes wrong:** Auth decorator is applied above `@app.route`, causing Flask to register the wrapper function's name instead of the original function's name.

**Why it happens:** Python decorators are applied bottom-up. If `@require_auth` is outermost (topmost line), it wraps `settings` before `@app.route` can inspect it. Without `@wraps(f)` this breaks `url_for()` because endpoint names become `decorated` instead of `settings`.

**How to avoid:** Always place `@app.route` first (topmost), `@require_auth` second:
```python
@app.route('/setting', methods=['GET', 'POST'])
@require_auth
def settings():
```
`functools.wraps(f)` inside the decorator copies `__name__`, `__doc__` etc., which Flask needs for endpoint registration.

**Warning signs:** `AssertionError: View function mapping is overwriting an existing endpoint function` on app startup.

### Pitfall 2: `request.authorization` is `None` When Header is Absent

**What goes wrong:** Accessing `auth.username` directly raises `AttributeError` when no `Authorization` header is sent.

**Why it happens:** `request.authorization` returns `None` (not an empty Authorization object) when the header is absent or malformed.

**How to avoid:** Always guard: `if auth and auth.username == 'admin' and hmac.compare_digest(auth.password or '', APP_PASSWORD)`.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'username'` in server logs.

### Pitfall 3: Empty `APP_PASSWORD` Check

**What goes wrong:** `hmac.compare_digest('', '')` returns `True`, inadvertently granting access when `APP_PASSWORD` is not set and a request arrives without credentials.

**Why it happens:** The empty-password opt-in guard must short-circuit before the compare, not after. If the `if not APP_PASSWORD` guard is absent, two requests both send empty passwords and both pass.

**How to avoid:** The `if not APP_PASSWORD: return f(*args, **kwargs)` guard must be the first line inside the decorator — before any header inspection.

**Warning signs:** Route accessible without credentials even after setting `APP_PASSWORD=` (empty value).

### Pitfall 4: Arduino `setAuthorization` Called Before `http.begin`

**What goes wrong:** Authorization header is not sent with the request.

**Why it happens:** `HTTPClient` resets internal state on `begin()`. Calling `setAuthorization` before `begin()` means the header is wiped.

**How to avoid:** Always call `setAuthorization` AFTER `http.begin(...)`:
```cpp
http.begin(*basicClient, imageUrl + downloadPath);
http.setAuthorization("admin", APP_PASSWORD);  // after begin
http.addHeader("batteryCap", String(headerValue));
http.GET();
```

**Warning signs:** 401 responses from server despite firmware having credentials set; serial log shows `GET failed: 401`.

### Pitfall 5: WWW-Authenticate Header Required for Browser Dialog

**What goes wrong:** Browser does not show native auth dialog; instead shows a plain 401 error page.

**Why it happens:** RFC 7235 requires the `WWW-Authenticate` response header to trigger the browser challenge flow. Without it, the browser treats the 401 as a regular error.

**How to avoid:** Always set `WWW-Authenticate: Basic realm="EPF"` on 401 responses. The `realm` string `"EPF"` is what appears in the browser dialog.

---

## Code Examples

Verified patterns from official sources:

### Complete `require_auth` Decorator (Flask 3.1.0)

```python
# Source: werkzeug Authorization docs + Python stdlib hmac
import hmac
from functools import wraps
from flask import request, make_response

APP_PASSWORD = os.getenv('APP_PASSWORD', '')   # after existing os.getenv() block


def require_auth(f):
    """Enforce HTTP Basic Auth when APP_PASSWORD is set.

    When APP_PASSWORD is empty/absent, all requests pass through (opt-in).
    Returns 401 + WWW-Authenticate header on missing or wrong credentials.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not APP_PASSWORD:
            return f(*args, **kwargs)
        auth = request.authorization
        if (
            auth
            and auth.username == 'admin'
            and hmac.compare_digest(auth.password or '', APP_PASSWORD)
        ):
            return f(*args, **kwargs)
        app.logger.warning('Auth failed from %s', request.remote_addr)
        response = make_response('Unauthorized', 401)
        response.headers['WWW-Authenticate'] = 'Basic realm="EPF"'
        return response
    return decorated
```

### Route Protection (all four routes)

```python
@app.route('/setting', methods=['GET', 'POST'])
@require_auth
def settings():
    ...

@app.route('/')
@require_auth
def index():
    return redirect(url_for('settings'))

@app.route('/download', methods=['GET'])
@require_auth
def process_and_download():
    ...

@app.route('/sleep', methods=['GET'])
@require_auth
def get_sleep_duration():
    ...
```

### compose.yml Addition

```yaml
environment:
  - IMMICH_API_KEY=your-api-key-here
  # - APP_PASSWORD=your-password-here   # Remove '#' and set a password to enable auth
```

### Arduino config.h Addition

```cpp
// HTTP Basic Auth (set to match server APP_PASSWORD env var; leave empty to disable)
#define APP_PASSWORD ""
```

### Arduino setAuthorization Usage

```cpp
// Source: espressif/arduino-esp32 HTTPClient/examples/Authorization/Authorization.ino
// After http.begin() — before http.GET()
http.setAuthorization("admin", APP_PASSWORD);

// Repeat for sleepHttp
sleepHttp.begin(*sleepBasicClient, sleepUrl);
sleepHttp.setAuthorization("admin", APP_PASSWORD);
```

### pytest Test Skeleton (RED contract)

```python
# tests/test_auth.py
import base64
import pytest
import app as app_module


def _basic_header(user='admin', password='secret'):
    creds = base64.b64encode(f'{user}:{password}'.encode()).decode()
    return {'Authorization': f'Basic {creds}'}


@pytest.fixture
def auth_client(monkeypatch):
    """Test client with APP_PASSWORD='secret' set."""
    monkeypatch.setattr(app_module, 'APP_PASSWORD', 'secret')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def open_client(monkeypatch):
    """Test client with APP_PASSWORD='' (auth disabled)."""
    monkeypatch.setattr(app_module, 'APP_PASSWORD', '')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `flask-basicauth` extension | Inline decorator with `request.authorization` | Flask 1.x → 2.x | No extension needed; werkzeug parses the header natively |
| `request.authorization['username']` dict access | `request.authorization.username` attribute | werkzeug 2.x | Both work; attribute access is cleaner |

**Deprecated/outdated:**
- `flask-basicauth`: Unmaintained extension; unnecessary — Flask/werkzeug provides `request.authorization` natively.
- Manual Base64 decode in route handlers: werkzeug does this automatically.

---

## Open Questions

1. **Firmware password storage: `config.h` constant vs. NVS**
   - What we know: `config.h` already holds `SERVER_BASE_URL` as a macro. NVS is used for `SERVER_BASE_URL` at runtime via `preferences.getString("SERVER_BASE_URL")`.
   - What's unclear: Whether the user wants the password editable without recompilation (NVS) or prefers simplicity (constant).
   - Recommendation: Default to `config.h` constant for this phase (matches existing pattern for other compile-time constants like `HTTP_TIMEOUT`). NVS approach can be added in a future phase if needed.

2. **README update scope**
   - What we know: README currently documents `IMMICH_API_KEY`. `APP_PASSWORD` should follow the same documentation pattern.
   - Recommendation: Add a short "Access Control" section after the existing environment variable documentation.

---

## Environment Availability

Step 2.6: SKIPPED — no new external dependencies. All required tools (Python stdlib `hmac`, Flask 3.1.0, Arduino HTTPClient) are already present in the project.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in `requirements.txt`) |
| Config file | none — pytest discovers `tests/` automatically |
| Quick run command | `pytest tests/test_auth.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Decorator passes request when `APP_PASSWORD` is empty | unit | `pytest tests/test_auth.py::test_no_password_set_allows_access -x` | Wave 0 |
| AUTH-02 | Missing credentials → 401 + `WWW-Authenticate` header | unit | `pytest tests/test_auth.py::test_protected_route_no_credentials_returns_401 -x` | Wave 0 |
| AUTH-02 | Wrong password → 401 | unit | `pytest tests/test_auth.py::test_wrong_password_returns_401 -x` | Wave 0 |
| AUTH-02 | `WWW-Authenticate` header present on 401 | unit | `pytest tests/test_auth.py::test_401_includes_www_authenticate_header -x` | Wave 0 |
| AUTH-03 | All 4 routes protected (parameterized) | unit | `pytest tests/test_auth.py::test_all_routes_require_auth -x` | Wave 0 |
| AUTH-04 | `APP_PASSWORD` loaded from env | unit | `pytest tests/test_auth.py::test_app_password_loaded_from_env -x` | Wave 0 |
| AUTH-06 | Correct credentials → 200 (smoke-tests route access) | unit | `pytest tests/test_auth.py::test_protected_route_correct_credentials_returns_200 -x` | Wave 0 |
| AUTH-07 | `hmac.compare_digest` used (verified by code inspection) | n/a | manual-only — not observable from outside | — |
| AUTH-08 | Failed attempt logged | unit | `pytest tests/test_auth.py::test_failed_auth_is_logged -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_auth.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_auth.py` — covers AUTH-01 through AUTH-08 (new file, written RED first)

*(Existing test infrastructure `tests/conftest.py` + `pytest` is sufficient; no new fixtures or framework install needed.)*

---

## Sources

### Primary (HIGH confidence)

- Flask 3.1.0 `request.authorization` — werkzeug `Authorization` object with `.username`, `.password` attributes
- Python stdlib `hmac.compare_digest` — [docs.python.org/3/library/hmac.html](https://docs.python.org/3/library/hmac.html)
- ESP32 Arduino Core official example: [github.com/espressif/arduino-esp32/.../Authorization.ino](https://github.com/espressif/arduino-esp32/blob/master/libraries/HTTPClient/examples/Authorization/Authorization.ino)

### Secondary (MEDIUM confidence)

- AvantMaker ESP32 HTTPClient `setAuthorization` docs — verified against official espressif example — [avantmaker.com/references/esp32-arduino-core-index/esp32-httpclient-library/esp32-httpclient-library-setauthorization/](https://avantmaker.com/references/esp32-arduino-core-index/esp32-httpclient-library/esp32-httpclient-library-setauthorization/)
- werkzeug Authorization object attributes — [tedboy.github.io/flask/generated/generated/werkzeug.Authorization.html](https://tedboy.github.io/flask/generated/generated/werkzeug.Authorization.html)

### Tertiary (LOW confidence)

- None — all findings are supported by primary or verified secondary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Flask 3.1.0 and Python stdlib are in `requirements.txt`; no new packages needed
- Architecture: HIGH — decorator pattern is standard Flask; `request.authorization` is werkzeug core API
- Pitfalls: HIGH — decorator stacking and `None` guard are well-known Flask patterns; Arduino timing verified by espressif example
- Arduino firmware: HIGH — `setAuthorization` is in official espressif/arduino-esp32 example

**Research date:** 2026-06-02
**Valid until:** 2026-09-02 (Flask 3.x API stable; HTTPClient API stable on ESP32 Arduino core)
