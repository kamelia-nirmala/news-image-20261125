"""make.fun bounty entry: one-page newspaper for Wednesday 25 November 2026.

Pure standard library: no randomness, no clock, no network. Two runs produce
byte-identical PNG files.

Every coordinate below is literal (taken from the brief). Every string is
measured against its own box before it is drawn, and the finished framebuffer
is inspected pixel by pixel: nothing may be clipped, nothing may overlap, and
no box may be left empty.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (0xF4, 0xEB, 0xD8)
PANEL = (0xEA, 0xDF, 0xC6)
INK = (0x1A, 0x1A, 0x1A)
RED = (0xC0, 0x39, 0x2B)
GREEN = (0x1E, 0x84, 0x49)
NAVY = (0x0F, 0x1B, 0x2D)
DARKTXT = (0x3A, 0x3A, 0x3A)
WHITE = (0xFF, 0xFF, 0xFF)
BLUE = (0x1F, 0x4E, 0x79)
ORANGE = (0xE8, 0x8B, 0x2A)
YELLOW = (0xF2, 0xC0, 0x4A)


def mix(a, b, t):
    """Flat colour between a and b, t in 0..1000. Integer only, so stable."""
    return tuple((a[i] * (1000 - t) + b[i] * t) // 1000 for i in range(3))


# --------------------------------------------------------------------------
# 5x7 pixel font. Uppercase, digits, space and punctuation. Cell 5px wide,
# advance 6px per scale step, 7px tall per scale step.
# --------------------------------------------------------------------------

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
    ".": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00110, 0b00110),
    ",": (0b00000, 0b00000, 0b00000, 0b00000, 0b00110, 0b00100, 0b01000),
    ":": (0b00000, 0b00110, 0b00110, 0b00000, 0b00110, 0b00110, 0b00000),
    ";": (0b00000, 0b00110, 0b00110, 0b00000, 0b00110, 0b00100, 0b01000),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "+": (0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000),
    "=": (0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000),
    "/": (0b00001, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b10000),
    "'": (0b00100, 0b00100, 0b01000, 0b00000, 0b00000, 0b00000, 0b00000),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "|": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
}

CHAR_W = 5
ADVANCE = 6
ROWS = 7


def text_width(s, scale):
    return len(s) * ADVANCE * scale - scale


# --------------------------------------------------------------------------
# Raster primitives. Whole pixels, no anti-aliasing, everything clipped to a
# rectangle so a shape can never touch a neighbouring box.
# --------------------------------------------------------------------------

CLIP = None


class Clip(object):
    """Confine drawing to a rectangle for the duration of a with-block."""

    def __init__(self, x, y, w, h):
        self.rect = (x, y, x + w, y + h)
        self.old = None

    def __enter__(self):
        global CLIP
        self.old = CLIP
        CLIP = self.rect

    def __exit__(self, *exc):
        global CLIP
        CLIP = self.old
        return False


def fill_rect(buf, x, y, w, h, rgb):
    if w <= 0 or h <= 0:
        return
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if CLIP is not None:
        x0 = max(x0, CLIP[0])
        y0 = max(y0, CLIP[1])
        x1 = min(x1, CLIP[2])
        y1 = min(y1, CLIP[3])
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(rgb) * (x1 - x0)
    n = len(row)
    for yy in range(y0, y1):
        off = (yy * W + x0) * 3
        buf[off:off + n] = row


def fill_circle(buf, cx, cy, r, rgb):
    if r <= 0:
        return
    for dy in range(-r, r + 1):
        dx = math.isqrt(max(0, r * r - dy * dy))
        fill_rect(buf, cx - dx, cy + dy, 2 * dx + 1, 1, rgb)


def fill_poly(buf, pts, rgb):
    """Scanline fill, even-odd rule."""
    n = len(pts)
    if n < 3:
        return
    ys = [p[1] for p in pts]
    top = max(0, min(ys))
    bot = min(H - 1, max(ys))
    for y in range(top, bot + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= yc < by) or (by <= yc < ay):
                xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
        if len(xs) < 2:
            continue
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa = int(xs[i] + 0.5)
            xb = int(xs[i + 1] - 0.5)
            if xb >= xa:
                fill_rect(buf, xa, y, xb - xa + 1, 1, rgb)


def fill_tri(buf, p1, p2, p3, rgb):
    fill_poly(buf, (p1, p2, p3), rgb)


def line(buf, x0, y0, x1, y1, tebal, rgb):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    half = tebal // 2
    while True:
        fill_rect(buf, x0 - half, y0 - half, tebal, tebal, rgb)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def text(buf, x, y, s, scale, rgb, box=None):
    """Draw a string. With a box, assert the whole string fits inside it."""
    assert s, "empty string"
    assert s == s.upper(), "not uppercase: %r" % s
    tw = text_width(s, scale)
    th = ROWS * scale
    for ch in s:
        assert ch in GLYPHS, "character missing from font: %r in %r" % (ch, s)
    if box is not None:
        bx, by, bw, bh = box
        assert x >= bx, "text starts left of its box: %r" % s
        assert y >= by, "text starts above its box: %r" % s
        assert x + tw <= bx + bw, "text overflows box (%d > %d): %r" % (
            x + tw, bx + bw, s)
        assert y + th <= by + bh, "text overflows box at the bottom: %r" % s
    pen = x
    for ch in s:
        rows = GLYPHS[ch]
        for r in range(ROWS):
            bits = rows[r]
            if not bits:
                continue
            for c in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - c)):
                    fill_rect(buf, pen + c * scale, y + r * scale, scale, scale, rgb)
        pen += ADVANCE * scale


def rect_border(buf, x, y, w, h, t, rgb):
    fill_rect(buf, x, y, w, t, rgb)
    fill_rect(buf, x, y + h - t, w, t, rgb)
    fill_rect(buf, x, y, t, h, rgb)
    fill_rect(buf, x + w - t, y, t, h, rgb)


# --------------------------------------------------------------------------
# Scenes. Each one fills its rectangle completely and is clipped to it.
# --------------------------------------------------------------------------

def scene_space(buf, x, y):
    """Pakistan's first astronaut lifting off from Jiuquan."""
    with Clip(x, y, 328, 130):
        fill_rect(buf, x, y, 328, 130, NAVY)
        fill_rect(buf, x, y + 96, 328, 34, mix(NAVY, PAPER, 70))
        fill_rect(buf, x, y + 112, 328, 18, mix(NAVY, PAPER, 130))
        stars = ((18, 12), (34, 26), (52, 10), (70, 34), (88, 18), (104, 40),
                 (120, 8), (142, 30), (160, 16), (178, 44), (196, 22), (214, 10),
                 (232, 36), (250, 20), (268, 44), (300, 12), (40, 50), (96, 56),
                 (150, 52), (206, 58), (262, 54), (310, 40))
        for sx, sy in stars:
            fill_rect(buf, x + sx, y + sy, 2, 2, mix(PAPER, NAVY, 120))
        fill_circle(buf, x + 288, y + 24, 12, mix(PAPER, NAVY, 80))
        fill_circle(buf, x + 283, y + 21, 11, NAVY)
        # launch tower
        for tx in (70, 94):
            fill_rect(buf, x + tx, y + 34, 4, 74, mix(PAPER, NAVY, 280))
        for ty in (46, 62, 78, 94):
            fill_rect(buf, x + 70, y + ty, 28, 2, mix(PAPER, NAVY, 280))
        # rocket
        fill_rect(buf, x + 128, y + 34, 22, 62, PAPER)
        fill_tri(buf, (x + 128, y + 34), (x + 150, y + 34), (x + 139, y + 8), PAPER)
        fill_rect(buf, x + 130, y + 42, 18, 4, mix(NAVY, PAPER, 120))
        fill_circle(buf, x + 139, y + 56, 5, mix(NAVY, PAPER, 220))
        fill_tri(buf, (x + 128, y + 74), (x + 128, y + 96), (x + 112, y + 96), RED)
        fill_tri(buf, (x + 150, y + 74), (x + 150, y + 96), (x + 166, y + 96), RED)
        fill_tri(buf, (x + 130, y + 96), (x + 148, y + 96), (x + 139, y + 124), ORANGE)
        fill_tri(buf, (x + 133, y + 96), (x + 145, y + 96), (x + 139, y + 114), YELLOW)
        fill_circle(buf, x + 110, y + 116, 7, mix(PAPER, NAVY, 380))
        fill_circle(buf, x + 170, y + 118, 6, mix(PAPER, NAVY, 380))


