"""
Tower Defense + Procedural Map  (v2)
พัฒนาโดย Mr.Prachya
-------------------------------
Single file, uses only the Python standard library (tkinter).
Run:  python tower_defense.py

Controls
  Left-click empty grass  : build the selected tower
  Left-click a tower      : select it (upgrade / sell / targeting)
  Right-click / Esc       : cancel
  1-9                     : pick a tower type
  Space                   : start the next wave
  U / S                   : upgrade / sell the selected tower
  T                       : change targeting mode of the selected tower
  F                       : game speed (1x / 2x / 3x)
  A                       : auto wave on/off
  P                       : pause
  R                       : restart on the same map
  N                       : new random map
"""

import math
import random
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser

# ---------------------------------------------------------------- settings
COLS, ROWS, CELL = 20, 14, 40
W, H = COLS * CELL, ROWS * CELL
PW = 300          # side panel width
TOP = 54          # top bar height
FONT = "Tahoma"   # replaced at startup by the best Thai-capable font found
MAX_LEVEL = 4
START_GOLD = 180
START_LIVES = 20

# modern dark theme
BG = "#121624"
CARD = "#1d2335"
CARD_HI = "#283049"
CARD_SEL = "#313d5c"
LINE = "#2c3550"
TEXT = "#e9ecf5"
MUTED = "#8a93ab"
DIM = "#525a72"
ACCENT = "#ffc845"
GOOD = "#3ddc84"
BAD = "#ff5370"
BLUE = "#4d9dff"
SHADOW = "#2b5230"       # drop shadow on grass (tk has no real transparency)
PATH_SHADOW = "#a5844f"  # drop shadow on the road

DEV_NAME = "Prachya WC"
REPO_URL = "https://github.com/prachyafff-cmyk/SimpleGame"

# attack: bullet | shell | missile | beam | chain | cone | none
TOWER_TYPES = {
    "gun": dict(name="ปืนกล", key="1", cost=50, attack="bullet", range=105, rate=0.30,
                dmg=7, speed=520, air=True, color="#4fc3f7",
                desc="ยิงรัวเร็ว ราคาถูก ยิงศัตรูบินได้"),
    "cannon": dict(name="ปืนใหญ่", key="2", cost=90, attack="shell", range=100, rate=1.25,
                   dmg=28, speed=280, splash=55, color="#ff8a65",
                   desc="กระสุนระเบิดวงกว้าง โจมตีภาคพื้นเท่านั้น"),
    "frost": dict(name="น้ำแข็ง", key="3", cost=70, attack="shell", range=95, rate=0.9,
                  dmg=3, speed=340, splash=42, slow=0.5, color="#9be7ff",
                  desc="แช่แข็งศัตรูรอบจุดตกให้เดินช้าลง"),
    "sniper": dict(name="สไนเปอร์", key="4", cost=125, attack="bullet", range=240, rate=1.7,
                   dmg=70, speed=1500, air=True, pierce=True, color="#ce93d8",
                   desc="ระยะไกลมาก ดาเมจสูง เจาะเกราะ"),
    "laser": dict(name="เลเซอร์", key="5", cost=140, attack="beam", range=120, rate=0,
                  dmg=14, air=True, color="#ff4fd8",
                  desc="ลำแสงต่อเนื่อง ยิ่งยิงนานยิ่งแรง (สูงสุด x3)"),
    "tesla": dict(name="สายฟ้า", key="6", cost=150, attack="chain", range=110, rate=1.1,
                  dmg=18, chain=3, air=True, color="#fff176",
                  desc="ฟ้าผ่ากระโดดไปหาศัตรูหลายตัว"),
    "flame": dict(name="พ่นไฟ", key="7", cost=110, attack="cone", range=80, rate=0.12,
                  dmg=2.5, burn=6, color="#ff7043",
                  desc="พ่นไฟเป็นกรวย ทำให้ติดไฟต่อเนื่อง"),
    "missile": dict(name="จรวด", key="8", cost=180, attack="missile", range=190, rate=1.7,
                    dmg=45, speed=230, splash=48, air=True, color="#90a4ae",
                    desc="จรวดนำวิถีระเบิดวงกว้าง เล็งตัวเลือดมาก"),
    "mine": dict(name="เหมืองทอง", key="9", cost=100, attack="none", range=0, rate=0,
                 dmg=0, gold=18, color="#ffd54f",
                 desc="ไม่โจมตี แต่ให้ทองทุกครั้งที่จบ Wave"),
}

TARGET_MODES = ["first", "last", "strong", "close"]
TARGET_NAMES = {"first": "หน้าสุด", "last": "ท้ายสุด", "strong": "เลือดมาก", "close": "ใกล้สุด"}

ENEMY_TYPES = {
    "grunt": dict(name="ทหาร", hp=30, speed=55, reward=5, r=9, gap=0.65, lives=1,
                  color="#ef5350", hint="ศัตรูพื้นฐาน"),
    "runner": dict(name="นักวิ่ง", hp=18, speed=108, reward=4, r=8, gap=0.38, lives=1,
                   color="#ffca28", hint="วิ่งเร็วมาก"),
    "flyer": dict(name="ค้างคาว", hp=26, speed=68, reward=7, r=9, gap=0.7, lives=1, air=True,
                  color="#ab47bc", hint="บินตรงข้ามแผนที่! ปืนใหญ่/น้ำแข็ง/ไฟ ยิงไม่ได้"),
    "splitter": dict(name="แตกตัว", hp=55, speed=44, reward=6, r=11, gap=0.9, lives=1,
                     color="#ff9800", hint="ตายแล้วแตกเป็นตัวเล็ก 2 ตัว"),
    "mini": dict(name="ลูกแตก", hp=14, speed=74, reward=2, r=6, gap=0.3, lives=1,
                 color="#ffb74d", hint=""),
    "tank": dict(name="รถถัง", hp=115, speed=33, reward=12, r=12, gap=1.0, lives=2, armor=4,
                 color="#8d6e63", hint="มีเกราะ ลดดาเมจ ใช้สไนเปอร์เจาะ"),
    "healer": dict(name="หมอ", hp=45, speed=48, reward=9, r=10, gap=0.9, lives=1,
                   color="#66bb6a", hint="รักษาเพื่อนรอบตัว ฆ่าก่อน!"),
    "shield": dict(name="โล่", hp=40, speed=50, reward=9, r=10, gap=0.8, lives=1, shield=45,
                   color="#42a5f5", hint="มีโล่ดูดดาเมจ ฟื้นได้เอง"),
    "ghost": dict(name="วิญญาณ", hp=42, speed=60, reward=8, r=9, gap=0.75, lives=1,
                  color="#e3e6ff", hint="หายตัวเป็นช่วงๆ ยิงไม่โดน"),
    "boss": dict(name="บอส", hp=700, speed=27, reward=100, r=17, gap=2.0, lives=8, armor=3,
                 color="#c62828", hint="เรียกลูกน้องออกมาเรื่อยๆ"),
}
UNLOCK = [("grunt", 1), ("runner", 2), ("flyer", 3), ("splitter", 4), ("tank", 5),
          ("healer", 6), ("shield", 7), ("ghost", 8)]
WAVE_WEIGHT = {"grunt": 3, "runner": 2, "flyer": 1.2, "splitter": 1.2, "tank": 1,
               "healer": 0.7, "shield": 1, "ghost": 1}


# ---------------------------------------------------------------- helpers
def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rrect(c, x0, y0, x1, y1, r, **kw):
    """Rounded rectangle on a canvas."""
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def rot_pts(x, y, ang, s, pts):
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for px, py in pts:
        out += [x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s]
    return out


def ang_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def value_noise(rng, cols, rows, scale):
    """Smooth random 2D noise in [0,1]."""
    gw, gh = int(cols / scale) + 2, int(rows / scale) + 2
    g = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def s(t):
        return t * t * (3 - 2 * t)

    out = [[0.0] * cols for _ in range(rows)]
    for y in range(rows):
        fy = y / scale
        iy, ty = int(fy), s(fy - int(fy))
        for x in range(cols):
            fx = x / scale
            ix, tx = int(fx), s(fx - int(fx))
            a = g[iy][ix] + (g[iy][ix + 1] - g[iy][ix]) * tx
            b = g[iy + 1][ix] + (g[iy + 1][ix + 1] - g[iy + 1][ix]) * tx
            out[y][x] = a + (b - a) * ty
    return out


