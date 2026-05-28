# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## date-overlay-rotation — draw_date_overlay ignored rotation causing wrong position and unreadable text
- **Date:** 2026-05-27
- **Error patterns:** date overlay, rotation, wrong position, wrong corner, upside down, rotated text, scale_img_in_memory, draw_date_overlay, rotationAngle, buffer coordinates
- **Root cause:** draw_date_overlay() accepted no rotation parameter and used buffer coordinates directly as viewer coordinates. For non-zero rotationAngle (default=270), the display is mounted at an angle so buffer and viewer coordinate systems differ. Result: overlay always lands at the buffer-space position (e.g. bottomRight in buffer = topLeft in viewer for rotation=270), and text drawn upright in buffer appears rotated to the viewer.
- **Fix:** Added rotation parameter to draw_date_overlay(). For non-zero rotation: compute viewer-space dimensions (transposed for 90/270), draw upright text at viewer-space position on RGBA canvas, rotate canvas by rotation° CCW to map to buffer-space, paste with alpha mask. Updated call site in scale_img_in_memory to pass rotation.
- **Files changed:** app.py, tests/test_date_overlay.py
---