def scene_tariff(buf, x, y):
    """Container port and the tariff sheet: 20%, 40% only if talks fail."""
    with Clip(x, y, 328, 130):
        fill_rect(buf, x, y, 328, 130, mix(PAPER, NAVY, 130))
        fill_rect(buf, x, y + 92, 328, 38, mix(PANEL, INK, 130))
        for gx in (16, 172):
            fill_rect(buf, x + gx, y + 22, 3, 70, INK)
        fill_rect(buf, x + 14, y + 22, 164, 3, INK)
        for i in range(5):
            fill_rect(buf, x + 30 + i * 28, y + 25, 2, 12, INK)
        colours = (RED, mix(RED, INK, 350), GREEN, mix(GREEN, INK, 350),
                   mix(PANEL, INK, 250))
        for row in range(3):
            for c in range(5):
                bx = x + 14 + c * 30
                by = y + 44 + row * 16
                col = colours[(row * 5 + c) % 5]
                fill_rect(buf, bx, by, 28, 14, mix(col, INK, 600))
                fill_rect(buf, bx + 1, by + 1, 26, 12, col)
        # tariff sheet
        fill_rect(buf, x + 196, y + 18, 116, 86, WHITE)
        rect_border(buf, x + 196, y + 18, 116, 86, 2, INK)
        text(buf, x + 206, y + 28, "20%", 4, RED, box=(x + 200, y + 22, 108, 34))
        text(buf, x + 206, y + 66, "CHINA", 2, INK, box=(x + 200, y + 62, 108, 18))
        fill_rect(buf, x + 288, y + 60, 4, 34, RED)
        fill_tri(buf, (x + 280, y + 64), (x + 300, y + 64), (x + 290, y + 50), RED)


def scene_fire(buf, x, y):
    """Fuel tanker on its side on the Cairo ring road, 31 dead."""
    with Clip(x, y, 328, 130):
        fill_rect(buf, x, y, 328, 130, mix(INK, RED, 380))
        fill_rect(buf, x, y, 328, 52, mix(INK, RED, 280))
        fill_rect(buf, x, y + 52, 328, 30, mix(RED, INK, 180))
        fill_rect(buf, x, y + 96, 328, 34, mix(INK, PAPER, 90))
        for dx in range(0, 328, 34):
            fill_rect(buf, x + dx, y + 112, 16, 3, mix(PAPER, INK, 300))
        # overturned tanker
        fill_rect(buf, x + 70, y + 74, 120, 26, PAPER)
        fill_rect(buf, x + 70, y + 74, 120, 4, mix(PAPER, INK, 120))
        fill_circle(buf, x + 70, y + 87, 13, PAPER)
        fill_circle(buf, x + 190, y + 87, 13, PAPER)
        fill_circle(buf, x + 96, y + 72, 7, INK)
        fill_circle(buf, x + 150, y + 72, 7, INK)
        fill_rect(buf, x + 86, y + 86, 88, 6, RED)
        fill_tri(buf, (x + 190, y + 74), (x + 214, y + 64), (x + 214, y + 96),
                 mix(PAPER, INK, 200))
        for fx, fh, fw in ((216, 44, 18), (238, 54, 16), (260, 38, 14)):
            fill_tri(buf, (x + fx, y + 96), (x + fx + fw, y + 96),
                     (x + fx + fw // 2, y + 96 - fh), ORANGE)
            fill_tri(buf, (x + fx + 4, y + 96), (x + fx + fw - 4, y + 96),
                     (x + fx + fw // 2, y + 96 - fh + 12), YELLOW)
        fill_circle(buf, x + 246, y + 30, 10, mix(INK, PAPER, 130))
        fill_circle(buf, x + 268, y + 18, 8, mix(INK, PAPER, 130))
        fill_circle(buf, x + 228, y + 20, 7, mix(INK, PAPER, 130))
        for cx in (22, 44, 300, 316):
            fill_rect(buf, x + cx, y + 100, 12, 6, mix(NAVY, PAPER, 200))


def scene_mid_shop(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, NAVY, 150))
        fill_rect(buf, x, y + 34, 196, 10, mix(PANEL, INK, 120))
        fill_rect(buf, x + 8, y + 8, 92, 28, PAPER)
        fill_rect(buf, x + 8, y + 8, 92, 5, RED)
        for i in range(6):
            fill_rect(buf, x + 8 + i * 15, y + 15, 8, 7,
                      RED if i % 2 == 0 else PAPER)
        fill_rect(buf, x + 26, y + 24, 16, 12, mix(NAVY, PAPER, 100))
        fill_rect(buf, x + 52, y + 24, 16, 12, mix(NAVY, PAPER, 200))
        fill_rect(buf, x + 76, y + 24, 16, 12, mix(NAVY, PAPER, 100))
        for i in range(4):
            fx = x + 112 + i * 16
            fill_circle(buf, fx, y + 18, 3, INK)
            fill_rect(buf, fx - 2, y + 22, 5, 11, INK)
        fill_rect(buf, x + 182, y + 16, 4, 18, GREEN)


def scene_mid_court(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, NAVY, 120))
        fill_rect(buf, x, y + 36, 196, 8, mix(PANEL, INK, 140))
        fill_poly(buf, [(x + 12, y + 18), (x + 92, y + 18), (x + 52, y + 4)], PAPER)
        fill_rect(buf, x + 12, y + 18, 81, 3, mix(PAPER, INK, 180))
        for i in range(4):
            fill_rect(buf, x + 20 + i * 18, y + 23, 7, 13, PAPER)
        fill_rect(buf, x + 12, y + 34, 81, 3, mix(PAPER, INK, 180))
        fill_rect(buf, x + 112, y + 12, 28, 11, INK)
        fill_rect(buf, x + 122, y + 23, 7, 14, mix(INK, RED, 300))
        fill_rect(buf, x + 108, y + 36, 34, 3, INK)
        fill_rect(buf, x + 152, y + 18, 30, 20, RED)
        fill_rect(buf, x + 156, y + 23, 22, 2, PAPER)
        fill_rect(buf, x + 156, y + 28, 22, 2, PAPER)


def scene_mid_shutter(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, NAVY, 160))
        fill_rect(buf, x, y + 36, 196, 8, mix(PANEL, INK, 130))
        fill_rect(buf, x + 8, y + 6, 104, 30, mix(PANEL, INK, 60))
        fill_rect(buf, x + 8, y + 6, 104, 5, RED)
        for i in range(5):
            fill_rect(buf, x + 11, y + 13 + i * 4, 98, 2, mix(PANEL, INK, 240))
        fill_rect(buf, x + 132, y + 8, 6, 18, RED)
        fill_poly(buf, [(x + 122, y + 24), (x + 148, y + 24), (x + 135, y + 38)], RED)
        fill_rect(buf, x + 162, y + 12, 24, 18, PAPER)
        fill_rect(buf, x + 166, y + 18, 16, 3, INK)
        fill_rect(buf, x + 166, y + 24, 10, 3, INK)


def scene_mid_rubble(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, RED, 180))
        fill_rect(buf, x, y + 34, 196, 10, mix(PANEL, INK, 160))
        fill_poly(buf, [(x + 8, y + 34), (x + 8, y + 12), (x + 22, y + 6),
                        (x + 30, y + 14), (x + 40, y + 8), (x + 46, y + 34)],
                  mix(PANEL, INK, 300))
        fill_poly(buf, [(x + 50, y + 34), (x + 50, y + 16), (x + 62, y + 10),
                        (x + 72, y + 18), (x + 78, y + 34)], mix(PANEL, INK, 240))
        fill_poly(buf, [(x + 86, y + 34), (x + 86, y + 20), (x + 98, y + 12),
                        (x + 108, y + 22), (x + 112, y + 34)], mix(PANEL, INK, 280))
        fill_circle(buf, x + 70, y + 10, 7, mix(INK, PAPER, 130))
        fill_circle(buf, x + 84, y + 6, 5, mix(INK, PAPER, 130))
        fill_poly(buf, [(x + 120, y + 34), (x + 130, y + 34), (x + 126, y + 18)], ORANGE)
        fill_poly(buf, [(x + 132, y + 34), (x + 140, y + 34), (x + 137, y + 24)], YELLOW)
        fill_rect(buf, x + 152, y + 26, 34, 8, mix(PANEL, INK, 200))


def scene_mid_pylon(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, NAVY, 210))
        fill_rect(buf, x, y + 36, 196, 8, mix(INK, NAVY, 300))
        line(buf, x + 40, y + 38, x + 58, y + 6, 2, INK)
        line(buf, x + 76, y + 38, x + 58, y + 6, 2, INK)
        fill_rect(buf, x + 46, y + 18, 25, 2, INK)
        fill_rect(buf, x + 42, y + 28, 33, 2, INK)
        fill_poly(buf, [(x + 96, y + 4), (x + 112, y + 4), (x + 104, y + 18),
                        (x + 116, y + 18), (x + 96, y + 40), (x + 102, y + 22),
                        (x + 92, y + 22)], YELLOW)
        for i, bw in enumerate((14, 20, 12, 24, 16)):
            fill_rect(buf, x + 130 + i * 12, y + 34 - bw, bw - 4, bw,
                      mix(INK, NAVY, 200))


