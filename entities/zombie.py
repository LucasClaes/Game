import math
import random
import pygame
from core.settings import TILE_SIZE, WHITE, ZOMBIE_TYPES, AGGRO_RADIUS

_PATH_INTERVAL = 0.45  # seconds between BFS recalculations

# Visual style per zombie type
_STYLE = {
    "basic":    {"color": (220, 60,  60),  "glow": (255, 80,  80),  "glow_r": 20, "shape": "rect"},
    "fast":     {"color": (255, 140, 30),  "glow": (255, 170, 60),  "glow_r": 17, "shape": "diamond"},
    "tank":     {"color": (160, 60,  220), "glow": (190, 90,  255), "glow_r": 26, "shape": "circle"},
    "ranged":   {"color": (180, 80,  200), "glow": (200, 110, 255), "glow_r": 18, "shape": "diamond"},
    "exploder": {"color": (60,  220, 80),  "glow": (80,  255, 100), "glow_r": 18, "shape": "circle"},
    "healer":   {"color": (200, 100, 220), "glow": (220, 130, 255), "glow_r": 20, "shape": "cross"},
    "lurker":   {"color": (0,   180, 180), "glow": (0,   220, 220), "glow_r": 16, "shape": "diamond"},
    "crawler":  {"color": (180, 100, 40),  "glow": (220, 130, 60),  "glow_r": 12, "shape": "rect"},
    "spitter":  {"color": (80,  200, 80),  "glow": (100, 240, 100), "glow_r": 18, "shape": "circle"},
    "bomber":   {"color": (240, 200, 30),  "glow": (255, 220, 60),  "glow_r": 20, "shape": "triangle"},
    "shielder": {"color": (100, 150, 220), "glow": (130, 180, 255), "glow_r": 22, "shape": "hex"},
    "phaser":   {"color": (180, 60,  200), "glow": (220, 80,  255), "glow_r": 18, "shape": "diamond"},
    "summoner": {"color": (220, 160, 50),  "glow": (255, 200, 80),  "glow_r": 22, "shape": "circle"},
    "vortex":   {"color": (50,  200, 220), "glow": (80,  240, 255), "glow_r": 20, "shape": "circle"},
    "behemoth": {"color": (200, 40,  40),  "glow": (255, 60,  60),  "glow_r": 34, "shape": "star"},
}


