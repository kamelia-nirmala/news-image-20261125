import struct
import zlib

SIZE_X = 1024
SIZE_Y = 1024

BACKDROP = (15, 27, 45)
PAPER = (255, 255, 255)
SIGNAL = (255, 212, 59)

GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", "..##.", "..##."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    ":": (".....", "..#..", "..#..", ".....", "..#..", "..#..", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", ".#.##", "#..##"),
}
def paint_rect(buf, x, y, w, h, rgb):
    """Fill an axis-aligned rectangle into an RGB bytearray, clipped to the canvas."""
    if w <= 0 or h <= 0:
        return

    x0 = x if x > 0 else 0
    y0 = y if y > 0 else 0
    x1 = x + w
    y1 = y + h
    if x1 > SIZE_X:
        x1 = SIZE_X
    if y1 > SIZE_Y:
        y1 = SIZE_Y

    if x0 >= x1 or y0 >= y1:
        return

    r, g, b = rgb[0] & 0xFF, rgb[1] & 0xFF, rgb[2] & 0xFF
    span = (x1 - x0) * 3
    row_bytes = bytes((r, g, b)) * (x1 - x0)

    stride = SIZE_X * 3
    start = x0 * 3
    end = start + span

    for row in range(y0, y1):
        base = row * stride
        buf[base + start:base + end] = row_bytes
def paint_disc(buf, cx, cy, r, rgb):
    cx = int(cx)
    cy = int(cy)
    r = int(r)
    if r < 0:
        return
    color = bytes(rgb)
    rr = r * r
    y0 = max(0, cy - r)
    y1 = min(SIZE_Y - 1, cy + r)
    for y in range(y0, y1 + 1):
        dy = y - cy
        dx = int((rr - dy * dy) ** 0.5)
        x0 = max(0, cx - dx)
        x1 = min(SIZE_X - 1, cx + dx)
        if x1 < x0:
            continue
        start = (y * SIZE_X + x0) * 3
        end = (y * SIZE_X + x1 + 1) * 3
        buf[start:end] = color * (x1 - x0 + 1)
def paint_tri(buf, x1, y1, x2, y2, x3, y3, rgb):
    y_low = min(y1, y2, y3)
    y_high = max(y1, y2, y3)

    y_first = int(y_low)
    if y_first < 0:
        y_first = 0

    y_last = int(y_high) + 1
    if y_last > SIZE_Y - 1:
        y_last = SIZE_Y - 1

    color = bytes(rgb)
    edges = (
        (x1, y1, x2, y2),
        (x2, y2, x3, y3),
        (x3, y3, x1, y1),
    )

    for y in range(y_first, y_last + 1):
        scan_y = y + 0.5
        crossings = []

        for ex1, ey1, ex2, ey2 in edges:
            if ey1 == ey2:
                continue
            if (ey1 <= scan_y < ey2) or (ey2 <= scan_y < ey1):
                crossings.append(
                    ex1 + (scan_y - ey1) * (ex2 - ex1) / (ey2 - ey1)
                )

        if len(crossings) < 2:
            continue

        crossings.sort()
        left = crossings[0]
        right = crossings[-1]

        x_start = int(left - 0.5)
        if x_start < left - 0.5:
            x_start += 1

        x_end = int(right - 0.5)
        if x_end > right - 0.5:
            x_end -= 1

        if x_start < 0:
            x_start = 0
        if x_end >= SIZE_X:
            x_end = SIZE_X - 1

        if x_start <= x_end:
            width = x_end - x_start + 1
            offset = (y * SIZE_X + x_start) * 3
            buf[offset:offset + width * 3] = color * width
def paint_text(buf, x, y, text, scale, rgb):
    rgb_bytes = bytes(rgb)
    row_block = rgb_bytes * scale
    row_block_size = len(row_block)
    advance = 6 * scale

    for index, ch in enumerate(text):
        glyph = GLYPHS[ch]
        glyph_x = x + index * advance

        for glyph_row, cells in enumerate(glyph):
            cell_y = y + glyph_row * scale

            for cell_col, cell in enumerate(cells):
                if cell != '#':
                    continue

                cell_x = glyph_x + cell_col * scale
                x_start = cell_x
                x_end = cell_x + scale

                if x_end <= 0 or x_start >= SIZE_X:
                    continue

                clipped_start = 0 if x_start < 0 else x_start
                clipped_end = SIZE_X if x_end > SIZE_X else x_end

                left_trim = (clipped_start - x_start) * 3
                right_trim = (x_end - clipped_end) * 3
                piece = row_block[left_trim:row_block_size - right_trim]

                for offset_y in range(scale):
                    yy = cell_y + offset_y
                    if yy < 0 or yy >= SIZE_Y:
                        continue

                    offset = (yy * SIZE_X + clipped_start) * 3
                    buf[offset:offset + len(piece)] = piece