def scene_mid_chart(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, NAVY)
        for gy in range(6, 40, 8):
            fill_rect(buf, x + 6, y + gy, 184, 1, mix(NAVY, PAPER, 60))
        for i, bh in enumerate((10, 14, 9, 16, 11, 7)):
            fill_rect(buf, x + 12 + i * 18, y + 38 - bh, 10, bh,
                      mix(NAVY, PAPER, 110))
        line(buf, x + 10, y + 12, x + 182, y + 30, 3, RED)
        fill_poly(buf, [(x + 176, y + 22), (x + 190, y + 32), (x + 178, y + 36)], RED)


def scene_mid_bill(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, NAVY, 140))
        fill_rect(buf, x, y + 38, 196, 6, mix(PANEL, INK, 130))
        fill_rect(buf, x + 10, y + 4, 74, 30, PAPER)
        fill_rect(buf, x + 10, y + 4, 74, 3, INK)
        fill_rect(buf, x + 16, y + 10, 40, 2, mix(PANEL, INK, 200))
        fill_rect(buf, x + 16, y + 14, 52, 2, mix(PANEL, INK, 200))
        text(buf, x + 16, y + 18, "26%", 2, RED, box=(x + 10, y + 4, 74, 30))
        fill_poly(buf, [(x + 104, y + 34), (x + 128, y + 34), (x + 116, y + 6)], ORANGE)
        fill_poly(buf, [(x + 110, y + 34), (x + 122, y + 34), (x + 116, y + 16)], YELLOW)
        fill_rect(buf, x + 150, y + 16, 6, 20, GREEN)
        fill_poly(buf, [(x + 140, y + 18), (x + 166, y + 18), (x + 153, y + 4)], GREEN)


def scene_mid_car(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PANEL, INK, 90))
        fill_rect(buf, x, y + 32, 196, 12, mix(INK, PAPER, 60))
        fill_rect(buf, x + 14, y + 16, 62, 14, PAPER)
        fill_poly(buf, [(x + 26, y + 16), (x + 34, y + 6), (x + 56, y + 6),
                        (x + 64, y + 16)], PAPER)
        fill_rect(buf, x + 34, y + 9, 18, 6, mix(NAVY, PAPER, 150))
        fill_circle(buf, x + 28, y + 31, 5, INK)
        fill_circle(buf, x + 62, y + 31, 5, INK)
        fill_rect(buf, x + 108, y + 8, 26, 10, INK)
        fill_rect(buf, x + 118, y + 18, 6, 12, mix(INK, RED, 300))
        fill_rect(buf, x + 104, y + 30, 32, 3, INK)
        fill_rect(buf, x + 150, y + 14, 34, 16, RED)
        fill_rect(buf, x + 156, y + 20, 22, 4, PAPER)


def scene_mid_guitar(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(INK, NAVY, 500))
        fill_poly(buf, [(x + 20, y), (x + 80, y), (x + 120, y + 44),
                        (x + 40, y + 44)], mix(NAVY, PAPER, 90))
        fill_circle(buf, x + 104, y + 30, 11, ORANGE)
        fill_circle(buf, x + 96, y + 20, 8, ORANGE)
        fill_rect(buf, x + 100, y + 4, 5, 18, PAPER)
        fill_rect(buf, x + 96, y, 13, 5, PAPER)
        for i in range(3):
            fill_rect(buf, x + 101, y + 8 + i * 4, 1, 16, INK)
        fill_circle(buf, x + 104, y + 30, 3, INK)


def scene_mid_refinery(buf, x, y):
    with Clip(x, y, 196, 44):
        fill_rect(buf, x, y, 196, 44, mix(PAPER, RED, 150))
        fill_rect(buf, x, y + 36, 196, 8, mix(PANEL, INK, 150))
        fill_rect(buf, x + 16, y + 14, 12, 24, mix(PANEL, INK, 260))
        fill_rect(buf, x + 32, y + 8, 10, 30, mix(PANEL, INK, 240))
        fill_rect(buf, x + 46, y + 18, 14, 20, mix(PANEL, INK, 260))
        fill_rect(buf, x + 66, y + 10, 4, 28, mix(PANEL, INK, 300))
        fill_poly(buf, [(x + 68, y + 10), (x + 74, y + 10), (x + 71, y + 2)], ORANGE)
        fill_circle(buf, x + 104, y + 28, 9, mix(PANEL, INK, 200))
        fill_rect(buf, x + 95, y + 28, 19, 10, mix(PANEL, INK, 200))
        fill_rect(buf, x + 140, y + 10, 12, 3, INK)
        fill_rect(buf, x + 144, y + 13, 4, 4, INK)
        for i in range(5):
            fill_rect(buf, x + 124 + i * 3, y + 14, 2, 2, mix(INK, PAPER, 200))
        fill_poly(buf, [(x + 160, y + 34), (x + 176, y + 34), (x + 168, y + 12)], YELLOW)


# --------------------------------------------------------------------------
# Story data. 3 hero + 10 mid + 13 list = 26 stories, all dated 25 Nov 2026.
# --------------------------------------------------------------------------

HERO = (
    dict(chip="CONFIRMED", cat="JIUQUAN, CHINA | SPACE",
         title=("PAKISTAN 1ST", "AT CHINA STATION"),
         sub=("MUHAMMAD ZEESHAN ALI LIFTED OFF FROM JIUQUAN",
              "AND DOCKED AT TIANGONG 3.5 HOURS LATER"),
         src="BBC + GUARDIAN", scene=scene_space, dot=(98, 40)),
    dict(chip="CONFIRMED", cat="WASHINGTON | TRADE",
         title=("US TARIFFS ON 14", "TRADE PARTNERS"),
         sub=("CHINA 20%, COULD DOUBLE TO 40% IF TALKS FAIL",
              "NEW DUTIES NOT EXPECTED TO START UNTIL NEXT YEAR"),
         src="BBC + BLOOMBERG", scene=scene_tariff, dot=(-77, 39)),
    dict(chip="CONFIRMED", cat="WARRAQ, EGYPT | DISASTER",
         title=("CAIRO FUEL TRUCK", "FIRE KILLS 31"),
         sub=("TRUCK OVERTURNED ON CAIRO RING ROAD, 21 INJURED",
              "27 VEHICLES BURNED, 39 AMBULANCES SENT"),
         src="BBC + DW", scene=scene_fire, dot=(31, 30)),
)

MID = (
    dict(chip="CONFIRMED", title=("COLOMBIA FREES", "ALL HOSTAGES", "IN CARTAGENA"),
         src="BBC + GUARDIAN", scene=scene_mid_shop, dot=(-75, 10)),
    dict(chip="CONFIRMED", title=("ISRAEL JUDGES", "URGE RETHINK", "ON NETANYAHU"),
         src="BBC + AL JAZEERA", scene=scene_mid_court, dot=(35, 32)),
    dict(chip="CONFIRMED", title=("UK POUNDLAND", "COLLAPSES", "11,000 JOBS"),
         src="BBC + GUARDIAN", scene=scene_mid_shutter, dot=(-1, 51)),
    dict(chip="CONFIRMED", title=("GAZA STRIKE", "KILLS HAMAS", "SECURITY CHIEF"),
         src="BBC + AL JAZEERA", scene=scene_mid_rubble, dot=(34, 31)),
    dict(chip="CONFIRMED", title=("RUSSIA STRIKES", "CUT POWER IN", "5 REGIONS"),
         src="AL JAZEERA + BBC", scene=scene_mid_pylon, dot=(30, 50)),
    dict(chip="CONFIRMED", title=("AI FEARS SEND", "US TECH STOCKS", "LOWER AGAIN"),
         src="BBC + BLOOMBERG", scene=scene_mid_chart, dot=(-74, 41)),
    dict(chip="CONFIRMED", title=("UK ENERGY BILLS", "UP 26 PERCENT", "IN JANUARY"),
         src="BBC + GUARDIAN", scene=scene_mid_bill, dot=(-1, 51)),
    dict(chip="CONFIRMED", title=("ENGLAND STAR", "STERLING NOT", "JAILED CRASH"),
         src="BBC + AL JAZEERA", scene=scene_mid_car, dot=(-1, 51)),
    dict(chip="CONFIRMED", title=("DURAN DURAN", "GUITARIST ANDY", "TAYLOR DIES 65"),
         src="BBC + GUARDIAN", scene=scene_mid_guitar, dot=(-3, 53)),
    dict(chip="CLAIM", title=("HOUTHIS SAY", "THEY HIT SAUDI", "OIL AND RIYADH"),
         src="DW + BLOOMBERG", scene=scene_mid_refinery, dot=(47, 25)),
)

