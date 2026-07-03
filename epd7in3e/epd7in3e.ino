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

// Consecutive-low-battery-boot counter. RTC_DATA_ATTR survives deep sleep
// (timer or EXT1 wake) but resets to 0 on power-on-reset/full power loss —
// exactly the persistence semantics needed for enforceLowBatteryGuard()'s
// escalation policy below (see D-15 rationale at enforceLowBatteryGuard()).
RTC_DATA_ATTR static int g_lowBatteryStreak = 0;

class EpaperManager
{
private:
  // SimpleWiFiManager wifiManager;
  EPaper epaper;
  String imageUrl = "";
  int m_batteryVoltageMv = 0;
  bool m_onBattery = false;
  uint8_t *m_frameBuf = nullptr; // PSRAM frame buffer; owned between readFrameData() and renderFrame()

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
      http.setAuthorization("admin", APP_PASSWORD);
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
          success = readFrameData(*http.getStreamPtr(), http.getSize());

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

            sleepHttp.setAuthorization("admin", APP_PASSWORD);
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
          Serial.printf("%s GET failed (code %d): %s\n",
                        isHttps ? "HTTPS" : "HTTP",
                        httpCode,
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

    // The frame and the sleep duration are now in hand — WiFi is no longer
    // needed. Power the radio down BEFORE the ~20-30 s panel refresh so the
    // modem (kept awake at ~80-100 mA by autoConnect()'s WiFi.setSleep(0)) does
    // not idle through the whole refresh. renderFrame() does the actual push +
    // refresh; hibernate() below re-issues WiFi off on its battery path, which
    // is harmless (idempotent).
    if (success)
    {
      WiFi.disconnect(true);
      WiFi.mode(WIFI_OFF);
      renderFrame();
    }

    // If we got a valid sleep duration, use it for hibernation
    if (success && sleepDuration > 0)
    {
      hibernate(sleepDuration);
    }
    else if (success)
    {
      // Download succeeded but server didn't provide a sleep duration — use default
      hibernate();
    }
    else
    {
      // Download failed — use shorter retry interval so device retries sooner
      Serial.printf("Download failed — retrying in %d s\n", (int)MIN_SLEEP_TIME);
      hibernate((int)MIN_SLEEP_TIME);
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

  // Stream the raw binary frame from the HTTP response into a PSRAM buffer.
  // READ ONLY — the ~20-30 s panel refresh is deliberately NOT done here. It is
  // deferred to renderFrame() so it can run AFTER WiFi is powered down. The
  // radio, left in no-sleep mode by autoConnect() (WiFi.setSleep(0)), otherwise
  // idles at ~80-100 mA for the entire refresh — the single largest avoidable
  // draw in the wake cycle. Ownership of the buffer passes to m_frameBuf, which
  // renderFrame() frees.
  bool readFrameData(WiFiClient &stream, int contentLength)
  {
    if (contentLength <= 0) {
      Serial.println("Invalid content length");
      return false;
    }

    // Allocate PSRAM frame buffer (960,000 bytes for 1200x1600 4bpp)
    const size_t FRAME_SIZE = 1200 * 1600 / 2; // 960000 bytes
    m_frameBuf = (uint8_t*)ps_malloc(FRAME_SIZE);
    if (!m_frameBuf) {
      Serial.println("PSRAM allocation failed — check ps_malloc availability");
      return false;
    }

    // Stream raw binary directly into the PSRAM frame buffer (binary transport — plan 10-01).
    size_t totalRead = 0;
    while (stream.connected() && totalRead < FRAME_SIZE) {
      int available = stream.available();
      if (available > 0) {
        size_t toRead = min((size_t)available, FRAME_SIZE - totalRead);
        int read = stream.readBytes(m_frameBuf + totalRead, (int)toRead);
        if (read > 0) totalRead += (size_t)read;
      } else {
        delay(1);
      }
    }

    if (totalRead != FRAME_SIZE) {
      Serial.printf("Warning: expected %d bytes, received %d\n", (int)FRAME_SIZE, (int)totalRead);
    }
    return true;
  }

  // Push the previously-read frame to the panel, trigger the refresh, and
  // release the PSRAM buffer. MUST be called only after WiFi is powered down
  // (see readFrameData() rationale). No-op if no frame was read.
  void renderFrame()
  {
    if (!m_frameBuf) return;
    Serial.println("Pushing image to display...");
    epaper.pushImage(0, 0, EPD_WIDTH, EPD_HEIGHT, (uint16_t*)m_frameBuf);
    epaper.update();
    epaper.sleep();
    free(m_frameBuf);
    m_frameBuf = nullptr;
    Serial.println("Display updated");
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
    rtc_gpio_isolate(GPIO_NUM_1);  // BAT_ADC_PIN — prevent ADC leakage path in deep sleep
    rtc_gpio_isolate(GPIO_NUM_6);  // ADC_EN_PIN — fully gate TPS22916 load switch
    // Tri-state SPI/display control pins before deep sleep to eliminate leakage
    // through the e-paper protection diodes. epaper.sleep() (sent by update())
    // only issues a software command — it does NOT change GPIO directions.
    // GPIO8/9/10/38/41/44 are digital-only on ESP32-S3 (NOT RTC-capable), so
    // rtc_gpio_isolate() does not apply; use SPI.end() + pinMode(INPUT) instead.
    // Do NOT use the gpio reset pin API — community reports it can block deep-sleep entry.
    SPI.end();                  // releases GPIO8 (SCLK) and GPIO9 (MOSI) from the SPI peripheral
    pinMode(DC_PIN,  INPUT);    // GPIO10
    pinMode(CS_PIN,  INPUT);    // GPIO44
    pinMode(CS1_PIN, INPUT);    // GPIO41
    pinMode(RST_PIN, INPUT);    // GPIO38
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
    // Timer wakeups are unattended production refresh cycles — no user is
    // present to hold the config button, so skip the Button poll entirely.
    // Button::result() blocks a minimum of ~1.5 s waiting for events; running
    // it on every hourly wake wastes ~0.3 mAh/day at ~80 mA for nothing.
    // A deliberate config-button press wakes the board via EXT1 (WAKEUP_PIN ==
    // CONFIG_PIN == GPIO2), and cold boot / reset is also a user-present event —
    // both still run the full poll so config mode remains reachable.
    if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_TIMER)
    {
      return false;
    }
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

    setCpuFrequencyMhz(CPU_FREQ_MHZ);   // 240->80 MHz before WiFi connect
    WiFi.mode(WIFI_STA);
    WiFi.setTxPower(WIFI_TX_POWER);     // LAN-adequate 8.5 dBm

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
  // Returns mV (after 1:1 divider compensation).
  //
  // NOTE on "Power source" naming: this board has NO USB/VBUS-sense GPIO
  // (confirmed from EE02 schematic — see .planning/phases/04-battery-voltage/
  // 04-RESEARCH.md). m_onBattery is therefore only a proxy for "a battery
  // cell is physically connected" (VBAT floats near 0V with none attached);
  // it CANNOT distinguish "running on battery" from "running on USB with a
  // battery also connected." The BQ24070 PMIC keeps VBAT elevated whenever
  // ANY power source is present, so m_onBattery is true in the overwhelming
  // majority of real-world (USB-plugged) boots too. Do not use this flag as
  // proof the device is unattended/unplugged.
  //
  // Multi-sample averaged read (10 samples) — matches the noise-reduction
  // approach already used for the HTTP header read in downloadImage() to
  // avoid single-sample ADC jitter (~50-100mV, documented in 04-RESEARCH.md)
  // flipping the guard decision near the MIN_BATTERY_VOLTAGE threshold.
  int checkVoltage()
  {
    pinMode(ADC_EN_PIN, OUTPUT);
    digitalWrite(ADC_EN_PIN, LOW);
    analogSetAttenuation(ADC_11db);
    analogReadResolution(12);
    digitalWrite(ADC_EN_PIN, HIGH);
    delay(10);  // load switch + divider settle time
    const int kSamples = 10;
    long rawMvSum = 0;
    for (int i = 0; i < kSamples; i++) {
      rawMvSum += analogReadMilliVolts(BAT_ADC_PIN);
      delay(5);
    }
    digitalWrite(ADC_EN_PIN, LOW);
    int vbatMv = (int)((rawMvSum / kSamples) * 2);  // 1:1 divider (R28=R29=10kΩ)
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
  // clear screen, disable WiFi, and enter a protective deep sleep. Does not
  // return (when it fires).
  //
  // IMPORTANT: because m_onBattery cannot distinguish "on battery" from
  // "on USB with VBAT coincidentally below threshold" (see checkVoltage()
  // note above — this board has no VBUS-sense/PG GPIO; re-confirmed directly
  // against the EE02 v1.0 schematic — BQ24070 ~PG pin 18 is explicitly
  // unpopulated on this board revision, and STAT1/STAT2 only drive the
  // charge-status LEDs, not any GPIO), this guard can fire even while the
  // board is powered externally by USB with a low/aging/not-yet-charged
  // battery cell attached.
  //
  // D-15 (escalation policy, added after real-hardware report that a single
  // low reading was bricking a USB-powered board for a full 24h): rather than
  // committing to an unrecoverable 24h sleep on the FIRST low-voltage boot,
  // treat the first (streak < LOW_BATTERY_ESCALATION_THRESHOLD) low readings
  // as "possibly transient / possibly USB-powered with a low cell" and only
  // sleep for MIN_SLEEP_TIME (short retry, matches the interval already used
  // for failed-download retries). If the board is genuinely on USB power,
  // the BQ24070 will have recharged the cell above threshold well before the
  // streak counter escalates, and the device recovers on its own within a
  // few short cycles instead of appearing bricked. Only after
  // LOW_BATTERY_ESCALATION_THRESHOLD consecutive independent boots still
  // read low (meaning the board is truly unattended on a dying/disconnected
  // battery, not USB-recharging between checks) does the guard escalate to
  // the full 24h protective sleep. g_lowBatteryStreak is RTC_DATA_ATTR so it
  // survives the short deep-sleep/wake cycles used here but resets to 0 on a
  // genuine power-on-reset (e.g. user unplugs/replugs), which is exactly the
  // desired reset condition. EXT1 GPIO wakeup on WAKEUP_PIN is armed
  // alongside the timer wakeup at every stage (mirrors hibernate()'s
  // battery-sleep path) so pressing the wake button always recovers the
  // device immediately regardless of which sleep duration is active.
  void enforceLowBatteryGuard()
  {
    if (!(m_onBattery && m_batteryVoltageMv < (int)MIN_BATTERY_VOLTAGE)) {
      g_lowBatteryStreak = 0; // voltage recovered (or no battery signal) — clear streak
      return;
    }

    g_lowBatteryStreak++;
    bool escalate = g_lowBatteryStreak >= LOW_BATTERY_ESCALATION_THRESHOLD;
    uint64_t sleepSeconds = escalate ? 86400ULL : (uint64_t)MIN_SLEEP_TIME;

    Serial.printf("Battery low (%d mV < %u mV), streak=%d — sleeping %s\n",
                  m_batteryVoltageMv, (unsigned)MIN_BATTERY_VOLTAGE,
                  g_lowBatteryStreak,
                  escalate ? "24h (escalated)" : "briefly (retry)");
    clearScreen();
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    rtc_gpio_isolate(GPIO_NUM_1);  // BAT_ADC_PIN — prevent ADC leakage path in deep sleep
    rtc_gpio_isolate(GPIO_NUM_6);  // ADC_EN_PIN — fully gate TPS22916 load switch
    SPI.end();                  // releases GPIO8 (SCLK) and GPIO9 (MOSI) from the SPI peripheral
    pinMode(DC_PIN,  INPUT);    // GPIO10
    pinMode(CS_PIN,  INPUT);    // GPIO44
    pinMode(CS1_PIN, INPUT);    // GPIO41
    pinMode(RST_PIN, INPUT);    // GPIO38
    esp_sleep_enable_timer_wakeup(sleepSeconds * 1000000ULL);
    rtc_gpio_init(WAKEUP_PIN);
    rtc_gpio_set_direction(WAKEUP_PIN, RTC_GPIO_MODE_INPUT_ONLY);
    rtc_gpio_pullup_en(WAKEUP_PIN);
    rtc_gpio_pulldown_dis(WAKEUP_PIN);
    esp_sleep_enable_ext1_wakeup(1ULL << WAKEUP_PIN, ESP_EXT1_WAKEUP_ANY_LOW);
    esp_deep_sleep_start();
  }
};

// Global instance
EpaperManager epaperManager;

void setup()
{
  Serial.begin(115200);
  // KNOWN HARDWARE LIMITATION (BV-05, D-12/D-13/D-14):
  // The green charge LEDs (D5, D16 on EE02 board) are driven by the
  // BQ24070 PMIC's STAT1/STAT2 open-drain outputs and are NOT connected
  // to any XIAO GPIO. When no battery is present the PMIC enters a
  // no-battery fault state and the LEDs blink. This cannot be suppressed
  // from firmware. Accepted as a hardware-only behavior.

  // Determine wake up reason BEFORE the serial-monitor delay so production
  // deep-sleep wakeups skip the 3 s wait (saves ~0.056 mAh per cycle).
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  bool isDevelopmentBoot = (wakeup_reason != ESP_SLEEP_WAKEUP_TIMER &&
                            wakeup_reason != ESP_SLEEP_WAKEUP_EXT1);
  if (isDevelopmentBoot) {
    delay(3000); // cold boot/reset: wait for USB-CDC serial monitor to enumerate
  } else {
    delay(50);   // production wakeup: minimal USB-CDC settle time
  }

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