def measure_text(text, scale):
    if not text:
        return 0
    return len(text) * 6 * scale - scale
def encode_png(path, buf):
    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    stride = SIZE_X * 3
    raw = bytearray()
    for y in range(SIZE_Y):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]

    ihdr = struct.pack(">IIBBBBB", SIZE_X, SIZE_Y, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw)))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)
def ico_rocket(buf, cx, cy):
    # flame
    paint_tri(buf, cx, cy + 42, cx - 9, cy + 16, cx + 9, cy + 16, SIGNAL)
    # body
    paint_rect(buf, cx - 12, cy - 22, 24, 40, SIGNAL)
    # nose cone
    paint_tri(buf, cx, cy - 44, cx - 14, cy - 20, cx + 14, cy - 20, SIGNAL)
    # fins
    paint_tri(buf, cx - 12, cy - 6, cx - 12, cy + 18, cx - 30, cy + 26, SIGNAL)
    paint_tri(buf, cx + 12, cy - 6, cx + 12, cy + 18, cx + 30, cy + 26, SIGNAL)
    # window
    paint_disc(buf, cx, cy - 6, 6, SIGNAL)


def ico_scales(buf, cx, cy):
    # vertical center bar
    paint_rect(buf, cx - 3, cy - 32, 6, 64, SIGNAL)
    # top horizontal bar
    paint_rect(buf, cx - 34, cy - 32, 68, 6, SIGNAL)
    # left pan
    paint_tri(buf, cx - 44, cy - 24, cx - 20, cy - 24, cx - 32, cy, SIGNAL)
    # right pan
    paint_tri(buf, cx + 20, cy - 24, cx + 44, cy - 24, cx + 32, cy, SIGNAL)
    # base
    paint_rect(buf, cx - 30, cy + 30, 60, 10, SIGNAL)
def ico_burst(buf, cx, cy):
    paint_tri(buf, cx, cy - 44, cx - 10, cy - 14, cx + 10, cy - 14, SIGNAL)
    paint_tri(buf, cx, cy + 44, cx - 10, cy + 14, cx + 10, cy + 14, SIGNAL)
    paint_tri(buf, cx - 44, cy, cx - 14, cy - 10, cx - 14, cy + 10, SIGNAL)
    paint_tri(buf, cx + 44, cy, cx + 14, cy - 10, cx + 14, cy + 10, SIGNAL)
    paint_tri(buf, cx - 31, cy - 31, cx - 3, cy - 16, cx - 16, cy - 3, SIGNAL)
    paint_tri(buf, cx + 31, cy - 31, cx + 3, cy - 16, cx + 16, cy - 3, SIGNAL)
    paint_tri(buf, cx - 31, cy + 31, cx - 16, cy + 3, cx - 3, cy + 16, SIGNAL)
    paint_tri(buf, cx + 31, cy + 31, cx + 16, cy + 3, cx + 3, cy + 16, SIGNAL)
    paint_disc(buf, cx, cy, 16, SIGNAL)


def ico_chip(buf, cx, cy):
    paint_rect(buf, cx - 24, cy - 24, 48, 6, SIGNAL)
    paint_rect(buf, cx - 24, cy + 18, 48, 6, SIGNAL)
    paint_rect(buf, cx - 24, cy - 18, 6, 36, SIGNAL)
    paint_rect(buf, cx + 18, cy - 18, 6, 36, SIGNAL)
    paint_rect(buf, cx - 15, cy - 15, 12, 12, SIGNAL)
    paint_rect(buf, cx + 3, cy - 15, 12, 12, SIGNAL)
    paint_rect(buf, cx - 15, cy + 3, 12, 12, SIGNAL)
    paint_rect(buf, cx + 3, cy + 3, 12, 12, SIGNAL)
    paint_rect(buf, cx - 38, cy - 18, 14, 8, SIGNAL)
    paint_rect(buf, cx - 38, cy - 4, 14, 8, SIGNAL)
    paint_rect(buf, cx - 38, cy + 10, 14, 8, SIGNAL)
    paint_rect(buf, cx + 24, cy - 18, 14, 8, SIGNAL)
    paint_rect(buf, cx + 24, cy - 4, 14, 8, SIGNAL)
    paint_rect(buf, cx + 24, cy + 10, 14, 8, SIGNAL)