LIST = (
    ("01", "DIMORPHOS", "HERA IMAGES SHOW CRATER NEARLY AS WIDE AS THE ASTEROID", ("BBC", "GUARDIAN"), None),
    ("02", "IOWA", "US ARMY DETONATES NEARLY 5 TONS OF UNSTABLE LEAD AZIDE", ("BBC", "DW"), (-93, 41)),
    ("03", "PYONGYANG", "NORTH KOREA ORDERS SWISS DIPLOMAT OUT OVER SANCTIONS", ("BBC", "AL JAZEERA"), (126, 39)),
    ("04", "CANBERRA", "SOLOMON ISLANDS SIGN SECURITY PACT WITH AUSTRALIA", ("BBC", "DW"), (149, -9)),
    ("05", "LONDON", "EA RECREATES JOHN MOTSON VOICE WITH AI FOR FC 27", ("BBC", "GUARDIAN"), (-1, 52)),
    ("06", "SYDNEY", "EX-POLICE OFFICER FOUND GUILTY OF MURDERING TWO MEN", ("BBC", "GUARDIAN"), (151, -34)),
    ("07", "CAPE TOWN", "COURT VOIDS PANEL THAT THREATENED RAMAPHOSA IMPEACHMENT", ("BBC", "AL JAZEERA"), (18, -34)),
    ("08", "BRUSSELS", "PUIGDEMONT SAYS HE WILL RETURN TO SPAIN ON 12 DEC", ("AL JAZEERA", "DW"), (4, 51)),
    ("09", "NEW YORK", "MACY THANKSGIVING PARADE MOVED TO SATURDAY BY STORM", ("GUARDIAN", "BLOOMBERG"), (-74, 41)),
    ("10", "ENUGU", "NIGERIA SEIZES 1.5 TONS OF METH AND ARRESTS SIX", ("BBC", "DW"), (7, 6)),
    ("11", "ESWATINI", "UK SENT SRI LANKAN ASYLUM SEEKER AFTER REFUSING HIM ENTRY", ("BBC", "GUARDIAN"), (31, -26)),
    ("12", "WASHINGTON", "FCC APPROVES 1 MILLION SPACEX ORBITAL DATA CENTRES", ("GUARDIAN", "AL JAZEERA"), (-77, 39)),
    ("13", "CALIFORNIA", "RECORD HIGH TIDES FLOOD THE COAST AND CRACK A PIER", ("GUARDIAN", "BLOOMBERG"), (-120, 36)),
)

KPI = (
    ("1ST", ("FOREIGN ASTRONAUT AT", "CHINA'S TIANGONG")),
    ("14", ("PARTNERS IN US", "TARIFF PLAN")),
    ("31", ("DEAD IN CAIRO", "FUEL FIRE")),
    ("11,000", ("POUNDLAND JOBS", "AT RISK")),
    ("+26%", ("UK ENERGY BILLS", "FROM JANUARY")),
    ("5", ("UKRAINE REGIONS", "HIT BY OUTAGES")),
)

DATE_LINES = (
    "HUAWEI GUILTY VERDICT - TUE 24 NOV (NEW YORK JURY)",
    "CAS REINSTATES SENEGAL AS AFCON CHAMPIONS - TUE 24 NOV",
    "CHEN JINING PROBE ANNOUNCED - TUE 24 NOV",
)

LEGEND_CONFIRMED = "CONFIRMED = 2+ MAJOR OUTLETS OPENED"
LEGEND_CLAIM = "CLAIM = ONE SIDE'S STATEMENT"
FOOTER = ("SOURCES: AL JAZEERA, BBC, DW, GUARDIAN, BLOOMBERG | "
          "ALL PICTURES DRAWN IN CODE | NO PHOTOS")

TOPBAR_LEFT = "THE WORLD IN ONE DAY"
TOPBAR_RIGHT = "26 STORIES | ALL DATED WEDNESDAY 25 NOVEMBER 2026"
MASTHEAD = "WEDNESDAY 25 NOVEMBER 2026"
SUBTITLE = ("PAKISTANI ASTRONAUT AT TIANGONG | US TARIFF PLAN | "
            "AI FEARS HIT STOCKS")
MAP_TITLE = "WHERE IT HAPPENED"
MAP_CAPTION = "RED DOT = STORY"
LIST_TITLE = "ALSO ON WEDNESDAY 25 NOVEMBER - 13 MORE"
DATE_TITLE = "DATE CHECK - LEFT OUT: NOT 25 NOVEMBER"

HERO_X = (12, 348, 684)
HERO_Y = 168
HERO_W = 328
HERO_H = 250
HERO_SCENE_H = 130
HERO_TITLE_MAX = 17
HERO_SUB_MAX = 50

MID_X = (10, 212, 414, 616, 818)
MID_Y = (426, 544)
MID_W = 196
MID_H = 112
MID_SCENE_H = 44
MID_TITLE_MAX = 15

MAP_X, MAP_Y, MAP_W, MAP_H = 13, 677, 318, 174
MAP_BOX = (12, 664, 320, 188)
LIST_X = 344
LIST_Y = 682
LIST_GAP = 13
LIST_TEXT_X = 364
LIST_MAX = 110


# --------------------------------------------------------------------------
# World map: coarse lon/lat outlines, equirectangular projection.
# --------------------------------------------------------------------------

LANDMASS = (
    ((-168, 66), (-160, 71), (-150, 70), (-140, 70), (-128, 71), (-115, 70),
     (-100, 72), (-85, 73), (-75, 70), (-62, 60), (-55, 50), (-64, 46),
     (-70, 43), (-75, 36), (-81, 26), (-90, 29), (-97, 26), (-105, 22),
     (-112, 30), (-118, 34), (-124, 41), (-124, 49), (-131, 55), (-140, 60),
     (-150, 60), (-160, 58)),
    ((-81, 8), (-76, 11), (-70, 12), (-60, 10), (-52, 5), (-44, -2),
     (-35, -6), (-38, -13), (-39, -18), (-48, -25), (-55, -30), (-58, -38),
     (-62, -41), (-65, -48), (-70, -55), (-74, -52), (-75, -45), (-73, -37),
     (-71, -30), (-70, -22), (-76, -14), (-81, -5)),
    ((-17, 15), (-16, 21), (-10, 28), (-2, 35), (9, 37), (20, 32), (32, 31),
     (35, 22), (43, 12), (51, 11), (42, -2), (40, -15), (35, -25), (25, -34),
     (18, -34), (12, -18), (8, 4), (-8, 5)),
    ((-9, 37), (-9, 43), (-2, 44), (3, 43), (9, 44), (13, 38), (16, 41),
     (24, 40), (28, 41), (30, 45), (40, 45), (45, 48), (42, 55), (35, 60),
     (30, 65), (25, 70), (15, 68), (10, 63), (5, 58), (0, 52), (-5, 48),
     (-9, 43)),
    ((30, 45), (40, 45), (50, 40), (60, 38), (68, 36), (66, 26), (72, 16),
     (77, 8), (81, 14), (87, 21), (90, 22), (92, 21), (98, 24), (105, 20),
     (108, 12), (112, 6), (120, 10), (122, 22),
     (128, 32), (132, 40), (140, 46), (145, 50), (152, 58), (160, 60),
     (170, 64), (180, 66), (180, 72), (168, 72), (150, 73), (130, 74),
     (110, 75), (90, 75), (75, 72), (60, 70), (50, 66), (40, 60), (32, 55),
     (28, 50)),
    ((113, -22), (122, -18), (130, -12), (142, -11), (147, -19), (153, -28),
     (150, -37), (140, -38), (130, -32), (115, -34)),
    ((-45, 60), (-30, 68), (-20, 75), (-30, 82), (-50, 82), (-58, 76),
     (-55, 66)),
    ((-5, 50), (1, 51), (0, 55), (-4, 58), (-6, 54)),
    ((130, 32), (136, 35), (141, 41), (145, 44), (142, 38), (136, 33)),
    ((43, -13), (50, -15), (48, -25), (44, -22)),
    ((166, -46), (174, -41), (178, -38), (172, -44)),
    # Arabian peninsula
    ((34, 29), (38, 31), (43, 30), (48, 30), (50, 28), (57, 25), (59, 22),
     (52, 16), (45, 12), (43, 17), (38, 22), (34, 28)),
    # Iran and the Makran coast, joining the Asian landmass
    ((44, 39), (50, 38), (56, 37), (61, 36), (63, 30), (60, 25), (57, 25),
     (50, 28), (48, 30), (44, 34)),
    # Indonesia, Malaysia, Philippines
    ((96, 6), (104, 2), (112, 1), (118, 5), (124, 7), (128, 4), (134, -2),
     (140, -4), (136, -8), (126, -9), (118, -9), (110, -7), (102, -3), (96, 3)),
    ((120, 18), (124, 18), (126, 10), (122, 7), (119, 12)),
)

STORY_DOTS = ([(p["dot"]) for p in HERO] + [p["dot"] for p in MID]
              + [e[4] for e in LIST if e[4] is not None])

