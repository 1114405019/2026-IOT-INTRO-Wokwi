from machine import Pin, I2C
import sh1107
import dht
import time
import math

# ============================================================
# 可調校常數
# ============================================================
STUDENT_ID    = "1114405019"  # 學號

# --- 顯示器 ---
oled_width    = 128
oled_height   = 128
center_x      = 64
center_y      = 90           # SH1107 Wokwi 校正視覺中心
text_y_offset = 36

# --- 計時 ---
ANIM_MS       = 250          # 動畫更新間隔 (ms)
SENSOR_MS     = 2000         # DHT22 讀取間隔 (ms)

# --- 溫度視覺化門檻 ---
TEMP_COOL_MAX = 20.0         # 低於此：涼爽區間
TEMP_HOT_MIN  = 30.0         # 高於此：炎熱區間

# --- 各溫度區間對應龍珠尺寸 (外圓半徑, 內圓半徑, 星半徑) ---
DRAGON_COOL   = (27, 24,  9)  # 涼爽：小龍珠
DRAGON_NORMAL = (35, 32, 13)  # 舒適：中龍珠
DRAGON_HOT    = (41, 38, 17)  # 炎熱：大龍珠

# --- 花火節動畫參數 ---
CHINESE_BASE_X  = 104        # 中文字欄 x 起點
CHINESE_BASE_YS = [78, 100, 122]  # 三字固定基準 y
CHINESE_WAVE    = (-2, 0, 2, 0)   # 波浪位移陣列

# ============================================================
# 硬體初始化
# ============================================================
i2c = I2C(0, scl=Pin(21), sda=Pin(22))
oled = sh1107.SH1107_I2C(oled_width, oled_height, i2c, address=0x3C, rotate=0)
dht_sensor = dht.DHT22(Pin(23))

# ============================================================
# 3x5 點陣英文字型
# ============================================================
FONT_3X5 = {
    "A": ("111","101","111","101","101"), "B": ("110","101","110","101","110"),
    "C": ("111","100","100","100","111"), "D": ("110","101","101","101","110"),
    "E": ("111","100","111","100","111"), "F": ("111","100","110","100","100"),
    "G": ("111","100","101","101","111"), "H": ("101","101","111","101","101"),
    "I": ("111","010","010","010","111"), "J": ("011","001","001","101","111"),
    "K": ("101","110","100","110","101"), "L": ("100","100","100","100","111"),
    "M": ("101","111","111","101","101"), "N": ("101","111","111","111","101"),
    "O": ("111","101","101","101","111"), "P": ("111","101","111","100","100"),
    "R": ("111","101","111","110","101"), "S": ("111","100","111","001","111"),
    "T": ("111","010","010","010","010"), "U": ("101","101","101","101","111"),
    "V": ("101","101","101","101","010"), "W": ("101","101","111","111","101"),
    "X": ("101","101","010","101","101"), "Y": ("101","101","010","010","010"),
    "Z": ("111","001","010","100","111"),
    "0": ("111","101","101","101","111"), "1": ("010","110","010","010","111"),
    "2": ("111","001","111","100","111"), "3": ("111","001","111","001","111"),
    "4": ("101","101","111","001","001"), "5": ("111","100","111","001","111"),
    "6": ("111","100","111","101","111"), "7": ("111","001","001","001","001"),
    "8": ("111","101","111","101","111"), "9": ("111","101","111","001","111"),
    ".": ("000","000","000","000","010"), "-": ("000","000","111","000","000"),
    " ": ("000","000","000","000","000"), "?": ("111","001","011","000","010"),
    "%": ("101","001","010","100","101"), "/": ("001","001","010","100","100"),
}

def draw_tiny_text(display, text, x, y, color=1):
    cx = x
    for ch in text.upper():
        glyph = FONT_3X5.get(ch, FONT_3X5["?"])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    display.pixel(cx + col, y + row, color)
        cx += 4

# ============================================================
# 中文 32x32 點陣字模（以 shrink=2 輸出 16x16 效果）
# make_16x16() 在啟動時將 32x32 降採樣為真正的 16x16 bytearray
# ============================================================

