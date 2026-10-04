#ifndef IMPROV_SERIAL_H
#define IMPROV_SERIAL_H

#include <Arduino.h>
#include <vector>

// A minimal Improv Serial (https://www.improv-wifi.com/serial/) responder.
//
// Improv is what ESP Web Tools speaks over the USB port right after it
// connects: it asks who the firmware is, so the web installer can recognise
// the frame, offer "Update" instead of "Install" and write the new firmware
// without erasing the flash (and the settings in it). Only the identification
// part is implemented: current state and device info. Wi-Fi provisioning,
// which Improv is really for, is deliberately not supported here -- the frame
// is set up through its own captive portal -- so those commands get "unknown
// command".
class ImprovSerial
{
public:
  void begin(Stream &stream, const char *firmwareName, const char *firmwareVersion,
             const char *chipVariant, const char *deviceName);

  // Feed it whatever has arrived on the stream. Returns true when a complete,
  // valid Improv packet was handled.
  bool poll();

private:
  enum PacketType : uint8_t
  {
    TYPE_CURRENT_STATE = 0x01,
    TYPE_ERROR_STATE = 0x02,
    TYPE_RPC_COMMAND = 0x03,
    TYPE_RPC_RESULT = 0x04,
  };

  enum Command : uint8_t
  {
    CMD_GET_CURRENT_STATE = 0x02,
    CMD_GET_DEVICE_INFO = 0x03,
  };

  // Reported as "provisioned": the frame manages its own Wi-Fi
  static const uint8_t STATE_PROVISIONED = 0x04;
  static const uint8_t ERROR_NONE = 0x00;
  static const uint8_t ERROR_INVALID_RPC = 0x01;
  static const uint8_t ERROR_UNKNOWN_COMMAND = 0x02;

  Stream *_stream = nullptr;
  const char *_firmwareName = "";
  const char *_firmwareVersion = "";
  const char *_chipVariant = "";
  const char *_deviceName = "";

  // Receive buffer: header (6) + version + type + length + data (<=255) + checksum
  uint8_t _buf[6 + 3 + 255 + 1];
  size_t _len = 0;

  void handlePacket(uint8_t type, const uint8_t *data, uint8_t length);
  void sendError(uint8_t error);
  void sendResult(uint8_t command, const std::vector<String> &strings);
  void sendPacket(uint8_t type, const uint8_t *data, uint8_t length);
};

#endif // IMPROV_SERIAL_H
