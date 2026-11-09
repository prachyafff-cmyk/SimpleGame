"""
Tower Defense + Procedural Map
พัฒนาโดย Mr.Prachya
-------------------------------
Single file, uses only the Python standard library (tkinter).
Run:  python tower_defense.py

Controls
  Left-click empty grass  : build the selected tower
  Left-click a tower      : select it (upgrade / sell)
  Right-click / Esc       : cancel
  1-4                     : pick a tower type
  Space                   : start the next wave
  U / S                   : upgrade / sell the selected tower
  F                       : change game speed (1x / 2x / 3x)
  P                       : pause
  R                       : restart on the same map
  N                       : new random map
"""

import math
import random
import time
import tkinter as tk

# ---------------------------------------------------------------- settings
COLS, ROWS, CELL = 20, 14, 40
W, H = COLS * CELL, ROWS * CELL
PANEL_W = 250
FONT = "Tahoma"
MAX_LEVEL = 4
START_GOLD = 160
START_LIVES = 20

PANEL_BG = "#1e2230"
PANEL_FG = "#e8e8f0"
ACCENT = "#ffd54f"

TOWER_TYPES = {
    "gun": dict(name="ปืนกล", key="1", cost=50, range=105, rate=0.32, dmg=7,
                speed=480, splash=0, slow=0, color="#4fc3f7",
                desc="ยิงเร็ว ราคาถูก"),
    "cannon": dict(name="ปืนใหญ่", key="2", cost=90, range=100, rate=1.25, dmg=28,
                   speed=260, splash=55, slow=0, color="#ff8a65",
                   desc="ระเบิดวงกว้าง"),
    "frost": dict(name="น้ำแข็ง", key="3", cost=70, range=95, rate=0.9, dmg=3,
                  speed=340, splash=40, slow=0.5, color="#b3e5fc",
                  desc="ทำให้ศัตรูช้าลง"),
    "sniper": dict(name="สไนเปอร์", key="4", cost=125, range=230, rate=1.7, dmg=65,
                   speed=1400, splash=0, slow=0, color="#ce93d8",
                   desc="ระยะไกล ดาเมจสูง"),
}

ENEMY_TYPES = {
    "normal": dict(hp=30, speed=55, reward=5, color="#e53935", r=9, gap=0.65, lives=1),
    "fast": dict(hp=17, speed=105, reward=4, color="#fdd835", r=7, gap=0.38, lives=1),
    "tank": dict(hp=120, speed=34, reward=12, color="#8e24aa", r=12, gap=1.0, lives=2),
    "boss": dict(hp=650, speed=28, reward=90, color="#263238", r=16, gap=2.0, lives=5),
}


# ---------------------------------------------------------------- helpers
def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


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
                # must not touch the path anywhere except the current cell
                ok = True
                for dd in dirs:
                    m = (nx + dd[0], ny + dd[1])
                    if m != (x, y) and m in vis:
                        ok = False
                        break
                if not ok:
                    continue
                w = base_w[d] * (2.0 if d == last_dir else 1.0)
                cands.append(d)
                weights.append(w)
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


# ---------------------------------------------------------------- entities
class Enemy:
    def __init__(self, kind, pts, hp_mult, reward_mult):
        spec = ENEMY_TYPES[kind]
        self.kind = kind
        self.pts = pts
        self.x, self.y = pts[0]
        self.i = 0
        self.max_hp = spec["hp"] * hp_mult
        self.hp = self.max_hp
        self.speed = spec["speed"]
        self.reward = max(1, int(round(spec["reward"] * reward_mult)))
        self.color = spec["color"]
        self.r = spec["r"]
        self.lives = spec["lives"]
        self.slow_t = 0.0
        self.slow_f = 1.0
        self.flash = 0.0
        self.dist = 0.0
        self.dead = False
        self.reached = False

    def apply_slow(self, factor, dur):
        if self.kind == "boss":
            factor = (1 + factor) / 2
        cur = self.slow_f if self.slow_t > 0 else 1.0
        self.slow_f = min(cur, factor)
        self.slow_t = max(self.slow_t, dur)

    def update(self, dt):
        if self.slow_t > 0:
            self.slow_t -= dt
            spd = self.speed * self.slow_f
        else:
            spd = self.speed
        self.flash = max(0.0, self.flash - dt)
        move = spd * dt
        self.dist += move
        while move > 0 and self.i < len(self.pts) - 1:
            tx, ty = self.pts[self.i + 1]
            dx, dy = tx - self.x, ty - self.y
            d = math.hypot(dx, dy)
            if d <= move:
                self.x, self.y = tx, ty
                self.i += 1
                move -= d
            else:
                self.x += dx / d * move
                self.y += dy / d * move
                move = 0
        if self.i >= len(self.pts) - 1:
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

    @property
    def spec(self):
        return TOWER_TYPES[self.kind]

    @property
    def dmg(self):
        return self.spec["dmg"] * (1.55 ** (self.level - 1))

    @property
    def range(self):
        return self.spec["range"] * (1 + 0.12 * (self.level - 1))

    @property
    def rate(self):
        return self.spec["rate"] * (0.88 ** (self.level - 1))

    @property
    def slow(self):
        if not self.spec["slow"]:
            return 0
        return max(0.25, self.spec["slow"] - 0.06 * (self.level - 1))

    @property
    def slow_dur(self):
        return 1.2 + 0.4 * (self.level - 1)

    @property
    def upgrade_cost(self):
        if self.level >= MAX_LEVEL:
            return None
        return int(self.spec["cost"] * 0.9 * self.level)

    @property
    def sell_value(self):
        return int(self.spent * 0.7)


