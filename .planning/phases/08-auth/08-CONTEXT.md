# Phase 8: Auth - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Add access control to the Flask app so it is not open to anyone on the local network. All four routes (`/`, `/setting`, `/download`, `/sleep`) require HTTP Basic Auth when `APP_PASSWORD` is set in the environment. When `APP_PASSWORD` is not set, the app runs without auth (backward-compatible opt-in).

The ESP32 firmware must also send credentials when calling `/download` and `/sleep`, so auth scope covers the entire app.

</domain>

<decisions>
## Implementation Decisions

### Auth Mechanism
- **D-01:** Use **HTTP Basic Auth**. The browser shows its native username/password dialog — no login page, no `/login` route, no Flask session or secret_key needed. A simple `@require_auth` decorator checks the `Authorization` header on every request.

### Credential Configuration
- **D-02:** Password is set via the `APP_PASSWORD` environment variable (loaded via `python-dotenv`, consistent with `IMMICH_API_KEY`). No UI controls for the password.
- **D-03:** Username is fixed as `"admin"`. Only `APP_PASSWORD` needs to be set — no `APP_USERNAME` env var.
- **D-04:** `APP_PASSWORD` added to `docker-compose.yml` as a commented-out example (like `IMMICH_API_KEY`). Also documented in README/`.env.example`.

### Firmware Endpoint Scope
- **D-05:** **All routes** are protected: `/`, `/setting`, `/download`, and `/sleep`. The ESP32 firmware must send HTTP Basic Auth credentials in its requests. This requires updating the firmware's `http.GET()` / `http.begin()` calls to include an `Authorization: Basic <base64(admin:PASSWORD)>` header.
- **D-06:** The Arduino firmware uses `http.setAuthorization("admin", password)` (HTTPClient API) — this is a single-line addition per request. The firmware reads the password from a hardcoded constant or NVS (implementation detail for planner).

### Disabled-Auth Behavior
- **D-07:** **Auth is opt-in.** When `APP_PASSWORD` is not set (empty string or absent), the decorator passes all requests through without authentication. Existing deployments are unaffected until `APP_PASSWORD` is added to their environment.
- **D-08:** When `APP_PASSWORD` is set and a request arrives without credentials (or with wrong credentials), the server responds with `401 Unauthorized` and a `WWW-Authenticate: Basic realm="EPF"` header, triggering the browser's native auth dialog.

### Claude's Discretion
- Whether the `@require_auth` decorator lives inline in `app.py` or as a small helper function — `app.py` is consistent with the existing single-file pattern.
- Constant-time comparison for the password check (`hmac.compare_digest`) to avoid timing attacks.
- Whether to log failed auth attempts (recommend yes, at WARN level).
- How the Arduino firmware stores the password (hardcoded constant vs. NVS preferences) — firmware implementation detail.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Flask app structure
- `app.py:1-40` — imports and `load_dotenv()` setup; `APP_PASSWORD` env var added alongside existing env var reads
- `app.py:324-332` — existing `os.getenv()` calls for `IMMICH_API_KEY`, `IMMICH_PHOTO_DEST`, etc. — `APP_PASSWORD` follows this pattern
- `app.py:824` — `@app.route('/setting')` — one of the routes to protect
- `app.py:928` — `@app.route('/')` — redirect route, also protected
- `app.py:1100` — `@app.route('/download')` — firmware endpoint, also protected
- `app.py:1132` — `@app.route('/sleep')` — firmware endpoint, also protected

### Deployment configuration
- `docker-compose.yml` — `IMMICH_API_KEY` example pattern; `APP_PASSWORD` added similarly as a commented-out env var

### Prior phase decisions relevant here
- `.planning/STATE.md` — established pattern: env vars via `os.getenv()`, `python-dotenv` already loaded at startup
- `.planning/phases/02-date-overlay/02-CONTEXT.md` — D-01: opt-in defaults (off unless configured) — same philosophy for auth

### Flask HTTP Basic Auth reference
- No external docs needed — Flask's `request.authorization` attribute gives username/password from the `Authorization` header directly. No extra library required.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `load_dotenv()` at line 32: already loads `.env` — `APP_PASSWORD=secret` just works in `.env` or `docker-compose.yml` env block.
- `os.getenv('IMMICH_API_KEY')` at line 324: exact pattern to replicate for `APP_PASSWORD = os.getenv('APP_PASSWORD', '')`.

### Established Patterns
- Single-file Flask app — `app.py` contains all route logic; the auth decorator goes in the same file before the route definitions.
- Env vars are read at module level and stored as module globals (e.g., `apikey = os.getenv('IMMICH_API_KEY')`).

### Integration Points
- All 4 `@app.route` decorators need the auth decorator stacked on top (or use Flask's `@app.before_request`).
- Arduino firmware: `http.begin(url)` → add `http.setAuthorization("admin", APP_PASSWORD)` before `http.GET()`. Applies to both the `/download` and `/sleep` calls in the `.ino` file.

</code_context>

<specifics>
## Specific Ideas

- Python `hmac.compare_digest(a, b)` for constant-time password comparison (prevents timing attacks even on a local network).
- `WWW-Authenticate: Basic realm="EPF"` — realm string identifies the app in the browser dialog.
- `docker-compose.yml` example: add `# - APP_PASSWORD=your-password-here` as a commented line under `environment:`.
- Arduino: `http.setAuthorization("admin", PASSWORD_CONSTANT)` — HTTPClient supports Basic Auth natively; no manual base64 needed.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-auth*
*Context gathered: 2026-06-01*
