#include <Arduino.h>
#include <SPI.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>
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
#include <WiFi.h>

/* Pin Layout — XIAO ESP32-S3 Plus on Seeed EE02 HAT
   BUSY   <> GPIO4  (D3) — confirmed from Seeed_GFX EPaper_Board_Pins_Setups.h
   RST    <> GPIO38 (internal, wired by EE02 board)
   DC     <> GPIO10
   CS     <> GPIO44 (D7) + CS1 GPIO41
   SCLK   <> GPIO8  (D8, HSPI)
   MOSI   <> GPIO9  (HSPI, write-only)
   WAKEUP <> GPIO2  (D0, RTC-capable)
   CONFIG <> GPIO2  (sampled at boot only)
   BAT_ADC <> GPIO1 (D0/A0) — BAT_ADC net via TPS22916 voltage divider
   ADC_EN  <> GPIO6 (D5/A5) — ADC_EN net, gates TPS22916 load switch
*/

Preferences preferences;

class EpaperManager
{
private:
  // SimpleWiFiManager wifiManager;
  EPaper epaper;
  String imageUrl = "";
  int m_batteryVoltageMv = 0;
  bool m_onBattery = false;

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

    String sleepUrl = baseUrl + sleepPath;

    // Setup client for image download
    if (isHttps)
    {
      secureClient = new WiFiClientSecure;
      secureClient->setInsecure();
      if (!http.begin(*secureClient, imageUrl + downloadPath))
      {
        Serial.println("Failed to initialize HTTPS connection");
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
        delete basicClient;
        return false;
      }
    }

    // Download and process image
    bool success = false;
    int sleepDuration = 0;
    bool retryOnError = true; // Add retry flag

    while (retryOnError && !success)
    {                       // Add retry loop
      retryOnError = false; // Default to no retry

      // ---- Battery-aware HTTP header (BV-04) ----
      // 50-sample averaged read for accurate header value. Single-read guard
      // already ran in setup() via EpaperManager::checkVoltage(); this is a
      // separate averaged read per original (git 8a000e1) behavior.
      pinMode(ADC_EN_PIN, OUTPUT);
      analogSetAttenuation(ADC_11db);
      analogReadResolution(12);
      digitalWrite(ADC_EN_PIN, HIGH);
      delay(10);
      int plusV = 0;
      for (int i = 0; i < 50; i++) {
        plusV += analogReadMilliVolts(BAT_ADC_PIN);
        delay(5);
      }
      int avgBatteryMv = (plusV / 50) * 2;  // 1:1 divider
      digitalWrite(ADC_EN_PIN, LOW);
      bool avgOnBattery = (avgBatteryMv > 1500);
      int headerValue = avgOnBattery ? avgBatteryMv : 0;
      http.addHeader("batteryCap", String(headerValue));
      Serial.printf("HTTP batteryCap header: %d mV (onBattery=%s)\n",
                    headerValue, avgOnBattery ? "true" : "false");
      // Refresh stored state so hibernate() sees the latest reading.
      m_batteryVoltageMv = avgBatteryMv;
      m_onBattery = avgOnBattery;
      // ---- end battery header ----

      for (uint8_t i = 0; i < MAX_RETRIES; i++)
      {
        int httpCode = http.GET();

        if (httpCode == HTTP_CODE_OK)
        {
          success = processImageData(*http.getStreamPtr(), http.getSize());

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
              StaticJsonDocument<200> doc;
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
          Serial.println("Server error (500), will retry once...");
          delay(RETRY_DELAY);
          retryOnError = true; // Enable one retry on 500 error
          break;               // Exit current retry loop
        }
        else
        {
          Serial.printf("%s GET failed: %s\n",
                        isHttps ? "HTTPS" : "HTTP",
                        http.errorToString(httpCode).c_str());
          break;
        }
      }
    }

    http.end();
    delay(10);
    if (secureClient)
      delete secureClient;
    if (basicClient)
      delete basicClient;

    // If we got a valid sleep duration, use it for hibernation
    if (success && sleepDuration > 0)
    {
      hibernate(sleepDuration);
    }
    else
    {
      // Use default sleep duration if server didn't provide one
      hibernate();
    }

