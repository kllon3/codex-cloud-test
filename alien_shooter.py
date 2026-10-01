"""飞机大战外星人。运行：python3 alien_shooter.py（需要桌面图形环境）。"""

from dataclasses import dataclass
import math
import random
import time
import tkinter as tk


WIDTH, HEIGHT = 640, 800
PLAYER_SPEED = 330


@dataclass
class Body:
    x: float
    y: float
    w: float
    h: float
    vx: float = 0
    vy: float = 0

    def overlaps(self, other):
        return (abs(self.x - other.x) < (self.w + other.w) / 2
                and abs(self.y - other.y) < (self.h + other.h) / 2)


class Game:
    """独立于窗口的游戏状态，便于验证移动、碰撞和关卡逻辑。"""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()
        self.state = "menu"

    def reset(self):
        self.player = Body(WIDTH / 2, HEIGHT - 80, 34, 42)
        self.shots = []
        self.enemy_shots = []
        self.enemies = []
        self.particles = []
        self.score = 0
        self.lives = 3
        self.wave = 0
        self.cooldown = 0
        self.invulnerable = 0
        self.wave_delay = 0
        self.state = "running"
        self.spawn_wave()

    def spawn_wave(self):
        self.wave += 1
        rows = min(3 + (self.wave - 1) // 3, 5)
        self.enemies = [Body(75 + column * 70, 145 + row * 54, 34, 28)
                        for row in range(rows) for column in range(8)]
        self.direction = 1
        self.enemy_timer = 0.9
        self.wave_delay = 0
        self.enemy_shots.clear()

    def burst(self, x, y, color):
        for _ in range(15):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(45, 170)
            self.particles.append([x, y, math.cos(angle) * speed,
                                   math.sin(angle) * speed, 0.5, color])

    def damage(self):
        if self.invulnerable > 0 or self.state != "running":
            return
        self.lives -= 1
        self.invulnerable = 1.8
        self.burst(self.player.x, self.player.y, "#67e8f9")
        if self.lives <= 0:
            self.state = "gameover"

    def update(self, dt, keys):
        if self.state != "running":
            return
        dt = min(max(dt, 0), 1 / 30)
        self.cooldown = max(0, self.cooldown - dt)
        self.invulnerable = max(0, self.invulnerable - dt)
        dx = int(bool(keys & {"d", "right"})) - int(bool(keys & {"a", "left"}))
        dy = int(bool(keys & {"s", "down"})) - int(bool(keys & {"w", "up"}))
        scale = PLAYER_SPEED * dt / (math.sqrt(2) if dx and dy else 1)
        self.player.x = max(28, min(WIDTH - 28, self.player.x + dx * scale))
        self.player.y = max(510, min(HEIGHT - 48, self.player.y + dy * scale))
        if "space" in keys and self.cooldown <= 0:
            self.shots.append(Body(self.player.x, self.player.y - 30, 6, 18, vy=-580))
            self.cooldown = 0.16

        for shot in self.shots + self.enemy_shots:
            shot.x += shot.vx * dt
            shot.y += shot.vy * dt
        self.shots = [s for s in self.shots if s.y > -20]
        self.enemy_shots = [s for s in self.enemy_shots if s.y < HEIGHT + 20]

        if self.enemies:
            shift = self.direction * min(48 + self.wave * 12, 155) * dt
            for enemy in self.enemies:
                enemy.x += shift
            if min(e.x for e in self.enemies) < 28 or max(e.x for e in self.enemies) > WIDTH - 28:
                self.direction *= -1
                for enemy in self.enemies:
                    enemy.x -= shift
                    enemy.y += 20
            self.enemy_timer -= dt
            if self.enemy_timer <= 0:
                # 只有每列最下方的外星人开火，子弹不会穿过同伴。
                front = [e for e in self.enemies
                         if not any(abs(e.x - other.x) < 1 and other.y > e.y
                                    for other in self.enemies)]
                enemy = self.rng.choice(front)
                aim = max(-65, min(65, (self.player.x - enemy.x) * 0.22))
                self.enemy_shots.append(Body(enemy.x, enemy.y + 20, 9, 16,
                                             aim, min(215 + self.wave * 18, 380)))
                self.enemy_timer = max(0.25, 0.95 - self.wave * 0.065)

        for shot in self.shots[:]:
            target = next((enemy for enemy in self.enemies if shot.overlaps(enemy)), None)
            if target is not None:
                self.enemies.remove(target)
                self.shots.remove(shot)
                self.score += 100
                self.burst(target.x, target.y, "#a3e635")

        for shot in self.enemy_shots[:]:
            if shot.overlaps(self.player):
                self.enemy_shots.remove(shot)
                self.damage()
        for enemy in self.enemies[:]:
            if enemy.overlaps(self.player):
                self.enemies.remove(enemy)
                self.burst(enemy.x, enemy.y, "#a3e635")
                self.damage()
            elif enemy.y + enemy.h / 2 >= HEIGHT - 25:
                self.state = "gameover"

        for particle in self.particles:
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        if not self.enemies and self.state == "running":
            self.wave_delay += dt
            if self.wave_delay >= 1.2:
                self.spawn_wave()


class AlienShooter:
    def __init__(self, root):
        self.root = root
        root.title("飞机大战外星人 · Alien Defense")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg="#080e20", highlightthickness=0)
        self.canvas.pack()
        self.game = Game()
        self.keys = set()
        self.stars = [[random.randrange(WIDTH), random.randrange(HEIGHT),
                       random.uniform(18, 75)] for _ in range(85)]
        self.last_time = time.perf_counter()
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        root.bind("<FocusOut>", self.focus_out)
        self.canvas.focus_set()
        self.frame()

    def key_down(self, event):
        key = event.keysym.lower()
        first_press = key not in self.keys
        self.keys.add(key)
        if not first_press:
            return
        if key == "return" and self.game.state in {"menu", "gameover"}:
            self.game.reset()
        elif key == "p" and self.game.state in {"running", "paused"}:
            self.game.state = "paused" if self.game.state == "running" else "running"
        elif key == "escape":
            self.root.destroy()

    def key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def focus_out(self, _event):
        self.keys.clear()
        if self.game.state == "running":
            self.game.state = "paused"

    def label(self, x, y, text, size=14, color="#e2e8f0", **kwargs):
        self.canvas.create_text(x, y, text=text, fill=color,
                                font=("sans-serif", size), **kwargs)

    def draw_ship(self):
        player = self.game.player
        if self.game.invulnerable > 0 and int(self.game.invulnerable * 12) % 2:
            return
        x, y = player.x, player.y
        c = self.canvas
        flame = 14 + random.randrange(10) if self.game.state == "running" else 14
        c.create_polygon(x - 7, y + 16, x, y + 16 + flame, x + 7, y + 16,
                         fill="#fbbf24", outline="")
        c.create_polygon(x, y - 24, x - 23, y + 18, x - 8, y + 12,
                         x, y + 17, x + 8, y + 12, x + 23, y + 18,
                         fill="#38bdf8", outline="#bae6fd", width=2)
        c.create_polygon(x, y - 13, x - 5, y + 5, x + 5, y + 5,
                         fill="#eff6ff", outline="")

    def draw_alien(self, enemy):
        x, y = enemy.x, enemy.y
        c = self.canvas
        c.create_line(x - 10, y - 9, x - 15, y - 18, fill="#bef264", width=3)
        c.create_line(x + 10, y - 9, x + 15, y - 18, fill="#bef264", width=3)
        c.create_polygon(x - 10, y - 12, x + 10, y - 12, x + 18, y - 3,
                         x + 18, y + 9, x + 10, y + 9, x + 10, y + 15,
                         x + 4, y + 9, x - 4, y + 9, x - 10, y + 15,
                         x - 10, y + 9, x - 18, y + 9, x - 18, y - 3,
                         fill="#a3e635", outline="#d9f99d")
        for eye in (-7, 7):
            c.create_rectangle(x + eye - 3, y - 3, x + eye + 3, y + 3,
                               fill="#080e20", outline="")

    def overlay(self, title, subtitle, instruction):
        c = self.canvas
        c.create_rectangle(52, 270, WIDTH - 52, 510, fill="#101c36",
                           outline="#334569", width=2)
        self.label(WIDTH / 2, 317, "✦  ALIEN DEFENSE  ✦", 13, "#67e8f9")
        self.label(WIDTH / 2, 365, title, 28, "#ffffff")
        self.label(WIDTH / 2, 413, subtitle, 14, "#94a3b8")
        self.label(WIDTH / 2, 468, instruction, 16, "#a3e635")

    def draw(self, dt):
        c, game = self.canvas, self.game
        c.delete("all")
        for star in self.stars:
            if game.state == "running":
                star[1] = (star[1] + star[2] * dt) % HEIGHT
            x, y, speed = star
            radius = 1 if speed < 45 else 1.5
            c.create_oval(x - radius, y - radius, x + radius, y + radius,
                          fill="#334569" if speed < 45 else "#7891b6", outline="")
        for enemy in game.enemies:
            self.draw_alien(enemy)
        for shot in game.shots:
            c.create_line(shot.x, shot.y - 9, shot.x, shot.y + 9,
                          fill="#67e8f9", width=4)
        for shot in game.enemy_shots:
            c.create_oval(shot.x - 4, shot.y - 8, shot.x + 4, shot.y + 8,
                          fill="#fb7185", outline="#fecdd3")
        self.draw_ship()
        for x, y, _vx, _vy, life, color in game.particles:
            radius = max(1, life * 5)
            c.create_oval(x - radius, y - radius, x + radius, y + radius,
                          fill=color, outline="")

        c.create_rectangle(0, 0, WIDTH, 87, fill="#10182e", outline="")
        self.label(24, 26, "星际防线", 20, "#67e8f9", anchor="w")
        self.label(24, 62, f"得分  {game.score:06d}", 14, anchor="w")
        self.label(WIDTH / 2, 62, f"第 {game.wave} 波", 14, "#a3e635")
        self.label(WIDTH - 24, 32, "生命  " + "♥ " * game.lives,
                   16, "#fb7185", anchor="e")
        self.label(WIDTH - 24, 62, "P 暂停", 12, "#94a3b8", anchor="e")
        c.create_line(0, 87, WIDTH, 87, fill="#263957")
        self.label(WIDTH / 2, HEIGHT - 16,
                   "方向键 / WASD 移动    空格 射击    Esc 退出", 11, "#94a3b8")
        if not game.enemies and game.state == "running":
            self.label(WIDTH / 2, 350, "下一波外星人即将抵达…", 20, "#a3e635")
        if game.state == "menu":
            self.overlay("飞机大战外星人", "消灭外星人，守住星际防线", "按 Enter 开始游戏")
        elif game.state == "paused":
            self.overlay("游戏已暂停", "稍作休息，舰队等你归来", "按 P 继续游戏")
        elif game.state == "gameover":
            self.overlay("任务结束", f"最终得分 {game.score}  ·  到达第 {game.wave} 波",
                         "按 Enter 重新开始")

    def frame(self):
        now = time.perf_counter()
        dt = min(now - self.last_time, 1 / 30)
        self.last_time = now
        self.game.update(dt, self.keys)
        self.draw(dt)
        self.root.after(16, self.frame)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit("无法打开游戏窗口，请在有图形桌面的电脑上运行。\n"
                         f"详细信息：{exc}") from exc
    AlienShooter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
