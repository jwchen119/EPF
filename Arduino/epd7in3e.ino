#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include "epd7in3e.h"
#include "FS.h"
#include <ArduinoJson.h>
// #include "SimpleWiFiManager.h"
#include <WiFiClientSecure.h>
#include "driver/rtc_io.h"
#include "config.h"
#include "button.h"
#include <Preferences.h>
#include <WifiCaptive.h>
#include <filesystem.h>
#include "nfc_writer.h"
#include "status_screen.h"

/* Pin Layout Description - P1
E-PAPER DRIVER BOARD  <>  FireBeetle ESP32-C6
BUSY                  <>  18  // E-paper busy signal input
RST                   <>  14  // E-paper reset control
DC                    <>  8   // Data/Command control
CS                    <>  1   // Chip select control
SCLK                  <>  23  // SPI clock
DIN                   <>  22  // SPI data input
GND                   <>  GND // Ground
VCC                   <>  3V3 // Power supply
SETTING               <>  2   // Configuration mode trigger pin
*/

/* Pin Layout Description - P2
ST25DV16 NFC/RFID TAG IC  <>  FireBeetle ESP32-C6
VIN                       <>  3V3  // Power supply
GND                       <>  GND  // Ground
SCL                       <>  20   // Data/Command control
SDA                       <>  19   // Chip select control
*/

Preferences preferences;

class EpaperManager
{
private:
  // SimpleWiFiManager wifiManager;
  Epd epd;
  NfcWriter nfcWriter;
  StatusScreen screen{epd};
  String imageUrl = "";
  String failReason = ""; // why this wake-up produced no photo, for the error screen
  int batteryMv = 0;      // measured once per wake-up in checkVoltage()