def gen_path(rng):
    """Random self-avoiding walk from the left edge to the right edge."""
    min_len = rng.randint(COLS + 18, COLS + 40)
    best = None
    dirs = [(1, 0), (0, 1), (0, -1), (-1, 0)]
    base_w = {(1, 0): 1.0, (0, 1): 1.6, (0, -1): 1.6, (-1, 0): 0.45}

    for _ in range(600):
        sy = rng.randrange(2, ROWS - 2)
        path = [(0, sy), (1, sy)]
        vis = set(path)
        last_dir = (1, 0)
        done = False
        for _step in range(400):
            x, y = path[-1]
            cands, weights = [], []
            for d in dirs:
                nx, ny = x + d[0], y + d[1]
                if not (1 <= ny <= ROWS - 2):
                    continue
                if not (1 <= nx <= COLS - 2 or (nx == COLS - 1 and x == COLS - 2)):
                    continue
                if (nx, ny) in vis:
                    continue
                ok = True
                for dd in dirs:
                    m = (nx + dd[0], ny + dd[1])
                    if m != (x, y) and m in vis:
                        ok = False
                        break
                if not ok:
                    continue
                cands.append(d)
                weights.append(base_w[d] * (2.0 if d == last_dir else 1.0))
            if not cands:
                break
            d = rng.choices(cands, weights)[0]
            nxt = (x + d[0], y + d[1])
            path.append(nxt)
            vis.add(nxt)
            last_dir = d
            if nxt[0] == COLS - 1:
                done = True
                break
        if done:
            if len(path) >= min_len:
                return path
            if best is None or len(path) > len(best):
                best = path
    if best:
        return best
    return [(x, ROWS // 2) for x in range(COLS)]


# ---------------------------------------------------------------- drawing
def draw_tower(c, kind, x, y, ang, level, s=1.0, tags=(), sel=False):
    col = TOWER_TYPES[kind]["color"]
    dark = lerp_color(col, "#000000", 0.45)
    h = 16 * s
    rrect(c, x - h + 2, y - h + 3, x + h + 2, y + h + 3, 7 * s, fill=SHADOW,
          outline="", tags=tags)
    rrect(c, x - h, y - h, x + h, y + h, 7 * s, fill="#3a4560",
          outline=ACCENT if sel else "#56627f", width=2 if sel else 1, tags=tags)
    R = lambda pts: rot_pts(x, y, ang, s, pts)

    def circ(cx, cy, r, **kw):
        c.create_oval(x + (cx - r) * s, y + (cy - r) * s, x + (cx + r) * s, y + (cy + r) * s,
                      tags=tags, **kw)

    if kind == "gun":
        circ(0, 0, 10, fill=col, outline=dark, width=2)
        for off in (-3.5, 3.5):
            c.create_line(*R([(2, off), (18, off)]), fill="#263238",
                          width=max(2, 3 * s), tags=tags)
        circ(0, 0, 4, fill="#eceff1", outline="")
    elif kind == "cannon":
        circ(0, 0, 11, fill=col, outline=dark, width=2)
        c.create_polygon(*R([(0, -4.5), (17, -4.5), (17, 4.5), (0, 4.5)]), fill="#4e342e",
                         tags=tags)
        c.create_polygon(*R([(14, -6), (19, -6), (19, 6), (14, 6)]), fill="#3e2723", tags=tags)
        circ(0, 0, 5, fill=dark, outline="")
    elif kind == "frost":
        hexa = [(math.cos(ang + i * math.pi / 3) * 12, math.sin(ang + i * math.pi / 3) * 12)
                for i in range(6)]
        c.create_polygon(*rot_pts(x, y, 0, s, hexa), fill=col, outline="#e1f5fe", width=2,
                         tags=tags)
        for i in range(3):
            a = ang + i * math.pi / 3
            c.create_line(x - math.cos(a) * 8 * s, y - math.sin(a) * 8 * s,
                          x + math.cos(a) * 8 * s, y + math.sin(a) * 8 * s,
                          fill="#ffffff", width=max(1, 2 * s), tags=tags)
        circ(0, 0, 3, fill="#ffffff", outline="")
    elif kind == "sniper":
        circ(0, 0, 8, fill=col, outline=dark, width=2)
        c.create_line(*R([(0, 0), (25, 0)]), fill="#4a148c", width=max(2, 3 * s), tags=tags)
        c.create_polygon(*R([(2, -6), (11, -6), (11, -2.5), (2, -2.5)]), fill="#212121",
                         tags=tags)
        circ(0, 0, 3, fill="#f3e5f5", outline="")
    elif kind == "laser":
        circ(0, 0, 11, fill="#311b42", outline=col, width=2)
        c.create_polygon(*R([(17, 0), (-6, -8), (-6, 8)]), fill=col, outline="#ffffff",
                         tags=tags)
        px, py = x + math.cos(ang) * 6 * s, y + math.sin(ang) * 6 * s
        c.create_oval(px - 3 * s, py - 3 * s, px + 3 * s, py + 3 * s, fill="#ffffff",
                      outline="", tags=tags)
    elif kind == "tesla":
        circ(0, 0, 12, fill="#37474f", outline=col, width=2)
        circ(0, 0, 8, fill="", outline=col, width=1)
        circ(0, 0, 5, fill="#fffde7", outline=col, width=2)
        for i in range(4):
            a = ang + i * math.pi / 2
            c.create_line(x + math.cos(a) * 6 * s, y + math.sin(a) * 6 * s,
                          x + math.cos(a + 0.4) * 11 * s, y + math.sin(a + 0.4) * 11 * s,
                          fill=col, width=1, tags=tags)
    elif kind == "flame":
        circ(0, 0, 10, fill="#bf360c", outline="#4e1a06", width=2)
        c.create_polygon(*R([(3, -4.5), (18, -6.5), (18, 6.5), (3, 4.5)]), fill="#455a64",
                         outline="#263238", tags=tags)
        tx, ty = x + math.cos(ang) * 18 * s, y + math.sin(ang) * 18 * s
        c.create_oval(tx - 3 * s, ty - 3 * s, tx + 3 * s, ty + 3 * s, fill=col, outline="",
                      tags=tags)
        circ(-3, 0, 3, fill="#ffab91", outline="")
    elif kind == "missile":
        c.create_polygon(*R([(-10, -11), (11, -11), (11, 11), (-10, 11)]), fill="#546e7a",
                         outline="#263238", width=2, tags=tags)
        for off in (-5.5, 5.5):
            c.create_polygon(*R([(-6, off - 3.5), (14, off - 3.5), (14, off + 3.5),
                                 (-6, off + 3.5)]), fill="#37474f", tags=tags)
            tx = x + (math.cos(ang) * 14 - math.sin(ang) * off) * s
            ty = y + (math.sin(ang) * 14 + math.cos(ang) * off) * s
            c.create_oval(tx - 2.5 * s, ty - 2.5 * s, tx + 2.5 * s, ty + 2.5 * s,
                          fill="#ff5252", outline="", tags=tags)
    elif kind == "mine":
        c.create_polygon(*rot_pts(x, y, 0, s, [(-12, -1), (12, -1), (9, 10), (-9, 10)]),
                         fill="#6d4c41", outline="#3e2723", width=2, tags=tags)
        for gx, gy, gr in ((-6, -5, 4.5), (1, -8, 5), (7, -4, 4)):
            circ(gx, gy, gr, fill=col, outline="#c79a00")
        circ(-6, 11, 2.5, fill="#212121", outline="")
        circ(6, 11, 2.5, fill="#212121", outline="")
    for i in range(level):
        px = x - 9 * s + i * 6 * s
        c.create_oval(px - 2 * s, y + h - 6 * s, px + 2 * s, y + h - 2 * s,
                      fill=ACCENT, outline="", tags=tags)


def draw_enemy(c, kind, x, y, r, ang, anim, tags=(), fill=None, flash=False,
               phased=False, shield_on=False, shadow=True):
    spec = ENEMY_TYPES[kind]
    col = fill or spec["color"]
    outline = "#ffffff" if flash else lerp_color(col, "#000000", 0.5)

    def eyes(fwd, side, size, color="#ffffff"):
        for sgn in (-1, 1):
            ex = x + math.cos(ang) * fwd - math.sin(ang) * side * sgn
            ey = y + math.sin(ang) * fwd + math.cos(ang) * side * sgn
            c.create_oval(ex - size, ey - size, ex + size, ey + size, fill=color,
                          outline="", tags=tags)
            px, py = ex + math.cos(ang) * size * 0.4, ey + math.sin(ang) * size * 0.4
            c.create_oval(px - size * 0.5, py - size * 0.5, px + size * 0.5, py + size * 0.5,
                          fill="#111111", outline="", tags=tags)

    if shadow:
        if spec.get("air"):
            c.create_oval(x - r * 0.8 + 5, y + r + 2, x + r * 0.8 + 5, y + r + 8,
                          fill=SHADOW, outline="", tags=tags)
        else:
            c.create_oval(x - r, y + r * 0.3, x + r, y + r + 4,
                          fill=PATH_SHADOW, outline="", tags=tags)

    if kind == "grunt":
        c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline=outline, width=2, tags=tags)
        eyes(r * 0.35, r * 0.38, r * 0.25)
    elif kind == "runner":
        c.create_polygon(*rot_pts(x, y, ang, 1, [(r * 1.35, 0), (-r, -r), (-r * 0.5, 0),
                                                 (-r, r)]),
                         fill=col, outline=outline, width=2, tags=tags)
        eyes(r * 0.2, r * 0.3, r * 0.22)
    elif kind == "tank":
        c.create_polygon(*rot_pts(x, y, ang, 1, [(-r, -r), (r, -r), (r, -r * 0.55),
                                                 (-r, -r * 0.55)]), fill="#3e2723", tags=tags)
        c.create_polygon(*rot_pts(x, y, ang, 1, [(-r, r * 0.55), (r, r * 0.55), (r, r),
                                                 (-r, r)]), fill="#3e2723", tags=tags)
        c.create_polygon(*rot_pts(x, y, ang, 1, [(-r * 0.85, -r * 0.6), (r * 0.85, -r * 0.6),
                                                 (r * 0.85, r * 0.6), (-r * 0.85, r * 0.6)]),
                         fill=col, outline="#bdbdbd" if not flash else "#ffffff", width=2,
                         tags=tags)
        c.create_line(*rot_pts(x, y, ang, 1, [(0, 0), (r * 1.45, 0)]), fill="#3e2723",
                      width=4, tags=tags)
        c.create_oval(x - r * 0.45, y - r * 0.45, x + r * 0.45, y + r * 0.45,
                      fill=lerp_color(col, "#000000", 0.3), outline="#bdbdbd", tags=tags)
    elif kind == "healer":
        c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline=outline, width=2, tags=tags)
        a, b = r * 0.55, r * 0.18
        c.create_rectangle(x - a, y - b, x + a, y + b, fill="#ffffff", outline="", tags=tags)
        c.create_rectangle(x - b, y - a, x + b, y + a, fill="#ffffff", outline="", tags=tags)
    elif kind == "shield":
        c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline=outline, width=2, tags=tags)
        eyes(r * 0.35, r * 0.38, r * 0.25)
        if shield_on:
            hexa = [(math.cos(anim * 1.5 + i * math.pi / 3) * (r + 5),
                     math.sin(anim * 1.5 + i * math.pi / 3) * (r + 5)) for i in range(6)]
            c.create_polygon(*rot_pts(x, y, 0, 1, hexa), fill="", outline="#80d8ff", width=2,
                             tags=tags)
    elif kind in ("splitter", "mini"):
        n = 9
        pts = []
        for i in range(n):
            a = i * 2 * math.pi / n
            rr = r * (1 + 0.14 * math.sin(anim * 6 + i * 1.7))
            pts += [x + math.cos(a) * rr, y + math.sin(a) * rr]
        c.create_polygon(pts, smooth=True, fill=col, outline=outline, width=2, tags=tags)
        if kind == "splitter":
            c.create_line(x - r * 0.1, y - r * 0.9, x + r * 0.15, y - r * 0.2, x - r * 0.1,
                          y + r * 0.3, fill=lerp_color(col, "#000000", 0.5), width=2, tags=tags)
        eyes(r * 0.35, r * 0.38, max(1.5, r * 0.24))
    elif kind == "flyer":
        flap = abs(math.sin(anim * 9))
        span = r * (0.8 + 1.0 * flap)
        wing = lerp_color(col, "#000000", 0.35)
        for sgn in (-1, 1):
            c.create_polygon(*rot_pts(x, y, ang, 1, [(r * 0.3, sgn * r * 0.3),
                                                     (-r * 0.2, sgn * (r * 0.4 + span)),
                                                     (-r * 0.6, sgn * (r * 0.2 + span * 0.6)),
                                                     (-r * 0.9, sgn * (r * 0.3 + span * 0.8)),
                                                     (-r * 0.5, sgn * r * 0.2)]),
                             fill=wing, outline=outline, tags=tags)
        c.create_oval(x - r * 0.7, y - r * 0.7, x + r * 0.7, y + r * 0.7, fill=col,
                      outline=outline, width=2, tags=tags)
        eyes(r * 0.25, r * 0.25, r * 0.18, "#ff8a80")
    elif kind == "ghost":
        wob = math.sin(anim * 6) * r * 0.2
        pts = [x - r, y + r, x - r, y - r * 0.2, x - r * 0.7, y - r, x, y - r * 1.25,
               x + r * 0.7, y - r, x + r, y - r * 0.2, x + r, y + r,
               x + r * 0.5, y + r * 0.55 + wob, x, y + r, x - r * 0.5, y + r * 0.55 - wob]
        if phased:
            c.create_polygon(pts, smooth=True, fill="", outline=col, width=2,
                             dash=(3, 3), tags=tags)
        else:
            c.create_polygon(pts, smooth=True, fill=col, outline=outline, width=2, tags=tags)
            c.create_oval(x - r * 0.5, y - r * 0.45, x - r * 0.15, y, fill="#1a1a2e",
                          outline="", tags=tags)
            c.create_oval(x + r * 0.15, y - r * 0.45, x + r * 0.5, y, fill="#1a1a2e",
                          outline="", tags=tags)
    elif kind == "boss":
        n = 12
        pts = []
        for i in range(n * 2):
            a = anim * 0.6 + i * math.pi / n
            rr = r * 1.28 if i % 2 == 0 else r * 0.95
            pts += [x + math.cos(a) * rr, y + math.sin(a) * rr]
        c.create_polygon(pts, fill="#4a0e0e", outline="#1a0000", tags=tags)
        c.create_oval(x - r * 0.92, y - r * 0.92, x + r * 0.92, y + r * 0.92, fill=col,
                      outline="#ffffff" if flash else "#3b0000", width=2, tags=tags)
        cy = y - r * 0.95
        c.create_polygon(x - r * 0.55, cy + 3, x - r * 0.55, cy - 7, x - r * 0.25, cy - 2,
                         x, cy - 10, x + r * 0.25, cy - 2, x + r * 0.55, cy - 7,
                         x + r * 0.55, cy + 3, fill=ACCENT, outline="#b8860b", tags=tags)
        eyes(r * 0.3, r * 0.35, r * 0.18, "#ffeb3b")


