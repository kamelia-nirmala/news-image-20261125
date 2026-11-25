"""WORLD NEWS front page renderer.

Pure standard-library image generation: a 1024x1024 RGB canvas drawn with
solid rectangles, discs and triangles, a hand-rolled 5x7 bitmap font, and a
minimal PNG encoder built on struct + zlib. Output is fully deterministic.
"""

import os
import struct
import zlib

W = 1024
H = 1024

BG = (15, 27, 45)
WHITE = (255, 255, 255)
SIGNAL = (255, 212, 59)

# 5 wide x 7 tall glyphs. Each row is 5 bits, bit 4 = leftmost pixel.
GLYPHS = {
    " ": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "-": (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    ",": (0b00000, 0b00000, 0b00000, 0b00000, 0b00110, 0b00100, 0b01000),
    ".": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00110, 0b00110),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    ":": (0b00000, 0b00110, 0b00110, 0b00000, 0b00110, 0b00110, 0b00000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "'": (0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100),
}

# Colour of pictogram cut-outs (window glass, chip core). Reassigned to the
# panel colour before each icon so the holes read as negative space.
_CUT = BG


def _isqrt(n):
    if n <= 0:
        return 0
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x


def paint_rect(buf, x, y, w, h, rgb):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(rgb) * (x1 - x0)
    span = len(row)
    stride = W * 3
    for yy in range(y0, y1):
        off = yy * stride + x0 * 3
        buf[off:off + span] = row


def paint_disc(buf, cx, cy, r, rgb):
    if r < 1:
        return
    r2 = r * r
    for dy in range(-r, r + 1):
        dx = _isqrt(r2 - dy * dy)
        paint_rect(buf, cx - dx, cy + dy, 2 * dx + 1, 1, rgb)


def paint_tri(buf, x1, y1, x2, y2, x3, y3, rgb):
    minx = max(0, min(x1, x2, x3))
    maxx = min(W - 1, max(x1, x2, x3))
    miny = max(0, min(y1, y2, y3))
    maxy = min(H - 1, max(y1, y2, y3))
    if maxx < minx or maxy < miny:
        return
    area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if area == 0:
        return
    sign = 1 if area > 0 else -1
    stride = W * 3
    for y in range(miny, maxy + 1):
        base = y * stride
        for x in range(minx, maxx + 1):
            w0 = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)
            w1 = (x3 - x2) * (y - y2) - (x - x2) * (y3 - y2)
            w2 = (x1 - x3) * (y - y3) - (x - x3) * (y1 - y3)
            if w0 * sign >= 0 and w1 * sign >= 0 and w2 * sign >= 0:
                off = base + x * 3
                buf[off] = rgb[0]
                buf[off + 1] = rgb[1]
                buf[off + 2] = rgb[2]


def measure_text(text, scale):
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def paint_text(buf, x, y, text, scale, rgb):
    pen = x
    for ch in text:
        rows = GLYPHS[ch]
        for ry in range(7):
            bits = rows[ry]
            col = 0
            while col < 5:
                if bits & (1 << (4 - col)):
                    start = col
                    while col < 5 and bits & (1 << (4 - col)):
                        col += 1
                    paint_rect(buf, pen + start * scale, y + ry * scale,
                               (col - start) * scale, scale, rgb)
                else:
                    col += 1
        pen += 6 * scale


def ico_rocket(buf, cx, cy):
    paint_tri(buf, cx - 10, cy - 14, cx + 10, cy - 14, cx, cy - 44, SIGNAL)
    paint_rect(buf, cx - 10, cy - 16, 20, 40, SIGNAL)
    paint_tri(buf, cx - 10, cy + 2, cx - 10, cy + 26, cx - 28, cy + 30, SIGNAL)
    paint_tri(buf, cx + 10, cy + 2, cx + 10, cy + 26, cx + 28, cy + 30, SIGNAL)
    paint_disc(buf, cx, cy - 2, 8, SIGNAL)
    paint_disc(buf, cx, cy - 2, 4, _CUT)


def ico_scales(buf, cx, cy):
    paint_rect(buf, cx - 3, cy - 36, 6, 66, SIGNAL)
    paint_rect(buf, cx - 20, cy + 28, 40, 8, SIGNAL)
    paint_rect(buf, cx - 38, cy - 36, 76, 6, SIGNAL)
    paint_rect(buf, cx - 34, cy - 30, 4, 14, SIGNAL)
    paint_rect(buf, cx + 30, cy - 30, 4, 14, SIGNAL)
    paint_tri(buf, cx - 44, cy - 16, cx - 24, cy - 16, cx - 34, cy + 2, SIGNAL)
    paint_tri(buf, cx + 24, cy - 16, cx + 44, cy - 16, cx + 34, cy + 2, SIGNAL)


def ico_burst(buf, cx, cy):
    paint_tri(buf, cx + 42, cy, cx + 16, cy - 9, cx + 16, cy + 9, SIGNAL)
    paint_tri(buf, cx - 42, cy, cx - 16, cy - 9, cx - 16, cy + 9, SIGNAL)
    paint_tri(buf, cx, cy - 42, cx - 9, cy - 16, cx + 9, cy - 16, SIGNAL)
    paint_tri(buf, cx, cy + 42, cx - 9, cy + 16, cx + 9, cy + 16, SIGNAL)
    paint_tri(buf, cx + 30, cy + 30, cx + 16, cy + 8, cx + 8, cy + 16, SIGNAL)
    paint_tri(buf, cx - 30, cy + 30, cx - 16, cy + 8, cx - 8, cy + 16, SIGNAL)
    paint_tri(buf, cx + 30, cy - 30, cx + 16, cy - 8, cx + 8, cy - 16, SIGNAL)
    paint_tri(buf, cx - 30, cy - 30, cx - 16, cy - 8, cx - 8, cy - 16, SIGNAL)
    paint_disc(buf, cx, cy, 9, SIGNAL)