  bool downloadImage()
  {
    // preferences.begin("data, true");
    imageUrl = preferences.getString("SERVER_BASE_URL");
    Serial.print("nas url: ");
    Serial.println(imageUrl);
    bool isHttps = imageUrl.startsWith("https://");
    WiFiClient *basicClient = nullptr;
    WiFiClientSecure *secureClient = nullptr;
    HTTPClient http;
    HTTPClient sleepHttp; // New HTTP client for sleep request
    http.setTimeout(HTTP_TIMEOUT);

    // Parse base URL for sleep request
    String baseUrl = imageUrl;
    const char *downloadPath = "/download";
    const char *sleepPath = "/sleep";
    // int downloadPos = baseUrl.lastIndexOf(downloadPath);
    // if (downloadPos != -1) {
    //   baseUrl = baseUrl.substring(0, downloadPos);
    // }
    String sleepUrl = baseUrl + sleepPath;

    // Setup client for image download
    if (isHttps)
    {
      secureClient = new WiFiClientSecure;
      secureClient->setInsecure();
      if (!http.begin(*secureClient, imageUrl + downloadPath))
      {
        Serial.println("Failed to initialize HTTPS connection");
        failReason = "Could not start the HTTPS client";
        delete secureClient;
        return false;
      }
    }
    else
    {
      basicClient = new WiFiClient;
      if (!http.begin(*basicClient, imageUrl + downloadPath))
      {
        Serial.println("Failed to initialize HTTP connection");
        failReason = "Could not start the HTTP client";
        delete basicClient;
        return false;
      }
    }

    // Battery voltage (millivolts) measured in checkVoltage() at boot
    http.addHeader("batteryCap", String(batteryMv));

    // Collect response headers for NFC photo URL
    const char *headerKeys[] = {NFC_PHOTO_URL_HEADER};
    http.collectHeaders(headerKeys, 1);

    // Download and process image
    bool success = false;
    int sleepDuration = 0;
    String photoUrl = "";

    // A 500 from the server, or a 202 while it is still processing, is retried
    // up to MAX_RETRIES times; any other failure gives up straight away.
    int httpCode = 0;
    for (uint8_t i = 0; i < MAX_RETRIES && !success; i++)
    {
      httpCode = http.GET();

      if (httpCode == HTTP_CODE_OK)
      {
        // Read photo URL from response header before consuming stream
        photoUrl = http.header(NFC_PHOTO_URL_HEADER);
        if (!photoUrl.isEmpty())
        {
          Serial.print(F("Photo URL from header: "));
          Serial.println(photoUrl);
          // Write NFC immediately so the tag is up-to-date before image processing
          nfcWriter.writePhotoUri(photoUrl);
          // nfcWriter.writePhotoUri("https://my.immich.app/albums/867e4d0a-8d36-4229-a0ed-ff9a3721e9f7/photos/ad80ae48-1a9d-42b0-8aae-eeeed255de5e");
        }
        else
        {
          Serial.println(F("Warning: X-Photo-Url header empty or not received"));
        }

        success = processImageData(&http);

        // After successful image download, get sleep duration
        if (success)
        {
          // Setup new client for sleep request
          WiFiClient *sleepBasicClient = nullptr;
          WiFiClientSecure *sleepSecureClient = nullptr;

          if (isHttps)
          {
            sleepSecureClient = new WiFiClientSecure;
            sleepSecureClient->setInsecure();
            sleepHttp.begin(*sleepSecureClient, sleepUrl);
          }
          else
          {
            sleepBasicClient = new WiFiClient;
            sleepHttp.begin(*sleepBasicClient, sleepUrl);
          }

          sleepHttp.addHeader("Accept", "application/json");
          int sleepHttpCode = sleepHttp.GET();

          if (sleepHttpCode == HTTP_CODE_OK)
          {
            String payload = sleepHttp.getString();
            // StaticJsonDocument<200> doc;
            JsonDocument doc;
            DeserializationError error = deserializeJson(doc, payload);

            if (!error)
            {
              sleepDuration = doc["sleep_duration"] | 0;
              if (sleepDuration > 0)
              {
                sleepDuration /= 1000; // Convert to seconds
              }
            }
          }

          sleepHttp.end();
          if (sleepSecureClient)
            delete sleepSecureClient;
          if (sleepBasicClient)
            delete sleepBasicClient;
        }
        break;
      }
      else if (httpCode == HTTP_CODE_ACCEPTED)
      {
        Serial.println("Server processing, waiting...");
        delay(RETRY_DELAY);
      }
      else if (httpCode == HTTP_CODE_INTERNAL_SERVER_ERROR)
      {
        Serial.printf("Server error (500), retry %u of %u...\n", i + 1, MAX_RETRIES);
        delay(RETRY_DELAY);
      }
      else
      {
        Serial.printf("%s GET failed: %s\n",
                      isHttps ? "HTTPS" : "HTTP",
                      http.errorToString(httpCode).c_str());
        break;
      }
    }

    if (!success)
    {
      if (httpCode == HTTP_CODE_OK)
        failReason = "The server answered, but the image data was incomplete or invalid";
      else if (httpCode > 0)
        failReason = "Server returned HTTP " + String(httpCode);
      else
        failReason = "Could not reach the server: " + http.errorToString(httpCode);
    }

    http.end();
    delay(10);
    if (secureClient)
      delete secureClient;
    if (basicClient)
      delete basicClient;

    if (success)
    {
      // A new photo is on the panel, so the failure count starts over. Follow
      // the server's schedule; if /sleep did not answer, fall back to the
      // default interval rather than losing a day.
      preferences.putUChar(PREFERENCES_CONNECT_API_RETRY_COUNT, 0);
      hibernate(sleepDuration > 0 ? sleepDuration : SLEEP_INTERVAL);
    }

    // Failed: the caller counts it and decides how long to sleep
    return false;
  }

  // check if https
  bool startsWith(const String &str, const char *prefix)
  {
    return str.substring(0, strlen(prefix)).equalsIgnoreCase(prefix);
  }

  // Checks if character is a valid delimiter in image data
  bool isDelimiter(char c)
  {
    return c == ',' || c == '\n' || c == '\r' || c == '\0';
  }