# ---------------------------------------------------------------- entities
class Enemy:
    def __init__(self, kind, game, hp_mult, reward_mult, armor_bonus=0):
        s = ENEMY_TYPES[kind]
        self.kind = kind
        self.air = s.get("air", False)
        self.route = game.air_pts if self.air else game.pts
        self.total = game.air_len if self.air else game.path_len
        self.x, self.y = self.route[0]
        self.i = 0
        self.dist = 0.0
        self.max_hp = s["hp"] * hp_mult
        self.hp = self.max_hp
        self.max_shield = s.get("shield", 0) * hp_mult
        self.shield = self.max_shield
        self.shield_cd = 0.0
        self.armor = s.get("armor", 0) + (armor_bonus if s.get("armor") else 0)
        self.speed = s["speed"]
        self.reward = max(1, int(round(s["reward"] * reward_mult)))
        self.color = s["color"]
        self.r = s["r"]
        self.lives = s["lives"]
        self.slow_t = 0.0
        self.slow_f = 1.0
        self.burn_t = 0.0
        self.burn_dps = 0.0
        self.flash = 0.0
        self.angle = 0.0
        self.anim = random.random() * 10
        self.cycle = random.random() * 2
        self.ab = 3.0 if kind == "boss" else 1.0
        self.phased = False
        self.dead = False
        self.reached = False

    @property
    def progress(self):
        return self.dist / self.total

    def targetable(self):
        return not self.dead and not self.phased

    def apply_slow(self, factor, dur):
        if self.kind == "boss":
            factor = (1 + factor) / 2
        cur = self.slow_f if self.slow_t > 0 else 1.0
        self.slow_f = min(cur, factor)
        self.slow_t = max(self.slow_t, dur)

    def update(self, dt):
        self.anim += dt
        if self.slow_t > 0:
            self.slow_t -= dt
            spd = self.speed * self.slow_f
        else:
            spd = self.speed
        if self.burn_t > 0:
            self.burn_t -= dt
            self.hp -= self.burn_dps * dt
        else:
            self.burn_dps = 0
        if self.max_shield:
            self.shield_cd -= dt
            if self.shield_cd <= 0 and self.shield < self.max_shield:
                self.shield = min(self.max_shield, self.shield + self.max_shield * 0.2 * dt)
        if self.kind == "ghost":
            self.cycle += dt
            self.phased = (self.cycle % 3.6) > 2.4
        self.flash = max(0.0, self.flash - dt)

        move = spd * dt
        self.dist += move
        while move > 0 and self.i < len(self.route) - 1:
            tx, ty = self.route[self.i + 1]
            dx, dy = tx - self.x, ty - self.y
            d = math.hypot(dx, dy)
            if d < 1e-6:
                self.i += 1
                continue
            self.angle = math.atan2(dy, dx)
            if d <= move:
                self.x, self.y = tx, ty
                self.i += 1
                move -= d
            else:
                self.x += dx / d * move
                self.y += dy / d * move
                move = 0
        if self.i >= len(self.route) - 1:
            self.reached = True


class Tower:
    def __init__(self, kind, cx, cy):
        self.kind = kind
        self.cx, self.cy = cx, cy
        self.x = cx * CELL + CELL / 2
        self.y = cy * CELL + CELL / 2
        self.level = 1
        self.cd = 0.0
        self.angle = -math.pi / 2
        self.spent = TOWER_TYPES[kind]["cost"]
        self.mode = "strong" if kind == "missile" else "first"
        self.beam_target = None
        self.beam_time = 0.0

    @property
    def spec(self):
        return TOWER_TYPES[self.kind]

    @property
    def dmg(self):
        return self.spec["dmg"] * (1.5 ** (self.level - 1))

    @property
    def range(self):
        return self.spec["range"] * (1 + 0.1 * (self.level - 1))

    @property
    def rate(self):
        return self.spec["rate"] * (0.9 ** (self.level - 1))

    @property
    def slow(self):
        if not self.spec.get("slow"):
            return 0
        return max(0.25, self.spec["slow"] - 0.06 * (self.level - 1))

    @property
    def slow_dur(self):
        return 1.2 + 0.4 * (self.level - 1)

    @property
    def chain(self):
        return self.spec.get("chain", 0) + (self.level - 1)

    @property
    def burn(self):
        return self.spec.get("burn", 0) * (1.45 ** (self.level - 1))

    @property
    def income(self):
        return int(self.spec.get("gold", 0) * (1 + 0.75 * (self.level - 1)))

    @property
    def upgrade_cost(self):
        if self.level >= MAX_LEVEL:
            return None
        return int(self.spec["cost"] * 0.9 * self.level)

    @property
    def sell_value(self):
        return int(self.spent * 0.7)


class Projectile:
    def __init__(self, t, target):
        self.x = t.x + math.cos(t.angle) * 16
        self.y = t.y + math.sin(t.angle) * 16
        self.target = target
        self.tx, self.ty = target.x, target.y
        sp = t.spec
        self.kind = t.kind
        self.speed = sp.get("speed", 400)
        self.dmg = t.dmg
        self.splash = sp.get("splash", 0)
        self.slow = t.slow
        self.slow_dur = t.slow_dur
        self.air = sp.get("air", False)
        self.pierce = sp.get("pierce", False)
        self.ang = t.angle
        self.done = False


def tower_stats(kind, level):
    """List of (label, value) for the info card."""
    t = Tower(kind, 0, 0)
    t.level = level
    sp = t.spec
    att = sp["attack"]
    rng = f"{t.range:.0f}"
    if att == "none":
        return [("รายได้", f"+{t.income}/เวฟ"), ("ขายได้", f"${t.sell_value}")]
    if att == "beam":
        return [("DPS", f"{t.dmg:.0f}-{t.dmg * 3:.0f}"), ("ระยะ", rng),
                ("ชาร์จเต็ม", "2 วิ"), ("อากาศ", "ได้")]
    if att == "cone":
        return [("ดาเมจ", f"{t.dmg / t.rate:.0f}/วิ"), ("ไฟไหม้", f"{t.burn:.0f}/วิ"),
                ("ระยะ", rng), ("มุมพ่น", "70°")]
    out = [("ดาเมจ", f"{t.dmg:.0f}"), ("ระยะ", rng), ("ยิง/วิ", f"{1 / t.rate:.1f}")]
    if t.slow:
        out.append(("ช้าลง", f"{int((1 - t.slow) * 100)}%"))
    elif att == "chain":
        out.append(("กระโดด", f"{t.chain} เป้า"))
    elif sp.get("pierce"):
        out.append(("พิเศษ", "เจาะเกราะ"))
    elif t.spec.get("splash"):
        out.append(("ระเบิด", f"{sp['splash']}"))
    else:
        out.append(("อากาศ", "ได้" if sp.get("air") else "ไม่ได้"))
    return out


