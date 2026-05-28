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
   BUSY   <> GPIO5  (D3)
   RST    <> GPIO38 (internal, wired by EE02 board)
   DC     <> GPIO10
   CS     <> GPIO44 (D7) + CS1 GPIO41
   SCLK   <> GPIO8  (D8, HSPI)
   MOSI   <> GPIO9  (HSPI, write-only)
   WAKEUP <> GPIO2  (D0, RTC-capable)
   CONFIG <> GPIO2  (sampled at boot only)
*/

Preferences preferences;

class EpaperManager
{
private:
  // SimpleWiFiManager wifiManager;
  EPaper epaper;
  String imageUrl = "";

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

  // Enter deep sleep mode with calculated wake-up interval
  void hibernate(int sleepDuration = 0)
  {
    // TODO: re-enable deep sleep once battery is connected
    Serial.printf("hibernate() skipped (no battery) — would sleep %d s\n",
                  sleepDuration > 0 ? sleepDuration : (int)SLEEP_INTERVAL);
    return;
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
};

// Global instance
EpaperManager epaperManager;

void setup()
{
  Serial.begin(115200);
  delay(3000); // wait for USB-CDC serial monitor to connect
  Serial.println("\n\n=== EPF booting ===");
  Serial.println("Hello World!");
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