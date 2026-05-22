# Week 13 Homework — SH1107 中文動畫溫度看板

**學號**：1114405019  
**平台**：ESP32 + MicroPython (Wokwi)  
**顯示器**：Grove SH1107 OLED 128×128

---

## 版面配置

```
┌─────────────────────────────────┐  y=0
│ 28.5 C          (溫度)          │  y=4
│ H:65%           (濕度)          │  y=14
│                                 │
│ Penghu University        2026   │  y=38
│ of Science and Tech             │  y=46
│ Dept of CSIE                    │  y=54
│ 1114405019      (學號)          │  y=62
│                                 │
│        ◯◯  (龍珠雙圓)           │  center y=90
│       ★    (五角星)             │
│                          花     │  y=78
│                          火     │  y=100
│                          節     │  y=122
└─────────────────────────────────┘  y=128
```

左半：資訊文字區（校名、溫濕度、學號）  
中央：龍珠主視覺（圓＋五角星，大小隨溫度改變）  
右側：花火節直排波浪動畫

---

## 動畫設計

每 **250 ms** 更新一幀，`frame` 從 0 循環至 11：

- `frame % 3 == 0`：「花」放大為 32×32，其他為 16×16 / 8×8
- `frame % 3 == 1`：「火」放大
- `frame % 3 == 2`：「節」放大（最大僅 16×16，比花火小一號）
- 波浪陣列 `(-2, 0, 2, 0)` 讓三字輪流上下浮動

---

## 溫度視覺化（加分項）

龍珠大小依溫度三段切換：

| 區間 | 外圓 r | 內圓 r | 星 r | 說明 |
|------|--------|--------|------|------|
| < 20 °C | 27 | 24 | 9  | 涼爽：小龍珠 |
| 20–30 °C | 35 | 32 | 13 | 舒適：中龍珠（預設）|
| > 30 °C | 41 | 38 | 17 | 炎熱：大龍珠 |

---

## 參數化設定（加分項）

頂部可調常數一覽：

```python
ANIM_MS       = 250          # 動畫更新間隔 (ms)
SENSOR_MS     = 2000         # DHT22 讀取間隔 (ms)
TEMP_COOL_MAX = 20.0         # 涼爽門檻 (°C)
TEMP_HOT_MIN  = 30.0         # 炎熱門檻 (°C)
DRAGON_COOL   = (27, 24,  9) # 涼爽龍珠尺寸
DRAGON_NORMAL = (35, 32, 13) # 舒適龍珠尺寸
DRAGON_HOT    = (41, 38, 17) # 炎熱龍珠尺寸
CHINESE_BASE_X  = 104        # 中文字欄 x 起點
CHINESE_BASE_YS = [78,100,122] # 三字固定基準 y
CHINESE_WAVE    = (-2, 0, 2, 0) # 波浪位移
center_x      = 64
center_y      = 90           # SH1107 Wokwi 校正視覺中心
```

---

## DHT22 整合

每 2 秒在非阻塞計時器觸發時呼叫 `read_sensor_safe()`：

```python
try:
    dht_sensor.measure()
    t = dht_sensor.temperature()
    h = dht_sensor.humidity()
    print("[DEBUG] temperature = {:.1f}C, humidity = {:.1f}%".format(t, h))
    return t, h, False
except Exception as e:
    print("[ERROR] DHT22 read failed:", e)
    return last_temp, last_hum, True   # 保留前次有效值
```

讀值失敗時 OLED 顯示 `Sensor Err`，程式繼續執行不崩潰。

---

## 系統流程圖

```
          開機
            │
            ▼
      硬體初始化
   (I2C / OLED / DHT22)
            │
            ▼
      生成 16x16 / 8x8
         中文字模
            │
            ▼
    ┌───────────────────┐
    │   主迴圈 while True │
    └───────┬───────────┘
            │
     now = ticks_ms()
            │
     ┌──────┴──────┐
     │             │
  2000ms         250ms
  到期?          到期?
     │             │
     ▼             ▼
read_sensor    draw_static_scene(temp)
_safe()        draw_chinese_animation(frame)
     │         draw_temperature(temp, hum)
  更新            oled.show()
temp/hum       frame = (frame+1) % 12
     │             │
     └──────┬──────┘
            │
         回到頂部
```

---

## 狀態機（動畫幀）

```
        frame % 3

    ┌────────────────────────────────────┐
    │                                    │
    ▼                                    │
[狀態 0: 花 放大]  ──250ms──▶  [狀態 1: 火 放大]
    ▲                                    │
    │                                    ▼
    └──────── 250ms ─── [狀態 2: 節 放大] ◀──250ms──┘
```

每個狀態：
- **active char**：32×32（花/火）或 16×16（節）
- **other chars**：16×16（花/火）或 8×8（節）
- wave 陣列讓每字在 y 軸 ±2px 浮動

---

## 遇到的問題與解法

**問題**：非放大的 16×16 字因 `cy` 累積計算＋wave 位移，在特定幀出現 6px 重疊。

**解法**：改用固定 `base_ys = [78, 100, 122]`，不讓「哪個字放大」影響其他字的基準位置；同時把 wave 幅度從 ±5 縮小至 ±2，確保相鄰字最小間距 ≥ 2px。
