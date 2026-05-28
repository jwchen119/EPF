/**
 * epdif.h
 * EE02 HAT + XIAO ESP32-S3 Plus + Seeed 13.3 inch Color Eink (T133A01)
 *
 * Replaces WaveShare EpdIf class with flat pin constants for the EE02 board.
 * All SPI setup is delegated to Seeed_GFX (TFT_eSPI back-end).
 */

#ifndef EPDIF_H
#define EPDIF_H

// EE02 board pin assignments for XIAO ESP32-S3 Plus
// Source: Seeed_GFX User_Setups/EPaper_Board_Pins_Setups.h
//         USE_XIAO_EPAPER_DISPLAY_BOARD_EE02 section
#define BUSY_PIN  5   // GPIO5  — D3 on XIAO header
#define RST_PIN   38  // GPIO38 — internal, wired on EE02 board (not on header)
#define DC_PIN    10  // GPIO10 — Data/Command
#define CS_PIN    44  // GPIO44 — primary chip-select (D7 mapping)
#define CS1_PIN   41  // GPIO41 — secondary chip-select (second driver IC on 13.3" panel)

#endif /* EPDIF_H */
