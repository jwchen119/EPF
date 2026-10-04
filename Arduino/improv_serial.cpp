#include "improv_serial.h"

static const uint8_t IMPROV_HEADER[6] = {'I', 'M', 'P', 'R', 'O', 'V'};
static const uint8_t IMPROV_VERSION = 0x01;

void ImprovSerial::begin(Stream &stream, const char *firmwareName, const char *firmwareVersion,
                         const char *chipVariant, const char *deviceName)
{
  _stream = &stream;
  _firmwareName = firmwareName;
  _firmwareVersion = firmwareVersion;
  _chipVariant = chipVariant;
  _deviceName = deviceName;
  _len = 0;
}

bool ImprovSerial::poll()
{
  if (!_stream)
    return false;
  bool handled = false;
  while (_stream->available() > 0)
  {
    uint8_t c = (uint8_t)_stream->read();

    // Hunt for the header byte by byte so stray input does not confuse the parser
    if (_len < sizeof(IMPROV_HEADER))
    {
      if (c == IMPROV_HEADER[_len])
        _buf[_len++] = c;
      else
        _len = (c == IMPROV_HEADER[0]) ? 1 : 0;
      continue;
    }

    _buf[_len++] = c;
    if (_len < 9)
      continue; // version, type and length not all in yet

    const uint8_t length = _buf[8];
    const size_t total = 9 + length + 1;
    if (_len < total)
      continue;

    // Whole packet: check version and checksum (sum of every byte before it)
    uint8_t sum = 0;
    for (size_t i = 0; i < total - 1; i++)
      sum += _buf[i];
    if (_buf[6] == IMPROV_VERSION && sum == _buf[total - 1])
    {
      handlePacket(_buf[7], _buf + 9, length);
      handled = true;
    }
    else
    {
      sendError(ERROR_INVALID_RPC);
    }
    _len = 0;
  }
  return handled;
}

void ImprovSerial::handlePacket(uint8_t type, const uint8_t *data, uint8_t length)
{
  // Only RPC commands come our way; they carry command id and data length
  if (type != TYPE_RPC_COMMAND || length < 2)
  {
    sendError(ERROR_INVALID_RPC);
    return;
  }

  // Every command clears the previous error, as the spec asks
  sendError(ERROR_NONE);

  switch (data[0])
  {
  case CMD_GET_CURRENT_STATE:
  {
    uint8_t state = STATE_PROVISIONED;
    sendPacket(TYPE_CURRENT_STATE, &state, 1);
    // No URL in the result: nothing for the installer's "Visit device"
    sendResult(CMD_GET_CURRENT_STATE, {});
    break;
  }

  case CMD_GET_DEVICE_INFO:
    sendResult(CMD_GET_DEVICE_INFO, {_firmwareName, _firmwareVersion, _chipVariant, _deviceName});
    break;

  default:
    sendError(ERROR_UNKNOWN_COMMAND);
    break;
  }
}

void ImprovSerial::sendError(uint8_t error)
{
  sendPacket(TYPE_ERROR_STATE, &error, 1);
}

void ImprovSerial::sendResult(uint8_t command, const std::vector<String> &strings)
{
  // command, data length, then each string as length + bytes
  std::vector<uint8_t> data;
  data.push_back(command);
  data.push_back(0);
  for (const String &s : strings)
  {
    size_t n = s.length();
    if (n > 255)
      n = 255;
    data.push_back((uint8_t)n);
    data.insert(data.end(), s.c_str(), s.c_str() + n);
  }
  if (data.size() - 2 > 255)
    return; // would not fit one packet
  data[1] = (uint8_t)(data.size() - 2);
  sendPacket(TYPE_RPC_RESULT, data.data(), (uint8_t)data.size());
}

void ImprovSerial::sendPacket(uint8_t type, const uint8_t *data, uint8_t length)
{
  if (!_stream)
    return;
  uint8_t out[6 + 3 + 255 + 1];
  size_t n = 0;
  memcpy(out, IMPROV_HEADER, 6);
  n = 6;
  out[n++] = IMPROV_VERSION;
  out[n++] = type;
  out[n++] = length;
  memcpy(out + n, data, length);
  n += length;
  uint8_t sum = 0;
  for (size_t i = 0; i < n; i++)
    sum += out[i];
  out[n++] = sum;
  // The installer's parser works line by line and drops anything that does
  // not start with the header, so a packet must begin on a fresh line: debug
  // output may have left one half written.
  _stream->write('\n');
  _stream->write(out, n);
  _stream->write('\n');
  _stream->flush();
}
