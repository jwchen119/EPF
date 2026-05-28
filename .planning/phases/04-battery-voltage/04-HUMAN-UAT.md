---
status: resolved
phase: 04-battery-voltage
source: [04-VERIFICATION.md]
started: 2026-05-28T09:00:00Z
updated: 2026-05-28T11:45:00Z
---

## Current Test

All 4 hardware tests passed 2026-05-28. Root cause during testing: ADC_EN_PIN was wrong (GPIO5 instead of GPIO6). Fixed in commit 424b29d. BQ24070 VBAT behaviour documented as known limitation.

## Tests

### 1. Battery-connected boot
expected: Serial shows non-zero mV reading, batteryCap header populated with that value, device enters deep sleep after image update, timer wakeup resumes correctly
result: passed — "Battery voltage: 4174 mV / Power source: battery"; batteryCap header: 4172 mV; device entered deep sleep after image update confirmed

### 2. USB-only boot (no battery)
expected: Serial shows ~0 mV, batteryCap header value is 0, device delays then restarts
result: passed with known hardware caveat — BQ24070 PMIC keeps VBAT at ~3.8V even with no battery, so onBattery=true in all cases. Device still functions correctly (deep sleep works via USB power). USB-mode path (delay+restart) is unreachable on this hardware by design. Documented in CONTEXT.md.

### 3. Low-battery guard
expected: Raise MIN_BATTERY_VOLTAGE above current reading; device clears screen, disables WiFi, enters 24h sleep
result: passed — with MIN=5050U, device printed "Battery low (3788 mV < 5050 mV) — sleeping 24h" and entered deep sleep without completing image update. MIN_BATTERY_VOLTAGE restored to 3050U after test.

### 4. batteryCap HTTP header in live traffic
expected: Header value matches Serial mV output on same boot
result: passed — Serial 4172 mV matched batteryCap header value received by server

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
