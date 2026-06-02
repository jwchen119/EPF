# Phase 8: Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 08-auth
**Areas discussed:** Auth mechanism, Credential configuration, Firmware endpoint scope, Disabled-auth behavior

---

## Auth Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP Basic Auth | Browser-native username/password dialog, no login page, no Flask session needed, simple decorator implementation | ✓ |
| Form-based session login | Custom /login route, session cookie after success, /logout route, requires Flask secret_key | |

**User's choice:** HTTP Basic Auth
**Notes:** No follow-up questions — clear and self-contained choice.

---

## Credential Configuration

### Password storage

| Option | Description | Selected |
|--------|-------------|----------|
| Environment variable | APP_PASSWORD in .env / docker-compose.yml, consistent with IMMICH_API_KEY pattern | ✓ |
| Via settings UI | Password field in /setting page — chicken-and-egg problem (need auth to reach settings) | |

**User's choice:** Environment variable (APP_PASSWORD)

### Username

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed username 'admin', password-only env var | Only APP_PASSWORD needs to be set, simpler for single-user home device | ✓ |
| Both username + password as env vars | APP_USERNAME + APP_PASSWORD both configurable | |

**User's choice:** Fixed 'admin' username, APP_PASSWORD only

---

## Firmware Endpoint Scope

| Option | Description | Selected |
|--------|-------------|----------|
| No auth on firmware endpoints | Only /setting and / require auth; ESP32 keeps calling /download and /sleep as-is, no firmware changes | |
| Protect all endpoints including firmware | All routes require auth; ESP32 sends HTTP Basic Auth credentials via http.setAuthorization() | ✓ |

**User's choice:** All routes protected (including /download and /sleep)
**Notes:** Requires firmware update — Arduino HTTPClient supports setAuthorization() natively.

---

## Disabled-Auth Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Allow all access (opt-in auth) | When APP_PASSWORD not set, app behaves as today — backward compatible | ✓ |
| Block all access until password configured | Force secure-by-default; existing deployments break on upgrade | |

**User's choice:** Opt-in auth — allow all access when APP_PASSWORD is not set

---

## Claude's Discretion

- Constant-time comparison via `hmac.compare_digest` (security best practice)
- Whether decorator is inline or a helper function
- Arduino firmware password storage approach (hardcoded constant vs. NVS)
- Whether to log failed auth attempts

## Deferred Ideas

None.
