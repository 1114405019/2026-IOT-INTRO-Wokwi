from machine import Pin, I2C
import sh1107
import dht
import time

# ── 可調校常數 ──────────────────────────────────────────────────────────────
oled_width       = 128
oled_height      = 128
SENSOR_INTERVAL  = 2000   # ms，DHT22 讀值間隔
FRAME_INTERVAL   = 250    # ms，動畫幀率
STUDENT_ID       = "1114405019"

# [主視覺座標]
circle_cx        = 36
circle_cy        = 56
circle_r1        = 24
circle_r2        = 21
star_size        = 9

# [中文動畫座標]
chinese_base_x   = 90
chinese_base_y   = 16

# [英文校名座標]
english_x        = 2
english_y_line1  = 104
english_y_line2  = 112
english_y_line3  = 120

# [其他資訊]
year_x           = 96
year_y           = 2
temp_x           = 2
temp_y           = 2
sid_x            = 2
sid_y            = 14

# ── 硬體初始化 ──────────────────────────────────────────────────────────────
i2c        = I2C(0, scl=Pin(21), sda=Pin(22))
oled       = sh1107.SH1107_I2C(oled_width, oled_height, i2c, address=0x3C, rotate=0)
dht_sensor = dht.DHT22(Pin(23))

# ── 小型英文字型 3x5 ────────────────────────────────────────────────────────
FONT_3X5 = {
    "A": ("111", "101", "111", "101", "101"), "C": ("111", "100", "100", "100", "111"),
    "D": ("110", "101", "101", "101", "110"), "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"), "G": ("111", "100", "101", "101", "111"),
    "H": ("101", "101", "111", "101", "101"), "I": ("111", "010", "010", "010", "111"),
    "L": ("100", "100", "100", "100", "111"), "N": ("101", "111", "111", "111", "101"),
    "O": ("111", "101", "101", "101", "111"), "P": ("111", "101", "111", "100", "100"),
    "R": ("111", "101", "111", "110", "101"), "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"), "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"), "Y": ("101", "101", "010", "010", "010"),
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"), "6": ("111", "100", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "001"), " ": ("000", "000", "000", "000", "000"),
    "?": ("111", "001", "011", "000", "010"),
}


def draw_tiny_text(display, text, x, y, color=1):
    cursor_x = x
    for ch in text.upper():
        glyph = FONT_3X5.get(ch, FONT_3X5["?"])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    display.pixel(cursor_x + col, y + row, color)
        cursor_x += 4


# ── 中文點陣 32x32 NotoSerifCJK-Bold ───────────────────────────────────────
FONT_82B1 = bytearray(
    b'\x00\x00\x00\x00\x00\x7c\x1e\x00\x00\x78\x1c\x10\x00\x78\x1c\x18\x00\x78\x1c\x3c\x7f\xff\xff\xfe'
    b'\x00\x78\x1c\x00\x00\x78\x1c\x00\x00\x78\x1c\x00\x00\x00\x00\x00\x00\xf0\xf8\x00\x00\xf8\xf0\x00'
    b'\x01\xf0\xf0\x70\x01\xe0\xf0\xf8\x03\xc0\xf1\xf0\x03\xc0\xf1\xe0\x07\xe0\xf3\xc0\x0f\xe0\xf7\x00'
    b'\x0d\xe0\xfc\x00\x19\xe0\xf0\x00\x31\xe0\xf0\x00\x41\xe0\xf0\x00\x01\xe0\xf0\x04\x01\xe0\xf0\x04'
    b'\x01\xe0\xf0\x04\x01\xe0\xf0\x0c\x01\xe0\xf0\x0c\x01\xe0\xff\xfe\x01\xe0\xff\xfe\x01\xe0\x7f\xfe'
    b'\x01\xc0\x0f\xe0\x00\x00\x00\x00'
)

FONT_706B = bytearray(
    b'\x00\x00\x00\x00\x00\x07\x00\x00\x00\x07\x80\x00\x00\x07\x80\x00\x00\x07\x80\x00\x00\x07\x80\x00'
    b'\x00\x07\x80\x00\x01\x07\x80\x60\x01\x07\x80\xf0\x01\x87\xc0\xfc\x01\x87\xc1\xf0\x03\x87\xc3\xe0'
    b'\x03\x87\xc3\xc0\x07\x8f\x47\x00\x0f\x8f\x6e\x00\x1f\x0f\x68\x00\x1f\x0f\x30\x00\x1e\x0f\x30\x00'
    b'\x00\x1e\x30\x00\x00\x1e\x38\x00\x00\x1e\x1c\x00\x00\x3c\x1e\x00\x00\x38\x1e\x00\x00\x78\x0f\x80'
    b'\x00\xf0\x0f\xc0\x01\xe0\x07\xf0\x03\xc0\x03\xfc\x07\x00\x01\xfe\x0e\x00\x00\xf8\x18\x00\x00\x70'
    b'\x40\x00\x00\x10\x00\x00\x00\x00'
)