SEA = mix(PAPER, NAVY, 110)
LAND = mix(PANEL, GREEN, 300)
COAST = mix(LAND, INK, 400)


def project(lon, lat):
    px = MAP_X + int((lon + 180) * MAP_W / 360.0)
    py = MAP_Y + int((90 - lat) * MAP_H / 180.0)
    return px, py


def cluster_dots(points, radius=7):
    """Merge places that land within `radius` px of each other on the map.

    At 318x174 the whole of western Europe is a handful of pixels wide, so
    separate markers there would overlap into one blob anyway. Clustering
    keeps one clean dot per visible place; the order is deterministic.
    """
    out = []
    for lon, lat in points:
        px_, py_ = project(lon, lat)
        for cx_, cy_ in out:
            if abs(px_ - cx_) <= radius and abs(py_ - cy_) <= radius:
                break
        else:
            out.append((px_, py_))
    return out


# One marker per distinct visible place; the asteroid story happens off Earth.
DOTS = cluster_dots(STORY_DOTS)


def draw_map(buf):
    fill_rect(buf, MAP_X, MAP_Y, MAP_W, MAP_H, SEA)
    with Clip(MAP_X, MAP_Y, MAP_W, MAP_H):
        for poly in LANDMASS:
            pts = [project(lon, lat) for lon, lat in poly]
            fill_poly(buf, pts, LAND)
            for i in range(len(pts)):
                a = pts[i]
                b = pts[(i + 1) % len(pts)]
                line(buf, a[0], a[1], b[0], b[1], 1, COAST)
        for dx, dy in DOTS:
            fill_circle(buf, dx, dy, 3, RED)
            fill_circle(buf, dx, dy, 1, INK)

# --------------------------------------------------------------------------
# Layout: every rectangle is computed once here and used by both the drawing
# and the checks, so the two can never drift apart.
# --------------------------------------------------------------------------

def hero_layout():
    out = []
    for i, p in enumerate(HERO):
        x = HERO_X[i]
        y = HERO_Y
        chip_w = text_width(p["chip"], 1) + 10
        cat_x = x + 10 + chip_w + 8
        cat_w = text_width(p["cat"], 1)
        title_boxes = []
        for j, ln in enumerate(p["title"]):
            title_boxes.append((x + 10, y + 152 + j * 26,
                                text_width(ln, 3), ROWS * 3))
        sub_boxes = []
        for j, ln in enumerate(p["sub"]):
            sub_boxes.append((x + 10, y + 210 + j * 12,
                              text_width(ln, 1), ROWS))
        src_w = text_width(p["src"], 1)
        out.append(dict(
            p=p, x=x, y=y, w=HERO_W, h=HERO_H,
            scene=(x, y, HERO_W, HERO_SCENE_H),
            chip=(x + 10, y + 134, chip_w, 14),
            chip_text=(x + 15, y + 137, text_width(p["chip"], 1), ROWS),
            cat_box=(cat_x, y + 137, cat_w, ROWS),
            title_boxes=title_boxes,
            sub_boxes=sub_boxes,
            src_box=(x + 10, y + 238, src_w, ROWS),
        ))
    return out


def mid_layout():
    out = []
    for i, p in enumerate(MID):
        x = MID_X[i % 5]
        y = MID_Y[i // 5]
        chip_w = text_width(p["chip"], 1) + 10
        title_boxes = []
        for j, ln in enumerate(p["title"]):
            title_boxes.append((x + 8, y + 60 + j * 16,
                                text_width(ln, 2), ROWS * 2))
        out.append(dict(
            p=p, x=x, y=y, w=MID_W, h=MID_H,
            scene=(x, y, MID_W, MID_SCENE_H),
            chip=(x + 8, y + 48, chip_w, 10),
            chip_text=(x + 13, y + 49, text_width(p["chip"], 1), ROWS),
            title_boxes=title_boxes,
        ))
    return out


def list_layout():
    out = []
    for i, (num, city, head, srcs, _dot) in enumerate(LIST):
        ly = LIST_Y + i * LIST_GAP
        line_s = "%s: %s (%s)" % (city, head, "+".join(srcs))
        out.append(dict(num=num, line=line_s, srcs=srcs, ly=ly,
                        chip=(LIST_X, ly - 2, 16, 11),
                        chip_text=(LIST_X + 2, ly, text_width(num, 1), ROWS),
                        text_box=(LIST_TEXT_X, ly - 2,
                                  text_width(line_s, 1), 11)))
    return out


def date_layout():
    boxes = []
    for i, ln in enumerate(DATE_LINES):
        boxes.append((20, 894 + i * 18, text_width(ln, 1), ROWS))
    return boxes


# --------------------------------------------------------------------------
# Drawing.
# --------------------------------------------------------------------------

def draw_topbar(buf):
    fill_rect(buf, 0, 0, W, 22, NAVY)
    text(buf, 12, 8, TOPBAR_LEFT, 1, PAPER, box=(12, 0, W - 24, 22))
    tw = text_width(TOPBAR_RIGHT, 1)
    rx = 1012 - tw
    assert rx >= 12 + text_width(TOPBAR_LEFT, 1) + 20, "top bar texts collide"
    text(buf, rx, 8, TOPBAR_RIGHT, 1, PAPER, box=(rx, 0, tw, 22))
    assert rx + tw == 1012, "right-hand top text must end at x=1012"


def draw_masthead(buf):
    text(buf, 44, 30, MASTHEAD, 6, INK, box=(12, 26, 1000, 46))
    assert 44 + text_width(MASTHEAD, 6) <= 1012, "masthead runs off the page"
    tw = text_width(SUBTITLE, 2)
    sx = (W - tw) // 2
    text(buf, sx, 82, SUBTITLE, 2, RED, box=(12, 78, 1000, 18))
    fill_rect(buf, 12, 104, 1000, 2, INK)


def draw_kpi(buf):
    for i, (num, labels) in enumerate(KPI):
        cx = 12 + i * 167
        text(buf, cx + 4, 114, num, 4, RED, box=(cx, 110, 167, 34))
        assert text_width(num, 4) <= 163, "KPI number too wide: %r" % num
        for j, lbl in enumerate(labels):
            assert len(lbl) <= 27, "KPI label over 27 chars: %r" % lbl
            text(buf, cx + 4, 146 + j * 8, lbl, 1, INK,
                 box=(cx, 144, 167, 18))


def draw_hero(buf, lay):
    for d in lay:
        p = d["p"]
        x, y = d["x"], d["y"]
        fill_rect(buf, x, y, HERO_W, HERO_H, PANEL)
        p["scene"](buf, x, y)
        rect_border(buf, x, y, HERO_W, HERO_H, 1, INK)

        chip_col = GREEN if p["chip"] == "CONFIRMED" else RED
        cx, cy, cw, ch = d["chip"]
        fill_rect(buf, cx, cy, cw, ch, chip_col)
        text(buf, d["chip_text"][0], d["chip_text"][1], p["chip"], 1, WHITE,
             box=(cx, cy, cw, ch))
        text(buf, d["cat_box"][0], d["cat_box"][1], p["cat"], 1, INK,
             box=(x + 10, y + 134, HERO_W - 20, 14))

        for (ln, (bx, by, bw, bh)) in zip(p["title"], d["title_boxes"]):
            text(buf, bx, by, ln, 3, INK, box=(bx, by, bw, bh))
        for (ln, (bx, by, bw, bh)) in zip(p["sub"], d["sub_boxes"]):
            text(buf, bx, by, ln, 1, DARKTXT, box=(bx, by, bw, bh))
        sb = d["src_box"]
        text(buf, sb[0], sb[1], p["src"], 1, DARKTXT,
             box=(x + 10, y + 238, HERO_W - 20, ROWS))


def draw_mid(buf, lay):
    for d in lay:
        p = d["p"]
        x, y = d["x"], d["y"]
        fill_rect(buf, x, y, MID_W, MID_H, PANEL)
        p["scene"](buf, x, y)
        rect_border(buf, x, y, MID_W, MID_H, 1, INK)

        chip_col = GREEN if p["chip"] == "CONFIRMED" else RED
        cx, cy, cw, ch = d["chip"]
        fill_rect(buf, cx, cy, cw, ch, chip_col)
        text(buf, d["chip_text"][0], d["chip_text"][1], p["chip"], 1, WHITE,
             box=(cx, cy, cw, ch))
        for (ln, (bx, by, bw, bh)) in zip(p["title"], d["title_boxes"]):
            text(buf, bx, by, ln, 2, INK, box=(bx, by, bw, bh))


def draw_bottom(buf):
    rect_border(buf, MAP_BOX[0], MAP_BOX[1], MAP_BOX[2], MAP_BOX[3], 1, INK)
    text(buf, 20, 666, MAP_TITLE, 1, INK, box=(20, 665, 160, 9))
    cw = text_width(MAP_CAPTION, 1)
    text(buf, 324 - cw, 666, MAP_CAPTION, 1, DARKTXT,
         box=(324 - cw, 665, cw, 9))
    draw_map(buf)

    text(buf, LIST_X, 666, LIST_TITLE, 1, RED, box=(LIST_X, 664, 668, 10))
    for d in list_layout():
        cx, cy, cw2, ch = d["chip"]
        fill_rect(buf, cx, cy, cw2, ch, BLUE)
        text(buf, d["chip_text"][0], d["chip_text"][1], d["num"], 1, WHITE,
             box=(cx, cy, cw2, ch))
        tb = d["text_box"]
        text(buf, tb[0], d["ly"], d["line"], 1, INK,
             box=(tb[0], tb[1], 1012 - tb[0], 11))


def draw_datebox(buf):
    rect_border(buf, 12, 860, 1000, 98, 2, RED)
    text(buf, 20, 866, DATE_TITLE, 2, RED, box=(16, 862, 992, 18))
    for (ln, (bx, by, bw, bh)) in zip(DATE_LINES, date_layout()):
        text(buf, bx, by, ln, 1, INK, box=(bx, by, bw, bh))


def draw_legend(buf):
    fill_rect(buf, 12, 964, 12, 11, GREEN)
    text(buf, 30, 966, LEGEND_CONFIRMED, 1, INK, box=(30, 964, 300, 11))
    x2 = 30 + text_width(LEGEND_CONFIRMED, 1) + 14
    fill_rect(buf, x2, 964, 12, 11, RED)
    text(buf, x2 + 18, 966, LEGEND_CLAIM, 1, INK,
         box=(x2 + 18, 964, 300, 11))


def draw_footer(buf):
    text(buf, 12, 996, FOOTER, 1, DARKTXT, box=(12, 994, 1000, 10))


# --------------------------------------------------------------------------
# Self-checks on the framebuffer.
# --------------------------------------------------------------------------

def px(buf, x, y):
    o = (y * W + x) * 3
    return (buf[o], buf[o + 1], buf[o + 2])


def glyph_extent(s, x, y, scale):
    """Exact bounding box of the ink a string will put down."""
    left = None
    right = None
    top = None
    bottom = None
    pen = x
    for ch in s:
        rows = GLYPHS[ch]
        for r in range(ROWS):
            bits = rows[r]
            if not bits:
                continue
            for c in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - c)):
                    gx = pen + c * scale
                    gy = y + r * scale
                    if left is None or gx < left:
                        left = gx
                    if right is None or gx + scale > right:
                        right = gx + scale
                    if top is None or gy < top:
                        top = gy
                    if bottom is None or gy + scale > bottom:
                        bottom = gy + scale
        pen += ADVANCE * scale
    if left is None:
        return None
    return (left, top, right - left, bottom - top)


