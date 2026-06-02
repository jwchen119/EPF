#ifndef CONFIG_H
#define CONFIG_H

// File system configuration
// #define CONFIG_FILE "/wifi_config.json"

// WiFi and HTTP configuration
#define HTTP_TIMEOUT 50000U // HTTP request timeout in ms
#define RETRY_DELAY 10000U  // Delay between retries in ms
#define MAX_RETRIES 5U      // Maximum number of retry attempts

// GPIO Configuration
#define CONFIG_PIN 2U          // Configuration mode trigger pin
#define BUTTON_DEBOUNCE 100U   // Button debounce time in ms
#define BUTTON_HOLD_TIME 3000U // Button hold time in ms

// Battery ADC configuration (EE02 board — confirmed from schematic)
#define BAT_ADC_PIN          1U    // GPIO1 = BAT_ADC net (A0/D0)
#define ADC_EN_PIN           6U    // GPIO6 = ADC_EN net (D5/A5 on XIAO) — drives TPS22916 load switch
#define MIN_BATTERY_VOLTAGE  3050U // mV — below this triggers 24h sleep

// Sleep and timing configuration
#define SLEEP_TIME_COMPENSATION 1.009f // Sleep time compensation factor
#define SLEEP_INTERVAL 3600U           // Default sleep interval in seconds (1 hour)
#define MIN_SLEEP_TIME 900U            // Minimum sleep time in seconds (15 minutes)

// Wake up source configuration
#define WAKEUP_PIN GPIO_NUM_2                 // GPIO 2 for wake up
#define WAKEUP_LEVEL ESP_GPIO_WAKEUP_GPIO_LOW // Wake up on low level

// HTTP chunk size for streaming reads (frame buffer is allocated in PSRAM)
#define HTTP_CHUNK_SIZE 16384U  // HTTP read chunk size (frame buffer is in PSRAM)

#define SERVER_BASE_URL "http://server.ip:15001"
// HTTP Basic Auth password (must match server APP_PASSWORD env var). Empty = no auth.
#define APP_PASSWORD ""
#define PREFERENCES_SLEEP_TIME_KEY "refresh_rate"
#define PREFERENCES_LAST_SLEEP_TIME "last_sleep"
#define PREFERENCES_CONNECT_API_RETRY_COUNT "retry_count"
#define PREFERENCES_CONNECT_WIFI_RETRY_COUNT "wifi_retry"

#define CONFIG_TIMEOUT 300000U // 5 minute

#endif // CONFIG_H