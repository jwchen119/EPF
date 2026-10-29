#ifndef WiFiCaptive_h
#define WiFiCaptive_h

#include <Arduino.h>
#include <AsyncTCP.h> //https://github.com/ESP32Async/AsyncTCP using the latest dev version from @ESP32Async
#include <DNSServer.h>
#include <ESPAsyncWebServer.h> //https://github.com/ESP32Async/ESPAsyncWebServer using the latest dev version from @ESP32Async
#include <esp_wifi.h>          //Used for mpdu_rx_disable android workaround
#include <WiFi.h>
#include <AsyncJson.h>
#include "Preferences.h"
#include "WifiCaptivePage.h"
#include <ArduinoJson.h>
#include <functional>
// #include <ArduinoLog.h>

#define WIFI_SSID "ESP32_ePAPER"
#define WIFI_PASSWORD NULL

// Define the DNS interval in milliseconds between processing DNS requests
#define DNS_INTERVAL 60
// Define the maximum number of clients that can connect to the server
#define MAX_CLIENTS 1
// Define the WiFi channel to be used (channel 6 in this case)
#define WIFI_CHANNEL 6
// Define the maximum number of possible saved credentials
#define WIFI_MAX_SAVED_CREDS 5
// Define the maximum number of connection attempts
#define WIFI_CONNECTION_ATTEMPTS 3
// Define max connection timeout
#define CONNECTION_TIMEOUT 15000
// An attempt ends once the driver has looked for the network this many times
// without finding it (each scan takes ~2.5 s, so about 5 s), instead of after
// the whole CONNECTION_TIMEOUT. Decided right after a scan has failed, so it
// never cuts off a connection that a scan has just found.
#define NO_AP_SCANS 2
// How long the portal stays up after connecting, so the page can read the outcome
#define RESULT_LINGER_MS 3000
// Local IP URL
#define LocalIPURL "http://4.3.2.1"

#define WIFI_SSID_KEY(i) ("wifi_" + String(i) + "_ssid").c_str()
#define WIFI_PSWD_KEY(i) ("wifi_" + String(i) + "_pswd").c_str()

#define WIFI_LAST_INDEX "wifi_last_index"

class WifiCaptive
{
private:
    struct WifiCredentials
    {
        String ssid;
        String pswd;
    };
    struct Network
    {
        String ssid;
        int32_t rssi;
        bool open;
        bool saved;
    };

    DNSServer *_dnsServer;
    AsyncWebServer *_server;
    String _ssid = "";
    String _password = "";
    String _api_server = "";

    std::function<void()> _resetcallback;
    // Called on every pass of the portal loop and of the connection wait, so
    // the sketch can keep answering the USB installer (improv_serial.*)
    std::function<void()> _idleCallback;
    // Called with the outcome of each connection attempt the portal makes
    std::function<void(bool connected)> _connectResultCallback;
    bool _portalRunning = false;
    // Scans in this attempt that did not find the network, reset when it
    // associates; lets waitForConnectResult() give up after NO_AP_SCANS
    volatile uint8_t _apMissedScans = 0;
    bool _eventsHooked = false;
    // How the last connection attempt went, polled by the page (/result);
    // written by the portal loop, read by the web server's task
    enum PortalResult : uint8_t
    {
        RESULT_IDLE,
        RESULT_CONNECTING,
        RESULT_FAILED,
        RESULT_CONNECTED
    };
    volatile PortalResult _portalResult = RESULT_IDLE;

    WifiCredentials _savedWifis[WIFI_MAX_SAVED_CREDS];

    void setUpDNSServer(DNSServer &dnsServer, const IPAddress &localIP);
    void setUpWebserver(AsyncWebServer &server, const IPAddress &localIP);
    uint8_t connect(String ssid, String pass);
    uint8_t waitForConnectResult(uint32_t timeout);
    uint8_t waitForConnectResult();
    void readWifiCredentials();
    void saveWifiCredentials(String ssid, String pass, String url);
    void saveLastUsedWifiIndex(int index);
    int readLastUsedWifiIndex();
    // void saveApiServer(String url);
    std::vector<WifiCredentials> matchNetworks(std::vector<Network> &scanResults, WifiCaptive::WifiCredentials wifiCredentials[]);
    std::vector<Network> getScannedUniqueNetworks(bool runScan);
    std::vector<Network> combineNetworks(std::vector<Network> &scanResults, WifiCaptive::WifiCredentials wifiCredentials[]);

public:
    /// @brief Starts WiFi configuration portal. A failed attempt keeps it
    /// running, so the page or the installer can try again.
    /// @return True if successfully connected to provided SSID, false otherwise.
    bool startPortal();

    /// @brief Checks if any ssid is saved
    /// @return True if any ssis is saved, false otherwise
    bool isSaved();

    /// @brief Resets all saved credentials
    void resetSettings();

    /// @brief sets the function callback that is triggered when uses performs soft reset
    /// @param func reset callback
    void setResetSettingsCallback(std::function<void()> func);

    /// @brief Connects to the saved SSID with the best signal strength
    /// @return True if successfully connected to saved SSID, false otherwise.
    bool autoConnect();
    /// @brief Called on every pass of the portal loop and connection wait
    void setIdleCallback(std::function<void()> func);
    /// @brief Called with the outcome of each connection attempt made by the portal
    void setConnectResultCallback(std::function<void(bool connected)> func);
    /// @brief Hands the portal credentials from elsewhere (Improv over USB). The
    /// portal loop connects with them as if the page had submitted them, and keeps
    /// running if they fail; the saved server URL is kept.
    void provision(const String &ssid, const String &password);
    /// @brief True while startPortal() is waiting for credentials
    bool isPortalRunning() { return _portalRunning; }
    /// @brief Stores a network as the one to try first, without connecting; the
    /// saved server URL is kept. For Improv requests outside the portal.
    void saveNetwork(const String &ssid, const String &password);
    /// @brief Connects to a network without saving it; true when connected
    bool tryNetwork(const String &ssid, const String &password);
};

extern WifiCaptive WifiCaptivePortal;

#endif