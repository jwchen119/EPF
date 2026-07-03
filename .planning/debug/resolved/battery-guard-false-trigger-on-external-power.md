---
status: resolved
trigger: "battery-guard-false-trigger-on-external-power"
created: 2026-07-03T00:00:00Z
updated: 2026-07-03T10:00:00Z
---

## Current Focus

RESOLVED. User confirmed on real hardware: "works now" — the escalating-retry policy (short
15-minute retry sleep for the first few consecutive low-voltage boots, only escalating to 24h
after LOW_BATTERY_ESCALATION_THRESHOLD consecutive low readings) resolved the issue. Board no
longer appears bricked when plugged into external power.
next_action: none — session archived

## Symptoms

expected: When the board is powered via USB/external power supply, it should detect the power source as external (not "battery") and should not trigger the low-battery deep-sleep guard, regardless of the ADC-read battery voltage.
actual: |
  Serial log on every boot/reset shows:
  ```
  First boot or reset
  Battery voltage: 2924 mV
  Power source: battery
  Battery low (2924 mV < 3050 mV) — sleeping 24h
  ```
  The board goes to sleep for 24h immediately, making it appear "bricked" while plugged into power — no display update, no further serial output, nothing until 24h timer.
errors: No crash/exception — triggered intentionally by enforceLowBatteryGuard() calling esp_deep_sleep_start() for 24h when it thinks battery is critically low.
reproduction: Plug the board into a power source (wall adapter or USB) and observe serial monitor output at boot. 100% reproducible per user report.
started: |
  Regression suspected around recent commits modifying enforceLowBatteryGuard() to tri-state SPI/GPIO/display pins:
  9f3dd7f feat(999.1-01): tri-state SPI/GPIO pins in enforceLowBatteryGuard()
  17796a1 docs(phase-999.1): complete phase execution
  975e9f1 docs(999.1-01): complete SPI/display GPIO tri-state plan
  764edb7 feat(999.1-01): tri-state SPI/display pins before deep sleep
  5a52fff docs(999.1): create phase plan for SPI/display GPIO tri-state before deep sleep

## Eliminated

- hypothesis: The recent tri-state SPI/GPIO commits (764edb7, 9f3dd7f, plus surrounding docs
    commits 975e9f1, 17796a1, 5a52fff) introduced or affected the power-source misclassification
  evidence: |
    `git show 764edb7` and `git show 9f3dd7f` diffs only add cleanup code (SPI.end(), pinMode(INPUT)
    for DC/CS/CS1/RST, rtc_gpio_isolate for GPIO1/GPIO6) that executes AFTER the decision to enter
    24h sleep has already been made inside enforceLowBatteryGuard() / hibernate(). Neither commit
    touches checkVoltage(), m_onBattery, MIN_BATTERY_VOLTAGE, BAT_ADC_PIN, or ADC_EN_PIN. The bug
    predates these commits.
  timestamp: 2026-07-03T00:10:00Z

- hypothesis: There is an unused/unwired BQ24070 PG (power-good), STAT1/STAT2, or other GPIO net on
    the EE02 schematic that was missed in the prior investigation and could be read directly to
    detect USB/external power presence.
  evidence: |
    Directly inspected 202000224_XIAO_ePaper_Display_Board_EE02_V1.pdf (Power.kicad_sch, page 4/6)
    at the component level:
    - U1A BQ24070RHLR pin 18 `~{PG}` (active-low Power Good output) has a red "X" annotation next
      to it in the schematic — Seeed's convention (confirmed by same red-X marks on other
      admittedly-DNP components e.g. R11/R17/D16/TP18) for "not populated / no connection." No net
      label runs from `~PG` to any XIAO GPIO pin — it is a dead-end pad.
    - STAT1 (pin 2) / STAT2 (pin 3) route only to D16/D5 (green charge-status LEDs) — confirmed
      already documented as D-12/D-13 in Phase 04, re-confirmed directly against schematic, and
      re-confirmed NOT wired to any GPIO net.
    - Cross-referenced every net label feeding into U3 (XIAO Plus MCU) on XIAO.kicad_sch (page 5/6):
      BAT_ADC, ADC_EN, PWR_EN, EDP_BUSY, EDP_RST, EDP_DC, BUTON1/2/3, RST, SPI0_*, SPI1_*. No `PG`,
      `~PG`, `STAT1`, `STAT2`, `CHRG`, or `VBUS_SENSE` net appears anywhere in this list.
    - `PWR_EN` net (which IS wired to a GPIO, per config.h ADC_EN_PIN=GPIO6 comment... actually
      PWR_EN and ADC_EN are two DISTINCT nets in the schematic — PWR_EN drives U16 TPS22916 load
      switch powering a separate 3V3 rail (unrelated function, e.g. NFC/font-chip power), while
      ADC_EN drives U17 TPS22916 gating the BAT_ADC divider). Neither is a power-source-presence
      signal; both are firmware-controlled outputs, not power-source inputs.
    - VBUS net does exist on the schematic (feeds TVS diode protection U7 and the ESP32-S3's own
      internal USB detection), but is not broken out to any spare/general-purpose XIAO GPIO pin
      anywhere in the design — it only reaches the native USB D+/D- and the PMIC's own IN pin.
  implication: CONFIRMED — this specific EE02 board revision (v1.0) genuinely provides no
    software-readable power-source-presence signal. The prior investigation's conclusion was
    correct; this is a hardware layout fact, not something missed in documentation. Re-verification
    directly against the schematic (rather than trusting the prior summary alone) is now complete
    and yields the same answer. Any correct fix must be a firmware POLICY change, not a hardware
    signal addition.
  timestamp: 2026-07-03T09:30:00Z