  // Process image data stream and update display
  bool processImageData(HTTPClient *http)
  {
    WiFiClient *stream = http->getStreamPtr();
    int contentLength = http->getSize();

    // Validate content length
    if (contentLength <= 0)
    {
      Serial.println("Invalid content length");
      return false;
    }
    Serial.printf("Content-Length: %d bytes\n", contentLength);
    Serial.println("Starting direct image processing...");

    epd.SendCommand(0x10);

    uint8_t *buffer = (uint8_t *)malloc(BUFFER_SIZE);
    if (buffer == NULL)
    {
      Serial.println("Buffer allocation failed");
      return false;
    }

    // The body is C-array text: "XX,XX,..." terminated by "};". Each hex pair
    // is decoded nibble by nibble as it streams past; anything that is not a
    // hex digit ends the current byte.
    uint8_t value = 0;
    uint8_t digits = 0;
    int totalBytesProcessed = 0;
    unsigned long started = millis();
    unsigned long firstData = 0;

    while (contentLength > 0 && http->connected())
    {
      // BUFFER_SIZE, not sizeof(buffer): buffer is a pointer, so sizeof() gave
      // 4 and the whole body was read four bytes at a time.
      int bytesToRead = min(contentLength, (int)BUFFER_SIZE);
      int bytesRead = stream->readBytes(buffer, bytesToRead);

      if (bytesRead > 0)
      {
        if (firstData == 0)
          firstData = millis();
        for (int i = 0; i < bytesRead; i++)
        {
          char c = (char)buffer[i];
          int8_t nibble = -1;
          if (c >= '0' && c <= '9')
            nibble = c - '0';
          else if (c >= 'a' && c <= 'f')
            nibble = c - 'a' + 10;
          else if (c >= 'A' && c <= 'F')
            nibble = c - 'A' + 10;

          if (nibble >= 0)
          {
            value = (value << 4) | nibble;
            digits++;
          }
          else if (digits > 0)
          {
            epd.SendData(value);
            value = 0;
            digits = 0;
          }
        }

        totalBytesProcessed += bytesRead;
        contentLength -= bytesRead;
      }
      else
      {
        if (!http->connected())
        {
          Serial.println("HTTP connection lost!");
          free(buffer);
          return false;
        }
        delay(10);
      }
    }

    if (digits > 0)
    {
      epd.SendData(value);
    }

    free(buffer);
    Serial.printf("[image] %d bytes of text received in %lu ms (first data after %lu ms), refreshing...\n",
                  totalBytesProcessed, millis() - started, firstData ? firstData - started : 0);
    unsigned long refreshStart = millis();
    epd.TurnOnDisplay();
    Serial.printf("[image] panel refresh took %lu ms\n", millis() - refreshStart);
    epd.Sleep();

    return true;
  }

  // Enter deep sleep mode with calculated wake-up interval
  void hibernate(int sleepDuration = 0)
  {
    Serial.println("Preparing for deep sleep...");

    // Use the provided duration, or the default interval when none was given
    int sleep_interval = sleepDuration > 0 ? sleepDuration : SLEEP_INTERVAL;

    // Cut NFC module power before sleep (GPIO held LOW during deep sleep)
    nfcWriter.powerOff();

    // Disconnect WiFi and turn off radio
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    fs_deinit();
    delay(50);
    // Print sleep duration for debugging
    Serial.printf("Sleep interval: %d seconds\n", sleep_interval);

    // Convert sleep time to microseconds
    uint64_t sleep_time = static_cast<uint64_t>(sleep_interval) * 1000000ULL;

    Serial.printf("Sleep time in microseconds: %llu\n", sleep_time);

    // Configure wake up sources
    esp_sleep_enable_timer_wakeup(sleep_time);

    // Configure GPIO wake up
    rtc_gpio_init(WAKEUP_PIN);
    rtc_gpio_set_direction(WAKEUP_PIN, RTC_GPIO_MODE_INPUT_ONLY);
    rtc_gpio_pullup_en(WAKEUP_PIN);
    rtc_gpio_pulldown_dis(WAKEUP_PIN);
    esp_sleep_enable_ext1_wakeup(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW);

    // Wait for serial output to complete
    Serial.println("Entering deep sleep mode...");
    Serial.flush();

    // Add delay before sleep
    delay(50);

    // Enter deep sleep
    esp_deep_sleep_start();
  }

  static void resetDeviceCredentials(void)
  {
    WifiCaptivePortal.resetSettings();
    bool res = preferences.clear();
    preferences.end();
    ESP.restart();
  }