# ---------------------------------------------------------------- game
class Game:
    def __init__(self, root):
        self.root = root
        root.title("Tower Defense + Procedural Map")
        root.resizable(False, False)
        root.configure(bg=BG)

        self.top = tk.Canvas(root, width=W + PW, height=TOP, bg=BG, highlightthickness=0)
        self.top.grid(row=0, column=0, columnspan=2)
        self.canvas = tk.Canvas(root, width=W, height=H, bg="#000", highlightthickness=0,
                                cursor="crosshair")
        self.canvas.grid(row=1, column=0)
        self.side = tk.Canvas(root, width=PW, height=H, bg=BG, highlightthickness=0)
        self.side.grid(row=1, column=1)

        self.f_toast = tkfont.Font(family=FONT, size=-16, weight="bold")

        self.mouse = None
        self.speed_mult = 1
        self.paused = False
        self.auto_wave = False
        self.best_wave = 0
        self.hover = {"top": None, "side": None}
        self.btns = {"top": [], "side": []}
        self.sig = {"top": None, "side": None}
        self.cvs = {"top": self.top, "side": self.side}

        for name, cv in self.cvs.items():
            cv.bind("<Motion>", lambda e, n=name: self.ui_motion(n, e.x, e.y))
            cv.bind("<Leave>", lambda e, n=name: self.ui_motion(n, -1, -1))
            cv.bind("<Button-1>", lambda e, n=name: self.ui_click(n, e.x, e.y))
        c = self.canvas
        c.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))
        c.bind("<Leave>", lambda e: setattr(self, "mouse", None))
        c.bind("<Button-1>", self.on_click)
        c.bind("<Button-3>", lambda e: self.cancel())
        root.bind("<Key>", self.on_key)

        self.new_game()
        self.last = time.perf_counter()
        self.loop()

    # ------------------------------------------------------------ setup
    def new_game(self, seed=None):
        self.seed = seed if seed is not None else random.randint(1, 999999)
        rng = random.Random(self.seed)
        self.wave_rng = random.Random(self.seed * 7 + 1)
        self.path = gen_path(rng)
        self.path_set = set(self.path)
        self.gen_terrain(rng)

        cx = lambda v: v * CELL + CELL / 2
        pts = [(cx(x), cx(y)) for x, y in self.path]
        sx, sy = pts[0]
        ex, ey = pts[-1]
        self.pts = [(sx - CELL, sy)] + pts + [(ex + CELL, ey)]
        self.path_len = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                            for a, b in zip(self.pts, self.pts[1:]))
        self.air_pts = [self.pts[0], self.pts[-1]]
        self.air_len = math.hypot(self.pts[-1][0] - self.pts[0][0],
                                  self.pts[-1][1] - self.pts[0][1])

        self.gold = START_GOLD
        self.lives = START_LIVES
        self.wave = 0
        self.kills = 0
        self.enemies = []
        self.pending = []
        self.towers = {}
        self.projectiles = []
        self.effects = []
        self.particles = []
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.wave_active = False
        self.auto_timer = 0.0
        self.hp_mult = 1.0
        self.reward_mult = 1.0
        self.gap_mult = 1.0
        self.armor_bonus = 0
        self.selected = None
        self.build_type = None
        self.game_over = False
        self.paused = False
        self.anim = 0.0
        self.next_queue, self.next_tag = self.build_wave(1)
        self.message = ("แผนที่ใหม่! วางป้อมแล้วกด Space เพื่อเริ่ม", 3.5, ACCENT)
        self.draw_map()

    def gen_terrain(self, rng):
        n1 = value_noise(rng, COLS, ROWS, 5)
        n2 = value_noise(rng, COLS, ROWS, 2.5)
        self.height = [[n1[y][x] * 0.7 + n2[y][x] * 0.3 for x in range(COLS)]
                       for y in range(ROWS)]
        water_lvl = rng.uniform(0.66, 0.74)
        self.terrain = {}
        near_path = set()
        for (x, y) in self.path:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    near_path.add((x + dx, y + dy))
        for y in range(ROWS):
            for x in range(COLS):
                if (x, y) in self.path_set:
                    self.terrain[(x, y)] = "path"
                elif self.height[y][x] > water_lvl:
                    self.terrain[(x, y)] = "water"
                else:
                    chance = 0.04 if (x, y) in near_path else 0.10
                    if rng.random() < chance:
                        self.terrain[(x, y)] = rng.choice(["tree", "tree", "rock"])
                    else:
                        self.terrain[(x, y)] = "grass"

    def draw_map(self):
        c = self.canvas
        c.delete("all")
        dr = random.Random(self.seed)
        for y in range(ROWS):
            for x in range(COLS):
                t = self.terrain[(x, y)]
                h = self.height[y][x]
                x0, y0 = x * CELL, y * CELL
                x1, y1 = x0 + CELL, y0 + CELL
                grass = lerp_color("#3f7a45", "#78b35d", h * 1.3 - 0.1)
                if (x + y) % 2:
                    grass = lerp_color(grass, "#000000", 0.04)
                if t == "water":
                    col = lerp_color("#3d8fd6", "#1b4f8a", (h - 0.66) * 4)
                    c.create_rectangle(x0, y0, x1, y1, fill=col, outline=col)
                    if dr.random() < 0.45:
                        wx, wy = x0 + dr.randint(6, 24), y0 + dr.randint(8, 30)
                        c.create_line(wx, wy, wx + 5, wy - 2, wx + 10, wy, fill="#8cc6f2",
                                      width=2, smooth=True)
                    continue
                c.create_rectangle(x0, y0, x1, y1, fill=grass, outline=grass)
                if t == "tree":
                    ox, oy = dr.randint(-4, 4), dr.randint(-4, 4)
                    cx, cy = x0 + 20 + ox, y0 + 18 + oy
                    c.create_oval(cx - 13, cy + 6, cx + 15, cy + 17,
                                  fill=lerp_color(grass, "#000000", 0.35), outline="")
                    c.create_rectangle(cx - 2, cy + 3, cx + 2, cy + 12, fill="#6d4c2f",
                                       outline="")
                    c.create_oval(cx - 13, cy - 13, cx + 13, cy + 8, fill="#2e7d32",
                                  outline="#1b5e20", width=2)
                    c.create_oval(cx - 7, cy - 9, cx + 3, cy - 1, fill="#4caf50", outline="")
                elif t == "rock":
                    cx, cy = x0 + 20, y0 + 22
                    c.create_oval(cx - 13, cy + 3, cx + 15, cy + 12,
                                  fill=lerp_color(grass, "#000000", 0.35), outline="")
                    c.create_polygon(cx - 13, cy + 6, cx - 9, cy - 8, cx + 2, cy - 12,
                                     cx + 12, cy - 4, cx + 13, cy + 7,
                                     fill="#90a4ae", outline="#546e7a", width=2)
                    c.create_line(cx - 5, cy - 6, cx + 3, cy - 9, fill="#cfd8dc", width=2)
                elif t == "grass" and dr.random() < 0.3:
                    gx, gy = x0 + dr.randint(5, 32), y0 + dr.randint(8, 32)
                    if dr.random() < 0.3:
                        fc = dr.choice(["#fff59d", "#f8bbd0", "#ffffff", "#b39ddb"])
                        c.create_oval(gx - 2, gy - 2, gx + 2, gy + 2, fill=fc, outline="")
                    else:
                        gc = lerp_color(grass, "#ffffff", 0.18)
                        c.create_line(gx, gy, gx - 2, gy - 5, fill=gc)
                        c.create_line(gx, gy, gx + 2, gy - 5, fill=gc)
        # shorelines
        for (x, y), t in self.terrain.items():
            if t != "water":
                continue
            x0, y0 = x * CELL, y * CELL
            for dx, dy, coords in ((0, -1, (x0, y0, x0 + CELL, y0)),
                                   (0, 1, (x0, y0 + CELL, x0 + CELL, y0 + CELL)),
                                   (-1, 0, (x0, y0, x0, y0 + CELL)),
                                   (1, 0, (x0 + CELL, y0, x0 + CELL, y0 + CELL))):
                if self.terrain.get((x + dx, y + dy), "water") != "water":
                    c.create_line(*coords, fill="#b3e0ff", width=2)
        # path as one smooth rounded road
        flat = [v for p in self.pts for v in p]
        c.create_line(*flat, width=CELL - 2, fill="#8a6a3e", capstyle=tk.ROUND,
                      joinstyle=tk.ROUND)
        c.create_line(*flat, width=CELL - 9, fill="#d9b77b", capstyle=tk.ROUND,
                      joinstyle=tk.ROUND)
        c.create_line(*flat, width=2, fill="#c9a46a", dash=(6, 8))
        for (x, y) in self.path:
            for _ in range(2):
                px, py = x * CELL + dr.randint(8, 30), y * CELL + dr.randint(8, 30)
                c.create_oval(px, py, px + 3, py + 3, fill="#b08b52", outline="")
        # start portal (swirl is animated in render)
        sx, sy = self.path[0]
        x0, y0 = sx * CELL, sy * CELL
        c.create_oval(x0 + 2, y0 + 2, x0 + 38, y0 + 38, fill="#2a0b4d", outline="#e040fb",
                      width=3)
        c.create_oval(x0 + 12, y0 + 12, x0 + 28, y0 + 28, fill="#0b0014", outline="")
        # castle at the end
        ex, ey = self.path[-1]
        x0, y0 = ex * CELL, ey * CELL
        c.create_rectangle(x0 + 6, y0 + 12, x0 + 34, y0 + 37, fill="#b0bec5",
                           outline="#455a64", width=2)
        for i in range(4):
            bx = x0 + 6 + i * 8
            c.create_rectangle(bx, y0 + 6, bx + 5, y0 + 12, fill="#b0bec5", outline="#455a64")
        c.create_rectangle(x0 + 15, y0 + 24, x0 + 25, y0 + 37, fill="#5d4037", outline="")
        c.create_line(x0 + 20, y0 + 6, x0 + 20, y0 - 7, fill="#263238", width=2)
        c.create_polygon(x0 + 20, y0 - 7, x0 + 32, y0 - 3, x0 + 20, y0 + 1, fill=BAD)

    # ------------------------------------------------------------ waves
    def build_wave(self, n):
        rng = self.wave_rng
        unlocked = [k for k, w in UNLOCK if n >= w]
        count = 6 + int(n * 1.7)
        tag = ""
        if n >= 4 and n % 5 == 0 and n % 10 != 0:
            kind = rng.choice(unlocked[1:])
            mult = 0.7 if kind in ("tank", "healer", "shield") else 1.25
            q = [kind] * int(count * mult)
            tag = "swarm"
        else:
            q = rng.choices(unlocked, [WAVE_WEIGHT[k] for k in unlocked], k=count)
            for k, w in UNLOCK:
                if w == n and k != "grunt":
                    for _ in range(3):
                        q.insert(rng.randrange(len(q) + 1), k)
            if n % 10 == 0:
                q += ["boss"] * (n // 10)
                tag = "boss"
        return q, tag

    def start_wave(self):
        if self.game_over or self.spawn_queue:
            return
        bonus = 0
        if self.enemies:  # calling early gives bonus gold
            bonus = 10 + self.wave
            self.gold += bonus
        self.wave += 1
        n = self.wave
        self.spawn_queue = list(self.next_queue)
        tag = self.next_tag
        self.next_queue, self.next_tag = self.build_wave(n + 1)
        self.spawn_timer = 0.0
        self.wave_active = True
        self.hp_mult = 1 + 0.22 * (n - 1) + 0.022 * (n - 1) ** 2
        self.reward_mult = 1 + 0.04 * (n - 1)
        self.gap_mult = max(0.5, 1 - 0.02 * n)
        self.armor_bonus = n // 8
        new = [k for k, w in UNLOCK if w == n and k != "grunt"]
        if new:
            s = ENEMY_TYPES[new[0]]
            self.flash_msg(f"ศัตรูใหม่: {s['name']} - {s['hint']}", 4.0, BAD)
        elif tag == "boss":
            self.flash_msg(f"Wave {n}  -  บอสมาแล้ว!", 2.5, BAD)
        elif tag == "swarm":
            self.flash_msg(f"Wave {n}  -  ฝูง{ENEMY_TYPES[self.spawn_queue[0]]['name']}!",
                           2.5, ACCENT)
        elif bonus:
            self.flash_msg(f"เรียก Wave {n} ก่อนเวลา  +{bonus} ทอง", 1.8, ACCENT)
        else:
            self.flash_msg(f"Wave {n}", 1.5, TEXT)

    # ------------------------------------------------------------ input
    def on_key(self, e):
        k = e.keysym.lower()
        for name, t in TOWER_TYPES.items():
            if e.char == t["key"]:
                self.choose(name)
                return
        actions = {"space": self.start_wave, "escape": self.cancel, "u": self.upgrade,
                   "s": self.sell, "t": self.cycle_mode, "f": self.toggle_speed,
                   "a": self.toggle_auto, "p": self.toggle_pause,
                   "r": lambda: self.new_game(self.seed), "n": self.new_game}
        if k in actions:
            actions[k]()

    def choose(self, kind):
        self.build_type = None if self.build_type == kind else kind
        self.selected = None

    def cancel(self):
        self.build_type = None
        self.selected = None

    def toggle_speed(self):
        self.speed_mult = self.speed_mult % 3 + 1

    def toggle_auto(self):
        self.auto_wave = not self.auto_wave

    def open_repo(self):
        webbrowser.open(REPO_URL)

    def toggle_pause(self):
        if not self.game_over:
            self.paused = not self.paused

    def cycle_mode(self):
        s = self.selected
        if s and s.spec["attack"] != "none":
            s.mode = TARGET_MODES[(TARGET_MODES.index(s.mode) + 1) % len(TARGET_MODES)]

    def can_build(self, cell):
        return self.terrain.get(cell) == "grass" and cell not in self.towers

    def on_click(self, e):
        if self.game_over:
            return
        cell = (e.x // CELL, e.y // CELL)
        if cell in self.towers:
            self.selected = self.towers[cell]
            self.build_type = None
            return
        if self.build_type:
            self.place_tower(self.build_type, cell)
            return
        self.selected = None

    def place_tower(self, kind, cell):
        cost = TOWER_TYPES[kind]["cost"]
        if not self.can_build(cell):
            self.flash_msg("สร้างตรงนี้ไม่ได้", 1.2, BAD)
            return False
        if self.gold < cost:
            self.flash_msg("ทองไม่พอ!", 1.2, BAD)
            return False
        self.gold -= cost
        t = Tower(kind, *cell)
        self.towers[cell] = t
        self.burst(t.x, t.y, "#ffffff", 8, 60)
        return True

    def upgrade(self):
        s = self.selected
        if not s or self.game_over:
            return
        uc = s.upgrade_cost
        if uc is None:
            self.flash_msg("เลเวลสูงสุดแล้ว", 1.2, MUTED)
        elif self.gold < uc:
            self.flash_msg("ทองไม่พอ!", 1.2, BAD)
        else:
            self.gold -= uc
            s.spent += uc
            s.level += 1
            self.effects.append(dict(kind="ring", x=s.x, y=s.y, t=0, dur=0.45, color=ACCENT,
                                     r=30))
            self.burst(s.x, s.y, ACCENT, 12, 90)

    def sell(self):
        s = self.selected
        if not s or self.game_over:
            return
        value = s.spent if self.wave == 0 else s.sell_value
        self.gold += value
        self.add_text(s.x, s.y, f"+{value}", ACCENT)
        del self.towers[(s.cx, s.cy)]
        self.selected = None

    def flash_msg(self, text, dur=1.4, color=TEXT):
        self.message = (text, dur, color)

    # ------------------------------------------------------------ UI widgets
    def ui_motion(self, name, x, y):
        hid = None
        for bid, (x0, y0, x1, y1), _cb, _en in self.btns[name]:
            if x0 <= x <= x1 and y0 <= y <= y1:
                hid = bid
                break
        if hid != self.hover[name]:
            self.hover[name] = hid
            self.cvs[name].configure(cursor="hand2" if hid else "")

    def ui_click(self, name, x, y):
        for bid, (x0, y0, x1, y1), cb, en in self.btns[name]:
            if x0 <= x <= x1 and y0 <= y <= y1:
                if en:
                    cb()
                return

    def button(self, cvname, bid, x0, y0, x1, y1, label, cb, style="normal", enabled=True,
               size=10, icon=None):
        c = self.cvs[cvname]
        hov = self.hover[cvname] == bid
        styles = {"normal": (CARD_HI, "#36405c", TEXT),
                  "primary": ("#2fbf71", "#3ddc84", "#08180f"),
                  "info": ("#3d7fe0", "#5a96f0", "#ffffff"),
                  "danger": ("#d63c58", "#ee5470", "#ffffff"),
                  "toggle_on": ("#2a6b4c", "#33805b", "#ffffff")}
        bg, bgh, fg = styles[style]
        if not enabled:
            bg, bgh, fg = "#20263a", "#20263a", DIM
        rrect(c, x0, y0, x1, y1, min(12, (y1 - y0) / 2), fill=bgh if hov else bg, outline="")
        cx = (x0 + x1) / 2
        if icon:
            tw = tkfont.Font(family=FONT, size=-round(size * 4 / 3), weight="bold").measure(label)
            ix = cx - tw / 2 - 8
            icon(c, ix, (y0 + y1) / 2, fg)
            cx += 8
        c.create_text(cx, (y0 + y1) / 2, text=label, fill=fg, font=(FONT, -round(size * 4 / 3), "bold"))
        self.btns[cvname].append((bid, (x0, y0, x1, y1), cb, enabled))

    # ------------------------------------------------------------ top bar
    def draw_top(self):
        c = self.top
        c.delete("all")
        self.btns["top"] = []
        c.create_rectangle(0, 0, W + PW, TOP, fill=BG, outline="")
        c.create_line(0, TOP - 1, W + PW, TOP - 1, fill=LINE)
        draw_tower(c, "tesla", 28, TOP / 2, self.anim, 0, 0.85)
        c.create_text(54, 20, anchor="w", text="TOWER DEFENSE", font=(FONT, -17, "bold"),
                      fill=TEXT)
        c.create_text(54, 38, anchor="w", text=f"Procedural Map  •  Seed {self.seed}",
                      font=(FONT, -11), fill=MUTED)

        def chip(x, w, icon, text, fg):
            rrect(c, x, 10, x + w, TOP - 10, 16, fill=CARD, outline=LINE)
            icon(x + 19, TOP / 2)
            c.create_text(x + 34, TOP / 2, anchor="w", text=text, fill=fg,
                          font=(FONT, -15, "bold"))
            return x + w + 8

        def coin(x, y):
            c.create_oval(x - 8, y - 8, x + 8, y + 8, fill=ACCENT, outline="#b8860b", width=2)
            c.create_text(x, y, text="$", fill="#7a5a00", font=(FONT, -11, "bold"))

        def heart(x, y):
            c.create_oval(x - 8, y - 7, x, y + 1, fill=BAD, outline="")
            c.create_oval(x, y - 7, x + 8, y + 1, fill=BAD, outline="")
            c.create_polygon(x - 7.5, y - 1.5, x + 7.5, y - 1.5, x, y + 8, fill=BAD, outline="")

        def flag(x, y):
            c.create_line(x - 5, y - 8, x - 5, y + 8, fill=MUTED, width=2)
            c.create_polygon(x - 4, y - 8, x + 8, y - 4, x - 4, y, fill=BLUE, outline="")

        def skull(x, y):
            c.create_oval(x - 7, y - 8, x + 7, y + 5, fill="#cfd3e0", outline="")
            c.create_rectangle(x - 4, y + 2, x + 4, y + 8, fill="#cfd3e0", outline="")
            c.create_oval(x - 5, y - 4, x - 1, y, fill=BG, outline="")
            c.create_oval(x + 1, y - 4, x + 5, y, fill=BG, outline="")

        x = 262
        x = chip(x, 96, coin, f"{self.gold}", ACCENT)
        x = chip(x, 76, heart, f"{self.lives}", BAD if self.lives <= 5 else TEXT)
        x = chip(x, 104, flag, f"Wave {self.wave}", TEXT)
        x = chip(x, 86, skull, f"{self.kills}", TEXT)

        # developer credit -> opens the GitHub repo
        def code_icon(cv, ix, iy, fg):
            cv.create_line(ix - 2, iy - 5, ix - 7, iy, ix - 2, iy + 5, fill=fg, width=2)
            cv.create_line(ix + 2, iy - 5, ix + 7, iy, ix + 2, iy + 5, fill=fg, width=2)

        self.button("top", "dev", x, 11, x + 120, TOP - 11, f"by {DEV_NAME}",
                    self.open_repo, size=9, icon=code_icon)

        # right-side controls
        right = W + PW - 12
        y0, y1 = 11, TOP - 11

        def pause_icon(cv, ix, iy, fg):
            if self.paused:
                cv.create_polygon(ix - 4, iy - 6, ix + 6, iy, ix - 4, iy + 6, fill=fg)
            else:
                cv.create_rectangle(ix - 5, iy - 6, ix - 1, iy + 6, fill=fg, outline="")
                cv.create_rectangle(ix + 1, iy - 6, ix + 5, iy + 6, fill=fg, outline="")

        def speed_icon(cv, ix, iy, fg):
            n = self.speed_mult
            for i in range(n):
                ox = ix - (n - 1) * 4 + i * 8
                cv.create_polygon(ox - 4, iy - 6, ox + 4, iy, ox - 4, iy + 6, fill=fg)

        # auto toggle
        ax0 = right - 98
        hov = self.hover["top"] == "auto"
        rrect(c, ax0, y0, right, y1, 14, fill="#36405c" if hov else CARD_HI, outline="")
        c.create_text(ax0 + 14, TOP / 2, anchor="w", text="Auto", fill=TEXT,
                      font=(FONT, -13, "bold"))
        tx0 = right - 44
        rrect(c, tx0, TOP / 2 - 8, tx0 + 32, TOP / 2 + 8, 8,
              fill=GOOD if self.auto_wave else "#4a536d", outline="")
        kx = tx0 + 24 if self.auto_wave else tx0 + 8
        c.create_oval(kx - 6, TOP / 2 - 6, kx + 6, TOP / 2 + 6, fill="#ffffff", outline="")
        self.btns["top"].append(("auto", (ax0, y0, right, y1), self.toggle_auto, True))

        sx1 = ax0 - 8
        self.button("top", "speed", sx1 - 84, y0, sx1, y1, f"{self.speed_mult}x",
                    self.toggle_speed, icon=speed_icon)
        px1 = sx1 - 92
        self.button("top", "pause", px1 - 104, y0, px1, y1,
                    "เล่นต่อ" if self.paused else "หยุด", self.toggle_pause,
                    style="info" if self.paused else "normal", icon=pause_icon)

    # ------------------------------------------------------------ side panel
    def draw_side(self):
        c = self.side
        c.delete("all")
        self.btns["side"] = []
        hov = self.hover["side"]

        c.create_text(14, 18, anchor="w", text="ป้อมป้องกัน", font=(FONT, -15, "bold"),
                      fill=TEXT)
        c.create_text(PW - 14, 18, anchor="e", text="กด 1-9 เพื่อเลือก", font=(FONT, -11),
                      fill=MUTED)
        cw, ch, gap = (PW - 24 - 16) / 3, 68, 8
        for idx, (k, t) in enumerate(TOWER_TYPES.items()):
            x0 = 12 + (idx % 3) * (cw + gap)
            y0 = 34 + (idx // 3) * (ch + gap)
            x1, y1 = x0 + cw, y0 + ch
            afford = self.gold >= t["cost"]
            sel = self.build_type == k
            bid = "t:" + k
            bg = CARD_SEL if sel else (CARD_HI if hov == bid else CARD)
            rrect(c, x0, y0, x1, y1, 10, fill=bg, outline=ACCENT if sel else LINE,
                  width=2 if sel else 1)
            mx = (x0 + x1) / 2
            draw_tower(c, k, mx, y0 + 25, -0.7, 0, 0.72)
            c.create_text(mx, y0 + 49, text=t["name"], font=(FONT, -12),
                          fill=TEXT if afford else DIM)
            c.create_text(mx, y0 + 61, text=f"${t['cost']}", font=(FONT, -12, "bold"),
                          fill=ACCENT if afford else DIM)
            rrect(c, x0 + 5, y0 + 5, x0 + 19, y0 + 19, 5, fill="#10141f", outline="")
            c.create_text(x0 + 12, y0 + 12, text=t["key"], font=(FONT, -11, "bold"),
                          fill=MUTED)
            self.btns["side"].append((bid, (x0, y0, x1, y1), lambda k=k: self.choose(k), True))

        # ---- info card
        y0, y1 = 262, 414
        rrect(c, 12, y0, PW - 12, y1, 12, fill=CARD, outline=LINE)
        s = self.selected
        show = hov[2:] if hov and hov.startswith("t:") else self.build_type
        if s:
            draw_tower(c, s.kind, 42, y0 + 30, -0.7, 0, 0.9)
            c.create_text(70, y0 + 20, anchor="w", text=s.spec["name"],
                          font=(FONT, -16, "bold"), fill=TEXT)
            for i in range(MAX_LEVEL):
                px = 76 + i * 14
                c.create_oval(px - 4, y0 + 38, px + 4, y0 + 46,
                              fill=ACCENT if i < s.level else "#3a4258", outline="")
            c.create_text(76 + MAX_LEVEL * 14, y0 + 42, anchor="w", text=f"เลเวล {s.level}",
                          font=(FONT, -12), fill=MUTED)
            cur = tower_stats(s.kind, s.level)
            nxt = None
            if hov == "up" and s.upgrade_cost:
                nxt = tower_stats(s.kind, s.level + 1)
            self.draw_stats(c, cur, nxt, y0 + 62)
            by = y0 + 100
            if s.spec["attack"] != "none":
                self.button("side", "mode", 24, by, PW - 24, by + 22,
                            f"เป้าหมาย: {TARGET_NAMES[s.mode]}   [T]", self.cycle_mode, size=9)
            uc = s.upgrade_cost
            by = y0 + 126
            self.button("side", "up", 24, by, PW / 2 - 4, by + 22,
                        f"อัปเกรด ${uc}" if uc else "สูงสุดแล้ว", self.upgrade, style="info",
                        enabled=bool(uc) and self.gold >= uc, size=9)
            sv = s.spent if self.wave == 0 else s.sell_value
            self.button("side", "sell", PW / 2 + 4, by, PW - 24, by + 22, f"ขาย ${sv}",
                        self.sell, style="danger", size=9)
        elif show:
            t = TOWER_TYPES[show]
            draw_tower(c, show, 42, y0 + 30, -0.7, 0, 0.9)
            c.create_text(70, y0 + 20, anchor="w", text=t["name"], font=(FONT, -16, "bold"),
                          fill=TEXT)
            c.create_text(70, y0 + 41, anchor="w", text=f"${t['cost']}",
                          font=(FONT, -13, "bold"), fill=ACCENT)
            if t["attack"] != "none":
                air = t.get("air", False)
                rrect(c, PW - 100, y0 + 33, PW - 24, y0 + 50, 8,
                      fill="#1f4a36" if air else "#4a1f2a", outline="")
                c.create_text(PW - 62, y0 + 41, text="อากาศ: ได้" if air else "อากาศ: ไม่ได้",
                              font=(FONT, -11, "bold"), fill=GOOD if air else BAD)
            c.create_text(24, y0 + 66, anchor="w", text=t["desc"], font=(FONT, -12),
                          fill=MUTED, width=PW - 48)
            self.draw_stats(c, tower_stats(show, 1), None, y0 + 98)
        else:
            c.create_text(24, y0 + 20, anchor="w", text="วิธีเล่น", font=(FONT, -15, "bold"),
                          fill=TEXT)
            lines = ["เลือกป้อมด้านบน แล้วคลิกบนพื้นหญ้า",
                     "คลิกที่ป้อมเพื่ออัปเกรด / ขาย / เปลี่ยนเป้า",
                     "คลิกขวา หรือ Esc เพื่อยกเลิก",
                     "ศัตรูบินได้จะบินตรงข้ามแผนที่",
                     "ขายป้อมก่อน Wave 1 ได้เงินคืนเต็ม"]
            for i, ln in enumerate(lines):
                c.create_oval(26, y0 + 46 + i * 20, 31, y0 + 51 + i * 20, fill=ACCENT,
                              outline="")
                c.create_text(38, y0 + 48 + i * 20, anchor="w", text=ln, font=(FONT, -12),
                              fill=MUTED)

        # ---- next wave preview
        y0, y1 = 422, 478
        rrect(c, 12, y0, PW - 12, y1, 12, fill=CARD, outline=LINE)
        n = self.wave + 1
        c.create_text(24, y0 + 14, anchor="w", text=f"Wave ถัดไป   {n}", font=(FONT, -13, "bold"),
                      fill=TEXT)
        if self.next_tag:
            label, col = ("BOSS", BAD) if self.next_tag == "boss" else ("ฝูง", ACCENT)
            rrect(c, PW - 74, y0 + 6, PW - 24, y0 + 22, 8, fill=col, outline="")
            c.create_text(PW - 49, y0 + 14, text=label, font=(FONT, -11, "bold"), fill="#1a1a1a")
        counts = {}
        for k in self.next_queue:
            counts[k] = counts.get(k, 0) + 1
        x = 34
        for k, cnt in list(counts.items())[:6]:
            draw_enemy(c, k, x, y0 + 38, 7, 0, 0, shadow=False, shield_on=(k == "shield"))
            c.create_text(x + 11, y0 + 39, anchor="w", text=f"x{cnt}", font=(FONT, -11, "bold"),
                          fill=MUTED)
            x += 44

        # ---- start wave button
        busy = bool(self.spawn_queue)
        if busy:
            label = f"ศัตรูกำลังมา...  ({len(self.spawn_queue)})"
        elif self.enemies:
            label = f"เรียก Wave {n} ก่อน  +${10 + self.wave}"
        else:
            label = f"เริ่ม Wave {n}    [Space]"
        self.button("side", "wave", 12, 486, PW - 12, 518, label, self.start_wave,
                    style="primary", enabled=not busy and not self.game_over, size=11)
        self.button("side", "restart", 12, 526, PW / 2 - 4, 552, "เล่นใหม่  [R]",
                    lambda: self.new_game(self.seed), size=9)
        self.button("side", "newmap", PW / 2 + 4, 526, PW - 12, 552, "แผนที่ใหม่  [N]",
                    self.new_game, size=9)

    def draw_stats(self, c, cur, nxt, y):
        for i, (label, val) in enumerate(cur):
            x = 24 + (i % 2) * 132
            yy = y + (i // 2) * 20
            c.create_text(x, yy, anchor="w", text=label, font=(FONT, -12), fill=MUTED)
            if nxt and nxt[i][1] != val:
                c.create_text(x + 62, yy, anchor="w", text=f"{val} » {nxt[i][1]}",
                              font=(FONT, -12, "bold"), fill=GOOD)
            else:
                c.create_text(x + 62, yy, anchor="w", text=val, font=(FONT, -12, "bold"),
                              fill=TEXT)

    def refresh_ui(self):
        s = self.selected
        top_sig = (self.gold, self.lives, self.wave, self.kills, self.paused, self.speed_mult,
                   self.auto_wave, self.hover["top"], self.seed)
        if top_sig != self.sig["top"]:
            self.sig["top"] = top_sig
            self.draw_top()
        side_sig = (self.gold, self.build_type, self.hover["side"], self.wave,
                    len(self.spawn_queue), bool(self.enemies), self.game_over, self.seed,
                    (id(s), s.level, s.mode) if s else None)
        if side_sig != self.sig["side"]:
            self.sig["side"] = side_sig
            self.draw_side()

    # ------------------------------------------------------------ combat
    def find_target(self, t):
        best, bestv = None, None
        rr = t.range * t.range
        can_air = t.spec.get("air", False)
        for e in self.enemies:
            if not e.targetable() or (e.air and not can_air):
                continue
            d2 = (e.x - t.x) ** 2 + (e.y - t.y) ** 2
            if d2 > rr:
                continue
            if t.mode == "first":
                v = e.progress
            elif t.mode == "last":
                v = -e.progress
            elif t.mode == "strong":
                v = e.hp + e.shield
            else:
                v = -d2
            if best is None or v > bestv:
                best, bestv = e, v
        return best

    def in_range(self, t, e):
        return (e.x - t.x) ** 2 + (e.y - t.y) ** 2 <= t.range * t.range

    def damage(self, e, amount, pierce=False, dot=False):
        if e.dead or e.phased:
            return
        if e.armor and not pierce:
            amount = amount * 0.6 if dot else max(amount * 0.3, amount - e.armor)
        if e.shield > 0:
            absorbed = min(e.shield, amount)
            e.shield -= absorbed
            amount -= absorbed
        e.shield_cd = 2.0
        e.hp -= amount
        e.flash = 0.06

    def aim(self, t, target, dt):
        want = math.atan2(target.y - t.y, target.x - t.x)
        t.angle += ang_diff(want, t.angle) * min(1.0, dt * 18)

    def fire_chain(self, t, target):
        hits = [target]
        cur = target
        for _ in range(t.chain - 1):
            nxt, bd = None, 80 * 80
            for e in self.enemies:
                if e in hits or not e.targetable():
                    continue
                d2 = (e.x - cur.x) ** 2 + (e.y - cur.y) ** 2
                if d2 < bd:
                    nxt, bd = e, d2
            if not nxt:
                break
            hits.append(nxt)
            cur = nxt
        pts = [(t.x, t.y)] + [(e.x, e.y) for e in hits]
        for k, e in enumerate(hits):
            self.damage(e, t.dmg * (0.8 ** k))
            self.burst(e.x, e.y, "#fff59d", 3, 70, life=0.2)
        jag = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = bx - ax, by - ay
            d = math.hypot(dx, dy) or 1
            nx, ny = -dy / d, dx / d
            for i in range(5):
                f = i / 5
                off = 0 if i == 0 else random.uniform(-7, 7)
                jag += [ax + dx * f + nx * off, ay + dy * f + ny * off]
        jag += [pts[-1][0], pts[-1][1]]
        self.effects.append(dict(kind="bolt", pts=jag, t=0, dur=0.16, x=0, y=0))

    def fire_cone(self, t):
        rr = t.range * t.range
        for e in self.enemies:
            if not e.targetable() or e.air:
                continue
            dx, dy = e.x - t.x, e.y - t.y
            if dx * dx + dy * dy > rr:
                continue
            if abs(ang_diff(math.atan2(dy, dx), t.angle)) < 0.62:
                self.damage(e, t.dmg, dot=True)
                e.burn_dps = max(e.burn_dps if e.burn_t > 0 else 0, t.burn)
                e.burn_t = 2.0
        for _ in range(3):
            a = t.angle + random.uniform(-0.45, 0.45)
            sp = random.uniform(150, 230) * t.range / 80
            self.particles.append([t.x + math.cos(a) * 16, t.y + math.sin(a) * 16,
                                   math.cos(a) * sp, math.sin(a) * sp, 0.33, 0.33,
                                   "#fff3a0", "#ff3d00", 6, 0, True])

    def hit(self, p):
        if p.splash:
            r2 = p.splash * p.splash
            for e in self.enemies:
                if e.dead or (e.air and not p.air):
                    continue
                if (e.x - p.x) ** 2 + (e.y - p.y) ** 2 <= r2:
                    self.damage(e, p.dmg)
                    if p.slow:
                        e.apply_slow(p.slow, p.slow_dur)
            if p.slow:
                self.effects.append(dict(kind="boom", x=p.x, y=p.y, t=0, dur=0.3,
                                         color="#e1f5fe", r=p.splash))
                self.burst(p.x, p.y, "#b3e5fc", 8, 80)
            else:
                self.effects.append(dict(kind="boom", x=p.x, y=p.y, t=0, dur=0.28,
                                         color="#ffab40", r=p.splash))
                self.burst(p.x, p.y, "#ff9100", 12, 120)
        elif p.target.targetable():
            self.damage(p.target, p.dmg, pierce=p.pierce)
            if p.kind == "sniper":
                self.burst(p.x, p.y, "#f3e5f5", 5, 90, life=0.2)

    # ------------------------------------------------------------ fx helpers
    def burst(self, x, y, color, n, speed, life=0.4):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(0.3, 1.0) * speed
            self.particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp, life, life,
                                   color, "#222222", 3, 0, False])

    def add_text(self, x, y, text, color):
        self.effects.append(dict(kind="text", x=x, y=y, t=0, dur=0.8, color=color, text=text))

    def spawn_child(self, kind, parent, jitter=6):
        e = Enemy(kind, self, self.hp_mult, self.reward_mult * 0.6, self.armor_bonus)
        e.route, e.total = parent.route, parent.total
        e.i, e.dist = parent.i, parent.dist - random.uniform(0, jitter)
        e.x = parent.x + random.uniform(-jitter, jitter)
        e.y = parent.y + random.uniform(-jitter, jitter)
        self.pending.append(e)

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.anim += dt
        if self.message:
            text, t, col = self.message
            self.message = (text, t - dt, col) if t - dt > 0 else None

        # spawning
        if self.spawn_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                kind = self.spawn_queue.pop(0)
                self.enemies.append(Enemy(kind, self, self.hp_mult, self.reward_mult,
                                          self.armor_bonus))
                nxt = self.spawn_queue[0] if self.spawn_queue else kind
                self.spawn_timer = ENEMY_TYPES[nxt]["gap"] * self.gap_mult

        # enemies + abilities
        for e in self.enemies:
            e.update(dt)
            if e.burn_t > 0 and random.random() < dt * 14:
                self.particles.append([e.x + random.uniform(-4, 4), e.y, 0, -40, 0.35, 0.35,
                                       "#ffd180", "#ff3d00", 3, 0, False])
            if e.kind == "healer":
                e.ab -= dt
                if e.ab <= 0:
                    e.ab = 1.6
                    for o in self.enemies:
                        if o is not e and not o.dead and \
                                (o.x - e.x) ** 2 + (o.y - e.y) ** 2 < 70 * 70:
                            o.hp = min(o.max_hp, o.hp + o.max_hp * 0.08)
                    self.effects.append(dict(kind="ring", x=e.x, y=e.y, t=0, dur=0.5,
                                             color=GOOD, r=70))
            elif e.kind == "boss":
                e.ab -= dt
                if e.ab <= 0:
                    e.ab = 5.0
                    for _ in range(2):
                        self.spawn_child("grunt", e, 10)
                    self.effects.append(dict(kind="ring", x=e.x, y=e.y, t=0, dur=0.5,
                                             color=BAD, r=40))
            if e.reached and not e.dead:
                e.dead = True
                self.lives -= e.lives
                ex, ey = self.pts[-2]
                self.effects.append(dict(kind="ring", x=ex, y=ey, t=0, dur=0.5,
                                         color=BAD, r=34))
        if self.lives <= 0 and not self.game_over:
            self.lives = 0
            self.game_over = True
            self.build_type = None
            self.best_wave = max(self.best_wave, self.wave)

        # towers
        for t in self.towers.values():
            att = t.spec["attack"]
            if att == "none":
                continue
            t.cd -= dt
            if att == "beam":
                tgt = t.beam_target
                if not (tgt and tgt.targetable() and self.in_range(t, tgt)
                        and (not tgt.air or t.spec.get("air"))):
                    new = self.find_target(t)
                    if new is not tgt:
                        t.beam_time = 0.0
                    tgt = t.beam_target = new
                if tgt:
                    self.aim(t, tgt, dt)
                    t.beam_time += dt
                    self.damage(tgt, t.dmg * (1 + min(2.0, t.beam_time)) * dt, dot=True)
                continue
            tgt = self.find_target(t)
            if not tgt:
                continue
            self.aim(t, tgt, dt)
            if t.cd > 0:
                continue
            t.cd = t.rate
            if att in ("bullet", "shell", "missile"):
                self.projectiles.append(Projectile(t, tgt))
            elif att == "chain":
                self.fire_chain(t, tgt)
            elif att == "cone":
                self.fire_cone(t)

        # projectiles
        for p in self.projectiles:
            if p.target.targetable():
                p.tx, p.ty = p.target.x, p.target.y
            dx, dy = p.tx - p.x, p.ty - p.y
            d = math.hypot(dx, dy)
            step = p.speed * dt
            if d > 0:
                p.ang = math.atan2(dy, dx)
            if d <= step:
                p.x, p.y = p.tx, p.ty
                self.hit(p)
                p.done = True
            else:
                p.x += dx / d * step
                p.y += dy / d * step
                if p.kind == "missile" and random.random() < 0.7:
                    self.particles.append([p.x - math.cos(p.ang) * 6, p.y - math.sin(p.ang) * 6,
                                           random.uniform(-10, 10), random.uniform(-10, 10),
                                           0.45, 0.45, "#eceff1", "#455a64", 3, 0, True])
        self.projectiles = [p for p in self.projectiles if not p.done]

        # deaths
        for e in self.enemies:
            if not e.dead and e.hp <= 0:
                e.dead = True
                self.gold += e.reward
                self.kills += 1
                self.add_text(e.x, e.y - 10, f"+{e.reward}", ACCENT)
                self.burst(e.x, e.y, e.color, 10 if e.kind != "boss" else 30,
                           110 if e.kind != "boss" else 180)
                if e.kind == "splitter":
                    for _ in range(2):
                        self.spawn_child("mini", e)
        self.enemies = [e for e in self.enemies if not e.dead] + self.pending
        self.pending = []

        # particles & effects
        for pt in self.particles:
            pt[0] += pt[2] * dt
            pt[1] += pt[3] * dt
            pt[2] *= 0.96
            pt[3] *= 0.96
            pt[4] -= dt
        self.particles = [pt for pt in self.particles if pt[4] > 0][-450:]
        for fx in self.effects:
            fx["t"] += dt
        self.effects = [fx for fx in self.effects if fx["t"] < fx["dur"]]

        # wave end
        if self.wave_active and not self.spawn_queue and not self.enemies and not self.game_over:
            self.wave_active = False
            bonus = 20 + self.wave * 3
            mine_gold = 0
            for t in self.towers.values():
                if t.kind == "mine":
                    mine_gold += t.income
                    self.add_text(t.x, t.y - 12, f"+{t.income}", ACCENT)
                    self.burst(t.x, t.y, ACCENT, 8, 70)
            self.gold += bonus + mine_gold
            extra = f"  เหมือง +{mine_gold}" if mine_gold else ""
            self.flash_msg(f"ผ่าน Wave {self.wave}!  โบนัส +{bonus}{extra}", 2.0, GOOD)
            self.auto_timer = 2.0
            self.best_wave = max(self.best_wave, self.wave)
        if self.auto_wave and not self.spawn_queue and not self.wave_active:
            self.auto_timer -= dt
            if self.auto_timer <= 0:
                self.start_wave()

    # ------------------------------------------------------------ render
    def render(self):
        c = self.canvas
        c.delete("dyn")
        T = "dyn"

        # portal swirl
        sx, sy = self.path[0]
        x0, y0 = sx * CELL, sy * CELL
        deg = (self.anim * 220) % 360
        for i in range(2):
            c.create_arc(x0 + 7, y0 + 7, x0 + 33, y0 + 33, start=deg + i * 180, extent=110,
                         style="arc", outline="#ea80fc", width=3, tags=T)

        # range previews
        hover_cell = None
        if self.mouse:
            hover_cell = (self.mouse[0] // CELL, self.mouse[1] // CELL)
        if hover_cell and self.build_type and not self.game_over and hover_cell in self.terrain:
            ok = self.can_build(hover_cell) and self.gold >= TOWER_TYPES[self.build_type]["cost"]
            col = GOOD if ok else BAD
            cx, cy = hover_cell[0] * CELL + CELL / 2, hover_cell[1] * CELL + CELL / 2
            r = TOWER_TYPES[self.build_type]["range"]
            if r:
                c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col, width=2,
                              dash=(6, 4), tags=T)
            rrect(c, cx - 19, cy - 19, cx + 19, cy + 19, 8, outline=col, width=2, fill="",
                  tags=T)
            if ok:
                draw_tower(c, self.build_type, cx, cy, -math.pi / 2, 0, 0.9, tags=T)
        show_range = self.selected
        if not show_range and not self.build_type and hover_cell in self.towers:
            show_range = self.towers[hover_cell]
        if show_range and show_range.range:
            s = show_range
            r = s.range
            c.create_oval(s.x - r, s.y - r, s.x + r, s.y + r, outline="#ffffff", width=2,
                          dash=(6, 4), tags=T)

        # towers
        for t in self.towers.values():
            draw_tower(c, t.kind, t.x, t.y, t.angle, t.level, 1.0, tags=T,
                       sel=t is self.selected)

        # ground enemies
        for e in self.enemies:
            if not e.air:
                self.draw_enemy_full(c, e, T)

        # laser beams
        for t in self.towers.values():
            tg = t.beam_target
            if t.kind == "laser" and tg and not tg.dead and not tg.phased:
                k = min(2.0, t.beam_time) / 2
                mx, my = t.x + math.cos(t.angle) * 16, t.y + math.sin(t.angle) * 16
                col = t.spec["color"]
                c.create_line(mx, my, tg.x, tg.y, fill=col, width=4 + 5 * k, tags=T)
                c.create_line(mx, my, tg.x, tg.y, fill="#ffffff", width=1 + 2 * k, tags=T)
                rr = 4 + 4 * k
                c.create_oval(tg.x - rr, tg.y - rr, tg.x + rr, tg.y + rr, fill="#ffffff",
                              outline=col, width=2, tags=T)

        # projectiles
        for p in self.projectiles:
            if p.kind == "cannon":
                c.create_oval(p.x - 5, p.y - 5, p.x + 5, p.y + 5, fill="#212121",
                              outline="#ff6d00", width=2, tags=T)
            elif p.kind == "sniper":
                c.create_line(p.x, p.y, p.x - math.cos(p.ang) * 22, p.y - math.sin(p.ang) * 22,
                              fill="#f3e5f5", width=2, tags=T)
            elif p.kind == "frost":
                c.create_oval(p.x - 5, p.y - 5, p.x + 5, p.y + 5, fill="#e1f5fe",
                              outline="#4fc3f7", width=2, tags=T)
            elif p.kind == "missile":
                c.create_polygon(*rot_pts(p.x, p.y, p.ang, 1, [(7, 0), (3, -3), (-6, -3),
                                                               (-6, 3), (3, 3)]),
                                 fill="#eceff1", outline="#455a64", tags=T)
                tx, ty = p.x + math.cos(p.ang) * 6, p.y + math.sin(p.ang) * 6
                c.create_oval(tx - 2, ty - 2, tx + 2, ty + 2, fill=BAD, outline="", tags=T)
            else:
                c.create_oval(p.x - 3, p.y - 3, p.x + 3, p.y + 3, fill="#fff59d",
                              outline="", tags=T)

        # air enemies on top
        for e in self.enemies:
            if e.air:
                self.draw_enemy_full(c, e, T)

        # particles
        for x, y, _vx, _vy, life, mlife, c1, c2, size, _g, grow in self.particles:
            k = life / mlife
            r = size * (0.6 + (1 - k) * 1.2) if grow else size * (0.3 + 0.7 * k)
            c.create_oval(x - r, y - r, x + r, y + r, fill=lerp_color(c2, c1, k),
                          outline="", tags=T)

        # effects
        for fx in self.effects:
            k = fx["t"] / fx["dur"]
            kind = fx["kind"]
            if kind == "text":
                c.create_text(fx["x"] + 1, fx["y"] - 24 * k + 1, text=fx["text"],
                              fill="#000000", font=(FONT, -12, "bold"), tags=T)
                c.create_text(fx["x"], fx["y"] - 24 * k, text=fx["text"], fill=fx["color"],
                              font=(FONT, -12, "bold"), tags=T)
            elif kind == "bolt":
                c.create_line(*fx["pts"], fill="#fff176", width=4, tags=T)
                c.create_line(*fx["pts"], fill="#ffffff", width=1.5, tags=T)
            elif kind == "boom":
                r = fx["r"] * (0.3 + 0.7 * k)
                c.create_oval(fx["x"] - r, fx["y"] - r, fx["x"] + r, fx["y"] + r,
                              outline=fx["color"], width=max(1, int(5 * (1 - k))), tags=T)
                if k < 0.35:
                    rc = fx["r"] * 0.45 * (1 - k / 0.35)
                    c.create_oval(fx["x"] - rc, fx["y"] - rc, fx["x"] + rc, fx["y"] + rc,
                                  fill="#fff8e1", outline=fx["color"], tags=T)
            else:  # ring
                r = fx["r"] * (0.4 + 0.6 * k)
                c.create_oval(fx["x"] - r, fx["y"] - r, fx["x"] + r, fx["y"] + r,
                              outline=fx["color"], width=max(1, int(3 * (1 - k))), tags=T)

        # toast message
        if self.message:
            text, _, col = self.message
            w = self.f_toast.measure(text) + 44
            rrect(c, W / 2 - w / 2, 12, W / 2 + w / 2, 46, 17, fill="#141927", outline=col,
                  width=2, tags=T)
            c.create_text(W / 2, 29, text=text, fill=col, font=self.f_toast, tags=T)

        if self.wave == 0 and not self.spawn_queue and not self.game_over:
            text = "เลือกป้อม (1-9) แล้ววางบนหญ้า  •  กด Space เพื่อเริ่ม"
            w = tkfont.Font(family=FONT, size=-13).measure(text) + 36
            rrect(c, W / 2 - w / 2, H - 44, W / 2 + w / 2, H - 14, 15, fill="#141927",
                  outline=LINE, tags=T)
            c.create_text(W / 2, H - 29, text=text, fill=MUTED, font=(FONT, -13), tags=T)

        if self.paused and not self.game_over:
            rrect(c, W / 2 - 170, H / 2 - 55, W / 2 + 170, H / 2 + 55, 20, fill=CARD,
                  outline=LINE, width=2, tags=T)
            c.create_text(W / 2, H / 2 - 14, text="หยุดชั่วคราว", fill=TEXT,
                          font=(FONT, -29, "bold"), tags=T)
            c.create_text(W / 2, H / 2 + 22, text="กด P เพื่อเล่นต่อ", fill=MUTED,
                          font=(FONT, -15), tags=T)
        if self.game_over:
            rrect(c, W / 2 - 220, H / 2 - 110, W / 2 + 220, H / 2 + 110, 24, fill=CARD,
                  outline=BAD, width=2, tags=T)
            c.create_text(W / 2, H / 2 - 62, text="GAME OVER", fill=BAD,
                          font=(FONT, -45, "bold"), tags=T)
            c.create_text(W / 2, H / 2 - 10,
                          text=f"รอดได้ถึง Wave {self.wave}   •   สังหาร {self.kills} ตัว",
                          fill=TEXT, font=(FONT, -19), tags=T)
            c.create_text(W / 2, H / 2 + 22, text=f"สถิติสูงสุด: Wave {self.best_wave}",
                          fill=ACCENT, font=(FONT, -15, "bold"), tags=T)
            c.create_text(W / 2, H / 2 + 94, text=f"พัฒนาโดย {DEV_NAME}", fill=DIM,
                          font=(FONT, -12), tags=T)
            c.create_text(W / 2, H / 2 + 66, text="R = เล่นแผนที่เดิม      N = แผนที่ใหม่",
                          fill=MUTED, font=(FONT, -15), tags=T)

    def draw_enemy_full(self, c, e, T):
        col = e.color
        if e.slow_t > 0:
            col = lerp_color(col, "#81d4fa", 0.55)
        y = e.y + (math.sin(e.anim * 4) * 3 if e.air else 0)
        draw_enemy(c, e.kind, e.x, y, e.r, e.angle, e.anim, tags=T, fill=col,
                   flash=e.flash > 0, phased=e.phased, shield_on=e.shield > 0)
        if e.phased:
            return
        if e.hp < e.max_hp or (e.max_shield and e.shield < e.max_shield):
            w = max(20, e.r * 2 + 6)
            bx, by = e.x - w / 2, y - e.r - 10
            frac = max(0.0, e.hp / e.max_hp)
            c.create_rectangle(bx - 1, by - 1, bx + w + 1, by + 4, fill="#111111", outline="",
                               tags=T)
            c.create_rectangle(bx, by, bx + w * frac, by + 3,
                               fill=lerp_color(BAD, GOOD, frac), outline="", tags=T)
            if e.max_shield:
                sf = e.shield / e.max_shield
                c.create_rectangle(bx, by - 4, bx + w * sf, by - 2, fill="#80d8ff",
                                   outline="", tags=T)

    # ------------------------------------------------------------ main loop
    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        if not self.paused and not self.game_over:
            for _ in range(self.speed_mult):
                self.update(dt)
        self.render()
        self.refresh_ui()
        self.root.after(16, self.loop)


def pick_font(root):
    fams = set(tkfont.families(root))
    for f in ("Leelawadee UI", "Leelawadee", "Segoe UI", "Tahoma"):
        if f in fams:
            return f
    return "TkDefaultFont"


def main():
    global FONT
    root = tk.Tk()
    FONT = pick_font(root)
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
