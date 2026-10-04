#ifndef CONFIG_H
#define CONFIG_H

// File system configuration
#define CONFIG_FILE "/wifi_config.json"

// Reported over Improv Serial to the web installer, which compares it with the
// manifest: same name means "update, keep the flash"; the version decides
// whether an update is offered at all. Bump it with every release.
#define FW_NAME "EPF photo frame firmware"
#define FW_VERSION "1.2.0"
// How long a USB-attached boot keeps answering Improv before carrying on, so
// the installer's identity check right after flashing gets its reply.
#define IMPROV_WAIT_MS 2000U

// WiFi and HTTP configuration
#define HTTP_TIMEOUT 50000U // HTTP request timeout in ms
#define RETRY_DELAY 10000U  // Delay between retries in ms
#define MAX_RETRIES 5U      // Maximum number of retry attempts

// GPIO Configuration
#define CONFIG_PIN 2U          // Configuration mode trigger pin
#define BUTTON_DEBOUNCE 100U   // Button debounce time in ms
#define BUTTON_HOLD_TIME 3000U // Button hold time in ms

// How long setup() waits for a serial monitor before carrying on. The long wait
// applies after power-on or a flash (PlatformIO's monitor needs a few seconds to
// reopen the port); wake-ups from deep sleep get the short one.
#define SERIAL_WAIT_BOOT_MS 10000U
#define SERIAL_WAIT_WAKE_MS 2000U

// Sleep and timing configuration
#define SLEEP_TIME_COMPENSATION 1.009f // Sleep time compensation factor
#define SLEEP_INTERVAL 3600U           // Default sleep interval in seconds (1 hour)
#define MIN_SLEEP_TIME 900U            // Minimum sleep time in seconds (15 minutes)

// Failure handling. Consecutive failed wake-ups (no Wi-Fi, server unreachable,
// download rejected) are counted in Preferences. The first QUIET_RETRIES keep
// the current photo on screen and retry after MIN_SLEEP_TIME doubled each time
// (15, 30, 60 minutes). The next failure draws the error screen once, and from
// then on the frame sleeps ERROR_SLEEP_TIME between attempts to spare the
// battery. A button press always retries at once and shows the error if it
// fails again. A successful download resets the count.
#define QUIET_RETRIES 3U
#define ERROR_SLEEP_TIME 21600U        // 6 hours

// Wake up source configuration
#define WAKEUP_PIN GPIO_NUM_2                 // GPIO 2 for wake up
#define WAKEUP_LEVEL ESP_GPIO_WAKEUP_GPIO_LOW // Wake up on low level

// Buffer configuration
#define BUFFER_SIZE 131072U // Buffer size for image processing

#define SERVER_BASE_URL "http://server.ip:15001"
#define PREFERENCES_SLEEP_TIME_KEY "refresh_rate"
// #define PREFERENCES_DEVICE_REGISTRED_KEY "plugin"
// #define PREFERENCES_FILENAME_KEY "filename"
#define PREFERENCES_LAST_SLEEP_TIME "last_sleep"
#define PREFERENCES_CONNECT_API_RETRY_COUNT "retry_count"
#define PREFERENCES_CONNECT_WIFI_RETRY_COUNT "wifi_retry"

#define CONFIG_TIMEOUT 300000 // 5 minute

// NFC Configuration (ST25DV)
#define NFC_SDA_PIN 19
#define NFC_SCL_PIN 20
#define NFC_POWER_PIN 4              // GPIO to directly power NFC module VCC
#define NFC_POWER_ON_DELAY_MS 50     // Delay after power on for ST25DV to stabilize
#define NFC_PHOTO_URL_HEADER "X-Photo-Url"

#endif // CONFIG_H