## Evidence

- timestamp: 2026-07-03T00:05:00Z
  checked: epd7in3e/epd7in3e.ino lines 474-520 (checkVoltage(), isOnBattery(), enforceLowBatteryGuard())
  found: |
    `m_onBattery = (vbatMv > 1500);` — power source is classified purely by whether VBAT (as read
    through the BAT_ADC divider) is above 1.5V. There is no actual USB/VBUS-sense signal read anywhere
    in the firmware.
  implication: "Power source: battery" is printed whenever VBAT > 1.5V, irrespective of whether USB
    power is actually present. This is a proxy, not a direct measurement of power source.

- timestamp: 2026-07-03T00:06:00Z
  checked: .planning/phases/04-battery-voltage/04-CONTEXT.md, 04-RESEARCH.md, 04-HUMAN-UAT.md
  found: |
    D-07 (2026-05-28): "Battery present: batteryVoltage > 1500 mV; USB only: <= 1500 mV" — this
    threshold was designed only to distinguish "no battery physically connected" (VBAT floats to 0V)
    from "battery connected." 04-RESEARCH.md line 212 confirms: "No VBUS pin exposed on XIAO EE02
    board; voltage divider method is the only available path" for USB detection — i.e. USB detection
    was never actually implemented; only a "no battery present" proxy exists.
    04-HUMAN-UAT.md test 2 explicitly documents: "BQ24070 PMIC keeps VBAT at ~3.8V even with no
    battery, so onBattery=true in all cases ... USB-mode path (delay+restart) is unreachable on this
    hardware by design." This was accepted/passed as a KNOWN LIMITATION, not fixed.
  implication: The firmware has never been able to reliably detect "external/USB power" as distinct
    from "battery power" on this hardware/board revision — m_onBattery essentially always evaluates
    true whenever any power is applied and VBAT sits above 1.5V, which includes normal USB-powered
    operation. This is the root design flaw behind "Power source: battery" appearing under USB power.

- timestamp: 2026-07-03T00:08:00Z
  checked: git log --oneline for epd7in3e.ino, e4270d9 "fix: Battery Detection (#8)" diff
  found: e4270d9 only fixed ADC_EN_PIN (GPIO5->GPIO6) and BUSY_PIN wiring; did not change or attempt
    to fix the onBattery proxy-detection logic or threshold.
  implication: The USB-vs-battery misclassification is not a regression from any single commit — it
    is the original, always-present behavior of checkVoltage() since Phase 04 introduced it
    (2026-05-28), unchanged through all subsequent commits up to HEAD.

- timestamp: 2026-07-03T00:09:00Z
  checked: enforceLowBatteryGuard() logic (line 502-520) vs hibernate() logic (line 286-299)
  found: |
    Both functions gate their behavior on the SAME m_onBattery flag which cannot distinguish real
    battery power from USB power. hibernate() at least has a "USB power path" fallback for
    m_onBattery == false, but enforceLowBatteryGuard() only checks `m_onBattery && voltage < 3050`,
    with no independent, more reliable, or corroborating signal.
  implication: Even if VBAT reads a valid battery-range voltage while actually running on USB power
    (e.g., battery present but partially discharged/aged, or connector/divider drift lowering the
    reading below 3050mV), enforceLowBatteryGuard() cannot tell the difference and will always apply
    the 24h sleep — even though the device is provably fine (has continuous power from USB) and
    should never truly "run out."
  timestamp_note: This matches the reported symptom exactly — VBAT 2924mV, just under the 3050mV
    threshold, classified as "battery", triggering 24h sleep, even though board is plugged into
    external power.

## Resolution