    return success;
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
  bool processImageData(WiFiClient &stream, int contentLength)
  {
    if (contentLength <= 0) {
      Serial.println("Invalid content length");
      return false;
    }

    // Allocate PSRAM frame buffer (960,000 bytes for 1200x1600 4bpp)
    uint8_t* frame_buf = (uint8_t*)ps_malloc(1200 * 1600 / 2);
    if (!frame_buf) {
      Serial.println("PSRAM allocation failed — check ps_malloc availability");
      return false;
    }
    size_t frame_offset = 0;
    const size_t FRAME_SIZE = 1200 * 1600 / 2;

    // Allocate HTTP read chunk buffer on heap
    uint8_t* chunk_buf = (uint8_t*)malloc(HTTP_CHUNK_SIZE);
    if (!chunk_buf) {
      Serial.println("Chunk buffer allocation failed");
      free(frame_buf);
      return false;
    }

    // Stream hex-CSV response into frame_buf
    String hexBuffer = "";
    int bytesRead = 0;

    while (stream.connected() && bytesRead < contentLength) {
      int available = stream.available();
      if (available > 0) {
        int toRead = min(available, (int)HTTP_CHUNK_SIZE);
        int read = stream.readBytes(chunk_buf, toRead);
        bytesRead += read;

        for (int i = 0; i < read; i++) {
          char c = (char)chunk_buf[i];
          if (isDelimiter(c)) {
            if (!hexBuffer.isEmpty()) {
              uint8_t byteValue = (uint8_t)strtol(hexBuffer.c_str(), NULL, 16);
              if (frame_offset < FRAME_SIZE) {
                frame_buf[frame_offset++] = byteValue;
              }
              hexBuffer = "";
            }
          } else {
            hexBuffer += c;
          }
        }
      } else {
        delay(1);
      }
    }

    // Handle any remaining hex in buffer
    if (!hexBuffer.isEmpty()) {
      uint8_t byteValue = (uint8_t)strtol(hexBuffer.c_str(), NULL, 16);
      if (frame_offset < FRAME_SIZE) {
        frame_buf[frame_offset++] = byteValue;
      }
    }

    free(chunk_buf);

    if (frame_offset != FRAME_SIZE) {
      Serial.printf("Warning: expected %d bytes, received %d\n", (int)FRAME_SIZE, (int)frame_offset);
    }

    // Push frame to display and trigger refresh
    Serial.println("Pushing image to display...");
    epaper.pushImage(0, 0, EPD_WIDTH, EPD_HEIGHT, (uint16_t*)frame_buf);
    epaper.update();
    epaper.sleep();
    free(frame_buf);
    Serial.println("Display updated");
    return true;
  }