def ico_chip(buf, cx, cy):
    paint_rect(buf, cx - 30, cy - 30, 60, 60, SIGNAL)
    paint_rect(buf, cx - 16, cy - 16, 32, 32, _CUT)
    paint_rect(buf, cx - 8, cy - 8, 16, 16, SIGNAL)
    for k in range(4):
        py = cy - 24 + k * 12
        paint_rect(buf, cx - 42, py, 12, 5, SIGNAL)
        paint_rect(buf, cx + 30, py, 12, 5, SIGNAL)
        px = cx - 24 + k * 12
        paint_rect(buf, px, cy - 42, 5, 12, SIGNAL)
        paint_rect(buf, px, cy + 30, 5, 12, SIGNAL)


def ico_plane(buf, cx, cy):
    paint_rect(buf, cx - 38, cy - 5, 76, 10, SIGNAL)
    paint_tri(buf, cx + 38, cy - 5, cx + 38, cy + 5, cx + 44, cy, SIGNAL)
    paint_tri(buf, cx - 2, cy - 5, cx - 2, cy + 5, cx - 34, cy - 40, SIGNAL)
    paint_tri(buf, cx - 2, cy - 5, cx - 2, cy + 5, cx - 34, cy + 40, SIGNAL)
    paint_tri(buf, cx - 38, cy - 5, cx - 38, cy + 5, cx - 44, cy - 26, SIGNAL)
    paint_tri(buf, cx - 38, cy - 5, cx - 38, cy + 5, cx - 44, cy + 26, SIGNAL)


def ico_ship(buf, cx, cy):
    paint_tri(buf, cx - 42, cy + 8, cx + 42, cy + 8, cx + 24, cy + 34, SIGNAL)
    paint_tri(buf, cx - 42, cy + 8, cx + 24, cy + 34, cx - 24, cy + 34, SIGNAL)
    paint_rect(buf, cx - 30, cy + 2, 60, 8, SIGNAL)
    paint_rect(buf, cx - 2, cy - 40, 4, 44, SIGNAL)
    paint_tri(buf, cx + 4, cy - 38, cx + 4, cy - 6, cx + 30, cy - 6, SIGNAL)
    paint_tri(buf, cx - 4, cy - 34, cx - 4, cy - 6, cx - 26, cy - 6, SIGNAL)


PANELS = (
    ((31, 111, 235), ico_rocket, ("SHENZHOU-24", "LAUNCHED 08:18", "FIRST FOREIGN")),
    ((217, 72, 15), ico_scales, ("US TARIFF PLAN", "14 PARTNERS", "CHINA 20%")),
    ((43, 138, 62), ico_burst, ("ISRAELI STRIKE", "HAMAS SECURITY", "CHIEF KILLED")),
    ((134, 46, 156), ico_chip, ("BANGLADESH", "MIN WAGE UP 36%", "17,000 TAKA")),
    ((194, 37, 92), ico_plane, ("CARTAGENA", "ALL HOSTAGES", "FREED IN RESCUE")),
    ((11, 114, 133), ico_ship, ("INDONESIA MINE", "RESCUE, 9 DEAD", "17 TRAPPED")),
)

PANEL_W = 492
PANEL_H = 270
COL_X = (16, 524)
ROW_Y = (150, 436, 722)
TEXT_X_OFF = 24
TEXT_Y_OFF = 118
LINE_STEP = 46
TEXT_SCALE = 5
MAX_LINE = 15


def build():
    global _CUT

    buf = bytearray(W * H * 3)
    paint_rect(buf, 0, 0, W, H, BG)

    paint_text(buf, 16, 28, "WORLD NEWS", 8, WHITE)
    paint_text(buf, 16, 88, "WEDNESDAY 25 NOVEMBER 2026", 5, WHITE)

    for index, (color, icon, lines) in enumerate(PANELS):
        px = COL_X[index % 2]
        py = ROW_Y[index // 2]

        paint_rect(buf, px, py, PANEL_W, PANEL_H, color)

        _CUT = color
        icon(buf, px + 246, py + 55)

        for row, line in enumerate(lines):
            assert len(line) <= MAX_LINE, "line %r exceeds %d chars" % (line, MAX_LINE)
            for ch in line:
                assert ch in GLYPHS, "no glyph for %r in %r" % (ch, line)
            width = measure_text(line, TEXT_SCALE)
            assert width <= PANEL_W - TEXT_X_OFF, (
                "line %r measures %dpx, panel allows %d"
                % (line, width, PANEL_W - TEXT_X_OFF)
            )
            paint_text(buf, px + TEXT_X_OFF, py + TEXT_Y_OFF + row * LINE_STEP,
                       line, TEXT_SCALE, WHITE)

    _CUT = BG
    return buf


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(path, buf):
    stride = W * 3
    raw = bytearray((stride + 1) * H)
    for y in range(H):
        src = y * stride
        dst = y * (stride + 1)
        raw[dst] = 0
        raw[dst + 1:dst + 1 + stride] = buf[src:src + stride]

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    buf = build()
    encode_png(os.path.join(out_dir, "entry.png"), buf)


if __name__ == "__main__":
    main()
