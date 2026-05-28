---
status: resolved
trigger: "Date overlay text is not rotated with the image and does not respect alignment relative to the rotated image"
created: 2026-05-27T00:00:00Z
updated: 2026-05-27T12:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - draw_date_overlay() ignores rotationAngle entirely; both text position and text orientation are wrong for non-zero rotation
test: Traced full execution path through git diff b494eac; confirmed old code handled rotation but new code removed it
expecting: fix requires: (1) remap position name to buffer-space coordinates for given rotation, (2) rotate text in buffer to appear upright to viewer
next_action: Implement fix in draw_date_overlay to accept rotation parameter and handle rotation-aware drawing

## Symptoms

expected: Overlay renders on the rotated image in the correct corner — e.g. 'bottomRight' stays bottom-right relative to the final displayed image
actual: Overlay text appears in wrong position after rotation (coordinates were calculated on pre-rotation image); text itself is not rotated to match image orientation
errors: No crash — visual bug only
reproduction: Configure date_overlay_enabled=true, set a position (e.g. bottomRight), rotate the image via server-side rotation in scale_img_in_memory, observe overlay lands in wrong spot
started: Introduced in Phase 02 plan 02-03 when overlay was wired into scale_img_in_memory

## Eliminated

- hypothesis: overlay applied before rotation in scale_img_in_memory
  evidence: Confirmed via code reading that draw_date_overlay is called AFTER load_scaled (rotation step). The ordering is correct. The bug is different.
  timestamp: 2026-05-27

- hypothesis: PIL's Image.fromarray produces wrong dimensions causing misaligned coords
  evidence: Both cpy_fallback.py and load_scaled always produce 1200x1600. Dimensions are always correct.
  timestamp: 2026-05-27

- hypothesis: No actual bug for rotation=0 use case
  evidence: For rotation=0, the current code is and always was correct. Bug only affects non-zero rotation.
  timestamp: 2026-05-27

## Evidence

- timestamp: 2026-05-27
  checked: git diff b494eac -- app.py (the commit that introduced the bug)
  found: Old draw_text_with_background handled rotation via if/elif for 0/90/180/270 — computed rotation-adjusted buffer coords AND rotated the text image. New draw_date_overlay ignores rotation completely.
  implication: For rotationAngle=270 (default), viewer's bottomRight = buffer's topRight. Text drawn upright in buffer appears 270° CCW rotated to viewer. Both position and text orientation are wrong.

- timestamp: 2026-05-27
  checked: cpy_fallback.py load_scaled → img.rotate(angle, expand=True) (PIL CCW rotation)
  found: PIL rotate(angle) is CCW. rotationAngle=270 → 270° CCW = 90° CW. Buffer content is 90° CW relative to viewer who looks at display mounted 90° CW.
  implication: For rotationAngle=270, viewer sees buffer from 90° CW perspective. Buffer (0,0) = viewer bottomLeft. Buffer (W,0) = viewer topLeft. Buffer (W,H) = viewer topRight. Buffer (0,H) = viewer bottomRight. So user's bottomRight should be drawn at buffer (0,H) = topLeft in buffer.

- timestamp: 2026-05-27
  checked: firmware (epd7in3e.ino) for hardware rotation
  found: No hardware rotation in firmware. Display renders buffer as-is.
  implication: rotationAngle is purely for display mounting compensation. Buffer coordinates ≠ viewer coordinates when rotation ≠ 0.

- timestamp: 2026-05-27
  checked: DEFAULT_CONFIG rotation=270
  found: Default rotation is 270 — meaning the device is ALWAYS used with a rotated display mounting. The bug affects 100% of default configurations.
  implication: This is not an edge case. Every default deployment has the overlay in the wrong position with unreadable text.

## Resolution

root_cause: draw_date_overlay() accepted no rotation parameter and used buffer coordinates directly as viewer coordinates. For non-zero rotationAngle, the display is mounted at an angle so buffer ≠ viewer coordinate system. Result: overlay always lands at buffer bottomRight regardless of user's configured position, AND text drawn upright in buffer appears rotated to the viewer (e.g., 90° CW for rotationAngle=270). The Phase 02-03 implementation correctly removed the old dead draw_text_with_background code but the replacement draw_date_overlay never handled rotation. The previous code was also commented out so no regression — this was a feature gap.

fix: Added rotation=0 parameter to draw_date_overlay(). When rotation != 0, the function: (1) computes viewer-space dimensions (transposed for 90/270), (2) draws upright text at viewer-space position on an RGBA canvas, (3) rotates the canvas by rotation° CCW (same rotation as load_scaled applies to image content) to map viewer-space to buffer-space, (4) pastes onto output_img using alpha mask. Updated call site in scale_img_in_memory to pass rotation=rotation.

verification: 13/13 tests pass including 4 new rotation-specific tests verifying that viewer's bottomRight maps to correct buffer corner for each of 0/90/180/270 rotation values. All original 9 Wave 0 tests still GREEN. app.py compiles clean. Confirmed working on physical device — date text appears in correct corner and is upright/readable.

files_changed: [app.py, tests/test_date_overlay.py]