def ink(s, x, y, scale):
    """The exact ink rectangle of a string, for the stray-pixel checks."""
    return glyph_extent(s, x, y, scale)


def ink_pixels(s, x, y, scale):
    """Exact set of pixels a string covers."""
    out = set()
    pen = x
    for ch in s:
        rows = GLYPHS[ch]
        for r in range(ROWS):
            bits = rows[r]
            if not bits:
                continue
            for c in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - c)):
                    gx = pen + c * scale
                    gy = y + r * scale
                    for dy in range(scale):
                        for dx in range(scale):
                            out.add((gx + dx, gy + dy))
        pen += ADVANCE * scale
    return out


def check_text_exact(s, x, y, scale, colour, base, tag):
    """Pixel-exact test: inside the string's bounding box every pixel is
    either exactly where the glyph puts ink, or the base colour. This catches
    a stray pixel sitting in the gap between two letters, which a rectangle
    test would let through."""
    ext = glyph_extent(s, x, y, scale)
    assert ext is not None, "%s: empty string" % tag
    ex, ey, ew, eh = ext
    want = ink_pixels(s, x, y, scale)
    for yy in range(ey, ey + eh):
        for xx in range(ex, ex + ew):
            got = px(buf_global, xx, yy)
            if (xx, yy) in want:
                assert got == colour, "%s: glyph pixel wrong colour at (%d,%d): %r" % (
                    tag, xx, yy, got)
            else:
                assert got == base, "%s: stray pixel at (%d,%d): %r in %r" % (
                    tag, xx, yy, got, s)


