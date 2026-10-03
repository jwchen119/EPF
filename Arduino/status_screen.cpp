#include "status_screen.h"
#include "fonts/spleen_8x16.h"

// The panel's data stream is row-major, two pixels per byte, left pixel in
// the high nibble -- the same layout the server packs photos in.
static const uint16_t PANEL_W = EPD_WIDTH;
static const uint16_t PANEL_H = EPD_HEIGHT;
static const uint16_t ROW_BYTES = PANEL_W / 2;

void StatusScreen::clear()
{
  _textCount = 0;
  _qrCount = 0;
}

uint16_t StatusScreen::text(uint16_t x, uint16_t y, const char *str, uint8_t scale, uint8_t color)
{
  if (scale == 0)
    scale = 1;
  if (_textCount < MAX_TEXT && y < PANEL_H)
  {
    TextItem &item = _text[_textCount++];
    item.x = x;
    item.y = y;
    item.scale = scale;
    item.color = color;
    strncpy(item.str, str, MAX_LEN);
    item.str[MAX_LEN] = '\0';
  }
  return y + lineHeight(scale);
}

uint16_t StatusScreen::paragraph(uint16_t x, uint16_t y, const char *str, uint16_t maxWidth,
                                 uint8_t scale, uint8_t color)
{
  if (scale == 0)
    scale = 1;
  const uint16_t maxChars = min<uint16_t>(maxWidth / (8 * scale), MAX_LEN);
  if (maxChars == 0)
    return y;

  char line[MAX_LEN + 1];
  uint16_t lineLen = 0;
  const char *p = str;

  while (*p)
  {
    // Next word, including the space that follows it
    const char *wordStart = p;
    while (*p && *p != ' ')
      p++;
    uint16_t wordLen = p - wordStart;
    while (*p == ' ')
      p++;

    if (lineLen > 0 && lineLen + 1 + wordLen > maxChars)
    {
      line[lineLen] = '\0';
      y = text(x, y, line, scale, color);
      lineLen = 0;
    }
    if (lineLen > 0)
      line[lineLen++] = ' ';

    // A single word longer than the line is split rather than dropped
    while (wordLen > 0)
    {
      uint16_t room = maxChars - lineLen;
      if (room == 0)
      {
        line[lineLen] = '\0';
        y = text(x, y, line, scale, color);
        lineLen = 0;
        room = maxChars;
      }
      uint16_t take = min<uint16_t>(room, wordLen);
      memcpy(line + lineLen, wordStart, take);
      lineLen += take;
      wordStart += take;
      wordLen -= take;
    }
  }
  if (lineLen > 0)
  {
    line[lineLen] = '\0';
    y = text(x, y, line, scale, color);
  }
  return y;
}

uint16_t StatusScreen::qr(uint16_t x, uint16_t y, const char *content, uint8_t modulePx)
{
  if (_qrCount >= MAX_QR || modulePx == 0)
    return 0;
  QrItem &item = _qr[_qrCount];
  if (qrcode_initText(&item.code, item.modules, QR_VERSION, ECC_LOW, content) != 0)
    return 0;
  item.x = x;
  item.y = y;
  item.modulePx = modulePx;
  _qrCount++;
  return item.code.size * modulePx;
}

void StatusScreen::setPixel(uint8_t *row, uint16_t x, uint8_t color)
{
  if (x >= PANEL_W)
    return;
  uint8_t &b = row[x >> 1];
  if (x & 1)
    b = (b & 0xF0) | (color & 0x0F);
  else
    b = (b & 0x0F) | (color << 4);
}

void StatusScreen::renderRow(uint16_t y, uint8_t *row)
{
  memset(row, (EPD_7IN3E_WHITE << 4) | EPD_7IN3E_WHITE, ROW_BYTES);

  for (uint8_t t = 0; t < _textCount; t++)
  {
    const TextItem &item = _text[t];
    const uint16_t h = lineHeight(item.scale);
    if (y < item.y || y >= item.y + h)
      continue;
    const uint8_t glyphRow = (y - item.y) / item.scale;
    uint16_t px = item.x;
    for (const char *c = item.str; *c && px < PANEL_W; c++)
    {
      uint8_t ch = (uint8_t)*c;
      if (ch < SPLEEN_8X16_FIRST || ch > SPLEEN_8X16_LAST)
        ch = '?';
      const uint8_t bits = pgm_read_byte(&SPLEEN_8X16[ch - SPLEEN_8X16_FIRST][glyphRow]);
      for (uint8_t bit = 0; bit < 8; bit++)
      {
        if (bits & (0x80 >> bit))
        {
          for (uint8_t s = 0; s < item.scale; s++)
            setPixel(row, px + bit * item.scale + s, item.color);
        }
      }
      px += 8 * item.scale;
    }
  }

  for (uint8_t q = 0; q < _qrCount; q++)
  {
    QrItem &item = _qr[q];
    const uint16_t side = item.code.size * item.modulePx;
    if (y < item.y || y >= item.y + side)
      continue;
    const uint8_t my = (y - item.y) / item.modulePx;
    for (uint8_t mx = 0; mx < item.code.size; mx++)
    {
      if (!qrcode_getModule(&item.code, mx, my))
        continue;
      const uint16_t px = item.x + mx * item.modulePx;
      for (uint8_t s = 0; s < item.modulePx; s++)
        setPixel(row, px + s, EPD_7IN3E_BLACK);
    }
  }
}

void StatusScreen::show()
{
  uint8_t row[ROW_BYTES];
  unsigned long started = millis();
  _epd.SendCommand(0x10);
  for (uint16_t y = 0; y < PANEL_H; y++)
  {
    renderRow(y, row);
    for (uint16_t i = 0; i < ROW_BYTES; i++)
      _epd.SendData(row[i]);
  }
  unsigned long streamed = millis();
  Serial.printf("[screen] %u text, %u QR items streamed in %lu ms, refreshing...\n",
                _textCount, _qrCount, streamed - started);
  _epd.TurnOnDisplay();
  Serial.printf("[screen] panel refresh took %lu ms\n", millis() - streamed);
}
