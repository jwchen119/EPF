# EPF - 電子紙相框

[English](README.md) | [繁體中文](README.zh-TW.md)

一個以 Waveshare 7.3 吋 Spectra 6（E6）彩色電子紙面板與 ESP32-C6 組成的電池供電相框。照片放在 [Immich](https://immich.app) 的相簿裡管理；一個小型 Flask 伺服器（通常以 Docker 跑在 NAS 上）負責挑選下一張照片、裁切、增強、抖色成面板的六種顏色，再把 ESP32 可以直接推進面板的位元組串流交給它。ESP32 完全不做影像處理，所以每張照片醒著的時間遠低於一分鐘，其餘時間都在深度睡眠。

這個倉庫裡有兩個部分，透過 HTTP 溝通：

| 部分 | 位置 | 功能 |
| --- | --- | --- |
| 伺服器 | `app.py`、`epf/`、`cpy.pyx`、`templates/`、`static/` | Docker 裡的 Flask 應用程式。連接 Immich、處理照片、提供設定頁、記錄相框回報、發送低電量通知。 |
| 韌體 | `Arduino/` | ESP32-C6 程式。Wi-Fi 設定入口、下載影像、面板驅動、選配的 NFC 標籤寫入、深度睡眠。 |
| 外殼 | `CAD/` | 相框零件的 STEP 檔。 |

## 運作方式

1. ESP32 醒來（定時或按下按鈕）並連上 Wi-Fi。
2. 呼叫伺服器的 `GET /download`，在請求標頭帶上電池電壓。
3. 伺服器從設定的 Immich 相簿挑一張照片，縮放與旋轉成 800x480，套用飽和度與對比，抖色成面板的六色，再以每個位元組兩個 4 位元像素打包。
4. 韌體把回應直接透過 SPI 串流進面板，不在 RAM 中保存整張圖，然後刷新顯示。
5. 若裝有 ST25DV NFC 標籤，韌體會把照片的 Immich 連結（來自 `X-Photo-Url` 回應標頭）寫進標籤，用手機碰一下相框就能開啟原圖。
6. 呼叫 `GET /sleep` 取得下次喚醒時間（會避開設定的安靜時段），然後回到深度睡眠。

## 功能

- **以 Immich 為照片來源。** 把照片丟進相簿就會出現在相框上，不需要手動複製或轉檔。HEIC 與 RAW 原圖由伺服器處理。
- **伺服器端處理。** 縮放、旋轉、符合或填滿、飽和度、對比與 Floyd-Steinberg 抖色都在伺服器執行，抖色核心以 Cython 撰寫。
- **低功耗。** ESP32 只在抓取與顯示照片時醒來，而且伺服器在交出一張照片後會立刻選好並處理下一張，所以一次喚醒約 36 秒，其中 30 秒是面板刷新。進入休眠前會先讓面板睡眠；原作者量得深度睡眠約 16 uA。
- **設定頁。** Immich 網址與相簿、旋轉、符合或填滿、隨機或最新優先、增強滑桿、安靜時段與喚醒間隔，全部在瀏覽器中儲存。可看到目前與下一張照片，並有按鈕可以換掉下一張。提供英文、繁體中文、簡體中文與日文。
- **狀態與歷史。** 頁面顯示 Immich 是否可連、相簿是否還存在、相框上次回報的時間與電量，以及回報、設定變更與錯誤的系統記錄。
- **低電量通知**，透過 Telegram 或 LINE Messaging API，在設定頁綁定。只有在測試訊息確實送達後才算綁定成功。
- **設定入口（Captive portal）。** 開機時長按按鈕，ESP32 會開啟一個 Wi-Fi 熱點與設定頁，可儲存最多五組網路與伺服器網址。改編自 [TRMNL 韌體](https://github.com/usetrmnl/firmware/tree/main/lib/wificaptive)。
- **HTTPS。** 韌體可以連接 HTTPS 的伺服器（不驗證憑證）。
- **NFC 標籤（選配）。** 裝上 ST25DV 標籤後，相框會提供目前顯示照片的連結。
- **一顆按鈕。** 睡眠中短按：醒來並抓新照片。開機時長按約 3 秒：進入設定入口。

## 硬體

- [DFRobot FireBeetle 2 ESP32-C6](https://www.dfrobot.com/product-2771.html)
- [Waveshare 7.3 吋 E Ink Spectra 6（E6）電子紙模組含 HAT](https://www.waveshare.com/7.3inch-e-paper-hat-e.htm)，800x480
- 附 PH2.0 接頭的鋰聚合物電池（FireBeetle 透過 USB 充電）
- 一顆瞬時按鈕，用於喚醒與設定
- 選配：ST25DV16 NFC 標籤模組（I2C）
- 深度足夠放入面板的相框；內部零件的 STEP 檔在 `CAD/`

### 接線

| 功能 | ESP32-C6 GPIO | 備註 |
| --- | --- | --- |
| 電子紙 BUSY | 18 | 輸入，內部上拉 |
| 電子紙 RST | 14 | |
| 電子紙 DC | 8 | |
| 電子紙 CS | 1 | |
| 電子紙 SCLK | 23 | SPI 時脈 |
| 電子紙 DIN | 22 | SPI MOSI |
| 電子紙 VCC / GND | 3V3 / GND | |
| 按鈕 | 2 | 接 GND，內部上拉；喚醒與設定 |
| 電池偵測 | 0（ADC） | 經 1:2 分壓 |
| NFC SDA | 19 | I2C，選配 |
| NFC SCL | 20 | I2C，選配 |
| NFC VCC | 4 | 由 GPIO 直接供電，睡眠期間保持低電位 |

## 伺服器

### 以 Docker Compose 執行（建議）

```bash
git clone https://github.com/jwchen119/EPF.git
cd EPF
cp .env.example .env        # 然後把你的 Immich API 金鑰填進去
docker compose up -d
```

設定頁在 `http://<主機>:15001/`。compose 檔把 `./config` 與 `./photos` 掛載進容器，所以設定、已顯示照片的紀錄、事件記錄與通知憑證都能在 `docker compose pull` 與重建容器後保留。它也設定了 `TZ`，這很重要：安靜時段與喚醒排程都以本地時間計算。

其餘全部在設定頁操作，沒有需要手動編輯的設定檔。

### 環境變數

| 變數 | 預設 | 用途 |
| --- | --- | --- |
| `IMMICH_API_KEY` | 必填 | Immich 網頁介面 → 帳號設定 → API 金鑰。啟動時讀取一次。 |
| `EPF_PORT` | `15001` | 設定頁與相框使用的主機埠。必須與相框設定入口中儲存的伺服器網址一致。 |
| `TZ` | `Asia/Taipei` | 本地時區。沒有設定時容器以 UTC 運行，安靜時段會偏移一個時差。 |
| `IMMICH_PHOTO_DEST` | `/photos` | 存放 `tracking.txt` 與 `events.jsonl` 的位置。不會有照片寫入磁碟。 |

### 不用 Compose 執行

```bash
docker run --name epf \
    -e IMMICH_API_KEY='<你的 Immich API 金鑰>' \
    -e TZ=Asia/Taipei \
    -v "$(pwd)/config:/config" \
    -v "$(pwd)/photos:/photos" \
    -d -p 15001:5000 jwchen119/epf
```

預建映像在 [Docker Hub](https://hub.docker.com/r/jwchen119/epf)。要自行建置，在倉庫根目錄執行 `docker build -t jwchen119/epf .`，或把 `docker-compose.yml` 裡的 `build: .` 取消註解。

### 資料存放位置

| 容器內路徑 | 內容 |
| --- | --- |
| `/config/config.yaml` | 從網頁儲存的設定。第一次啟動時以預設值建立，並監看外部修改。 |
| `/config/credentials.json` | Telegram 與 LINE 的權杖，只在測試訊息成功後寫入。 |
| `/photos/tracking.txt` | 目前相簿中哪些照片已經顯示過。 |
| `/photos/events.jsonl` | 設定頁顯示的系統記錄。 |

### HTTP 端點

韌體使用的兩個：

| 端點 | 使用者 | 用途 |
| --- | --- | --- |
| `GET /download` | 相框 | 下一張照片的十六進位位元組串流，已預先準備好，相框不必在列出相簿與處理影像時保持清醒。請求標頭 `batteryCap` 帶電池電壓（毫伏）；回應標頭 `X-Photo-Url` 帶照片的 Immich 連結供 NFC 標籤使用。 |
| `GET /sleep` | 相框 | `{current_time, next_wakeup, sleep_duration}`；`sleep_duration` 單位為毫秒，已考慮安靜時段。 |

其餘端點服務設定頁：`/setting`（GET 顯示，POST 儲存）、`/status`、`/log`、`/log/clear`、`/next`（GET 顯示，POST 重新選擇）、`/preview/original`、`/preview/next`，以及 `/notify/bind`、`/notify/unbind`、`/notify/channels`、`/notify/test`。設定頁沒有身分驗證，請把埠留在區網內，或放在會加上驗證的反向代理後面。

### 給開發者的備註

- `cpy.so` 是提交在倉庫裡、預先編譯好的 Linux x86-64 Cython 模組。修改 `cpy.pyx` 不會有效果，除非在 Linux 上重新建置（`cython` 加 NumPy 標頭）並替換該二進位檔。這個模組無法在 Windows 載入，所以 `python app.py` 只能在 Linux 或 Docker 中執行。
- 伺服器端的模組配置、影像管線與完整的 HTTP 契約記錄在 `CLAUDE.md`。
- 三組調色盤必須一致：`cpy.pyx` 內的純 RGB 調色盤、`epf/imaging.py` 內實測的面板顏色，以及 `Arduino/epd7in3e.h` 內的 `EPD_7IN3E_*` 顏色代碼。

## 韌體

### 從瀏覽器安裝（最簡單）

網頁安裝器 **https://jwchen119.github.io/EPF/** 可以用 Chrome 或 Edge 把已發布的韌體寫進相框，不需要安裝任何東西。每個版本有兩個按鈕：**升級**只寫入程式區並保留 Wi-Fi 與伺服器設定（被問到「Erase device」時不要勾選）；**完整安裝**寫入全部內容並清除設定，給全新的板子用。先把相框喚醒，因為它的 USB 埠只在醒著時存在：短按可讓它醒約 40 秒，開機時長按 3 秒會進入設定畫面並保持清醒 5 分鐘。

這個頁面就是倉庫裡的 `docs/` 資料夾，由 GitHub Pages 提供。要發布新版本，先建置韌體，再執行 `python docs/firmware/add_version.py <版本> --notes-en ... --notes-zh ...`，它會把映像複製到 `docs/firmware/v<版本>/`、寫入 manifest 並更新版本清單。

### 以 PlatformIO 建置

用 VS Code 搭配 PlatformIO 或 pioarduino 擴充套件開啟 `Arduino` 資料夾，或在命令列：

```bash
cd Arduino
pio run                 # 建置
pio run -t upload       # 透過 USB 燒錄
pio device monitor      # 序列埠輸出，115200 baud
```

`platformio.ini` 會拉入 ESP32-C6 板卡支援（pioarduino 分支的 Espressif 平台，因為上游尚未支援 C6）、`min_spiffs` 分割表與所有函式庫：ArduinoJson 7、AsyncTCP 與 ESPAsyncWebServer（ESP32Async 分支）、NTPClient、STM32duino ST25DV 與 QRCode。

`pio run -t upload` 只寫入 bootloader、分割表與應用程式，所以存在 NVS 的 Wi-Fi 與伺服器設定在更新後仍會保留。建置同時也會產生 `firmware.factory.bin`，這是給從位址 0 寫入的工具（例如 [web.esphome.io](https://web.esphome.io/)）用的單一映像；寫入它會清除整顆 flash，包括那些設定，相框之後會進入設定模式。相框的 USB 埠只在醒著時存在，所以上傳前先按一下按鈕（或長按進入設定畫面）。

### 以 Arduino IDE 建置

1. 安裝 ESP32 板卡套件（3.x），選擇 **DFRobot FireBeetle 2 ESP32-C6**。
2. 把 `Arduino` 資料夾複製到別處並改名為 `epd7in3e`，以符合 `epd7in3e.ino`。
3. 從 Library Manager 安裝：ArduinoJson（7.x）、Async TCP 與 ESP Async WebServer（ESP32Async 版本）、STM32duino ST25DV、QRCode（Richard Moore）。
4. 選擇應用程式空間至少 1.9 MB 的分割方案（例如「Minimal SPIFFS」），然後上傳。

即使沒有裝 NFC 標籤，編譯仍需要該函式庫；執行時找不到標籤會直接略過 NFC 寫入。

### 初次設定

1. 給相框供電，並在開機時長按按鈕約 3 秒。序列埠監視器會印出 `long press`，面板顯示設定畫面（網路名稱、網址與兩個 QR code），ESP32 開啟名為 `ESP32_ePAPER` 的熱點。沒有儲存任何網路的相框會自動顯示同一個畫面。
2. 連上熱點（掃第一個 QR code，或手動選擇網路）；設定頁會自動開啟。若沒有，掃第二個 QR code 或瀏覽 `http://4.3.2.1`。熱點在 5 分鐘後關閉。
3. 選擇你的 Wi-Fi、輸入密碼與伺服器網址，例如 `http://192.168.1.10:15001`。最多記住五組網路並依序嘗試。
4. 儲存。相框連線、抓取第一張照片，然後進入睡眠。

之後要修改設定，用同樣方式在重新開機時長按按鈕。已儲存的網路會列在頁面上，可直接選擇而不必重新輸入密碼。

### 日常行為

- 依伺服器回傳的排程喚醒，或短按按鈕立即喚醒。
- 電壓低於 3.05 V 時，相框清除畫面並睡 24 小時以保護電池。
- 伺服器錯誤（HTTP 500）在同一次喚醒內最多重試五次，每次間隔十秒。若照片到了但排程沒到，相框睡一小時。
- 一次喚醒沒有拿到新照片（沒有 Wi-Fi、連不上伺服器、下載被拒）時，相框保留目前的照片，在 15、30、60 分鐘後安靜地重試。第四次也失敗時才畫出錯誤畫面，說明原因、伺服器網址、網路、電量與下次嘗試時間，之後每 6 小時檢查一次以節省電池。按下按鈕一律立即重試、把排程重設為 15 分鐘，若那次也失敗則顯示錯誤畫面。第一張成功的照片會清除計數。
- 初次設定後，在設定頁設定好相簿之前，伺服器會回應錯誤。設定好後，等下次重試，或按一下按鈕立即抓第一張照片。
- 電池耗盡時，面板會顯示充電提醒而不是變成空白。
- 若面板在 60 秒內沒有回應，韌體會放棄這次刷新而不是卡住。
- 裝有 NFC 標籤時，抓取新照片期間標籤顯示「Updating...」，之後帶著目前顯示照片的連結。標籤在深度睡眠期間斷電。

### 編輯設定入口頁面

`WifiCaptivePage.h` 是入口頁的 HTML，以 gzip 壓縮成 C 陣列。原始檔是 `Arduino/AP_webpage_src/index.html`。修改後執行：

```bash
python Arduino/AP_webpage_src/compress_html.py
```

`decompress_html.py` 可以反向從標頭檔還原 HTML。

## 致謝

- `WifiCaptive*` 改編自 [TRMNL 韌體](https://github.com/usetrmnl/firmware/tree/main/lib/wificaptive)。
- `epd7in3e.*` 與 `epdif.*` 以 Waveshare 的 7.3 吋 E6 面板驅動為基礎。

## 授權

MIT，見 `LICENSE`。