class Zombie:
    SIZE  = 28
    IDLE  = 0
    CHASE = 1

    def __init__(self, tile_x: int, tile_y: int, zombie_type: str = "basic", elite: bool = False):
        stats = ZOMBIE_TYPES.get(zombie_type, ZOMBIE_TYPES["basic"])
        self.pos = pygame.Vector2(
            tile_x * TILE_SIZE + TILE_SIZE // 2,
            tile_y * TILE_SIZE + TILE_SIZE // 2,
        )
        self.speed = float(stats["speed"])
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]
        self.damage = stats["damage"]
        self.coin_drop = stats["coin_drop"]
        self.zombie_type = zombie_type
        self.elite = elite
        if elite:
            self.hp = self.hp * 2
            self.max_hp = self.hp
            self.speed *= 1.3
            self.coin_drop = 3
        # Crawler is smaller
        size = 18 if zombie_type == "crawler" else self.SIZE
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self._draw_size = size
        self.alive = True
        self._state = Zombie.IDLE
        self._hit_flash = 0.0
        self._invincible = 0.0
        self._path: list = []
        self._path_timer: float = 0.0
        self._anim = 0.0
        self._shoot_range = stats.get("shoot_range", 0)
        self._shoot_cooldown = stats.get("shoot_cooldown", 2.0)
        self._shoot_timer = self._shoot_cooldown

        # Exploder / Bomber shared
        self.death_data = {}

        # Healer
        self._heal_radius   = stats.get("heal_radius",   0)
        self._heal_amount   = stats.get("heal_amount",   0)
        self._heal_interval = stats.get("heal_interval", 2.0)
        self._heal_timer    = 0.0
        self._healing_flash = 0.0

        # Lurker
        self._lurk_aggro = stats.get("lurk_aggro", AGGRO_RADIUS)
        self._hidden = zombie_type == "lurker"

        # Phaser
        self._phase_timer = stats.get("phase_cooldown", 4.0)

        # Summoner
        self._summon_timer = stats.get("summon_cooldown", 5.0)
        self._summon_cap   = stats.get("summon_cap", 3)

        # Behemoth slam
        self._slam_timer       = stats.get("slam_cooldown", 5.0)
        self._slam_radius      = stats.get("slam_radius", 140)
        self._slam_damage      = stats.get("slam_damage", 80)
        self._slam_telegraphing = False
        self._slam_telegraph_timer = 0.0
        self.slam_ready = False  # read by playing.py each frame

    def update(self, dt: float, player_pos: pygame.Vector2,
               walls: list, tile_grid=None, tile_w: int = 30, tile_h: int = 20,
               zombies: list = None) -> tuple:
        """Return (new_enemy_bullets, new_zombies)."""
        if not self.alive:
            return [], []
        self._hit_flash = max(0.0, self._hit_flash - dt)
        self._invincible = max(0.0, self._invincible - dt)
        self._anim += dt
        self.slam_ready = False
        self._depenetrate(walls)

        # Aggro detection: switch to CHASE when player is close enough
        aggro_dist = self._lurk_aggro if self.zombie_type == "lurker" else AGGRO_RADIUS
        if self._state == Zombie.IDLE:
            if (player_pos - self.pos).length() <= aggro_dist:
                self._state = Zombie.CHASE
                self._hidden = False

        if self._state == Zombie.IDLE:
            return [], []

        # Spitter: stationary, fires acid shots
        if self.zombie_type == "spitter" and self._shoot_range > 0:
            dist = (player_pos - self.pos).length()
            if dist <= self._shoot_range:
                self._shoot_timer -= dt
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                if self._shoot_timer <= 0:
                    self._shoot_timer = self._shoot_cooldown
                    direction = (player_pos - self.pos).normalize()
                    from entities.enemy_bullet import EnemyBullet
                    b = EnemyBullet(self.pos, direction * 160, 1)
                    b.spawn_trap = True
                    return [b], []
            return [], []

        # Ranged zombie: stop and shoot when in range
        if self.zombie_type == "ranged" and self._shoot_range > 0:
            dist = (player_pos - self.pos).length()
            if dist <= self._shoot_range:
                self._shoot_timer -= dt
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                if self._shoot_timer <= 0:
                    self._shoot_timer = self._shoot_cooldown
                    direction = (player_pos - self.pos).normalize()
                    from entities.enemy_bullet import EnemyBullet
                    return [EnemyBullet(self.pos, direction * 200, 1)], []
                return [], []

        # Phaser: teleport toward player periodically
        if self.zombie_type == "phaser":
            self._phase_timer -= dt
            if self._phase_timer <= 0:
                self._phase_timer = ZOMBIE_TYPES["phaser"]["phase_cooldown"]
                dist = (player_pos - self.pos).length()
                if dist > 0:
                    direction = (player_pos - self.pos).normalize()
                    jump = min(ZOMBIE_TYPES["phaser"]["phase_dist"], dist - 20)
                    if jump > 0:
                        self.pos += direction * jump
                        self.rect.center = (int(self.pos.x), int(self.pos.y))
                self._invincible = 0.3

        # Behemoth slam telegraph
        if self.zombie_type == "behemoth":
            self._slam_timer -= dt
            if self._slam_timer <= 0:
                self._slam_timer = ZOMBIE_TYPES["behemoth"]["slam_cooldown"]
                self.slam_ready = True
            elif self._slam_timer <= 1.0:
                self._slam_telegraphing = True
                self._slam_telegraph_timer = self._slam_timer
            else:
                self._slam_telegraphing = False

        self._path_timer -= dt
        if tile_grid is not None and (self._path_timer <= 0 or not self._path):
            self._path_timer = _PATH_INTERVAL
            start = (int(self.pos.x // TILE_SIZE), int(self.pos.y // TILE_SIZE))
            goal  = (int(player_pos.x // TILE_SIZE), int(player_pos.y // TILE_SIZE))
            from systems.pathfinding import bfs_path
            self._path = bfs_path(tile_grid, tile_w, tile_h, start, goal)

        # Follow next waypoint or fall back to direct chase
        if self._path:
            tx, ty = self._path[0]
            target = pygame.Vector2(tx * TILE_SIZE + TILE_SIZE // 2,
                                    ty * TILE_SIZE + TILE_SIZE // 2)
            if (target - self.pos).length() < TILE_SIZE * 0.55:
                self._path.pop(0)
            else:
                self._move_toward(target, dt, walls)
        else:
            self._move_toward(player_pos, dt, walls)

        self.rect.center = (int(self.pos.x), int(self.pos.y))

        # Healer: periodically restore HP to nearby zombies
        if self.zombie_type == "healer" and self._heal_radius > 0:
            self._heal_timer -= dt
            self._healing_flash = max(0.0, self._healing_flash - dt)
            if self._heal_timer <= 0 and zombies is not None:
                self._heal_timer = self._heal_interval
                for z in zombies:
                    if z is not self and z.alive:
                        if (z.pos - self.pos).length() <= self._heal_radius:
                            z.hp = min(z.max_hp, z.hp + self._heal_amount)
                            z._hit_flash = 0.0
                            self._healing_flash = 0.3

        # Summoner: spawn basic zombies periodically
        if self.zombie_type == "summoner" and zombies is not None:
            self._summon_timer -= dt
            if self._summon_timer <= 0:
                self._summon_timer = ZOMBIE_TYPES["summoner"]["summon_cooldown"]
                alive_basic = sum(1 for z in zombies if z.alive and z.zombie_type == "basic")
                if alive_basic < self._summon_cap:
                    ox = random.randint(-2, 2)
                    oy = random.randint(-2, 2)
                    tx = int(self.pos.x // TILE_SIZE) + ox
                    ty = int(self.pos.y // TILE_SIZE) + oy
                    return [], [Zombie(tx, ty, "basic")]

        return [], []

    def _depenetrate(self, walls: list):
        for wall in walls:
            if not self.rect.colliderect(wall):
                continue
            ox_left  = self.rect.right  - wall.left
            ox_right = wall.right  - self.rect.left
            oy_top   = self.rect.bottom - wall.top
            oy_bot   = wall.bottom - self.rect.top
            min_push = min(ox_left, ox_right, oy_top, oy_bot)
            if min_push <= 0:
                continue
            if min_push == ox_left:
                self.pos.x -= ox_left
            elif min_push == ox_right:
                self.pos.x += ox_right
            elif min_push == oy_top:
                self.pos.y -= oy_top
            else:
                self.pos.y += oy_bot
            self.rect.center = (int(self.pos.x), int(self.pos.y))

    def _move_toward(self, target: pygame.Vector2, dt: float, walls: list):
        diff = target - self.pos
        if diff.length() < 1:
            return
        move = diff.normalize() * self.speed * dt

        new_rect = self.rect.move(move.x, move.y)
        if not any(new_rect.colliderect(w) for w in walls):
            self.pos += move
            return
        new_rect_x = self.rect.move(move.x, 0)
        if not any(new_rect_x.colliderect(w) for w in walls):
            self.pos.x += move.x
            return
        new_rect_y = self.rect.move(0, move.y)
        if not any(new_rect_y.colliderect(w) for w in walls):
            self.pos.y += move.y

    def take_damage(self, amount: int) -> bool:
        if self._invincible > 0:
            return False
        self._state = Zombie.CHASE
        self._hidden = False
        self.hp -= amount
        self._hit_flash = 0.12
        self._invincible = 0.14
        if self.hp <= 0:
            self.alive = False
            if self.zombie_type == "exploder":
                self.death_data = {
                    "explode": True,
                    "pos": self.pos.copy(),
                    "radius": 80,
                    "damage": 50,
                }
            elif self.zombie_type == "bomber":
                stats = ZOMBIE_TYPES["bomber"]
                self.death_data = {
                    "explode": True,
                    "pos": self.pos.copy(),
                    "radius": stats["explode_radius"],
                    "damage": stats["explode_damage"],
                }
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if not self.alive:
            return
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)
        style = _STYLE.get(self.zombie_type, _STYLE["basic"])
        body_color = WHITE if self._hit_flash > 0 else style["color"]
        half = self._draw_size // 2

        from systems.gfx import glow
        if self.zombie_type == "exploder":
            danger  = 1.0 - (self.hp / self.max_hp)
            pulse_r = int(style["glow_r"] + danger * 14 + math.sin(self._anim * 6) * 4)
            glow(surface, cx, cy, pulse_r, style["glow"], int(65 + danger * 80))
        elif self.zombie_type == "bomber":
            pulse = abs(math.sin(self._anim * (3.0 + 4.0 * (1.0 - self.hp / self.max_hp))))
            glow(surface, cx, cy, int(style["glow_r"] + pulse * 10), style["glow"], int(65 + pulse * 90))
        elif self.zombie_type == "phaser" and self._invincible > 0:
            glow(surface, cx, cy, style["glow_r"] + 8, style["glow"], 150)
        elif self.zombie_type == "behemoth" and self._slam_telegraphing:
            t = self._slam_telegraph_timer
            ring_r = int(20 + (1.0 - t) * self._slam_radius)
            pygame.draw.circle(surface, (255, 60, 30), (cx, cy), ring_r, 2)
            glow(surface, cx, cy, style["glow_r"] + 10, (255, 80, 30), 120)
        else:
            glow(surface, cx, cy, style["glow_r"], style["glow"], 65)

        shape = style["shape"]

        # Lurker: draw faint ghost outline only while hidden
        if self.zombie_type == "lurker" and self._hidden:
            sz = self._draw_size
            s = pygame.Surface((sz * 3, sz * 3), pygame.SRCALPHA)
            sp = [(sz * 3 // 2,        sz * 3 // 2 - half),
                  (sz * 3 // 2 + half, sz * 3 // 2),
                  (sz * 3 // 2,        sz * 3 // 2 + half),
                  (sz * 3 // 2 - half, sz * 3 // 2)]
            pygame.draw.polygon(s, (0, 220, 220, 40), sp)
            surface.blit(s, (cx - sz * 3 // 2, cy - sz * 3 // 2))
            return

        # Shielder: draw shield arc on front
        if self.zombie_type == "shielder":
            shield_pts = []
            for a in range(-45, 46, 10):
                rad = math.radians(a)
                sx = cx + int(math.cos(rad) * (half + 6))
                sy = cy + int(math.sin(rad) * (half + 6))
                shield_pts.append((sx, sy))
            if len(shield_pts) > 1:
                pygame.draw.lines(surface, (130, 200, 255), False, shield_pts, 3)

        if shape == "circle":
            pygame.draw.circle(surface, body_color, (cx, cy), half)
            ring_col = (100, 255, 120) if self.zombie_type == "summoner" else (220, 180, 255)
            pygame.draw.circle(surface, ring_col, (cx, cy), half, 2)
        elif shape == "diamond":
            pts = [(cx, cy - half), (cx + half, cy),
                   (cx, cy + half), (cx - half, cy)]
            pygame.draw.polygon(surface, body_color, pts)
            pygame.draw.polygon(surface, (255, 200, 100), pts, 2)
        elif shape == "cross":
            bar_thickness = 8
            color_to_use = (100, 255, 100) if self._healing_flash > 0 else body_color
            pygame.draw.rect(surface, color_to_use,
                             (cx - half, cy - bar_thickness // 2, self._draw_size, bar_thickness))
            pygame.draw.rect(surface, color_to_use,
                             (cx - bar_thickness // 2, cy - half, bar_thickness, self._draw_size))
            pygame.draw.rect(surface, (220, 150, 255),
                             (cx - half, cy - bar_thickness // 2, self._draw_size, bar_thickness), 1)
            pygame.draw.rect(surface, (220, 150, 255),
                             (cx - bar_thickness // 2, cy - half, bar_thickness, self._draw_size), 1)
        elif shape == "triangle":
            pts = [(cx, cy - half), (cx + half, cy + half), (cx - half, cy + half)]
            pygame.draw.polygon(surface, body_color, pts)
            pygame.draw.polygon(surface, (255, 240, 80), pts, 2)
        elif shape == "hex":
            pts = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                pts.append((cx + int(math.cos(angle) * half),
                             cy + int(math.sin(angle) * half)))
            pygame.draw.polygon(surface, body_color, pts)
            pygame.draw.polygon(surface, (160, 210, 255), pts, 2)
        elif shape == "star":
            outer, inner = half, half // 2
            pts = []
            for i in range(10):
                r = outer if i % 2 == 0 else inner
                angle = math.radians(36 * i - 90)
                pts.append((cx + int(math.cos(angle) * r),
                             cy + int(math.sin(angle) * r)))
            pygame.draw.polygon(surface, body_color, pts)
            pygame.draw.polygon(surface, (255, 120, 80), pts, 2)
        else:
            draw_rect = pygame.Rect(cx - half, cy - half, self._draw_size, self._draw_size)
            pygame.draw.rect(surface, body_color, draw_rect, border_radius=5)
            pygame.draw.rect(surface, (255, 130, 130), draw_rect, 2, border_radius=5)
            pygame.draw.circle(surface, (255, 230, 230), (cx - 5, cy - 4), 3)
            pygame.draw.circle(surface, (255, 230, 230), (cx + 5, cy - 4), 3)
            pygame.draw.circle(surface, (60, 0, 0), (cx - 5, cy - 4), 1)
            pygame.draw.circle(surface, (60, 0, 0), (cx + 5, cy - 4), 1)

        # Phaser: phase shimmer when invincible
        if self.zombie_type == "phaser" and self._invincible > 0:
            alpha = int(self._invincible / 0.3 * 120)
            s = pygame.Surface((self._draw_size * 2, self._draw_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 100, 255, alpha),
                                (self._draw_size, self._draw_size), half + 4)
            surface.blit(s, (cx - self._draw_size, cy - self._draw_size))

        # Elite outline
        if self.elite:
            elite_r = pygame.Rect(cx - half - 3, cy - half - 3,
                                  self._draw_size + 6, self._draw_size + 6)
            pygame.draw.rect(surface, (255, 220, 0), elite_r, 2, border_radius=7)

        # HP bar
        bar_w = self._draw_size + 4
        bar_h = 4
        bx = cx - bar_w // 2
        by = cy - half - 9
        pygame.draw.rect(surface, (30, 10, 10), (bx, by, bar_w, bar_h), border_radius=2)
        hp_ratio = max(0, self.hp / self.max_hp)
        bar_color = (200, 60, 60) if hp_ratio > 0.4 else (255, 200, 0)
        pygame.draw.rect(surface, bar_color,
                         (bx, by, int(bar_w * hp_ratio), bar_h), border_radius=2)