  // Check if configuration mode should be entered
  bool shouldEnterConfigMode()
  {
    // Check configuration pin with debounce
    // if (digitalRead(CONFIG_PIN) == LOW) {
    //   delay(BUTTON_DEBOUNCE);
    //   return digitalRead(CONFIG_PIN) == LOW;
    // }
    // return false;
    Button button(CONFIG_PIN);
    return button.result();
  }

public:
  // False when the timer woke us. Errors are then kept off the panel until
  // the quiet retries are used up; see failAndSleep().
  bool manualWake = true;

  bool begin()
  {
    // Serial.begin() moved to the top of setup() so early diagnostics are not dropped
    delay(50);

    // Release RTC GPIO hold from previous deep sleep so we can re-control pins
    rtc_gpio_hold_dis(static_cast<gpio_num_t>(NFC_POWER_PIN));

    pinMode(CONFIG_PIN, INPUT_PULLUP);

    // Initialize NFC first and write placeholder to prevent stale URL reads
    if (!nfcWriter.begin())
    {
      Serial.println(F("NFC init failed, NFC writes will be skipped"));
    }
    else
    {
      nfcWriter.writePlaceholder();
    }

    // Preferences first: failAndSleep() needs them even if the panel fails
    preferences.begin("data", false);

    if (epd.Init() != 0)
    {
      Serial.println(F("e-Paper init failed"));
      failReason = "The e-Paper panel did not respond";
      return false;
    }
    Serial.println(F("e-Paper initialized successfully"));

    // initialize spiffs
    fs_init();

    WiFi.mode(WIFI_STA);

    // Check configuration button
    if (shouldEnterConfigMode())
    {
      Serial.println(F("Config button pressed, entering config mode..."));
      showSetupScreen();

      bool res = WifiCaptivePortal.startPortal();
      if (res)
      {
        Serial.println(F("Config mode completed"));
        return true;
      }
      if (!WifiCaptivePortal.isSaved())
      {
        failReason = "Wi-Fi setup was not completed";
        return false;
      }
      // Otherwise fall through and try the saved networks
    }

    // If button not pressed, try normal startup
    if (WifiCaptivePortal.isSaved())
    {
      int connection_res = WifiCaptivePortal.autoConnect();
      if (connection_res)
      {
        preferences.putInt(PREFERENCES_CONNECT_WIFI_RETRY_COUNT, 1);
        return true;
      }
      failReason = "Could not connect to any saved Wi-Fi network";
    }
    else
    {
      // Nothing saved yet: show how to reach the portal, then run it
      showSetupScreen();
      WifiCaptivePortal.setResetSettingsCallback(resetDeviceCredentials);
      bool res = WifiCaptivePortal.startPortal();
      if (res)
      {
        preferences.putInt(PREFERENCES_CONNECT_WIFI_RETRY_COUNT, 1);
        return true;
      }
      failReason = "Wi-Fi setup was not completed";
    }
    Serial.println(F("No valid WiFi configuration found - main"));
    return false;
  }

  void update()
  {
    Serial.println(F("Update method called"));

    if (WiFi.status() != WL_CONNECTED)
    {
      failReason = "Wi-Fi is not connected";
    }
    else
    {
      Serial.println(F("WiFi Connected. Downloading image"));
      // Returns only on failure; on success it hibernates on the server's schedule
      downloadImage();
    }

    Serial.print(F("No new photo this wake-up: "));
    Serial.println(failReason);
    failAndSleep();
  }

  // Every wake-up that produced no photo ends here. The failure is counted in
  // Preferences, the error screen is drawn only when it is worth a full
  // refresh, and the sleep grows with each failure (QUIET_RETRIES and
  // ERROR_SLEEP_TIME in config.h). Never returns.
  void failAndSleep()
  {
    // A button press means someone is intervening, so the back-off starts
    // over: the next quiet retry comes after MIN_SLEEP_TIME, not ERROR_SLEEP_TIME.
    uint8_t failures = manualWake ? 0 : preferences.getUChar(PREFERENCES_CONNECT_API_RETRY_COUNT, 0);
    if (failures < 255)
      failures++;
    preferences.putUChar(PREFERENCES_CONNECT_API_RETRY_COUNT, failures);

    uint32_t sleepSeconds = failures <= QUIET_RETRIES
                                ? (uint32_t)MIN_SLEEP_TIME << (failures - 1)
                                : (uint32_t)ERROR_SLEEP_TIME;

    // Timer wake-ups keep the photo and retry quietly. The panel is redrawn
    // only when someone pressed the button, or once when the quiet retries
    // run out; after that the error is already on screen and stays.
    bool showError = manualWake || failures == QUIET_RETRIES + 1;
    Serial.printf("Consecutive failures: %u, next attempt in %lu s, error screen: %s\n",
                  failures, (unsigned long)sleepSeconds, showError ? "yes" : "no");
    if (showError)
      showErrorScreen(sleepSeconds);
    epd.Sleep(); // the failure paths never reach processImageData()'s Sleep()
    hibernate(sleepSeconds);
  }

