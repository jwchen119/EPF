# Phase 4: Battery Voltage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 04-battery-voltage
**Areas discussed:** LED identification, USB vs battery behavior, Low battery response

---

## LED Identification

| Option | Description | Selected |
|--------|-------------|----------|
| The orange/green charge LED (TP4054 charger IC) | Rapidly blinks when no battery; may be controllable via CHG pin if wired to GPIO | ✓ |
| The yellow user LED (GPIO21) | Built-in LED on GPIO21 — fully software-controllable | |
| Not sure — let researcher decide | Researcher finds from schematic | |

**User's choice:** The orange/green charge LED from the TP4054 charger IC

**Follow-up — LED software control:**

| Option | Description | Selected |
|--------|-------------|----------|
| Don't know — let researcher find from schematic | Researcher checks Seeed schematic for CHG pin wiring | ✓ |
| Hardware-only (no GPIO control) | TP4054 drives it directly | |
| There is a GPIO for it | User confirmed from schematic | |

**User's choice:** Researcher should determine from schematic

---

## USB vs Battery Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — stay awake on USB, sleep only on battery | Deep sleep skipped when USB-powered; easier development | ✓ |
| Sleep regardless of power source | Same behavior everywhere — simpler code | |

**User's choice:** Skip deep sleep on USB

**Follow-up — what to do after displaying on USB:**

| Option | Description | Selected |
|--------|-------------|----------|
| Wait a fixed interval, then refresh again | Use server-specified sleep duration, then loop | ✓ |
| Restart immediately (ESP.restart()) | Begin cycle again without sleeping | |
| Halt — show image and stop | Idle loop, manual reset to refresh | |

**User's choice:** Wait the server-specified interval, then refresh again

---

## Low Battery Response

| Option | Description | Selected |
|--------|-------------|----------|
| Keep original: sleep 24h when < 3.05V | Simple and proven; device wakes to check recovery | ✓ |
| Change threshold or sleep duration | Different cutoff or wake interval | |

**User's choice:** Keep original — 24h sleep when voltage < 3050 mV

---

## Claude's Discretion

- Exact ADC GPIO pin for battery voltage (researcher verifies from schematic — user explicitly skipped this gray area)
- ADC attenuation settings
- USB idle loop implementation details
- Whether averaged or single ADC read is used for low-voltage guard

## Deferred Ideas

None.
