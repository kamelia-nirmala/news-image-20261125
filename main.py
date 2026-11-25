"""Front-page news poster: 1024x1024 PNG, pure standard library."""

import os
import struct
import zlib

W = 1024
H = 1024

BG = (15, 27, 45)
WHITE = (255, 255, 255)
YELLOW = (255, 212, 59)

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
    "I": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b11111),
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
    "/": (0b00001, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b10000),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "'": (0b00100, 0b00100, 0b01000, 0b00000, 0b00000, 0b00000, 0b00000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100),
}


def paint_rect(buf, x, y, w, h, rgb):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(rgb) * (x1 - x0)
    n = len(row)
    for yy in range(y0, y1):
        s = (yy * W + x0) * 3
        buf[s:s + n] = row


def paint_disc(buf, cx, cy, r, rgb):
    for dy in range(-r, r + 1):
        rem = r * r - dy * dy
        dx = 0
        while (dx + 1) * (dx + 1) <= rem:
            dx += 1
        paint_rect(buf, cx - dx, cy + dy, 2 * dx + 1, 1, rgb)


def paint_tri(buf, x1, y1, x2, y2, x3, y3, rgb):
    minx = max(0, min(x1, x2, x3))
    maxx = min(W - 1, max(x1, x2, x3))
    miny = max(0, min(y1, y2, y3))
    maxy = min(H - 1, max(y1, y2, y3))
    ax, ay = 2 * x1, 2 * y1
    bx, by = 2 * x2, 2 * y2
    cx, cy = 2 * x3, 2 * y3
    area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    if area == 0:
        return
    for py in range(miny, maxy + 1):
        Y = 2 * py + 1
        for px in range(minx, maxx + 1):
            X = 2 * px + 1
            w0 = (bx - ax) * (Y - ay) - (X - ax) * (by - ay)
            w1 = (cx - bx) * (Y - by) - (X - bx) * (cy - by)
            w2 = (ax - cx) * (Y - cy) - (X - cx) * (ay - cy)
            if (w0 >= 0 and w1 >= 0 and w2 >= 0) or (w0 <= 0 and w1 <= 0 and w2 <= 0):
                paint_rect(buf, px, py, 1, 1, rgb)


def measure_text(text, scale):
    return len(text) * 6 * scale - scale


def paint_text(buf, x, y, text, scale, rgb):
    pen = x
    for ch in text:
        rows = GLYPHS[ch]
        for r in range(7):
            bits = rows[r]
            if not bits:
                continue
            for c in range(5):
                if bits & (1 << (4 - c)):
                    paint_rect(buf, pen + c * scale, y + r * scale, scale, scale, rgb)
        pen += 6 * scale


def ico_rocket(buf, cx, cy):
    paint_rect(buf, cx - 13, cy - 16, 26, 50, YELLOW)
    paint_tri(buf, cx - 13, cy - 16, cx + 13, cy - 16, cx, cy - 48, YELLOW)
    paint_tri(buf, cx - 13, cy + 8, cx - 13, cy + 34, cx - 32, cy + 34, YELLOW)
    paint_tri(buf, cx + 13, cy + 8, cx + 13, cy + 34, cx + 32, cy + 34, YELLOW)
    paint_rect(buf, cx - 8, cy + 34, 16, 10, YELLOW)
    paint_disc(buf, cx, cy - 2, 8, (31, 111, 235))


def ico_scales(buf, cx, cy):
    paint_rect(buf, cx - 4, cy - 36, 8, 76, YELLOW)
    paint_rect(buf, cx - 48, cy - 36, 96, 6, YELLOW)
    paint_rect(buf, cx - 22, cy + 40, 44, 6, YELLOW)
    paint_tri(buf, cx - 52, cy - 28, cx - 26, cy - 28, cx - 39, cy - 6, YELLOW)
    paint_tri(buf, cx + 26, cy - 28, cx + 52, cy - 28, cx + 39, cy - 6, YELLOW)


def ico_flag_spain(buf, cx, cy):
    x = cx - 45
    y = cy - 28
    paint_rect(buf, x, y, 90, 14, (170, 21, 27))
    paint_rect(buf, x, y + 14, 90, 28, (255, 196, 0))
    paint_rect(buf, x, y + 42, 90, 14, (170, 21, 27))


def ico_flag_bangladesh(buf, cx, cy):
    paint_rect(buf, cx - 45, cy - 28, 90, 56, (0, 106, 78))
    paint_disc(buf, cx - 12, cy, 16, (244, 42, 65))


def ico_flag_colombia(buf, cx, cy):
    x = cx - 45
    y = cy - 28
    paint_rect(buf, x, y, 90, 28, (252, 209, 22))
    paint_rect(buf, x, y + 28, 90, 14, (0, 56, 147))
    paint_rect(buf, x, y + 42, 90, 14, (206, 17, 38))


def ico_flag_indonesia(buf, cx, cy):
    x = cx - 45
    y = cy - 28
    paint_rect(buf, x, y, 90, 28, (255, 0, 0))
    paint_rect(buf, x, y + 28, 90, 28, (255, 255, 255))


PANELS = (
    ((31, 111, 235), ico_rocket, ("CHINA LAUNCHES", "1ST FOREIGN", "ASTRONAUT")),
    ((217, 72, 15), ico_scales, ("US PROPOSES NEW", "TARIFFS ON 14", "CHINA 20%")),
    ((43, 138, 62), ico_flag_spain, ("PUIGDEMONT TO", "RETURN TO SPAIN", "ON DEC 12")),
    ((134, 46, 156), ico_flag_bangladesh, ("BANGLADESH", "GARMENT PAY UP", "36% 17,000 TAKA")),
    ((194, 37, 92), ico_flag_colombia, ("COLOMBIA FREES", "REMAINING", "HOSTAGES")),
    ((11, 114, 133), ico_flag_indonesia, ("INDONESIA MINE", "FLOOD: 9 DEAD", "17 TRAPPED")),
)

PANEL_W = 492
PANEL_H = 270
COL_X = (16, 524)
ROW_Y = (150, 436, 722)


def build():
    buf = bytearray(W * H * 3)
    paint_rect(buf, 0, 0, W, H, BG)

    paint_text(buf, 16, 28, "WORLD NEWS", 8, WHITE)
    paint_text(buf, 16, 88, "WEDNESDAY 25 NOVEMBER 2026", 5, WHITE)

    for i, (color, icon, lines) in enumerate(PANELS):
        px = COL_X[i % 2]
        py = ROW_Y[i // 2]
        paint_rect(buf, px, py, PANEL_W, PANEL_H, color)
        icon(buf, px + 246, py + 55)
        for j, line in enumerate(lines):
            for ch in line:
                assert ch in GLYPHS, "missing glyph for %r" % ch
            assert measure_text(line, 5) <= PANEL_W - 24, "line too wide: %r" % line
            paint_text(buf, px + 24, py + 118 + j * 46, line, 5, WHITE)

    return buf


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def encode_png(path, buf):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_chunk(b"IHDR", ihdr))
        f.write(_chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(_chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    buf = build()
    encode_png(os.path.join(out_dir, "entry.png"), buf)


if __name__ == "__main__":
    main()