  static String humanDuration(uint32_t seconds)
  {
    if (seconds % 3600 == 0)
    {
      uint32_t hours = seconds / 3600;
      return String(hours) + (hours == 1 ? " hour" : " hours");
    }
    return String(seconds / 60) + " minutes";
  }

  // Why there is no new photo, and what happens next. A full refresh, so it
  // is only called from failAndSleep() once that has decided it is worth it.
  void showErrorScreen(uint32_t sleepSeconds)
  {
    const uint16_t left = 40;
    const uint16_t width = EPD_WIDTH - 2 * left;
    screen.clear();
    uint16_t y = screen.text(left, 40, "Photo update failed", 3, EPD_7IN3E_RED);
    y += 8;
    y = screen.paragraph(left, y, failReason.c_str(), width, 2);
    y += 8;

    String line = "Server: " + (imageUrl.length() ? imageUrl : String("not set"));
    y = screen.paragraph(left, y, line.c_str(), width, 2);
    line = "Wi-Fi: ";
    if (WiFi.status() == WL_CONNECTED)
      line += WiFi.SSID() + " (" + String(WiFi.RSSI()) + " dBm, " + WiFi.localIP().toString() + ")";
    else
      line += "not connected";
    y = screen.paragraph(left, y, line.c_str(), width, 2);
    line = "Battery: " + String(batteryMv / 1000.0f, 2) + " V";
    y = screen.text(left, y, line.c_str(), 2);
    y += 8;

    line = "Next attempt in " + humanDuration(sleepSeconds) + ". Press the button to retry now.";
    y = screen.paragraph(left, y, line.c_str(), width, 2);
    screen.text(left, y, "Hold button 3 s at boot to change settings.", 2);

    screen.text(left, EPD_HEIGHT - 20, "Firmware built " __DATE__, 1);
    screen.show();
  }

  // How to reach the captive portal. Drawn before the access point starts,
  // for phones that do not open the page by themselves and for computers.
  void showSetupScreen()
  {
    const uint16_t left = 40;
    const uint16_t width = 440; // the right side is for the QR codes
    screen.clear();
    uint16_t y = screen.text(left, 32, "Photo frame setup", 3);
    y += 12;
    y = screen.text(left, y, "1. Join this Wi-Fi network:", 2);
    y = screen.text(left + 48, y, WIFI_SSID, 2, EPD_7IN3E_BLUE);
    y += 4;
    y = screen.text(left, y, "2. Open the setup page:", 2);
    y = screen.text(left + 48, y, LocalIPURL, 2, EPD_7IN3E_BLUE);
    y += 12;
    y = screen.paragraph(left, y, "Phones usually open the page by themselves. If not, scan the second code or type the address.", width, 2);
    y += 8;
    String line = "Closes after " + String(CONFIG_TIMEOUT / 60000) + " minutes.";
    screen.text(left, y, line.c_str(), 2);

    // The Wi-Fi join string phones understand, and the portal address
    const char *apPassword = WIFI_PASSWORD;
    String wifiQr = apPassword == nullptr
                        ? String("WIFI:T:nopass;S:") + WIFI_SSID + ";;"
                        : String("WIFI:T:WPA;S:") + WIFI_SSID + ";P:" + apPassword + ";;";
    const uint16_t qx = 560;
    const uint8_t modulePx = 5; // 33 modules x 5 px = 165 px
    uint16_t side = screen.qr(qx, 56, wifiQr.c_str(), modulePx);
    screen.text(qx, 56 + side + 8, "1. Wi-Fi", 2);
    side = screen.qr(qx, 272, LocalIPURL, modulePx);
    screen.text(qx, 272 + side + 8, "2. Setup page", 2);

    String footer = "Battery " + String(batteryMv / 1000.0f, 2) + " V   Firmware built " __DATE__;
    screen.text(left, EPD_HEIGHT - 32, footer.c_str(), 1);
    screen.show();
  }