root_cause: |
  Two compounding issues, both pre-existing (not caused by the recent tri-state GPIO commits
  764edb7/9f3dd7f, which only add pin-cleanup after the sleep decision is already made):

  1. HARDWARE FACT (BQ24070 power-path management, re-confirmed directly against the EE02 v1.0
     KiCad schematic, Power.kicad_sch, U1A BQ24070RHLR): the PMIC independently powers the system
     rail (VSYS) from whichever source (USB/VBUS or battery) is present, while VBAT continues to
     reflect the actual battery cell's own state of charge. A deeply discharged/aged/never-fully-
     charged LiPo cell can genuinely read below 3050mV even while USB is actively powering the
     system and charging the cell. Critically, this board revision has NO software-readable
     power-source-presence signal: the BQ24070's `~PG` (power-good, pin 18) is explicitly
     unpopulated (marked DNP with a red-X schematic annotation, same convention used for other
     confirmed-absent components), and STAT1/STAT2 (pins 2/3) route only to the D5/D16
     charge-status LEDs — not to any XIAO GPIO. No `PG`, `STAT`, `CHRG`, or `VBUS_SENSE` net
     reaches the MCU anywhere in the design. This directly re-confirms (rather than merely
     re-asserting) the prior investigation's conclusion — the hardware genuinely cannot report
     power-source presence to firmware on this board.

  2. LOGIC FLAW in enforceLowBatteryGuard() (original bug, present before this debug session):
     the guard treated a single ambiguous low-voltage reading as proof the device is
     unattended and about to lose power, and committed immediately to an unrecoverable 24h sleep.
     Because m_onBattery can never distinguish "on battery" from "on USB with VBAT coincidentally
     low," this guard fires even on a perfectly safe, continuously-USB-powered board — and did so
     unconditionally on the very first low reading, with no chance for the BQ24070 to recharge the
     cell above threshold before the lockout committed.
fix: |
  Round 1 (averaging + EXT1 wake) was insufficient per user's real-hardware report: VBAT reads
  consistently low across boots even under USB power (not just noise), and the wake-button
  mitigation did not stop the guard from firing in the first place — user still saw immediate 24h
  sleep with no self-recovery.

  Round 2 (this fix) changes the POLICY in epd7in3e/epd7in3e.ino:

  - Added `g_lowBatteryStreak` (RTC_DATA_ATTR int, survives deep sleep, resets to 0 on genuine
    power-on-reset) and `LOW_BATTERY_ESCALATION_THRESHOLD` (config.h, default 4).
  - enforceLowBatteryGuard() no longer commits to 24h sleep on the first low reading. It now:
    - Resets the streak to 0 and returns immediately whenever voltage recovers above threshold
      (or m_onBattery is false).
    - Increments the streak on each low reading.
    - Sleeps only MIN_SLEEP_TIME (900s / 15min, matching the existing failed-download retry
      interval) while streak < LOW_BATTERY_ESCALATION_THRESHOLD, then wakes and re-measures.
    - Escalates to the full 86400s (24h) protective sleep only once
      LOW_BATTERY_ESCALATION_THRESHOLD consecutive independent boots all read low — i.e., only
      once the board has had multiple chances (each ~15 min apart) to prove the low reading isn't
      just USB-recharging-in-progress.
    - EXT1 GPIO wakeup remains armed at every stage (both short-retry and escalated sleep) so the
      wake button always recovers the device immediately regardless of sleep duration.

  This directly addresses the user's real requirement: a board plugged into external power now
  self-recovers within a few short (15 min) cycles as the BQ24070 recharges the cell, instead of
  going dark for 24h on the very first ambiguous reading. A genuinely unattended, disconnected, or
  truly dying battery still receives real 24h protection, just after brief confirmation rather than
  instantly.

  NOTE: A structural fix (only ever entering ANY sleep path when the device can prove it is not on
  external power) remains impossible on this hardware revision without adding a VBUS-sense/PG GPIO
  wire — confirmed unpopulated on the v1.0 schematic — which is a hardware change out of scope for
  firmware. This policy-based escalation is the correct firmware-only mitigation given that
  constraint.
verification: |
  Reviewed applied diff for syntax/type correctness (RTC_DATA_ATTR global scope access from class
  method, uint64_t cast for sleepSeconds * 1000000ULL, LOW_BATTERY_ESCALATION_THRESHOLD comparison
  against int streak) — no arduino-cli available in this sandboxed environment to run a real
  compile check.
  Traced logic against original symptom: VBAT ~2924-2956mV consistently on every boot while
  plugged into power -> guard now sleeps only 15 min per cycle (not 24h) for the first 3
  consecutive low readings, giving the BQ24070 charging path time to raise VBAT above 3050mV
  before any 24h escalation could occur. This should make the board self-recover within
  ~45-60 minutes of being plugged in, rather than appearing bricked for 24h.
  No physical hardware available in this environment; requesting human verification on actual
  board (see checkpoint) — specifically: plug in board, confirm it wakes again after ~15 min
  (not 24h), and confirm voltage/behavior converges to normal operation within a few cycles as
  the battery recharges.

  CONFIRMED ON REAL HARDWARE (2026-07-03): User reports "works now" — board plugged into
  external power no longer appears bricked; escalating-retry policy allows self-recovery within
  short cycles instead of committing to an immediate 24h sleep.
files_changed:
  - epd7in3e/epd7in3e.ino
  - epd7in3e/config.h
