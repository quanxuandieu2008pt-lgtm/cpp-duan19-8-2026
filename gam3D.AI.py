"""
GAME BẮN SÚNG GÓC NHÌN THỨ NHẤT ĐẤU BOT (kiểu Truy Kích) - chỉ dùng thư viện chuẩn
Không cần cài thêm gì, chạy được trên Python 3.15:   python fps_tk.py

Điều khiển:
  W / S        : tiến / lùi
  A / D        : đi ngang trái / phải
  ← / → hoặc Q / E : xoay camera
  M            : bật/tắt xoay bằng chuột (đưa chuột sang trái/phải màn hình để xoay)
  Chuột trái / Space : bắn (giữ để bắn liên thanh)
  R            : nạp đạn
  Shift        : chạy nhanh
  N            : đổi chế độ ngày / đêm
  Enter        : chơi lại sau khi thua hoặc thắng

Mỗi bản đồ có 3 đợt bot; hoàn thành bản đồ đầu tiên sẽ mở bản đồ tiếp theo.
"""
import math
import random
import time
import tkinter as tk

# ===================== CẤU HÌNH =====================
SW, SH = 800, 500          # kích thước cửa sổ
NCOL = 160                 # số cột tia (tăng = đẹp hơn nhưng chậm hơn)
CW = SW // NCOL
FOV = 0.66
MAG_SIZE = 30
RELOAD_TIME = 1.5
FIRE_DELAY = 0.11
DAMAGE = 34
BOT_HP = 100
BOT_SPEED = 1.6
BOT_DAMAGE = 7
BOT_ACCURACY = 0.30
STREETLIGHTS = [
    (5.5, 1.5), (14.5, 1.5), (2.5, 4.5), (14.5, 4.5),
    (8.5, 8.5), (5.5, 10.5), (14.5, 10.5),
    (5.5, 15.5), (14.5, 15.5),
]

MAP = [
    "####################",
    "#..................#",
    "#..##....##....##..#",
    "#..#......#....#...#",
    "#..................#",
    "#......###..###....#",
    "#......#......#....#",
    "#..#...#..##..#..#.#",
    "#..#..........#..#.#",
    "#.......#..#.......#",
    "#.......#..#.......#",
    "#..#..........#..#.#",
    "#..#...#....#.#..#.#",
    "#......#....#......#",
    "#......###..###....#",
    "#..................#",
    "#..#......#....#...#",
    "#..##....##....##..#",
    "#..................#",
    "####################",
]
MH, MW = len(MAP), len(MAP[0])
MAPS = (MAP, ["".join(MAP[y][x] for y in range(MH)) for x in range(MW)])
MAP_NAMES = ("KHU PHỐ", "KHU PHỐ XOAY CHIỀU")
WAVES_PER_MAP = 3


def is_wall(x, y, map_data=MAP):
    xi, yi = int(x), int(y)
    if xi < 0 or yi < 0 or yi >= len(map_data) or xi >= len(map_data[yi]):
        return True
    return map_data[yi][xi] != '.'


def clear_line(x1, y1, x2, y2, map_data=MAP):
    """Kiểm tra không có tường chắn giữa 2 điểm."""
    d = math.hypot(x2 - x1, y2 - y1)
    n = max(1, int(d / 0.15))
    for i in range(1, n):
        t = i / n
        if is_wall(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, map_data):
            return False
    return True


def shade(rgb, k):
    k = max(0.12, min(1.0, k))
    return "#%02x%02x%02x" % (int(rgb[0] * k), int(rgb[1] * k), int(rgb[2] * k))


class Bot:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = BOT_HP
        self.strafe = random.choice([-1, 1])
        self.strafe_t = random.uniform(1, 3)
        self.next_shot = time.perf_counter() + random.uniform(0.8, 1.6)
        self.flash = 0.0


