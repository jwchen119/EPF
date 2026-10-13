#ifndef IMPROV_SERIAL_H
#define IMPROV_SERIAL_H

#include <Arduino.h>
#include <functional>
#include <vector>

// A small Improv Serial (https://www.improv-wifi.com/serial/) responder.
//
// Improv is what ESP Web Tools speaks over the USB port right after it
// connects. It asks who the firmware is, so the web installer can recognise
// the frame, offer "Update" instead of "Install" and write the new firmware
// without erasing the flash (and the settings in it). It can also hand over
// Wi-Fi credentials, so a frame is set up from the browser that flashed it
// instead of through the captive portal. Implemented: current state, device
// info, the network scan and Wi-Fi settings; everything else answers
// "unknown command". No URL is ever offered, so the installer shows no
// "Visit device" entry.
class ImprovSerial
{
public:
  enum State : uint8_t
  {
    STATE_READY = 0x02, // "authorized": will accept Wi-Fi settings
    STATE_PROVISIONING = 0x03,
    STATE_PROVISIONED = 0x04,
  };

  // Called with the SSID and password from the installer. Return true to
  // accept them; the caller then reports the outcome with provisioned() or
  // failed().
  typedef std::function<bool(const String &ssid, const String &password)> WifiHandler;

  void begin(Stream &stream, const char *firmwareName, const char *firmwareVersion,
             const char *chipVariant, const char *deviceName);

  void onWifiSettings(WifiHandler handler) { _onWifi = handler; }

  // Feed it whatever has arrived on the stream. Returns true when a complete,
  // valid Improv packet was handled.
  bool poll();

  // Outcome of a Wi-Fi attempt accepted by onWifiSettings
  void provisioned();
  void failed();

  // The frame is on Wi-Fi already (a saved network connected): report so
  void markProvisioned();

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
    CMD_WIFI_SETTINGS = 0x01,
    CMD_GET_CURRENT_STATE = 0x02,
    CMD_GET_DEVICE_INFO = 0x03,
    CMD_GET_WIFI_NETWORKS = 0x04,
  };

  static const uint8_t ERROR_NONE = 0x00;
  static const uint8_t ERROR_INVALID_RPC = 0x01;
  static const uint8_t ERROR_UNKNOWN_COMMAND = 0x02;
  static const uint8_t ERROR_UNABLE_TO_CONNECT = 0x03;

  Stream *_stream = nullptr;
  const char *_firmwareName = "";
  const char *_firmwareVersion = "";
  const char *_chipVariant = "";
  const char *_deviceName = "";
  WifiHandler _onWifi;
  State _state = STATE_READY;

  // Receive buffer: header (6) + version + type + length + data (<=255) + checksum
  uint8_t _buf[6 + 3 + 255 + 1];
  size_t _len = 0;

  void handlePacket(uint8_t type, const uint8_t *data, uint8_t length);
  void handleWifiSettings(const uint8_t *data, uint8_t length);
  void sendNetworks();
  void setState(State state);
  void sendState();
  void sendError(uint8_t error);
  void sendResult(uint8_t command, const std::vector<String> &strings);
  void sendPacket(uint8_t type, const uint8_t *data, uint8_t length);
};

#endif // IMPROV_SERIAL_H