  // Enter low-power state with calculated wake-up interval.
  // Battery mode -> real deep sleep with timer + EXT1 GPIO2 wakeup.
  // USB mode    -> delay then ESP.restart() (deep sleep stalls boards without battery).
  void hibernate(int sleepDuration = 0)
  {
    int sleep_interval = sleepDuration > 0 ? sleepDuration : (int)SLEEP_INTERVAL;

    if (!m_onBattery) {
      // USB power path (BV-02, BV-03): skip deep sleep entirely.
      // delay() in Arduino-ESP32 calls vTaskDelay internally, which feeds the
      // task watchdog. Cast to uint32_t to avoid int*int overflow at >2147s.
      Serial.printf("USB power: waiting %d s then restarting\n", sleep_interval);
      Serial.flush();
      delay((uint32_t)sleep_interval * 1000UL);
      ESP.restart();
      return;
    }

    // Battery power path (BV-03): full deep sleep.
    Serial.printf("Battery power: entering deep sleep for %d s\n", sleep_interval);
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    fs_deinit();
    delay(50);

    uint64_t sleep_time = (uint64_t)sleep_interval * 1000000ULL;
    esp_sleep_enable_timer_wakeup(sleep_time);

    rtc_gpio_init(WAKEUP_PIN);
    rtc_gpio_set_direction(WAKEUP_PIN, RTC_GPIO_MODE_INPUT_ONLY);
    rtc_gpio_pullup_en(WAKEUP_PIN);
    rtc_gpio_pulldown_dis(WAKEUP_PIN);
    esp_sleep_enable_ext1_wakeup(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW);

    Serial.println("Entering deep sleep...");
    Serial.flush();
    delay(50);
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
  bool begin()
  {
    Serial.begin(115200);
    delay(50);
    pinMode(CONFIG_PIN, INPUT_PULLUP);

    epaper.begin();

    // Re-create sprite buffer here (PSRAM is guaranteed available at this point).
    // The EPaper global constructor runs before PSRAM is set up if PSRAM board option
    // is disabled, leaving _img8 = null and causing a crash on update().
    epaper.deleteSprite();
    if (!epaper.createSprite(EPD_WIDTH, EPD_HEIGHT)) {
      Serial.println(F("ERROR: EPaper sprite allocation failed — enable PSRAM in board settings"));
      Serial.println(F("  Arduino IDE > Tools > PSRAM > OPI PSRAM"));
      return false;
    }
    Serial.println(F("e-Paper initialized successfully (Seeed_GFX)"));

    // initialize spiffs
    fs_init();

    // initialize preferences
    preferences.begin("data", true);

    WiFi.mode(WIFI_STA);

    // Check configuration button
    if (shouldEnterConfigMode())
    {
      Serial.println(F("Config button pressed, entering config mode..."));
      epaper.fillScreen(TFT_WHITE); epaper.update();
      // epaper.sleep();

      bool res = WifiCaptivePortal.startPortal();
      if (res)
      {
        Serial.println(F("Config mode completed"));
        return true;
      }
      // else {
      //   epd.Clear(EPD_7IN3E_WHITE);
      //   epd.Sleep();
      //   return false;
      // }
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
      // else {
      //   epd.Clear(EPD_7IN3E_WHITE);
      //   epd.Sleep();
      // }
    }
    else
    {
      WifiCaptivePortal.setResetSettingsCallback(resetDeviceCredentials);
      bool res = WifiCaptivePortal.startPortal();
      if (res)
      {
        preferences.putInt(PREFERENCES_CONNECT_WIFI_RETRY_COUNT, 1);
        return true;
      }
      //   if (!res) {
      //     epd.Clear(EPD_7IN3E_WHITE);
      //     epd.Sleep();
    }
    // }
    Serial.println(F("No valid WiFi configuration found - main"));
    return false;
  }

  void update()
  {
    Serial.println(F("Update method called"));

    if (WiFi.status() == WL_CONNECTED)
    {
      Serial.println(F("WiFi Connected. Downloading image"));
      if (downloadImage())
      {
        Serial.println(F("Image download successful"));
      }
      else
      {
        Serial.println(F("Image download failed"));
      }
    }
    else
    {
      Serial.println(F("WiFi not connected. Cannot download image"));
    }

    Serial.println(F("Entering sleep mode"));
    hibernate();
  }

  // Clear the e-paper display
  void clearScreen()
  {
    epaper.begin();
    delay(100);
    epaper.fillScreen(TFT_WHITE);
    epaper.update();
    epaper.sleep();
  }

  // Read battery voltage via GPIO1 ADC behind GPIO5 ADC_EN gate.
  // Returns mV (after 1:1 divider compensation). Single-sample read for
  // the low-battery guard. The averaged read for the HTTP header is
  // handled separately in downloadImage() (Plan 02).
  int checkVoltage()
  {
    pinMode(ADC_EN_PIN, OUTPUT);
    digitalWrite(ADC_EN_PIN, LOW);
    analogSetAttenuation(ADC_11db);
    analogReadResolution(12);
    digitalWrite(ADC_EN_PIN, HIGH);
    delay(10);  // load switch + divider settle time
    int rawMv = analogReadMilliVolts(BAT_ADC_PIN);
    digitalWrite(ADC_EN_PIN, LOW);
    int vbatMv = rawMv * 2;  // 1:1 divider (R28=R29=10kΩ)
    m_batteryVoltageMv = vbatMv;
    m_onBattery = (vbatMv > 1500);
    Serial.printf("Battery voltage: %d mV\n", vbatMv);
    Serial.printf("Power source: %s\n", m_onBattery ? "battery" : "USB");
    return vbatMv;
  }

  // Accessor used by Plan 02 to thread state into hibernate() / downloadImage().
  bool isOnBattery() const { return m_onBattery; }
  int batteryVoltageMv() const { return m_batteryVoltageMv; }

  // Low-battery guard: if running on battery and below MIN_BATTERY_VOLTAGE,
  // clear screen, disable WiFi, and enter 24h deep sleep. Does not return.
  void enforceLowBatteryGuard()
  {
    if (m_onBattery && m_batteryVoltageMv < (int)MIN_BATTERY_VOLTAGE) {
      Serial.printf("Battery low (%d mV < %u mV) — sleeping 24h\n",
                    m_batteryVoltageMv, (unsigned)MIN_BATTERY_VOLTAGE);
      clearScreen();
      WiFi.disconnect(true);
      WiFi.mode(WIFI_OFF);
      esp_sleep_enable_timer_wakeup(86400ULL * 1000000ULL);
      esp_deep_sleep_start();
    }
  }
};

// Global instance
EpaperManager epaperManager;

void setup()
{
  Serial.begin(115200);
  delay(3000); // wait for USB-CDC serial monitor to connect
  // KNOWN HARDWARE LIMITATION (BV-05, D-12/D-13/D-14):
  // The green charge LEDs (D5, D16 on EE02 board) are driven by the
  // BQ24070 PMIC's STAT1/STAT2 open-drain outputs and are NOT connected
  // to any XIAO GPIO. When no battery is present the PMIC enters a
  // no-battery fault state and the LEDs blink. This cannot be suppressed
  // from firmware. Accepted as a hardware-only behavior.
  
  // Determine wake up reason
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();

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

  epaperManager.checkVoltage();
  epaperManager.enforceLowBatteryGuard();

  if (epaperManager.begin())
  {
    Serial.println(F("Begin successful, calling update"));
    epaperManager.update();
  }
  else
  {
    Serial.println(F("Begin failed"));
    epaperManager.clearScreen();

    delay(30000);
    ESP.restart();
  }
}

void loop()
{
  // deepsleep
}