# '花'  Unicode U+82B1  32x32
FONT_82B1_32 = bytearray(
    b'\x00\x00\x00\x00\x00\x7c\x1e\x00\x00\x78\x1c\x10'
    b'\x00\x78\x1c\x18\x00\x78\x1c\x3c\x7f\xff\xff\xfe'
    b'\x00\x78\x1c\x00\x00\x78\x1c\x00\x00\x78\x1c\x00'
    b'\x00\x00\x00\x00\x00\xf0\xf8\x00\x00\xf8\xf0\x00'
    b'\x01\xf0\xf0\x70\x01\xe0\xf0\xf8\x03\xc0\xf1\xf0'
    b'\x03\xc0\xf1\xe0\x07\xe0\xf3\xc0\x0f\xe0\xf7\x00'
    b'\x0d\xe0\xfc\x00\x19\xe0\xf0\x00\x31\xe0\xf0\x00'
    b'\x41\xe0\xf0\x00\x01\xe0\xf0\x04\x01\xe0\xf0\x04'
    b'\x01\xe0\xf0\x04\x01\xe0\xf0\x0c\x01\xe0\xf0\x0c'
    b'\x01\xe0\xff\xfe\x01\xe0\xff\xfe\x01\xe0\x7f\xfe'
    b'\x01\xc0\x0f\xe0\x00\x00\x00\x00'
)

# '火'  Unicode U+706B  32x32
FONT_706B_32 = bytearray(
    b'\x00\x00\x00\x00\x00\x07\x00\x00\x00\x07\x80\x00'
    b'\x00\x07\x80\x00\x00\x07\x80\x00\x00\x07\x80\x00'
    b'\x00\x07\x80\x00\x01\x07\x80\x60\x01\x07\x80\xf0'
    b'\x01\x87\xc0\xfc\x01\x87\xc1\xf0\x03\x87\xc3\xe0'
    b'\x03\x87\xc3\xc0\x07\x8f\x47\x00\x0f\x8f\x6e\x00'
    b'\x1f\x0f\x68\x00\x1f\x0f\x30\x00\x1e\x0f\x30\x00'
    b'\x00\x1e\x30\x00\x00\x1e\x38\x00\x00\x1e\x1c\x00'
    b'\x00\x3c\x1e\x00\x00\x38\x1e\x00\x00\x78\x0f\x80'
    b'\x00\xf0\x0f\xc0\x01\xe0\x07\xf0\x03\xc0\x03\xfc'
    b'\x07\x00\x01\xfe\x0e\x00\x00\xf8\x18\x00\x00\x70'
    b'\x40\x00\x00\x10\x00\x00\x00\x00'
)

# '節'  Unicode U+7BC0  32x32
FONT_7BC0_32 = bytearray(
    b'\x07\x80\x38\x00\x07\x84\x7c\x18\x07\x0e\x78\x3c'
    b'\x0f\xff\x7f\xfe\x0e\xe0\xe7\x00\x1c\x70\xc3\x80'
    b'\x18\x71\x83\xc0\x30\x71\x03\xc0\x60\x74\x01\x90'
    b'\x0c\x0e\x38\x38\x0f\xff\x3f\xfc\x0e\x0f\x38\x3c'
    b'\x0e\x0f\x38\x3c\x0e\x0f\x38\x3c\x0f\xff\x38\x3c'
    b'\x0e\x0f\x38\x3c\x0e\x0f\x38\x3c\x0e\x0f\x38\x3c'
    b'\x0e\x0f\x38\x3c\x0f\xff\x38\x3c\x0e\x0e\x38\x3c'
    b'\x0e\x20\x38\x3c\x0e\x38\x38\x3c\x0e\x1c\x38\xf8'
    b'\x0e\x1e\x38\x78\x1f\xff\x38\x78\x7f\xc7\x38\x60'
    b'\x7f\x07\x38\x00\x3c\x07\x38\x00\x20\x00\x38\x00'
    b'\x00\x00\x30\x00\x00\x00\x00\x00'
)