FONT_7BC0 = bytearray(
    b'\x07\x80\x38\x00\x07\x84\x7c\x18\x07\x0e\x78\x3c\x0f\xff\x7f\xfe\x0e\xe0\xe7\x00\x1c\x70\xc3\x80'
    b'\x18\x71\x83\xc0\x30\x71\x03\xc0\x60\x74\x01\x90\x0c\x0e\x38\x38\x0f\xff\x3f\xfc\x0e\x0f\x38\x3c'
    b'\x0e\x0f\x38\x3c\x0e\x0f\x38\x3c\x0f\xff\x38\x3c\x0e\x0f\x38\x3c\x0e\x0f\x38\x3c\x0e\x0f\x38\x3c'
    b'\x0e\x0f\x38\x3c\x0f\xff\x38\x3c\x0e\x0e\x38\x3c\x0e\x20\x38\x3c\x0e\x38\x38\x3c\x0e\x1c\x38\xf8'
    b'\x0e\x1e\x38\x78\x1f\xff\x38\x78\x7f\xc7\x38\x60\x7f\x07\x38\x00\x3c\x07\x38\x00\x20\x00\x38\x00'
    b'\x00\x00\x30\x00\x00\x00\x00\x00'
)

CHARS = {'花': (FONT_82B1, 32, 32), '火': (FONT_706B, 32, 32), '節': (FONT_7BC0, 32, 32)}


def glyph_pixel(data, width, x, y):
    row_bytes = (width + 7) // 8
    return (data[y * row_bytes + x // 8] >> (7 - (x % 8))) & 1


def draw_char(display, char, x, y, shrink=1, wrap_y=False):
    if char not in CHARS:
        return
    data, w, h = CHARS[char]
    out_w, out_h = (w + shrink - 1) // shrink, (h + shrink - 1) // shrink
    for oy in range(out_h):
        for ox in range(out_w):
            if glyph_pixel(data, w, ox * shrink, oy * shrink):
                px, py = x + ox, y + oy
                if wrap_y:
                    py %= oled_height
                if 0 <= px < oled_width and 0 <= py < oled_height:
                    display.pixel(px, py, 1)


def draw_circle(display, cx, cy, r, color=1):
    x, y, err = r, 0, 0
    while x >= y:
        display.pixel(cx + x, cy + y, color); display.pixel(cx + y, cy + x, color)
        display.pixel(cx - y, cy + x, color); display.pixel(cx - x, cy + y, color)
        display.pixel(cx - x, cy - y, color); display.pixel(cx - y, cy - x, color)
        display.pixel(cx + y, cy - x, color); display.pixel(cx + x, cy - y, color)
        y += 1
        if err <= 0:
            err += 2 * y + 1
        if err > 0:
            x -= 1
            err -= 2 * x + 1


def draw_star(display, cx, cy, size, color=1):
    pts = [
        (cx,                        cy - size),
        (cx + int(size * 0.35),     cy - int(size * 0.25)),
        (cx + size,                 cy - int(size * 0.2)),
        (cx + int(size * 0.5),      cy + int(size * 0.25)),
        (cx + int(size * 0.6),      cy + size),
        (cx,                        cy + int(size * 0.45)),
        (cx - int(size * 0.6),      cy + size),
        (cx - int(size * 0.5),      cy + int(size * 0.25)),
        (cx - size,                 cy - int(size * 0.2)),
        (cx - int(size * 0.35),     cy - int(size * 0.25)),
    ]
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        display.line(x1, y1, x2, y2, color)


def draw_static_scene(display):
    display.fill(0)
    draw_circle(display, circle_cx, circle_cy, circle_r1, 1)
    draw_circle(display, circle_cx, circle_cy, circle_r2, 1)
    draw_star(display, circle_cx, circle_cy, star_size, 1)
    draw_tiny_text(display, "Penghu University",    english_x, english_y_line1)
    draw_tiny_text(display, "of Science and Tech",  english_x, english_y_line2)
    draw_tiny_text(display, "Dept of CSIE",         english_x, english_y_line3)
    display.text("2026", year_x, year_y)


def draw_chinese_animation(display, frame):
    chars = "花火節"
    base_y, base_x, spacing = chinese_base_y, chinese_base_x, 6
    wave = (-3, 0, 3, 0)
    active = frame % len(chars)
    cy = base_y
    for i, ch in enumerate(chars):
        enlarged = (i == active)
        shrink = 1 if enlarged else 2
        size = 32 if enlarged else 16
        x = (base_x - 8) if enlarged else base_x
        y = cy + wave[(frame + i) % len(wave)]
        if enlarged:
            y -= 4
        draw_char(display, ch, x, y, shrink=shrink, wrap_y=False)
        cy += (24 + spacing) if enlarged else (16 + spacing)


def draw_temperature(display, temp_str):
    display.text(temp_str, temp_x, temp_y)
    draw_tiny_text(display, STUDENT_ID, sid_x, sid_y)


def read_sensor_safe():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except:
        return None, None


frame = 0
last_sensor = time.ticks_ms() - SENSOR_INTERVAL
temp_str = "--.- C"

while True:
    now = time.ticks_ms()
    if time.ticks_diff(now, last_sensor) >= SENSOR_INTERVAL:
        t, h = read_sensor_safe()
        if t is not None:
            temp_str = "{:.1f} C".format(t)
        last_sensor = now

    draw_static_scene(oled)
    draw_chinese_animation(oled, frame)
    draw_temperature(oled, temp_str)
    oled.show()
    frame = (frame + 1) % 3
    time.sleep_ms(FRAME_INTERVAL)