def ico_plane(buf, cx, cy):
    paint_rect(buf, cx - 36, cy, 58, 14, SIGNAL)
    paint_tri(buf, cx + 22, cy, cx + 22, cy + 14, cx + 43, cy + 7, SIGNAL)
    paint_tri(buf, cx - 6, cy, cx + 16, cy, cx - 24, cy - 31, SIGNAL)
    paint_tri(buf, cx - 36, cy, cx - 24, cy, cx - 40, cy - 26, SIGNAL)
    paint_tri(buf, cx - 36, cy + 14, cx - 20, cy + 14, cx - 43, cy + 30, SIGNAL)


def ico_ship(buf, cx, cy):
    paint_rect(buf, cx - 40, cy + 2, 65, 15, SIGNAL)
    paint_tri(buf, cx + 25, cy + 2, cx + 25, cy + 17, cx + 42, cy + 10, SIGNAL)
    paint_rect(buf, cx - 6, cy - 33, 4, 35, SIGNAL)
    paint_tri(buf, cx - 2, cy - 32, cx - 2, cy - 4, cx + 30, cy - 4, SIGNAL)
    paint_rect(buf, cx - 32, cy + 26, 20, 4, SIGNAL)
    paint_rect(buf, cx + 4, cy + 26, 24, 4, SIGNAL)
DATE_LINE = "WEDNESDAY 25 NOVEMBER 2026"

PANELS = [
    ((31, 111, 235), ico_rocket, ("SHENZHOU-24", "LAUNCHED 08:18", "FIRST FOREIGN")),
    ((217, 72, 15), ico_scales, ("US TARIFF PLAN", "14 PARTNERS", "CHINA 20%")),
    ((43, 138, 62), ico_burst, ("ISRAELI STRIKE", "HAMAS SECURITY", "CHIEF KILLED")),
    ((134, 46, 156), ico_chip, ("BANGLADESH", "MIN WAGE UP 36%", "17,000 TAKA")),
    ((194, 37, 92), ico_plane, ("CARTAGENA", "ALL HOSTAGES", "FREED IN RESCUE")),
    ((11, 114, 133), ico_ship, ("INDONESIA MINE", "RESCUE, 3 DEAD", "23 TRAPPED")),
]
def build():
    buf = bytearray(SIZE_X * SIZE_Y * 3)
    paint_rect(buf, 0, 0, SIZE_X, SIZE_Y, BACKDROP)

    assert measure_text("WORLD NEWS", 8) <= SIZE_X
    for ch in DATE_LINE:
        assert ch in GLYPHS

    for color, icon, lines in PANELS:
        assert len(lines) <= 3
        for line in lines:
            assert len(line) <= 15
            for ch in line:
                assert ch in GLYPHS
            assert measure_text(line, 5) <= 492 - 24

    title_x = (SIZE_X - measure_text("WORLD NEWS", 8)) // 2
    paint_text(buf, title_x, 18, "WORLD NEWS", 8, PAPER)

    date_x = (SIZE_X - measure_text(DATE_LINE, 5)) // 2
    paint_text(buf, date_x, 92, DATE_LINE, 5, PAPER)

    SLOTS = [
        (16, 150),
        (524, 150),
        (16, 436),
        (524, 436),
        (16, 722),
        (524, 722),
    ]

    for i, (color, icon, lines) in enumerate(PANELS):
        px, py = SLOTS[i]
        paint_rect(buf, px, py, 492, 270, color)
        icon(buf, px + 246, py + 55)
        for j, line in enumerate(lines):
            paint_text(buf, px + 24, py + 118 + j * 46, line, 5, PAPER)

    return buf
import os


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    buf = build()
    os.makedirs(out_dir, exist_ok=True)
    encode_png(os.path.join(out_dir, "entry.png"), buf)


if __name__ == "__main__":
    main()
