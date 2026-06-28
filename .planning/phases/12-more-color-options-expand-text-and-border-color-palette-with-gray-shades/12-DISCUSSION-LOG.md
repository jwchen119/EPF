# Phase 12: More Color Options — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 12-more-color-options-expand-text-and-border-color-palette-with-gray-shades
**Areas discussed:** Which gray shades, Naming in UI, Scope of changes

---

## Which Gray Shades

| Option | Description | Selected |
|--------|-------------|----------|
| 2 grays: Dark Gray + Light Gray | (64,64,64) + (192,192,192). Useful contrast options without clutter. | |
| 3 grays: Dark + Mid + Light | Adds mid-gray (128,128,128). Could go black or white after quantization. | ✓ |
| 1 gray: mid-gray only | Single generic 'Gray' option. Minimal change. | |

**User's choice:** 3 grays (Dark Gray, Gray, Light Gray)
**Notes:** User wants a full spread — dark/mid/light.

---

## Naming in UI

| Option | Description | Selected |
|--------|-------------|----------|
| Dark Gray / Gray / Light Gray | Clear descriptive names. | ✓ |
| Dark Gray / Mid Gray / Light Gray | More explicit about the middle. | |
| Slate / Gray / Silver | Evocative but less precise. | |

**User's choice:** Dark Gray / Gray / Light Gray

---

## Gray Order in Dropdown

| Option | Description | Selected |
|--------|-------------|----------|
| After White, before Yellow | Black, White, Dark Gray, Gray, Light Gray, Yellow… Achromatics grouped at top. | ✓ |
| At the end of the list | Existing items unchanged, grays appended. | |

**User's choice:** After White, before Yellow

---

## Scope of Changes

| Option | Description | Selected |
|--------|-------------|----------|
| OVERLAY_COLORS + 3 dropdowns only | Add grays to OVERLAY_COLORS dict and 3 selects in settings.html. No palette change. | ✓ |
| Also add grays to T133A01 hardware palette | Not recommended — hardware palette is fixed. | |

**User's choice:** OVERLAY_COLORS + 3 dropdowns only

---

## Claude's Discretion

- Whether any test fixtures enumerating OVERLAY_COLORS need updating
- Verifying existing OVERLAY_COLORS.get() callers work transparently with new entries

## Deferred Ideas

None.