class Game:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Đấu Bot - FPS (tkinter, Python 3.15)")
        self.root.resizable(False, False)
        self.c = tk.Canvas(self.root, width=SW, height=SH, bg="black", highlightthickness=0)
        self.c.pack()

        self.keys = set()
        self.firing = False
        self.mouse_look = False
        self.night_mode = False
        self.mx = SW / 2
        self.root.bind("<KeyPress>", lambda e: self.keys.add(e.keysym.lower()))
        self.root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym.lower()))
        self.root.bind("<ButtonPress-1>", lambda e: setattr(self, "firing", True))
        self.root.bind("<ButtonRelease-1>", lambda e: setattr(self, "firing", False))
        self.root.bind("<Motion>", lambda e: setattr(self, "mx", e.x))
        self.root.bind("<KeyPress-m>", self.toggle_mouse)
        self.root.bind("<KeyPress-r>", lambda e: self.reload())
        self.root.bind("<KeyPress-n>", self.toggle_time)
        self.root.bind("<Return>", lambda e: self.reset() if not self.alive else None)

        # Trời + đất
        self.sky = self.c.create_rectangle(0, 0, SW, SH // 2, fill="#6f9fd6", outline="")
        self.ground = self.c.create_rectangle(0, SH // 2, SW, SH, fill="#4a4f45", outline="")
        # Pool cột tường
        self.cols = [self.c.create_rectangle(0, 0, 0, 0, outline="") for _ in range(NCOL)]
        self.zbuf = [1e9] * NCOL

        # Minimap
        self.ms = 5

        # HUD
        self.hit_overlay = self.c.create_rectangle(0, 0, SW, SH, fill="red",
                                                   stipple="gray50", outline="", state="hidden")
        self.hp_txt = self.c.create_text(20, SH - 20, anchor="sw", fill="#4f4",
                                         font=("Consolas", 22, "bold"))
        self.ammo_txt = self.c.create_text(SW - 20, SH - 20, anchor="se", fill="white",
                                           font=("Consolas", 22, "bold"))
        self.info_txt = self.c.create_text(SW - 15, 12, anchor="ne", fill="white",
                                           font=("Consolas", 13))
        self.msg_txt = self.c.create_text(SW // 2, SH // 3, fill="#ff4", justify="center",
                                          font=("Consolas", 28, "bold"))
        cx, cy = SW // 2, SH // 2
        self.xh = [self.c.create_line(cx - 12, cy, cx - 4, cy, fill="white", width=2),
                   self.c.create_line(cx + 4, cy, cx + 12, cy, fill="white", width=2),
                   self.c.create_line(cx, cy - 12, cx, cy - 4, fill="white", width=2),
                   self.c.create_line(cx, cy + 4, cx, cy + 12, fill="white", width=2)]
        # Súng AK và hai tay người chơi
        self.weapon_parts = [
            self.c.create_polygon(0, 0, 0, 0, fill="#65452a", outline="#241a11", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#252a25", outline="#101210", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#75502c", outline="#241a11", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#343832", outline="#111", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#1d211f", outline="#090a09", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#242825", outline="#101210", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#b8875c", outline="#392719", width=2),
            self.c.create_polygon(0, 0, 0, 0, fill="#b8875c", outline="#392719", width=2),
        ]
        self.muzzle = self.c.create_oval(0, 0, 0, 0, fill="#ffdd33", outline="", state="hidden")

        self.map_index = 0
        self.map_data = MAPS[self.map_index]
        self.reset()
        self.last = time.perf_counter()
        self.root.after(16, self.loop)

    # ---------------- Trạng thái ----------------
    def draw_minimap_map(self):
        self.c.delete("map_bg")
        for j, row in enumerate(self.map_data):
            for i, cell in enumerate(row):
                col = "#222" if cell == '.' else "#aaa"
                self.c.create_rectangle(8 + i * self.ms, 8 + j * self.ms,
                                        8 + (i + 1) * self.ms, 8 + (j + 1) * self.ms,
                                        fill=col, outline="", tags="map_bg")

    def reset(self):
        self.map_index = 0
        self.map_data = MAPS[self.map_index]
        self.draw_minimap_map()
        self.px, self.py = 1.5, 1.5
        self.ang = 0.8
        self.hp = 100
        self.alive = True
        self.ammo = MAG_SIZE
        self.reloading = False
        self.reload_end = 0
        self.last_shot = 0
        self.kills = 0
        self.wave = 0
        self.stage_wave = 0
        self.bots = []
        self.next_wave_at = None
        self.msg_until = 0
        self.hit_until = 0
        self.muzzle_until = 0
        self.bob = 0.0
        self.c.itemconfig(self.msg_txt, text="")
        self.start_wave()

    def toggle_mouse(self, _e=None):
        self.mouse_look = not self.mouse_look
        self.say("Xoay bằng chuột: " + ("BẬT" if self.mouse_look else "TẮT"), 1.0)

    def toggle_time(self, _e=None):
        self.night_mode = not self.night_mode
        self.say("CHẾ ĐỘ " + ("BAN ĐÊM" if self.night_mode else "BAN NGÀY"), 1.2)

    def light_level(self, x, y):
        if not self.night_mode:
            return 1.6
        level = 0.42
        for lx, ly in STREETLIGHTS:
            distance = math.hypot(x - lx, y - ly)
            if distance < 7 and clear_line(x, y, lx, ly, self.map_data):
                level += 1.45 / (1 + distance * 0.7)
        return min(level, 1.65)

    def say(self, text, secs=1.5, color="#ff4"):
        self.c.itemconfig(self.msg_txt, text=text, fill=color)
        self.msg_until = time.perf_counter() + secs

    def start_wave(self):
        self.wave += 1
        self.stage_wave += 1
        self.next_wave_at = None
        n = 3 + self.wave * 2
        cells = [(i + 0.5, j + 0.5) for j, row in enumerate(self.map_data)
                 for i, cell in enumerate(row)
                 if cell == '.' and math.hypot(i + 0.5 - self.px, j + 0.5 - self.py) > 8]
        for x, y in random.sample(cells, min(n, len(cells))):
            self.bots.append(Bot(x, y))
        self.say(f"ĐỢT {self.wave}!", 1.5, "#ff6")

    def advance_map(self):
        self.map_index += 1
        self.map_data = MAPS[self.map_index]
        self.stage_wave = 0
        self.px, self.py = 1.5, 1.5
        self.ang = 0.8
        self.hp = min(100, self.hp + 35)
        self.ammo = MAG_SIZE
        self.reloading = False
        self.bots.clear()
        self.draw_minimap_map()
        self.start_wave()
        self.say(f"MÀN {self.map_index + 1}: {MAP_NAMES[self.map_index]}", 2.5, "#ff6")

    def reload(self):
        if self.alive and not self.reloading and self.ammo < MAG_SIZE:
            self.reloading = True
            self.reload_end = time.perf_counter() + RELOAD_TIME

    # ---------------- Logic ----------------
    def try_move(self, x, y, dx, dy, r=0.22):
        nx, ny = x, y
        if not is_wall(x + dx + math.copysign(r, dx) if dx else x, y, self.map_data):
            nx = x + dx
        if not is_wall(nx, y + dy + math.copysign(r, dy) if dy else y, self.map_data):
            ny = y + dy
        return nx, ny

    def to_screen(self, bx, by):
        dirx, diry = math.cos(self.ang), math.sin(self.ang)
        planex, planey = -diry * FOV, dirx * FOV
        sx, sy = bx - self.px, by - self.py
        inv = 1.0 / (planex * diry - dirx * planey)
        tx = inv * (diry * sx - dirx * sy)
        ty = inv * (-planey * sx + planex * sy)
        return tx, ty

    def shoot(self, now):
        self.ammo -= 1
        self.last_shot = now
        self.muzzle_until = now + 0.05
        best, best_ty, crit = None, 1e9, False
        for b in self.bots:
            tx, ty = self.to_screen(b.x, b.y)
            if (ty <= 0.1 or not clear_line(self.px, self.py, b.x, b.y, self.map_data)
                    or ty > self.zbuf[NCOL // 2]):
                continue
            off = abs(tx / ty) * (SW / 2)
            if off < 0.18 * SH / ty and ty < best_ty:
                best, best_ty = b, ty
                crit = off < 0.09 * SH / ty
        if best:
            best.hp -= DAMAGE * (2 if crit else 1)
            best.flash = 0.12
            for l in self.xh:
                self.c.itemconfig(l, fill="red")
            self.root.after(100, lambda: [self.c.itemconfig(l, fill="white") for l in self.xh])
            if crit:
                self.say("HEADSHOT x2!", 0.5, "#f80")
            if best.hp <= 0:
                self.bots.remove(best)
                self.kills += 1

    def update(self, dt, now):
        if not self.alive:
            return
        k = self.keys
        # Xoay
        turn = 0.0
        if "left" in k or "q" in k:
            turn -= 2.4
        if "right" in k or "e" in k:
            turn += 2.4
        if self.mouse_look:
            off = (self.mx - SW / 2) / (SW / 2)
            if abs(off) > 0.12:
                turn += off * 3.5
        self.ang += turn * dt

        # Di chuyển
        sp = (4.2 if "shift_l" in k or "shift_r" in k else 2.6) * dt
        fx, fy = math.cos(self.ang), math.sin(self.ang)
        mx = my = 0.0
        if "w" in k:
            mx += fx; my += fy
        if "s" in k:
            mx -= fx; my -= fy
        if "a" in k:
            mx += fy; my -= fx
        if "d" in k:
            mx -= fy; my += fx
        if mx or my:
            l = math.hypot(mx, my)
            self.px, self.py = self.try_move(self.px, self.py, mx / l * sp, my / l * sp)
            self.bob += dt * 9
        # Nạp đạn
        if self.reloading and now >= self.reload_end:
            self.reloading = False
            self.ammo = MAG_SIZE
        # Bắn
        if (self.firing or "space" in k) and not self.reloading and now - self.last_shot > FIRE_DELAY:
            if self.ammo > 0:
                self.shoot(now)
            else:
                self.reload()

        # Bot
        for b in self.bots:
            b.flash = max(0, b.flash - dt)
            dx, dy = self.px - b.x, self.py - b.y
            dist = math.hypot(dx, dy)
            los = dist < 14 and clear_line(b.x, b.y, self.px, self.py, self.map_data)
            ux, uy = dx / dist, dy / dist
            vx = vy = 0.0
            if dist > 5 or not los:
                vx, vy = ux, uy
            elif dist < 3:            b.strafe_t -= dt
            if b.strafe_t <= 0:
                b.strafe *= -1
                b.strafe_t = random.uniform(1, 3)
            if los:
                vx += -uy * b.strafe * 0.7
                vy += ux * b.strafe * 0.7
            vl = math.hypot(vx, vy)
            if vl > 0.01:
                step = BOT_SPEED * dt / vl
                nx, ny = self.try_move(b.x, b.y, vx * step, vy * step, 0.25)
                if (nx, ny) == (b.x, b.y):
                    b.strafe *= -1
                b.x, b.y = nx, ny
            if los and now >= b.next_shot:
                b.next_shot = now + random.uniform(0.6, 1.3)
                if random.random() < BOT_ACCURACY:
                    self.hp -= BOT_DAMAGE
                    self.hit_until = now + 0.25
                    if self.hp <= 0:
                        self.hp = 0
                        self.alive = False
                        self.say("BẠN ĐÃ HY SINH!\nNhấn ENTER để chơi lại", 1e9, "#f44")
                        break

        # Đợt mới
        if self.alive and not self.bots:
            if self.next_wave_at is None:
                self.next_wave_at = now + 3
                if self.stage_wave < WAVES_PER_MAP or self.map_index < len(MAPS) - 1:
                    self.say("HẠ GỤC TOÀN BỘ! Màn/đợt tiếp theo sắp bắt đầu...", 3, "#4f4")
                else:
                    self.say("HẠ GỤC TOÀN BỘ! Sắp hoàn thành game...", 3, "#4f4")
            elif now >= self.next_wave_at:
                if self.stage_wave < WAVES_PER_MAP:
                    self.start_wave()
                elif self.map_index < len(MAPS) - 1:
                    self.advance_map()
                else:
                    self.alive = False
                    self.say("CHIẾN THẮNG!\nNhấn ENTER để chơi lại", 1e9, "#4f4")

    # ---------------- Vẽ ----------------
    def render(self, now):
        dirx, diry = math.cos(self.ang), math.sin(self.ang)
        planex, planey = -diry * FOV, dirx * FOV
        horizon = SH / 2 + (math.sin(self.bob) * 3 if self.alive else 0)
        self.c.itemconfig(self.sky, fill="#101a35" if self.night_mode else "#6f9fd6")
        self.c.itemconfig(self.ground, fill="#20251f" if self.night_mode else "#4a4f45")

        for i in range(NCOL):
            camx = 2 * i / NCOL - 1
            rdx, rdy = dirx + planex * camx, diry + planey * camx
            mapx, mapy = int(self.px), int(self.py)
            ddx = abs(1 / rdx) if rdx else 1e30
            ddy = abs(1 / rdy) if rdy else 1e30
            if rdx < 0:
                stepx, sdx = -1, (self.px - mapx) * ddx
            else:
                stepx, sdx = 1, (mapx + 1 - self.px) * ddx
            if rdy < 0:
                stepy, sdy = -1, (self.py - mapy) * ddy
            else:
                stepy, sdy = 1, (mapy + 1 - self.py) * ddy
            side = 0
            for _ in range(64):
                if sdx < sdy:
                    sdx += ddx; mapx += stepx; side = 0
                else:
                    sdy += ddy; mapy += stepy; side = 1
                if is_wall(mapx, mapy, self.map_data):
                    break
            perp = (sdx - ddx) if side == 0 else (sdy - ddy)
            perp = max(perp, 0.05)
            self.zbuf[i] = perp
            h = SH / perp
            top = horizon - h / 2
            base = (190, 150, 105) if side == 0 else (150, 115, 80)
            if (mapx in (0, len(self.map_data[0]) - 1)
                    or mapy in (0, len(self.map_data) - 1)):
                base = (130, 135, 150) if side == 0 else (100, 105, 120)
            self.c.coords(self.cols[i], i * CW, top, (i + 1) * CW, top + h)
            light = self.light_level(mapx + 0.5, mapy + 0.5)
            self.c.itemconfig(self.cols[i], fill=shade(base, light / (1 + perp * 0.45)))

        # Đèn đường và bot (vẽ xa trước, gần sau)
        self.c.delete("spr")
        items = []
        for b in self.bots:
            tx, ty = self.to_screen(b.x, b.y)
            if ty > 0.15:
                items.append((ty, tx, "bot", b))
        for lx, ly in STREETLIGHTS:
            tx, ty = self.to_screen(lx, ly)
            if ty > 0.15:
                items.append((ty, tx, "lamp", (lx, ly)))
        for ty, tx, kind, obj in sorted(items, key=lambda t: -t[0]):
            h = SH / ty
            cx = SW / 2 * (1 + tx / ty)
            floor_y = horizon + h / 2
            halfw = (0.30 if kind == "bot" else 0.10) * h
            c0 = max(0, int((cx - halfw) / CW))
            c1 = min(NCOL - 1, int((cx + halfw) / CW))
            vis = [c for c in range(c0, c1 + 1) if ty < self.zbuf[c]]
            if not vis:
                continue
            l = max(cx - halfw, vis[0] * CW)
            r = min(cx + halfw, (vis[-1] + 1) * CW)
            if kind == "lamp":
                lx, ly = obj
                k = self.light_level(lx, ly) / (1 + ty * 0.35)
                head_y = floor_y - 0.92 * h
                if self.night_mode:
                    for radius, stipple in ((0.16, "gray25"), (0.10, "gray50")):
                        glow = radius * h
                        self.c.create_oval(cx - glow, head_y - glow, cx + glow, head_y + glow,
                                           fill="#ffe68a", stipple=stipple, outline="", tags="spr")
                self.c.create_line(cx, floor_y, cx, head_y, fill=shade((48, 51, 49), k),
                                   width=max(2, int(0.025 * h)), tags="spr")
                self.c.create_line(cx, head_y + 0.04 * h, cx + 0.13 * h, head_y + 0.04 * h,
                                   fill=shade((48, 51, 49), k), width=max(2, int(0.025 * h)),
                                   tags="spr")
                self.c.create_oval(cx + 0.08 * h, head_y + 0.01 * h,
                                   cx + 0.17 * h, head_y + 0.07 * h,
                                   fill="#ffe68a" if self.night_mode else "#d9d3a2",
                                   outline="", tags="spr")
                continue

            b = obj
            k = self.light_level(b.x, b.y) / (1 + ty * 0.45)
            flash = b.flash > 0
            uniform = (205, 210, 195) if flash else (78, 91, 66)
            vest = (235, 235, 220) if flash else (105, 91, 61)
            skin = (255, 235, 210) if flash else (194, 151, 116)
            boots = (240, 240, 230) if flash else (38, 39, 34)
            if vis[0] <= int(cx / CW) <= vis[-1]:
                self.c.create_oval(cx - 0.10 * h, floor_y - 0.97 * h,
                                   cx + 0.10 * h, floor_y - 0.79 * h,
                                   fill=shade(skin, k), outline="", tags="spr")
                self.c.create_arc(cx - 0.11 * h, floor_y - 1.01 * h,
                                  cx + 0.11 * h, floor_y - 0.80 * h, start=0, extent=180,
                                  fill=shade((67, 76, 54), k), outline="", tags="spr")
                self.c.create_oval(cx - 0.065 * h, floor_y - 0.91 * h,
                                   cx - 0.035 * h, floor_y - 0.89 * h,
                                   fill="#171716", outline="", tags="spr")
                self.c.create_oval(cx + 0.035 * h, floor_y - 0.91 * h,
                                   cx + 0.065 * h, floor_y - 0.89 * h,
                                   fill="#171716", outline="", tags="spr")
            self.c.create_rectangle(cx - 0.035 * h, floor_y - 0.82 * h,
                                    cx + 0.035 * h, floor_y - 0.75 * h,
                                    fill=shade(skin, k), outline="", tags="spr")
            self.c.create_polygon(cx - 0.13 * h, floor_y - 0.76 * h,
                                  cx + 0.13 * h, floor_y - 0.76 * h,
                                  cx + 0.16 * h, floor_y - 0.42 * h,
                                  cx + 0.10 * h, floor_y - 0.37 * h,
                                  cx - 0.10 * h, floor_y - 0.37 * h,
                                  cx - 0.16 * h, floor_y - 0.42 * h,
                                  fill=shade(uniform, k), outline="", tags="spr")
            self.c.create_polygon(cx - 0.12 * h, floor_y - 0.72 * h,
                                  cx - 0.21 * h, floor_y - 0.68 * h,
                                  cx - 0.17 * h, floor_y - 0.49 * h,
                                  cx - 0.10 * h, floor_y - 0.47 * h,
                                  cx - 0.07 * h, floor_y - 0.55 * h,
                                  fill=shade(uniform, k), outline="", tags="spr")
            self.c.create_polygon(cx + 0.12 * h, floor_y - 0.72 * h,
                                  cx + 0.21 * h, floor_y - 0.68 * h,
                                  cx + 0.17 * h, floor_y - 0.49 * h,
                                  cx + 0.10 * h, floor_y - 0.47 * h,
                                  cx + 0.07 * h, floor_y - 0.55 * h,
                                  fill=shade(uniform, k), outline="", tags="spr")
            self.c.create_rectangle(cx - 0.13 * h, floor_y - 0.66 * h,
                                    cx + 0.13 * h, floor_y - 0.43 * h,
                                    fill=shade(vest, k), outline="#27291f", tags="spr")
            self.c.create_line(cx, floor_y - 0.72 * h, cx, floor_y - 0.44 * h,
                               fill=shade((45, 49, 38), k), width=max(1, int(0.012 * h)),
                               tags="spr")
            self.c.create_rectangle(cx - 0.12 * h, floor_y - 0.40 * h,
                                    cx + 0.12 * h, floor_y - 0.36 * h,
                                    fill=shade((52, 48, 35), k), outline="", tags="spr")
            for side in (-1, 1):
                leg_x = cx + side * 0.065 * h
                self.c.create_polygon(leg_x - 0.055 * h, floor_y - 0.36 * h,
                                      leg_x + 0.045 * h, floor_y - 0.36 * h,
                                      leg_x + 0.04 * h, floor_y - 0.10 * h,
                                      leg_x + 0.09 * h, floor_y - 0.06 * h,
                                      leg_x - 0.08 * h, floor_y - 0.06 * h,
                                      fill=shade(uniform, k), outline="", tags="spr")
                self.c.create_rectangle(leg_x - 0.085 * h, floor_y - 0.09 * h,
                                        leg_x + 0.09 * h, floor_y - 0.025 * h,
                                        fill=shade(boots, k), outline="", tags="spr")
            bw = 0.18 * h
            self.c.create_rectangle(cx - bw, floor_y - 1.08 * h, cx + bw, floor_y - 1.04 * h,
                                    fill="#400", outline="", tags="spr")
            self.c.create_rectangle(cx - bw, floor_y - 1.08 * h,
                                    cx - bw + 2 * bw * max(b.hp, 0) / BOT_HP,
                                    floor_y - 1.04 * h, fill="#3f3", outline="", tags="spr")

        # Minimap động
        self.c.delete("mm")
        ms = self.ms
        for b in self.bots:
            self.c.create_oval(8 + b.x * ms - 2, 8 + b.y * ms - 2, 8 + b.x * ms + 2,
                               8 + b.y * ms + 2, fill="red", outline="", tags="mm")
        self.c.create_oval(8 + self.px * ms - 2, 8 + self.py * ms - 2, 8 + self.px * ms + 2,
                           8 + self.py * ms + 2, fill="#4f4", outline="", tags="mm")
        self.c.create_line(8 + self.px * ms, 8 + self.py * ms, 8 + (self.px + dirx * 2) * ms,
                           8 + (self.py + diry * 2) * ms, fill="#4f4", tags="mm")

        # Súng AK + hiệu ứng
        gx = SW // 2 + 90 + math.cos(self.bob * 0.5) * 6
        gy = SH - 70 + abs(math.sin(self.bob)) * 6
        recoil = 10 if now < self.muzzle_until else 0
        if self.reloading:
            gy += 60
        gy += recoil
        shapes = [
            [(gx + 38, gy - 12), (gx + 94, gy - 5), (gx + 94, gy + 12),
             (gx + 48, gy + 8), (gx + 34, gy + 2)],
            [(gx + 34, gy - 24), (gx + 84, gy - 24), (gx + 84, gy - 12),
             (gx + 38, gy - 10), (gx + 22, gy - 15)],
            [(gx - 5, gy - 30), (gx + 31, gy - 30), (gx + 34, gy - 18),
             (gx - 8, gy - 16)],
            [(gx - 12, gy - 18), (gx + 40, gy - 18), (gx + 43, gy + 8),
             (gx + 28, gy + 18), (gx - 15, gy + 10)],
            [(gx - 78, gy - 27), (gx - 9, gy - 27), (gx - 5, gy - 18),
             (gx - 78, gy - 18)],
            [(gx - 55, gy - 15), (gx + 6, gy - 15), (gx + 2, gy - 7),
             (gx - 54, gy - 7), (gx - 62, gy - 11)],
            [(gx + 1, gy + 8), (gx + 19, gy + 10), (gx + 15, gy + 39),
             (gx + 2, gy + 45), (gx - 8, gy + 20)],
            [(gx - 45, gy + 1), (gx - 12, gy + 2), (gx - 21, gy + 31),
             (gx - 38, gy + 33)],
        ]
        for part, points in zip(self.weapon_parts, shapes):
            self.c.coords(part, *(coordinate for point in points for coordinate in point))
        if now < self.muzzle_until:
            self.c.coords(self.muzzle, gx - 88, gy - 34, gx - 66, gy - 12)
            self.c.itemconfig(self.muzzle, state="normal")
        else:
            self.c.itemconfig(self.muzzle, state="hidden")
        self.c.itemconfig(self.hit_overlay, state="normal" if now < self.hit_until else "hidden")
        self.c.tag_raise(self.hit_overlay)
        for l in self.xh:
            self.c.tag_raise(l)
        for part in self.weapon_parts:
            self.c.tag_raise(part)
        self.c.tag_raise(self.muzzle)
        for t in (self.hp_txt, self.ammo_txt, self.info_txt, self.msg_txt):
            self.c.tag_raise(t)

        hp_col = "#4f4" if self.hp > 50 else ("#fa0" if self.hp > 25 else "#f33")
        self.c.itemconfig(self.hp_txt, text=f"HP {self.hp}", fill=hp_col)
        self.c.itemconfig(self.ammo_txt,
                          text="ĐANG NẠP..." if self.reloading else f"{self.ammo}/{MAG_SIZE}")
        self.c.itemconfig(self.info_txt,
                          text=f"{'ĐÊM' if self.night_mode else 'NGÀY'}   "
                               f"Màn {self.map_index + 1} - Đợt {self.stage_wave}/{WAVES_PER_MAP}   "
                               f"Hạ gục {self.kills}   Bot còn {len(self.bots)}")
        if now > self.msg_until and self.alive:
            self.c.itemconfig(self.msg_txt, text="")

    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        self.update(dt, now)
        self.render(now)
        self.root.after(10, self.loop)


if __name__ == "__main__":
    Game().root.mainloop()
