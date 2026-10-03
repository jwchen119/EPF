#ifndef STATUS_SCREEN_H
#define STATUS_SCREEN_H

#include <Arduino.h>
#include <qrcode.h>
#include "epd7in3e.h"

// Text and QR codes drawn straight into the panel's data stream.
//
// The panel takes 800x480 pixels at 4 bits each, which would be a 192 KB
// framebuffer. Instead the screen is composed as a short list of items and
// rendered one row (400 bytes) at a time while the bytes are sent, so it costs
// no more RAM than the photo download does. Every show() is a full refresh,
// the same 15-25 seconds as a photo: callers must decide *whether* to draw,
// not just what.
class StatusScreen
{
public:
  static const uint8_t MAX_TEXT = 16;
  static const uint8_t MAX_QR = 2;
  static const uint8_t MAX_LEN = 80; // characters kept per text item

  // QR version 4 is 33x33 modules and holds 78 bytes at ECC_LOW, enough for
  // the Wi-Fi join string and the portal URL.
  static const uint8_t QR_VERSION = 4;
  static const uint8_t QR_SIZE = 4 * QR_VERSION + 17;

  explicit StatusScreen(Epd &epd) : _epd(epd), _textCount(0), _qrCount(0) {}

  void clear();

  // One line of text in the 8x16 font scaled up by `scale`. Returns the y
  // just below the line. Text past the right edge is clipped.
  uint16_t text(uint16_t x, uint16_t y, const char *str, uint8_t scale = 2,
                uint8_t color = EPD_7IN3E_BLACK);

  // Word-wrapped text no wider than maxWidth pixels. Returns the y below the
  // last line.
  uint16_t paragraph(uint16_t x, uint16_t y, const char *str, uint16_t maxWidth,
                     uint8_t scale = 2, uint8_t color = EPD_7IN3E_BLACK);

  // A QR code of `content` with modulePx pixels per module. Returns the side
  // length in pixels, or 0 if the content did not fit or no slot was free.
  uint16_t qr(uint16_t x, uint16_t y, const char *content, uint8_t modulePx);

  static uint16_t textWidth(const char *str, uint8_t scale)
  {
    return strlen(str) * 8 * scale;
  }
  static uint16_t lineHeight(uint8_t scale) { return 16 * scale; }

  // Streams the composed screen to the panel and triggers the refresh. The
  // panel is left powered; the caller puts it to sleep.
  void show();

private:
  struct TextItem
  {
    uint16_t x, y;
    uint8_t scale, color;
    char str[MAX_LEN + 1];
  };

  struct QrItem
  {
    uint16_t x, y;
    uint8_t modulePx;
    QRCode code;
    uint8_t modules[(QR_SIZE * QR_SIZE + 7) / 8];
  };

  Epd &_epd;
  TextItem _text[MAX_TEXT];
  uint8_t _textCount;
  QrItem _qr[MAX_QR];
  uint8_t _qrCount;

  void renderRow(uint16_t y, uint8_t *row);
  static void setPixel(uint8_t *row, uint16_t x, uint8_t color);
};

#endif // STATUS_SCREEN_H
