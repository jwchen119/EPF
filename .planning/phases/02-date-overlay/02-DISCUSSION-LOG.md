# Phase 2: Date Overlay - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 02-date-overlay
**Areas discussed:** Overlay toggle + missing date fallback

---

## Overlay Toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Off by default, user enables in settings | Safer default — existing displays won't change appearance until the user turns it on. | ✓ |
| On by default | Overlay always shows unless user explicitly disables it in settings. | |

**User's choice:** Off by default, user enables in settings
**Notes:** Clean default — won't break existing deployments.

---

## Missing Date Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Hide the overlay silently | If no date found, the image renders without any overlay. Clean, no placeholders. | ✓ |
| Show a placeholder text | Show something like 'Unknown date' or a dash when no date is available. | |
| Fall back to file modification date | Use the file's last-modified timestamp as a last resort. | |

**User's choice:** Hide the overlay silently
**Notes:** Simple and clean — no visible change when metadata is missing.

---

## Claude's Discretion

- Date format (defaulted to DD.MM.YYYY)
- Font size and visual style (white text, black background, matching existing partial code)
- Position + rotation interaction semantics (positions apply to final rendered image)
- All 3 additional gray areas (Date format, Position+rotation, Visual style) were not selected for discussion

## Deferred Ideas

None.