class Projectile:
    def __init__(self, tower, target):
        self.x, self.y = tower.x, tower.y
        self.target = target
        self.tx, self.ty = target.x, target.y
        self.speed = tower.spec["speed"]
        self.dmg = tower.dmg
        self.splash = tower.spec["splash"]
        self.slow = tower.slow
        self.slow_dur = tower.slow_dur
        self.color = tower.spec["color"]
        self.kind = tower.kind
        self.done = False


# ---------------------------------------------------------------- game
class Game:
    def __init__(self, root):
        self.root = root
        root.title("Tower Defense + Procedural Map")
        root.resizable(False, False)
        root.configure(bg=PANEL_BG)

        self.canvas = tk.Canvas(root, width=W, height=H, bg="#000",
                                highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=0)
        self.panel = tk.Frame(root, bg=PANEL_BG, width=PANEL_W, height=H)
        self.panel.grid(row=0, column=1, sticky="ns")
        self.panel.pack_propagate(False)
        self.build_panel()

        self.mouse = None
        self.speed_mult = 1
        self.paused = False
        self.auto_wave = tk.BooleanVar(value=False)

        c = self.canvas
        c.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))
        c.bind("<Leave>", lambda e: setattr(self, "mouse", None))
        c.bind("<Button-1>", self.on_click)
        c.bind("<Button-3>", lambda e: self.cancel())
        root.bind("<Escape>", lambda e: self.cancel())
        root.bind("<space>", lambda e: self.start_wave())
        root.bind("<Key>", self.on_key)

        self.auto_chk.configure(variable=self.auto_wave)
        self.new_game()
        self.last = time.perf_counter()
        self.loop()

    # ------------------------------------------------------------ panel UI
    def build_panel(self):
        p = self.panel
        tk.Label(p, text="TOWER DEFENSE", font=(FONT, 15, "bold"),
                 bg=PANEL_BG, fg=ACCENT).pack(pady=(10, 0))
        tk.Label(p, text="Procedural Map", font=(FONT, 9),
                 bg=PANEL_BG, fg="#9aa").pack()

        self.var_stats = tk.StringVar()
        tk.Label(p, textvariable=self.var_stats, font=(FONT, 11), justify="left",
                 anchor="w", bg=PANEL_BG, fg=PANEL_FG).pack(fill="x", padx=12, pady=8)

        tk.Label(p, text="เลือกป้อม", font=(FONT, 10, "bold"),
                 bg=PANEL_BG, fg=ACCENT, anchor="w").pack(fill="x", padx=12)
        self.tower_btns = {}
        for k, t in TOWER_TYPES.items():
            b = tk.Button(p, text=f"[{t['key']}] {t['name']}   ${t['cost']}",
                          font=(FONT, 10), anchor="w", relief="flat",
                          bg="#2c3246", fg=PANEL_FG, activebackground="#3a4260",
                          activeforeground="white", bd=0, padx=8, pady=3,
                          command=lambda k=k: self.choose(k))
            b.pack(fill="x", padx=12, pady=2)
            self.tower_btns[k] = b
        self.var_desc = tk.StringVar()
        tk.Label(p, textvariable=self.var_desc, font=(FONT, 9), bg=PANEL_BG,
                 fg="#aab", wraplength=PANEL_W - 24, justify="left",
                 anchor="w").pack(fill="x", padx=12, pady=(2, 6))

        self.btn_wave = tk.Button(p, text="เริ่ม Wave  [Space]", font=(FONT, 11, "bold"),
                                  bg="#43a047", fg="white", activebackground="#2e7d32",
                                  relief="flat", bd=0, pady=4, command=self.start_wave)
        self.btn_wave.pack(fill="x", padx=12, pady=(4, 2))

        row = tk.Frame(p, bg=PANEL_BG)
        row.pack(fill="x", padx=12, pady=2)
        self.auto_chk = tk.Checkbutton(row, text="Auto wave", font=(FONT, 9),
                                       bg=PANEL_BG, fg=PANEL_FG, selectcolor="#2c3246",
                                       activebackground=PANEL_BG, activeforeground=PANEL_FG)
        self.auto_chk.pack(side="left")
        self.btn_speed = tk.Button(row, text="Speed 1x [F]", font=(FONT, 9),
                                   bg="#2c3246", fg=PANEL_FG, relief="flat", bd=0, padx=6,
                                   command=self.toggle_speed)
        self.btn_speed.pack(side="right")

        tk.Frame(p, bg="#3a4260", height=1).pack(fill="x", padx=12, pady=6)

        self.var_info = tk.StringVar()
        tk.Label(p, textvariable=self.var_info, font=(FONT, 9), bg=PANEL_BG, fg=PANEL_FG,
                 justify="left", anchor="nw", height=5).pack(fill="x", padx=12)
        row2 = tk.Frame(p, bg=PANEL_BG)
        row2.pack(fill="x", padx=12, pady=2)
        self.btn_up = tk.Button(row2, text="อัปเกรด [U]", font=(FONT, 9), bg="#1e88e5",
                                fg="white", relief="flat", bd=0, command=self.upgrade)
        self.btn_up.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_sell = tk.Button(row2, text="ขาย [S]", font=(FONT, 9), bg="#e53935",
                                  fg="white", relief="flat", bd=0, command=self.sell)
        self.btn_sell.pack(side="left", expand=True, fill="x", padx=(2, 0))

        tk.Frame(p, bg="#3a4260", height=1).pack(fill="x", padx=12, pady=6)
        row3 = tk.Frame(p, bg=PANEL_BG)
        row3.pack(fill="x", padx=12)
        tk.Button(row3, text="เล่นใหม่ [R]", font=(FONT, 9), bg="#2c3246", fg=PANEL_FG,
                  relief="flat", bd=0, command=lambda: self.new_game(self.seed)
                  ).pack(side="left", expand=True, fill="x", padx=(0, 2))
        tk.Button(row3, text="แผนที่ใหม่ [N]", font=(FONT, 9), bg="#2c3246", fg=PANEL_FG,
                  relief="flat", bd=0, command=self.new_game
                  ).pack(side="left", expand=True, fill="x", padx=(2, 0))

        tk.Label(p, text="คลิกซ้าย: สร้าง/เลือกป้อม\nคลิกขวา/Esc: ยกเลิก   P: หยุด",
                 font=(FONT, 8), bg=PANEL_BG, fg="#889", justify="left"
                 ).pack(side="bottom", anchor="w", padx=12, pady=8)

    def refresh_panel(self):
        stats = (f"ทอง:     {self.gold}\n"
                 f"ชีวิต:    {self.lives}\n"
                 f"Wave:    {self.wave}\n"
                 f"สังหาร:  {self.kills}\n"
                 f"Seed:    {self.seed}")
        if self.var_stats.get() != stats:
            self.var_stats.set(stats)

        for k, b in self.tower_btns.items():
            afford = self.gold >= TOWER_TYPES[k]["cost"]
            bg = "#4a5580" if k == self.build_type else "#2c3246"
            fg = PANEL_FG if afford else "#666a7a"
            if b.cget("bg") != bg or b.cget("fg") != fg:
                b.configure(bg=bg, fg=fg)

        if self.build_type:
            t = TOWER_TYPES[self.build_type]
            desc = (f"{t['name']}: {t['desc']}\nดาเมจ {t['dmg']}  ระยะ {t['range']}  "
                    f"ยิงทุก {t['rate']:.2f}s")
        else:
            desc = "กด 1-4 หรือคลิกปุ่มเพื่อเลือกป้อม"
        if self.var_desc.get() != desc:
            self.var_desc.set(desc)

        busy = bool(self.spawn_queue)
        wtxt = "กำลังปล่อยศัตรู..." if busy else f"เริ่ม Wave {self.wave + 1}  [Space]"
        if self.btn_wave.cget("text") != wtxt:
            self.btn_wave.configure(text=wtxt, bg="#555" if busy else "#43a047")

        s = self.selected
        if s:
            uc = s.upgrade_cost
            info = (f"{s.spec['name']}  เลเวล {s.level}/{MAX_LEVEL}\n"
                    f"ดาเมจ {s.dmg:.0f}   ระยะ {s.range:.0f}\n"
                    f"ยิงทุก {s.rate:.2f}s"
                    + (f"   ช้าลง {int((1 - s.slow) * 100)}%" if s.slow else "") + "\n"
                    f"อัปเกรด: {'$' + str(uc) if uc else 'สูงสุดแล้ว'}\n"
                    f"ขายได้: ${s.sell_value}")
        else:
            info = "คลิกที่ป้อมเพื่อดูข้อมูล\nอัปเกรด หรือขาย"
        if self.var_info.get() != info:
            self.var_info.set(info)
        st_up = "normal" if s and s.upgrade_cost and self.gold >= s.upgrade_cost else "disabled"
        st_sell = "normal" if s else "disabled"
        if self.btn_up.cget("state") != st_up:
            self.btn_up.configure(state=st_up)
        if self.btn_sell.cget("state") != st_sell:
            self.btn_sell.configure(state=st_sell)

    # ------------------------------------------------------------ setup
    def new_game(self, seed=None):
        self.seed = seed if seed is not None else random.randint(1, 999999)
        rng = random.Random(self.seed)
        self.rng = random.Random(self.seed * 7 + 1)  # wave randomness
        self.path = gen_path(rng)
        self.path_set = set(self.path)
        self.gen_terrain(rng)

        cx = lambda c: c * CELL + CELL / 2
        pts = [(cx(x), cx(y)) for x, y in self.path]
        sx, sy = pts[0]
        ex, ey = pts[-1]
        self.pts = [(sx - CELL, sy)] + pts + [(ex + CELL, ey)]

        self.gold = START_GOLD
        self.lives = START_LIVES
        self.wave = 0
        self.kills = 0
        self.enemies = []
        self.towers = {}
        self.projectiles = []
        self.effects = []
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.wave_active = False
        self.auto_timer = 0.0
        self.selected = None
        self.build_type = None
        self.game_over = False
        self.paused = False
        self.message = ("แผนที่ใหม่! กด Space เพื่อเริ่ม", 3.0)
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
                    r = rng.random()
                    chance = 0.04 if (x, y) in near_path else 0.10
                    if r < chance:
                        self.terrain[(x, y)] = rng.choice(["tree", "tree", "rock"])
                    else:
                        self.terrain[(x, y)] = "grass"
        self.deco_rng = random.Random(rng.random())

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
                grass = lerp_color("#356b33", "#6aa84f", h * 1.3 - 0.1)
                if t == "water":
                    col = lerp_color("#3b82c4", "#1d4f87", (h - 0.66) * 4)
                    c.create_rectangle(x0, y0, x1, y1, fill=col, outline=col)
                    if dr.random() < 0.5:
                        wx, wy = x0 + dr.randint(6, 26), y0 + dr.randint(8, 30)
                        c.create_line(wx, wy, wx + 8, wy, fill="#7fb6e6", width=2)
                elif t == "path":
                    col = lerp_color("#c9a66b", "#b08b52", dr.random())
                    c.create_rectangle(x0, y0, x1, y1, fill=col, outline=col)
                    for _ in range(2):
                        px, py = x0 + dr.randint(4, 34), y0 + dr.randint(4, 34)
                        c.create_oval(px, py, px + 3, py + 3, fill="#9c7a46", outline="")
                else:
                    c.create_rectangle(x0, y0, x1, y1, fill=grass, outline=lerp_color(grass, "#000000", 0.08))
                    if t == "tree":
                        ox, oy = dr.randint(-4, 4), dr.randint(-4, 4)
                        cx, cy = x0 + 20 + ox, y0 + 20 + oy
                        c.create_oval(cx - 12, cy + 6, cx + 12, cy + 14, fill="#2a4a22", outline="")
                        c.create_rectangle(cx - 2, cy + 2, cx + 2, cy + 10, fill="#6d4c2f", outline="")
                        c.create_oval(cx - 12, cy - 14, cx + 12, cy + 6, fill="#2e7d32", outline="#1b5e20")
                        c.create_oval(cx - 6, cy - 10, cx + 2, cy - 4, fill="#43a047", outline="")
                    elif t == "rock":
                        cx, cy = x0 + 20, y0 + 22
                        c.create_polygon(cx - 13, cy + 6, cx - 9, cy - 8, cx + 2, cy - 12,
                                         cx + 12, cy - 4, cx + 13, cy + 7,
                                         fill="#8d8d8d", outline="#5f5f5f", width=2)
                        c.create_line(cx - 5, cy - 6, cx + 3, cy - 9, fill="#b5b5b5", width=2)
                    elif dr.random() < 0.25:
                        gx, gy = x0 + dr.randint(5, 32), y0 + dr.randint(5, 32)
                        c.create_line(gx, gy, gx - 2, gy - 5, fill=lerp_color(grass, "#ffffff", 0.2))
                        c.create_line(gx, gy, gx + 2, gy - 5, fill=lerp_color(grass, "#ffffff", 0.2))
        # path edge shading
        for (x, y) in self.path:
            x0, y0 = x * CELL, y * CELL
            for dx, dy, coords in ((0, -1, (x0, y0, x0 + CELL, y0)),
                                   (0, 1, (x0, y0 + CELL, x0 + CELL, y0 + CELL)),
                                   (-1, 0, (x0, y0, x0, y0 + CELL)),
                                   (1, 0, (x0 + CELL, y0, x0 + CELL, y0 + CELL))):
                if (x + dx, y + dy) not in self.path_set and 0 <= x + dx < COLS:
                    c.create_line(*coords, fill="#7a5c32", width=2)
        # start portal
        sx, sy = self.path[0]
        x0, y0 = sx * CELL, sy * CELL
        c.create_oval(x0 + 4, y0 + 4, x0 + 36, y0 + 36, fill="#4a148c", outline="#e040fb", width=3)
        c.create_oval(x0 + 12, y0 + 12, x0 + 28, y0 + 28, fill="#000", outline="#ea80fc")
        # castle at the end
        ex, ey = self.path[-1]
        x0, y0 = ex * CELL, ey * CELL
        c.create_rectangle(x0 + 6, y0 + 12, x0 + 34, y0 + 36, fill="#9e9e9e", outline="#424242", width=2)
        for i in range(4):
            bx = x0 + 6 + i * 8
            c.create_rectangle(bx, y0 + 6, bx + 5, y0 + 12, fill="#9e9e9e", outline="#424242")
        c.create_rectangle(x0 + 16, y0 + 24, x0 + 24, y0 + 36, fill="#5d4037", outline="")
        c.create_line(x0 + 20, y0 + 6, x0 + 20, y0 - 6, fill="#333", width=2)
        c.create_polygon(x0 + 20, y0 - 6, x0 + 31, y0 - 2, x0 + 20, y0 + 1, fill="#e53935")

    # ------------------------------------------------------------ input
    def on_key(self, e):
        k = e.keysym.lower()
        for name, t in TOWER_TYPES.items():
            if e.char == t["key"]:
                self.choose(name)
                return
        if k == "u":
            self.upgrade()
        elif k == "s":
            self.sell()
        elif k == "f":
            self.toggle_speed()
        elif k == "p":
            if not self.game_over:
                self.paused = not self.paused
        elif k == "r":
            self.new_game(self.seed)
        elif k == "n":
            self.new_game()

    def choose(self, kind):
        self.build_type = None if self.build_type == kind else kind
        self.selected = None

    def cancel(self):
        self.build_type = None
        self.selected = None

    def toggle_speed(self):
        self.speed_mult = self.speed_mult % 3 + 1
        self.btn_speed.configure(text=f"Speed {self.speed_mult}x [F]")

    def can_build(self, cell):
        return (cell in self.terrain and self.terrain[cell] == "grass"
                and cell not in self.towers)

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
            self.flash_msg("สร้างตรงนี้ไม่ได้")
            return False
        if self.gold < cost:
            self.flash_msg("ทองไม่พอ!")
            return False
        self.gold -= cost
        self.towers[cell] = Tower(kind, *cell)
        return True

    def upgrade(self):
        s = self.selected
        if not s or self.game_over:
            return
        uc = s.upgrade_cost
        if uc is None:
            self.flash_msg("เลเวลสูงสุดแล้ว")
        elif self.gold < uc:
            self.flash_msg("ทองไม่พอ!")
        else:
            self.gold -= uc
            s.spent += uc
            s.level += 1
            self.effects.append(dict(kind="ring", x=s.x, y=s.y, t=0, dur=0.4, color=ACCENT, r=26))

    def sell(self):
        s = self.selected
        if not s or self.game_over:
            return
        self.gold += s.sell_value
        self.add_text(s.x, s.y, f"+{s.sell_value}", ACCENT)
        del self.towers[(s.cx, s.cy)]
        self.selected = None

    def flash_msg(self, text):
        self.message = (text, 1.3)

    # ------------------------------------------------------------ waves
    def start_wave(self):
        if self.game_over or self.spawn_queue:
            return
        bonus = 0
        if self.enemies:  # calling early gives bonus gold
            bonus = 10 + self.wave
            self.gold += bonus
            self.flash_msg(f"เรียก wave ก่อนเวลา +{bonus} ทอง")
        self.wave += 1
        n = self.wave
        q = []
        count = 6 + int(n * 1.8)
        for _ in range(count):
            r = self.rng.random()
            if n >= 5 and r < min(0.28, 0.05 + n * 0.012):
                q.append("tank")
            elif n >= 3 and r < 0.45:
                q.append("fast")
            else:
                q.append("normal")
        if n % 5 == 0 and n % 10 != 0:
            q += ["tank"] * (2 + n // 5)
        if n % 10 == 0:
            q += ["boss"] * (n // 10)
        self.spawn_queue = q
        self.spawn_timer = 0.0
        self.wave_active = True
        self.hp_mult = 1 + 0.22 * (n - 1) + 0.022 * (n - 1) ** 2
        self.reward_mult = 1 + 0.04 * (n - 1)
        self.gap_mult = max(0.5, 1 - 0.02 * n)
        if not bonus:
            self.flash_msg(f"Wave {n}" + ("  -  BOSS!" if n % 10 == 0 else ""))

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.message:
            text, t = self.message
            self.message = (text, t - dt) if t - dt > 0 else None

        # spawning
        if self.spawn_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                kind = self.spawn_queue.pop(0)
                self.enemies.append(Enemy(kind, self.pts, self.hp_mult, self.reward_mult))
                nxt = self.spawn_queue[0] if self.spawn_queue else kind
                self.spawn_timer = ENEMY_TYPES[nxt]["gap"] * self.gap_mult

        # enemies
        for e in self.enemies:
            e.update(dt)
            if e.reached and not e.dead:
                e.dead = True
                self.lives -= e.lives
                self.effects.append(dict(kind="ring", x=W - 20, y=e.y, t=0, dur=0.5,
                                         color="#ff1744", r=30))
        if self.lives <= 0:
            self.lives = 0
            self.game_over = True
            self.build_type = None

        # towers
        for t in self.towers.values():
            t.cd -= dt
            target, best = None, -1
            rr = t.range * t.range
            for e in self.enemies:
                if e.dead:
                    continue
                if (e.x - t.x) ** 2 + (e.y - t.y) ** 2 <= rr and e.dist > best:
                    target, best = e, e.dist
            if target:
                want = math.atan2(target.y - t.y, target.x - t.x)
                diff = (want - t.angle + math.pi) % (2 * math.pi) - math.pi
                t.angle += diff * min(1.0, dt * 18)
                if t.cd <= 0:
                    self.projectiles.append(Projectile(t, target))
                    t.cd = t.rate

        # projectiles
        for p in self.projectiles:
            if not p.target.dead:
                p.tx, p.ty = p.target.x, p.target.y
            dx, dy = p.tx - p.x, p.ty - p.y
            d = math.hypot(dx, dy)
            step = p.speed * dt
            if d <= step:
                p.x, p.y = p.tx, p.ty
                self.hit(p)
                p.done = True
            else:
                p.x += dx / d * step
                p.y += dy / d * step
        self.projectiles = [p for p in self.projectiles if not p.done]

        # kills
        for e in self.enemies:
            if not e.dead and e.hp <= 0:
                e.dead = True
                self.gold += e.reward
                self.kills += 1
                self.add_text(e.x, e.y - 10, f"+{e.reward}", ACCENT)
                self.effects.append(dict(kind="pop", x=e.x, y=e.y, t=0, dur=0.3,
                                         color=e.color, r=e.r + 8))
        self.enemies = [e for e in self.enemies if not e.dead]

        # effects
        for fx in self.effects:
            fx["t"] += dt
        self.effects = [fx for fx in self.effects if fx["t"] < fx["dur"]]

        # wave end
        if self.wave_active and not self.spawn_queue and not self.enemies and not self.game_over:
            self.wave_active = False
            bonus = 20 + self.wave * 3
            self.gold += bonus
            self.flash_msg(f"ผ่าน Wave {self.wave}!  โบนัส +{bonus} ทอง")
            self.auto_timer = 2.0
        if self.auto_wave.get() and not self.spawn_queue and not self.wave_active:
            self.auto_timer -= dt
            if self.auto_timer <= 0:
                self.start_wave()

    def hit(self, p):
        if p.splash:
            r2 = p.splash * p.splash
            for e in self.enemies:
                if not e.dead and (e.x - p.x) ** 2 + (e.y - p.y) ** 2 <= r2:
                    self.damage(e, p.dmg)
                    if p.slow:
                        e.apply_slow(p.slow, p.slow_dur)
            col = "#e1f5fe" if p.slow else "#ffab40"
            self.effects.append(dict(kind="boom", x=p.x, y=p.y, t=0, dur=0.25,
                                     color=col, r=p.splash))
        elif not p.target.dead:
            self.damage(p.target, p.dmg)
            if p.kind == "sniper":
                self.effects.append(dict(kind="pop", x=p.x, y=p.y, t=0, dur=0.15,
                                         color="#f3e5f5", r=10))

    def damage(self, e, amount):
        e.hp -= amount
        e.flash = 0.06

    def add_text(self, x, y, text, color):
        self.effects.append(dict(kind="text", x=x, y=y, t=0, dur=0.8, color=color, text=text))

    # ------------------------------------------------------------ render
    def render(self):
        c = self.canvas
        c.delete("dyn")
        T = "dyn"

        # hover preview
        if self.mouse and self.build_type and not self.game_over:
            mx, my = self.mouse
            cell = (mx // CELL, my // CELL)
            if cell in self.terrain:
                ok = self.can_build(cell) and self.gold >= TOWER_TYPES[self.build_type]["cost"]
                x0, y0 = cell[0] * CELL, cell[1] * CELL
                col = "#69f0ae" if ok else "#ff5252"
                cx, cy = x0 + CELL / 2, y0 + CELL / 2
                r = TOWER_TYPES[self.build_type]["range"]
                c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col, dash=(4, 4), tags=T)
                c.create_rectangle(x0 + 1, y0 + 1, x0 + CELL - 1, y0 + CELL - 1,
                                   outline=col, width=2, tags=T)

        if self.selected:
            s = self.selected
            r = s.range
            c.create_oval(s.x - r, s.y - r, s.x + r, s.y + r, outline="#ffffff",
                          dash=(3, 3), width=1, tags=T)

        # towers
        for t in self.towers.values():
            col = t.spec["color"]
            x0, y0 = t.cx * CELL, t.cy * CELL
            sel = t is self.selected
            c.create_rectangle(x0 + 4, y0 + 4, x0 + CELL - 4, y0 + CELL - 4,
                               fill="#455a64", outline=ACCENT if sel else "#263238",
                               width=2, tags=T)
            c.create_oval(t.x - 11, t.y - 11, t.x + 11, t.y + 11, fill=col,
                          outline=lerp_color(col, "#000000", 0.4), width=2, tags=T)
            ca, sa = math.cos(t.angle), math.sin(t.angle)
            if t.kind == "gun":
                for off in (-3, 3):
                    ox, oy = -sa * off, ca * off
                    c.create_line(t.x + ox, t.y + oy, t.x + ox + ca * 17, t.y + oy + sa * 17,
                                  fill="#263238", width=3, tags=T)
            elif t.kind == "cannon":
                c.create_line(t.x, t.y, t.x + ca * 16, t.y + sa * 16,
                              fill="#3e2723", width=8, tags=T)
            elif t.kind == "sniper":
                c.create_line(t.x, t.y, t.x + ca * 22, t.y + sa * 22,
                              fill="#311b92", width=3, tags=T)
            elif t.kind == "frost":
                pts = []
                for i in range(6):
                    a = t.angle + i * math.pi / 3
                    pts += [t.x + math.cos(a) * 9, t.y + math.sin(a) * 9]
                c.create_polygon(pts, fill="#ffffff", outline="#4fc3f7", tags=T)
            c.create_oval(t.x - 4, t.y - 4, t.x + 4, t.y + 4, fill="#eceff1", outline="", tags=T)
            for i in range(t.level):
                px = x0 + 8 + i * 7
                c.create_rectangle(px, y0 + CELL - 9, px + 4, y0 + CELL - 5,
                                   fill=ACCENT, outline="", tags=T)

        # enemies
        for e in self.enemies:
            r = e.r
            col = e.color
            if e.slow_t > 0:
                col = lerp_color(col, "#81d4fa", 0.55)
            outline = "#ffffff" if e.flash > 0 else "#111111"
            c.create_oval(e.x - r, e.y - r + 3, e.x + r, e.y + r + 3, fill="#1b3018",
                          outline="", tags=T)
            c.create_oval(e.x - r, e.y - r, e.x + r, e.y + r, fill=col,
                          outline=outline, width=2, tags=T)
            if e.kind == "boss":
                c.create_polygon(e.x - 9, e.y - r + 2, e.x - 9, e.y - r - 8, e.x - 4, e.y - r - 3,
                                 e.x, e.y - r - 10, e.x + 4, e.y - r - 3, e.x + 9, e.y - r - 8,
                                 e.x + 9, e.y - r + 2, fill=ACCENT, outline="#bf8f00", tags=T)
            # eyes
            c.create_oval(e.x - 4, e.y - 3, e.x - 1, e.y, fill="white", outline="", tags=T)
            c.create_oval(e.x + 1, e.y - 3, e.x + 4, e.y, fill="white", outline="", tags=T)
            if e.hp < e.max_hp:
                w = r * 2 + 4
                frac = max(0.0, e.hp / e.max_hp)
                bx, by = e.x - w / 2, e.y - r - 8
                c.create_rectangle(bx, by, bx + w, by + 4, fill="#300", outline="", tags=T)
                c.create_rectangle(bx, by, bx + w * frac, by + 4,
                                   fill=lerp_color("#ff1744", "#76ff03", frac), outline="", tags=T)

        # projectiles
        for p in self.projectiles:
            if p.kind == "cannon":
                c.create_oval(p.x - 5, p.y - 5, p.x + 5, p.y + 5, fill="#212121",
                              outline="#ff6d00", tags=T)
            elif p.kind == "sniper":
                d = math.hypot(p.tx - p.x, p.ty - p.y) or 1
                c.create_line(p.x, p.y, p.x - (p.tx - p.x) / d * 18, p.y - (p.ty - p.y) / d * 18,
                              fill="#f3e5f5", width=2, tags=T)
            elif p.kind == "frost":
                c.create_oval(p.x - 4, p.y - 4, p.x + 4, p.y + 4, fill="#e1f5fe",
                              outline="#4fc3f7", tags=T)
            else:
                c.create_oval(p.x - 3, p.y - 3, p.x + 3, p.y + 3, fill="#fff59d",
                              outline="", tags=T)

        # effects
        for fx in self.effects:
            k = fx["t"] / fx["dur"]
            if fx["kind"] == "text":
                c.create_text(fx["x"], fx["y"] - 22 * k, text=fx["text"], fill=fx["color"],
                              font=(FONT, 9, "bold"), tags=T)
            elif fx["kind"] == "boom":
                r = fx["r"] * (0.3 + 0.7 * k)
                c.create_oval(fx["x"] - r, fx["y"] - r, fx["x"] + r, fx["y"] + r,
                              outline=fx["color"], width=max(1, int(4 * (1 - k))), tags=T)
            else:  # ring / pop
                r = fx["r"] * (0.4 + 0.6 * k)
                c.create_oval(fx["x"] - r, fx["y"] - r, fx["x"] + r, fx["y"] + r,
                              outline=fx["color"], width=max(1, int(3 * (1 - k))), tags=T)

        # messages / overlays
        if self.message:
            text, _ = self.message
            c.create_rectangle(W / 2 - 190, 10, W / 2 + 190, 44, fill="#000000",
                               stipple="gray50", outline="", tags=T)
            c.create_text(W / 2, 27, text=text, fill="white", font=(FONT, 13, "bold"), tags=T)
        if self.paused:
            c.create_text(W / 2, H / 2, text="หยุดชั่วคราว  (กด P)", fill="white",
                          font=(FONT, 26, "bold"), tags=T)
        if self.game_over:
            c.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="", tags=T)
            c.create_text(W / 2, H / 2 - 40, text="GAME OVER", fill="#ff5252",
                          font=(FONT, 40, "bold"), tags=T)
            c.create_text(W / 2, H / 2 + 15,
                          text=f"รอดได้ถึง Wave {self.wave}   สังหาร {self.kills} ตัว",
                          fill="white", font=(FONT, 16), tags=T)
            c.create_text(W / 2, H / 2 + 50, text="R = เล่นแผนที่เดิม    N = แผนที่ใหม่",
                          fill=ACCENT, font=(FONT, 13), tags=T)

    # ------------------------------------------------------------ main loop
    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        if not self.paused and not self.game_over:
            for _ in range(self.speed_mult):
                self.update(dt)
        self.render()
        self.refresh_panel()
        self.root.after(16, self.loop)


def main():
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