def text_runs():
    """Every drawn string with its position, scale and the rectangle it must
    stay inside. One list feeds both the drawing checks and the overlap test."""
    runs = []

    def add(s, x, y, scale, box, tag):
        runs.append(dict(s=s, x=x, y=y, scale=scale, box=box, tag=tag))

    add(TOPBAR_LEFT, 12, 8, 1, (0, 0, W, 22), "top left")
    tw = text_width(TOPBAR_RIGHT, 1)
    add(TOPBAR_RIGHT, 1012 - tw, 8, 1, (0, 0, W, 22), "top right")
    add(MASTHEAD, 44, 30, 6, (0, 22, W, 82), "masthead")
    stw = text_width(SUBTITLE, 2)
    add(SUBTITLE, (W - stw) // 2, 82, 2, (0, 78, W, 24), "subtitle")
    for i, (num, labels) in enumerate(KPI):
        cx = 12 + i * 167
        add(num, cx + 4, 114, 4, (cx, 110, 167, 34), "kpi num %d" % i)
        for j, lbl in enumerate(labels):
            add(lbl, cx + 4, 146 + j * 8, 1, (cx, 142, 167, 20),
                "kpi label %d/%d" % (i, j))
    for d in hero_layout():
        p = d["p"]
        add(p["chip"], d["chip_text"][0], d["chip_text"][1], 1, d["chip"], "chip")
        add(p["cat"], d["cat_box"][0], d["cat_box"][1], 1,
            (d["x"], d["y"] + 134, HERO_W, 14), "cat")
        for k, (ln, b) in enumerate(zip(p["title"], d["title_boxes"])):
            add(ln, b[0], b[1], 3, (d["x"], d["y"], HERO_W, HERO_H),
                "hero title %d" % k)
        for k, (ln, b) in enumerate(zip(p["sub"], d["sub_boxes"])):
            add(ln, b[0], b[1], 1, (d["x"], d["y"], HERO_W, HERO_H),
                "hero sub %d" % k)
        add(p["src"], d["src_box"][0], d["src_box"][1], 1,
            (d["x"], d["y"], HERO_W, HERO_H), "hero src")
    for d in mid_layout():
        p = d["p"]
        add(p["chip"], d["chip_text"][0], d["chip_text"][1], 1, d["chip"], "mid chip")
        for k, (ln, b) in enumerate(zip(p["title"], d["title_boxes"])):
            add(ln, b[0], b[1], 2, (d["x"], d["y"], MID_W, MID_H),
                "mid title %d" % k)
    add(MAP_TITLE, 20, 666, 1, (MAP_BOX[0], MAP_BOX[1], MAP_BOX[2], 12), "map title")
    add(MAP_CAPTION, 324 - text_width(MAP_CAPTION, 1), 666, 1,
        (MAP_BOX[0], MAP_BOX[1], MAP_BOX[2], 12), "map caption")
    add(LIST_TITLE, LIST_X, 666, 1, (LIST_X, 664, 1012 - LIST_X, 10), "list title")
    for d in list_layout():
        add(d["num"], d["chip_text"][0], d["chip_text"][1], 1, d["chip"], "list num")
        add(d["line"], LIST_TEXT_X, d["ly"], 1, (LIST_TEXT_X, d["ly"] - 2,
                                                1012 - LIST_TEXT_X, 11), "list line")
    add(DATE_TITLE, 20, 866, 2, (16, 862, 992, 18), "date title")
    for k, (ln, b) in enumerate(zip(DATE_LINES, date_layout())):
        add(ln, b[0], b[1], 1, (16, 862, 992, 96), "date line %d" % k)
    add(LEGEND_CONFIRMED, 30, 966, 1, (30, 964, 400, 11), "legend confirmed")
    x2 = 30 + text_width(LEGEND_CONFIRMED, 1) + 14
    add(LEGEND_CLAIM, x2 + 18, 966, 1, (x2 + 18, 964, 1012 - (x2 + 18), 11),
        "legend claim")
    add(FOOTER, 12, 996, 1, (12, 994, 1000, 10), "footer")
    return runs


def check_text_runs():
    runs = text_runs()
    assert len(runs) >= 90, "too few text runs recorded: %d" % len(runs)
    rects = []
    for r in runs:
        ext = glyph_extent(r["s"], r["x"], r["y"], r["scale"])
        assert ext is not None, "empty text run: %r" % r["tag"]
        ex, ey, ew, eh = ext
        bx, by, bw, bh = r["box"]
        assert ex >= bx and ey >= by, "%s: ink starts outside its box: %r" % (
            r["tag"], r["s"])
        assert ex + ew <= bx + bw, "%s: ink is clipped on the right: %r" % (
            r["tag"], r["s"])
        assert ey + eh <= by + bh, "%s: ink is clipped at the bottom: %r" % (
            r["tag"], r["s"])
        rects.append((ex, ey, ew, eh, r["s"], r["tag"]))

    # No two text runs may share a pixel.
    for i in range(len(rects)):
        ax, ay, aw, ah, a_s, a_t = rects[i]
        for j in range(i + 1, len(rects)):
            bx, by, bw, bh, b_s, b_t = rects[j]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                raise AssertionError("text overlap: %r (%s) and %r (%s)" % (
                    a_s, a_t, b_s, b_t))


def check_paper(x, y, w, h, tag):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            assert px(buf_global, xx, yy) == PAPER, \
                "%s: paper gutter dirty at (%d,%d)" % (tag, xx, yy)


def check_solid(x, y, w, h, colour, tag):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            assert px(buf_global, xx, yy) == colour, \
                "%s: expected solid %r at (%d,%d)" % (tag, colour, xx, yy)


def check_border(x, y, w, h, t, colour, tag):
    for xx in range(x, x + w):
        for dy in range(t):
            assert px(buf_global, xx, y + dy) == colour, "%s: top border" % tag
            assert px(buf_global, xx, y + h - 1 - dy) == colour, "%s: bottom border" % tag
    for yy in range(y, y + h):
        for dx in range(t):
            assert px(buf_global, x + dx, yy) == colour, "%s: left border" % tag
            assert px(buf_global, x + w - 1 - dx, yy) == colour, "%s: right border" % tag


def check_clean(x, y, w, h, base, allowed, tag, inset=1):
    """Inside a box every pixel is either the base colour or in an allowed rect."""
    for yy in range(y + inset, y + h - inset):
        spans = []
        for ax, ay, aw, ah in allowed:
            if ay <= yy < ay + ah:
                spans.append((ax, ax + aw))
        spans.sort()
        xi = x + inset
        right = x + w - inset
        for s0, s1 in spans:
            stop = min(s0, right)
            while xi < stop:
                assert px(buf_global, xi, yy) == base, \
                    "%s: stray pixel at (%d,%d)" % (tag, xi, yy)
                xi += 1
            if s1 > xi:
                xi = s1
        while xi < right:
            assert px(buf_global, xi, yy) == base, \
                "%s: stray pixel at (%d,%d)" % (tag, xi, yy)
            xi += 1


def count_colour(x, y, w, h, colour):
    n = 0
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if px(buf_global, xx, yy) == colour:
                n += 1
    return n


def count_not(x, y, w, h, colour):
    n = 0
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if px(buf_global, xx, yy) != colour:
                n += 1
    return n


def distinct_colours(x, y, w, h, step=2):
    seen = set()
    for yy in range(y, y + h, step):
        for xx in range(x, x + w, step):
            seen.add(px(buf_global, xx, yy))
    return seen


def check_scene(rect, tag):
    x, y, w, h = rect
    assert count_colour(x, y, w, h, PANEL) == 0, "%s: scene does not cover its box" % tag
    assert len(distinct_colours(x, y, w, h)) >= 3, "%s: scene is flat/empty" % tag


def check_text_box(box, colour, tag, minimum=6):
    n = count_colour(box[0], box[1], box[2], box[3], colour)
    assert n >= minimum, "%s: text missing (%d px)" % (tag, n)


def check_all(buf):
    global buf_global
    buf_global = buf

    check_text_runs()

    # --- data integrity -------------------------------------------------
    assert len(HERO) == 3, "need 3 hero stories"
    assert len(MID) == 10, "need 10 mid stories"
    assert len(LIST) == 13, "need 13 list stories"
    assert 3 + 10 + 13 == 26, "story count must be 26"
    nums = [e[0] for e in LIST]
    assert nums == ["%02d" % i for i in range(1, 14)], "list numbering broken"
    for e in LIST:
        assert len(e[3]) >= 2, "list story needs 2 sources: %r" % (e[1],)
        assert len(e[2]) <= 60, "list headline too long: %r" % (e[2],)
    for p in HERO:
        assert len(p["title"]) <= 2, "hero title over 2 lines"
        for ln in p["title"]:
            assert len(ln) <= HERO_TITLE_MAX, "hero title over %d: %r" % (
                HERO_TITLE_MAX, ln)
        for ln in p["sub"]:
            assert len(ln) <= HERO_SUB_MAX, "hero sub over %d: %r" % (
                HERO_SUB_MAX, ln)
    for p in MID:
        assert len(p["title"]) == 3, "mid title must be 3 lines"
        for ln in p["title"]:
            assert len(ln) <= MID_TITLE_MAX, "mid title over %d: %r" % (
                MID_TITLE_MAX, ln)

    # --- paper gutters stay empty --------------------------------------
    for (y0, y1, tag) in ((22, 29, "under top bar"), (73, 81, "under masthead"),
                          (97, 103, "under subtitle"), (106, 109, "under rule"),
                          (162, 167, "above hero"), (419, 425, "under hero"),
                          (539, 543, "between mid rows"), (657, 663, "under mid"),
                          (853, 859, "under bottom"), (959, 963, "under date box"),
                          (976, 995, "above footer"), (1004, 1023, "bottom margin")):
        check_paper(0, y0, W, y1 - y0 + 1, tag)
    check_paper(0, 168, 12, 250, "left of hero")
    check_paper(1012, 168, 12, 250, "right of hero")
    check_paper(0, 426, 10, 112, "left of mid row 1")
    check_paper(1015, 426, 9, 112, "right of mid row 1")
    check_paper(0, 544, 10, 112, "left of mid row 2")
    check_paper(1015, 544, 9, 112, "right of mid row 2")
    check_paper(0, 664, 12, 188, "left of map")
    check_paper(333, 664, 11, 188, "between map and list")
    check_paper(0, 860, 12, 98, "left of date box")
    check_paper(1012, 860, 12, 98, "right of date box")

    # --- top bar and masthead ------------------------------------------
    check_solid(0, 0, 12, 22, NAVY, "top bar left edge")
    check_solid(1012, 0, 12, 22, NAVY, "top bar right edge")
    check_solid(0, 0, W, 8, NAVY, "top bar above text")
    check_solid(0, 15, W, 7, NAVY, "top bar below text")
    check_text_box((12, 8, text_width(TOPBAR_LEFT, 1), ROWS), PAPER, "top bar left")
    tw = text_width(TOPBAR_RIGHT, 1)
    check_text_box((1012 - tw, 8, tw, ROWS), PAPER, "top bar right")
    check_text_box((44, 30, text_width(MASTHEAD, 6), 42), INK, "masthead", 400)
    stw = text_width(SUBTITLE, 2)
    check_text_box(((W - stw) // 2, 82, stw, 14), RED, "subtitle", 200)
    check_solid(12, 104, 1000, 2, INK, "masthead rule")

    # --- KPI ------------------------------------------------------------
    for i, (num, labels) in enumerate(KPI):
        cx = 12 + i * 167
        check_text_box((cx + 4, 114, text_width(num, 4), 28), RED,
                       "KPI number %d" % i, 40)
        for j, lbl in enumerate(labels):
            check_text_box((cx + 4, 146 + j * 8, text_width(lbl, 1), ROWS), INK,
                           "KPI label %d/%d" % (i, j))

    # --- hero panels ----------------------------------------------------
    hl = hero_layout()
    for d in hl:
        x, y, w, h = d["x"], d["y"], d["w"], d["h"]
        p = d["p"]
        tag = "hero %s" % p["cat"]
        check_border(x, y, w, h, 1, INK, tag)
        assert d["scene"][1] + d["scene"][3] <= d["chip"][1] - 2, \
            "%s: scene touches the chip" % tag
        assert d["chip"][1] + d["chip"][3] <= d["title_boxes"][0][1] - 2, \
            "%s: chip touches the title" % tag
        assert d["title_boxes"][-1][1] + d["title_boxes"][-1][3] < d["sub_boxes"][0][1], \
            "%s: title touches the sub" % tag
        assert d["sub_boxes"][-1][1] + d["sub_boxes"][-1][3] < d["src_box"][1], \
            "%s: sub touches the source" % tag
        for bx, by, bw, bh in d["title_boxes"] + d["sub_boxes"] + [d["src_box"]]:
            assert bx + bw <= x + w - 3, "%s: text runs past the panel edge" % tag
            assert by + bh <= y + h - 3, "%s: text runs past the panel floor" % tag
        check_scene(d["scene"], tag)
        check_solid(d["chip"][0], d["chip"][1], 3, 3,
                    GREEN if p["chip"] == "CONFIRMED" else RED, tag + " chip")
        allowed = [d["scene"], d["chip"],
                   ink(p["cat"], d["cat_box"][0], d["cat_box"][1], 1),
                   ink(p["src"], d["src_box"][0], d["src_box"][1], 1),
                   ink(p["chip"], d["chip_text"][0], d["chip_text"][1], 1)]
        allowed += [ink(ln, b[0], b[1], 3)
                    for ln, b in zip(p["title"], d["title_boxes"])]
        allowed += [ink(ln, b[0], b[1], 1)
                    for ln, b in zip(p["sub"], d["sub_boxes"])]
        check_clean(x, y, w, h, PANEL, allowed, tag)
        check_text_box(d["chip_text"], WHITE, tag + " chip text")
        check_text_exact(p["chip"], d["chip_text"][0], d["chip_text"][1], 1,
                         WHITE, GREEN if p["chip"] == "CONFIRMED" else RED,
                         tag + " chip")
        check_text_box(d["cat_box"], INK, tag + " category")
        check_text_exact(p["cat"], d["cat_box"][0], d["cat_box"][1], 1,
                         INK, PANEL, tag + " category")
        for k, (ln, b) in enumerate(zip(p["title"], d["title_boxes"])):
            check_text_box(b, INK, "%s title %d" % (tag, k), 20)
            check_text_exact(ln, b[0], b[1], 3, INK, PANEL,
                             "%s title %d" % (tag, k))
        for k, (ln, b) in enumerate(zip(p["sub"], d["sub_boxes"])):
            check_text_box(b, DARKTXT, "%s sub %d" % (tag, k), 20)
            check_text_exact(ln, b[0], b[1], 1, DARKTXT, PANEL,
                             "%s sub %d" % (tag, k))
        check_text_box(d["src_box"], DARKTXT, tag + " source", 20)
        check_text_exact(p["src"], d["src_box"][0], d["src_box"][1], 1,
                         DARKTXT, PANEL, tag + " source")

    # --- mid panels -----------------------------------------------------
    ml = mid_layout()
    for d in ml:
        x, y, w, h = d["x"], d["y"], d["w"], d["h"]
        p = d["p"]
        tag = "mid %s" % p["title"][0]
        check_border(x, y, w, h, 1, INK, tag)
        assert d["scene"][1] + d["scene"][3] <= d["chip"][1] - 2, \
            "%s: scene touches the chip" % tag
        assert d["chip"][1] + d["chip"][3] <= d["title_boxes"][0][1] - 2, \
            "%s: chip touches the title" % tag
        for k in range(len(d["title_boxes"]) - 1):
            a = d["title_boxes"][k]
            b = d["title_boxes"][k + 1]
            assert a[1] + a[3] <= b[1], "%s: title lines overlap" % tag
        for bx, by, bw, bh in d["title_boxes"]:
            assert bx + bw <= x + w - 3, "%s: title runs past the panel" % tag
            assert by + bh <= y + h - 3, "%s: title runs past the panel floor" % tag
        check_scene(d["scene"], tag)
        check_solid(d["chip"][0], d["chip"][1], 3, 3,
                    GREEN if p["chip"] == "CONFIRMED" else RED, tag + " chip")
        allowed = [d["scene"], d["chip"],
                   ink(p["chip"], d["chip_text"][0], d["chip_text"][1], 1)]
        allowed += [ink(ln, b[0], b[1], 2)
                    for ln, b in zip(p["title"], d["title_boxes"])]
        check_clean(x, y, w, h, PANEL, allowed, tag)
        check_text_box(d["chip_text"], WHITE, tag + " chip text")
        check_text_exact(p["chip"], d["chip_text"][0], d["chip_text"][1], 1,
                         WHITE, GREEN if p["chip"] == "CONFIRMED" else RED,
                         tag + " chip")
        for k, (ln, b) in enumerate(zip(p["title"], d["title_boxes"])):
            check_text_box(b, INK, "%s title %d" % (tag, k), 12)
            check_text_exact(ln, b[0], b[1], 2, INK, PANEL,
                             "%s title %d" % (tag, k))

    # --- map ------------------------------------------------------------
    check_border(MAP_BOX[0], MAP_BOX[1], MAP_BOX[2], MAP_BOX[3], 1, INK, "map frame")
    assert MAP_X > MAP_BOX[0] and MAP_Y > MAP_BOX[1], "map interior not inset"
    assert MAP_X + MAP_W < MAP_BOX[0] + MAP_BOX[2], "map interior too wide"
    assert MAP_Y + MAP_H < MAP_BOX[1] + MAP_BOX[3], "map interior too tall"
    assert count_colour(MAP_X, MAP_Y, MAP_W, MAP_H, PAPER) == 0, \
        "map interior has unpainted paper"
    land_px = count_colour(MAP_X, MAP_Y, MAP_W, MAP_H, LAND)
    assert land_px > 1500, "map land is too small: %d px" % land_px
    assert count_colour(MAP_X, MAP_Y, MAP_W, MAP_H, RED) > 13 * 8, \
        "map story dots missing"

    # --- list -----------------------------------------------------------
    check_text_box((LIST_X, 666, text_width(LIST_TITLE, 1), ROWS), RED,
                   "list title", 40)
    ll = list_layout()
    allowed = [ink(LIST_TITLE, LIST_X, 666, 1)]
    for d in ll:
        assert LIST_TEXT_X + text_width(d["line"], 1) <= 1012, \
            "list line runs past x=1012: %r" % d["line"]
        assert len(d["line"]) <= LIST_MAX, "list line over %d chars: %r" % (
            LIST_MAX, d["line"])
        allowed.append(d["chip"])
        allowed.append(ink(d["line"], LIST_TEXT_X, d["ly"], 1))
        allowed.append(ink(d["num"], d["chip_text"][0], d["chip_text"][1], 1))
        check_solid(d["chip"][0], d["chip"][1], 3, 3, BLUE, "list chip %s" % d["num"])
        check_text_box(d["chip_text"], WHITE, "list num %s" % d["num"], 4)
        check_text_exact(d["num"], d["chip_text"][0], d["chip_text"][1], 1,
                         WHITE, BLUE, "list num %s" % d["num"])
        check_text_box((d["text_box"][0], d["ly"], text_width(d["line"], 1), ROWS),
                       INK, "list line %s" % d["num"], 30)
        check_text_exact(d["line"], LIST_TEXT_X, d["ly"], 1, INK, PAPER,
                         "list line %s" % d["num"])
    for k in range(len(ll) - 1):
        assert ll[k]["ly"] + ROWS <= ll[k + 1]["ly"], "list lines overlap"
    check_clean(340, 664, 676, 192, PAPER, allowed, "list column")

    # --- date check box --------------------------------------------------
    check_border(12, 860, 1000, 98, 2, RED, "date box")
    check_text_box((20, 866, text_width(DATE_TITLE, 2), 14), RED,
                   "date title", 60)
    db = date_layout()
    for k, (ln, b) in enumerate(zip(DATE_LINES, db)):
        check_text_box(b, INK, "date line %d" % k, 30)
    allowed = [ink(DATE_TITLE, 20, 866, 2)]
    allowed += [ink(ln, b[0], b[1], 1) for ln, b in zip(DATE_LINES, db)]
    check_clean(12, 860, 1000, 98, PAPER, allowed, "date box", 2)

    # --- legend and footer ----------------------------------------------
    check_solid(12, 964, 12, 11, GREEN, "legend green chip")
    check_text_box((30, 966, text_width(LEGEND_CONFIRMED, 1), ROWS), INK,
                   "legend confirmed", 30)
    x2 = 30 + text_width(LEGEND_CONFIRMED, 1) + 14
    check_solid(x2, 964, 12, 11, RED, "legend red chip")
    check_text_box((x2 + 18, 966, text_width(LEGEND_CLAIM, 1), ROWS), INK,
                   "legend claim", 20)
    assert x2 + 18 + text_width(LEGEND_CLAIM, 1) <= 1012, "legend runs off page"
    check_text_box((12, 996, text_width(FOOTER, 1), ROWS), DARKTXT,
                   "footer", 80)


def build():
    buf = bytearray(W * H * 3)
    fill_rect(buf, 0, 0, W, H, PAPER)
    draw_topbar(buf)
    draw_masthead(buf)
    draw_kpi(buf)
    draw_hero(buf, hero_layout())
    draw_mid(buf, mid_layout())
    draw_bottom(buf)
    draw_datebox(buf)
    draw_legend(buf)
    draw_footer(buf)
    check_all(buf)
    return buf


# --------------------------------------------------------------------------
# PNG output.
# --------------------------------------------------------------------------

def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


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
    path = os.path.join(out_dir, "entry.png")
    encode_png(path, buf)
    size = os.path.getsize(path)
    assert size <= 1024 * 1024, "PNG is larger than 1 MiB: %d" % size


if __name__ == "__main__":
    main()
