/**
 * epd7in3e.h
 * EE02 HAT + XIAO ESP32-S3 Plus + Seeed 13.3 inch Color Eink (T133A01)
 *
 * Defines resolution and color constants for the T133A01 display.
 * T133A01 4bpp color nibble codes — different from WaveShare UC8179 family.
 *
 * Source: Seeed_GFX TFT_Drivers/T133A01_Defines.h and
 *         examples/reTerminal_E1004_SDcard_Color6/dither.cpp (PAL_E6 / kE6Rgb table)
 */

#ifndef __EPD_7IN3E_H__
#define __EPD_7IN3E_H__

#include "epdif.h"

// Display resolution — T133A01 portrait-native
#define EPD_WIDTH  1200
#define EPD_HEIGHT 1600

// Type aliases (Arduino-style)
#define UWORD   unsigned int
#define UBYTE   unsigned char
#define UDOUBLE unsigned long

/**
 * T133A01 4bpp color nibble codes.
 * These are the raw nibble values sent over SPI — NOT sequential indices.
 * T133A01 4bpp color nibble codes — different from WaveShare UC8179 family:
 *   WaveShare UC8179: BLACK=0x0, WHITE=0x1, GREEN=0x2, BLUE=0x3, RED=0x4, YELLOW=0x5
 *   T133A01:          WHITE=0x0, GREEN=0x2, RED=0x6, YELLOW=0xB, BLUE=0xD, BLACK=0xF
 */
#define EPD_7IN3E_WHITE  0x0
#define EPD_7IN3E_GREEN  0x2
#define EPD_7IN3E_RED    0x6
#define EPD_7IN3E_YELLOW 0xB
#define EPD_7IN3E_BLUE   0xD
#define EPD_7IN3E_BLACK  0xF

#endif /* __EPD_7IN3E_H__ */