  // Check battery voltage level
  // Average of 50 ADC samples on pin 0, doubled for the 1:2 divider
  bool checkVoltage()
  {
    analogReadResolution(12);
    long sum = 0;
    for (int i = 0; i < 50; i++)
    {
      sum += analogReadMilliVolts(0);
      delay(5);
    }
    batteryMv = (sum / 50) * 2;
    Serial.print("BAT millivolts value = ");
    Serial.print(batteryMv);
    Serial.println("mV");
    // Return false if battery voltage is below 3.05V
    return batteryMv >= 3050;
  }

  // Shown instead of a blank panel when the battery is too low to carry on
  void showLowBatteryScreen()
  {
    epd.Init();
    delay(1000);
    screen.clear();
    uint16_t y = screen.text(40, 160, "Battery empty", 3, EPD_7IN3E_RED);
    y += 16;
    String line = "Battery: " + String(batteryMv / 1000.0f, 2) + " V. Please charge the frame.";
    y = screen.paragraph(40, y, line.c_str(), EPD_WIDTH - 80, 2);
    screen.paragraph(40, y, "It checks again in 24 hours, or press the button after charging.", EPD_WIDTH - 80, 2);
    screen.show();
    epd.Sleep();
  }
};

// Global instance
EpaperManager epaperManager;

void setup()
{
  // USB CDC (HWCDCSerial) must be begin()'d first; otherwise HWCDC::write() drops output because tx_ring_buf == NULL
  Serial.begin(115200);
  // Serial is the USB Serial/JTAG port. When the frame is plugged into a PC
  // that has no terminal open, the host's driver fills its own buffer once
  // and then stops reading, and every Serial write would then block for up to
  // 20 x 100 ms waiting for room: measured 92 s awake instead of 37 s. A
  // 2 ms wait is plenty for a terminal that is actually reading; without one,
  // output is dropped instead of stalling the frame.
  Serial.setTxTimeoutMs(2);
  // Wait for the host to open the serial port so early output is not lost; the
  // loop exits as soon as a monitor attaches. After a power-on or a flash the
  // PlatformIO monitor needs several seconds to reopen the port, hence the long
  // wait. A wake-up from deep sleep is routine and only gets the short one, so
  // the frame on battery is not held up by a monitor that is not there.
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  const uint32_t serialWaitMs =
      (wakeup_reason == ESP_SLEEP_WAKEUP_UNDEFINED) ? SERIAL_WAIT_BOOT_MS : SERIAL_WAIT_WAKE_MS;
  for (uint32_t t0 = millis(); !Serial && (millis() - t0) < serialWaitMs;)
  {
    delay(10);
  }
  Serial.println();
  Serial.print(F("=== boot: serial up after "));
  Serial.print(millis());
  Serial.println(F("ms ==="));

  if (wakeup_reason == ESP_SLEEP_WAKEUP_TIMER)
  {
    Serial.println("Wakeup caused by timer");
  }
  else if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT1)
  {
    Serial.println("Wakeup caused by external signal using RTC_GPIO");
  }
  else
  {
    Serial.println("First boot or reset");
  }
  epaperManager.manualWake = (wakeup_reason != ESP_SLEEP_WAKEUP_TIMER);

  if (!epaperManager.checkVoltage())
  {
    Serial.println(F("Battery low voltage (< 3.0V)"));
    Serial.println(F("Sleep for 24hr"));
    epaperManager.showLowBatteryScreen();
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(1000);
    esp_sleep_enable_timer_wakeup(86400 * 1000000ULL);
    esp_deep_sleep_start();
  }
  if (epaperManager.begin())
  {
    Serial.println(F("Begin successful, calling update"));
    epaperManager.update();
  }
  else
  {
    // No Wi-Fi, no panel, or setup abandoned: count it and sleep with
    // back-off instead of restarting in a loop that never sleeps.
    Serial.println(F("Begin failed"));
    epaperManager.failAndSleep();
  }
}

void loop()
{
  // deepsleep
}