# EPF Project Roadmap

## Phase 1: Hardware Port — FireBeetle C6 + WaveShare 7.3" → XIAO S3 Plus + Seeed 13.3" Color Eink

**Goal:** Port firmware and server to the EE02 kit (XIAO ESP32-S3 Plus + Seeed 13.3" T133A01 display). Replace WaveShare driver with Seeed_GFX. Update server palette and resolution.

**Requirements:** HW-01, HW-02, HW-03, HW-04, HW-05, HW-06, HW-07

**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Replace WaveShare driver headers with EE02 pin constants and Seeed_GFX includes
- [x] 01-02-PLAN.md — Rewrite main .ino: Seeed_GFX API, PSRAM frame buffer, remove battery guard, fix sleep API
- [x] 01-03-PLAN.md — Update server palette (T133A01 colors), nibble map, and 1200x1600 resolution

## Phase 2: Date Overlay — Show photo date on e-paper display

**Goal:** Extract the date a photo was taken (from Immich API metadata or file EXIF) and render it as a configurable text overlay on the processed image. The overlay position (9 alignments: topLeft, topCenter, topRight, centerLeft, center, centerRight, bottomLeft, bottomCenter, bottomRight) must be configurable via config.yaml and the web settings UI.

**Requirements:** DO-01, DO-02, DO-03, DO-04, DO-05

**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — Wave 0: pytest infra + 9 failing test stubs locking DO-01..DO-05 contracts
- [x] 02-02-PLAN.md — Add module-level parse_photo_date() and draw_date_overlay() helpers (TDD GREEN for pure logic)
- [x] 02-03-PLAN.md — Wire overlay into scale_img_in_memory + DEFAULT_CONFIG + settings UI; remove dead code