def _glyph_bit(data, width, x, y):
    """從 bytearray 點陣讀取 (x,y) 的 bit，MSB first。"""
    byte_idx = y * ((width + 7) // 8) + x // 8
    return (data[byte_idx] >> (7 - (x % 8))) & 1

def make_16x16(font32):
    """將 32x32 bytearray 降採樣為真正的 16x16 bytearray（32 bytes）。"""
    out = bytearray(32)
    for oy in range(16):
        for ox in range(16):
            if _glyph_bit(font32, 32, ox * 2, oy * 2):
                out[oy * 2 + ox // 8] |= (1 << (7 - (ox % 8)))
    return out

# 啟動時預先產生 16x16 字模
FONT_82B1_16 = make_16x16(FONT_82B1_32)
FONT_706B_16 = make_16x16(FONT_706B_32)
FONT_7BC0_16 = make_16x16(FONT_7BC0_32)

def make_8x8(font32):
    """將 32x32 bytearray 降採樣為 8x8 bytearray（8 bytes）。"""
    out = bytearray(8)
    for oy in range(8):
        for ox in range(8):
            if _glyph_bit(font32, 32, ox * 4, oy * 4):
                out[oy] |= (1 << (7 - ox))
    return out

FONT_7BC0_8 = make_8x8(FONT_7BC0_32)

CHARS_8  = {'節': FONT_7BC0_8}
CHARS_16 = {'花': FONT_82B1_16, '火': FONT_706B_16, '節': FONT_7BC0_16}
CHARS_32 = {'花': FONT_82B1_32, '火': FONT_706B_32, '節': FONT_7BC0_32}

def draw_char(display, ch, x, y, size=16, wrap_y=False):
    """
    畫一個中文字。size=8/16/32 分別用對應字模。
    wrap_y=True 時，超出底部的像素接回頂部（SH1107 Wokwi 特性）。
    """
    if size == 32:
        data, w = CHARS_32.get(ch), 32
    elif size == 8:
        data, w = CHARS_8.get(ch), 8
    else:
        data, w = CHARS_16.get(ch), 16
    if data is None:
        return
    for oy in range(w):
        for ox in range(w):
            if _glyph_bit(data, w, ox, oy):
                px = x + ox
                py = y + oy
                if wrap_y:
                    py %= oled_height
                if 0 <= px < oled_width and 0 <= py < oled_height:
                    display.pixel(px, py, 1)

# ============================================================
# 圓形（Bresenham）與五角星（數學公式）
# ============================================================

def draw_circle(display, cx, cy, r, color=1):
    x, y, err = r, 0, 0
    while x >= y:
        display.pixel(cx + x, cy + y, color)
        display.pixel(cx + y, cy + x, color)
        display.pixel(cx - y, cy + x, color)
        display.pixel(cx - x, cy + y, color)
        display.pixel(cx - x, cy - y, color)
        display.pixel(cx - y, cy - x, color)
        display.pixel(cx + y, cy - x, color)
        display.pixel(cx + x, cy - y, color)
        y += 1
        if err <= 0:
            err += 2 * y + 1
        if err > 0:
            x -= 1
            err -= 2 * x + 1

def draw_star(display, cx, cy, outer_r, color=1):
    """用數學公式畫五角星：5 個外頂點 + 5 個內凹點交替連線。"""
    inner_r = int(outer_r * 0.382)  # 黃金比例內圓半徑
    pts = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5   # 每步 36°
        r = outer_r if (i % 2 == 0) else inner_r
        pts.append((cx + int(r * math.cos(angle)),
                    cy - int(r * math.sin(angle))))
    for i in range(10):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 10]
        display.line(x1, y1, x2, y2, color)

# ============================================================
# 四個主要函式
# ============================================================

def draw_static_scene(display, temp_c=25.0):
    """清空畫面並畫靜態底圖：龍珠（大小隨溫度）、校名、年份、學號。"""
    display.fill(0)

    # 依溫度區間選龍珠尺寸
    if temp_c < TEMP_COOL_MAX:
        o_r, i_r, s_r = DRAGON_COOL
    elif temp_c > TEMP_HOT_MIN:
        o_r, i_r, s_r = DRAGON_HOT
    else:
        o_r, i_r, s_r = DRAGON_NORMAL

    draw_circle(display, center_x, center_y, o_r, 1)
    draw_circle(display, center_x, center_y, i_r, 1)
    draw_star(display, center_x, center_y, s_r, 1)

    # 校名（3x5 字型）
    def ty(y):
        return y + text_y_offset
    draw_tiny_text(display, "Penghu University",   2, ty(2))
    draw_tiny_text(display, "of Science and Tech", 2, ty(10))
    draw_tiny_text(display, "Dept of CSIE",        2, ty(18))
    display.text("2026", 88, ty(2))
    draw_tiny_text(display, STUDENT_ID, 2, ty(26))


def draw_chinese_animation(display, frame):
    """
    花火節直排波浪動畫。
    每幀有一個字放大（32x32），其餘縮小（16x16）。
    base_ys 為固定基準，不隨放大字改變，避免 16x16 字互相壓疊。
    wave 幅度 ±2 < 間隔 6 的一半，確保非放大字不重疊。
    """
    chars   = "花火節"
    base_x  = CHINESE_BASE_X
    base_ys = CHINESE_BASE_YS
    wave    = CHINESE_WAVE
    active  = frame % len(chars)

    for i, ch in enumerate(chars):
        enlarged = (i == active)
        wo       = wave[(frame + i) % len(wave)]

        if i == 2:          # 節：一律比花/火小一號（8x8 / 16x16）
            size = 16 if enlarged else 8
            if enlarged:
                x = base_x - 4          # 16px 字靠左補 4px 使視覺置中
                y = base_ys[i] - 4 + wo
            else:
                x = base_x + 4          # 8px 字右移 4px 使視覺置中
                y = base_ys[i] + wo
        else:               # 花、火：16x16 / 32x32
            size = 32 if enlarged else 16
            if enlarged:
                x = base_x - 8
                y = base_ys[i] - 8 + wo
            else:
                x = base_x
                y = base_ys[i] + wo

        draw_char(display, ch, x, y, size=size, wrap_y=True)


def draw_temperature(display, temp_c, humidity, has_error=False):
    """在畫面左上角顯示溫濕度（或錯誤訊息）。"""
    if has_error:
        display.text("Sensor Err", 2, 4)
        display.text("-- .- C", 2, 14)
        return
    temp_str = "{:.1f} C".format(temp_c)
    hum_str  = "H:{:.0f}%".format(humidity)
    display.text(temp_str, 2, 4)
    display.text(hum_str,  2, 14)


def read_sensor_safe(sensor, last_temp, last_hum):
    """
    安全讀取 DHT22。
    成功：回傳 (temp, hum, False)，並在 Serial 印出 debug。
    失敗：保留前次有效值，回傳 (last_temp, last_hum, True)。
    """
    try:
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
        print("[DEBUG] temperature = {:.1f}C, humidity = {:.1f}%".format(t, h))
        return t, h, False
    except Exception as e:
        print("[ERROR] DHT22 read failed:", e)
        return last_temp, last_hum, True

# ============================================================
# 主迴圈（非阻塞計時）
# ============================================================
frame        = 0
temp_c       = 25.0
humidity     = 50.0
sensor_error = False

last_anim_ms   = time.ticks_ms()
last_sensor_ms = time.ticks_ms()

while True:
    now = time.ticks_ms()

    # B. 每 2 秒讀一次 DHT22
    if time.ticks_diff(now, last_sensor_ms) >= SENSOR_MS:
        temp_c, humidity, sensor_error = read_sensor_safe(
            dht_sensor, temp_c, humidity)
        last_sensor_ms = now

    # A/C/D. 每 250ms 更新一幀動畫
    if time.ticks_diff(now, last_anim_ms) >= ANIM_MS:
        draw_static_scene(oled, temp_c)   # C. 靜態底圖（龍珠隨溫度縮放）
        draw_chinese_animation(oled, frame)  # A. 花火節動畫
        draw_temperature(oled, temp_c, humidity, sensor_error)  # C. 溫度
        oled.show()                        # D. 更新顯示
        frame = (frame + 1) % 12
        last_anim_ms = now
