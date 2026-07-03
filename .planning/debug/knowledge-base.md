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

## battery-guard-false-trigger-on-external-power — board appears bricked for 24h when plugged into external power
- **Date:** 2026-07-03
- **Error patterns:** Power source: battery, Battery low, sleeping 24h, bricked, external power, USB power, enforceLowBatteryGuard, m_onBattery, VBAT, BQ24070, deep sleep, 24h sleep
- **Root cause:** Two compounding issues. (1) Hardware fact: EE02 v1.0 board has no software-readable power-source-presence signal — BQ24070 PG pin is unpopulated (DNP) and STAT1/STAT2 only drive charge-status LEDs, not any GPIO; m_onBattery is only a proxy based on VBAT > 1500mV and cannot distinguish real battery power from USB power with a low/aging cell. (2) Logic flaw: enforceLowBatteryGuard() treated a single ambiguous low-voltage reading as proof of imminent power loss and committed immediately to an unrecoverable 24h deep sleep, with no chance for the BQ24070 to recharge the cell above threshold first.
- **Fix:** Added g_lowBatteryStreak (RTC_DATA_ATTR int, survives deep sleep, resets on power-on-reset) and LOW_BATTERY_ESCALATION_THRESHOLD (config.h). enforceLowBatteryGuard() now sleeps only MIN_SLEEP_TIME (15min) for the first few consecutive low readings (streak < threshold) and re-checks; only escalates to the full 86400s (24h) sleep after LOW_BATTERY_ESCALATION_THRESHOLD consecutive independent low-voltage boots. Streak resets to 0 whenever voltage recovers or m_onBattery is false. Also averaged 10 ADC samples in checkVoltage() to reduce single-sample jitter. EXT1 GPIO wakeup remains armed at every stage.
- **Files changed:** epd7in3e/epd7in3e.ino, epd7in3e/config.h
---
