import math
import random
import pygame
from core.settings import TILE_SIZE
from entities.enemy_bullet import EnemyBullet

_BULLET_SPEED    = 220
_BULLET_DAMAGE   = 2
_SIZE            = 56
_INV_WINDOW      = 0.14
_CHARGE_SPEED    = 210
_CHARGE_DURATION = 0.45

_COLOR_P1 = (130, 50,  200)
_COLOR_P2 = (210, 100, 30)
_COLOR_P3 = (220, 40,  40)
_GLOW_P1  = (160, 80,  240)
_GLOW_P2  = (240, 140, 60)
_GLOW_P3  = (255, 70,  50)

_NECRO_C1   = (30,  100, 30)
_NECRO_C2   = (80,  180, 50)
_NECRO_C3   = (160, 220, 40)
_NECRO_GL1  = (60,  200, 60)
_NECRO_GL2  = (130, 240, 80)
_NECRO_GL3  = (200, 255, 60)

_SPAWN_COOLDOWNS = [6.0, 4.0, 2.5]  # per phase index


def _hex_points(cx, cy, radius):
    return [
        (int(cx + math.cos(math.radians(a)) * radius),
         int(cy + math.sin(math.radians(a)) * radius))
        for a in range(0, 360, 60)
    ]


def _pent_points(cx, cy, radius):
    return [
        (int(cx + math.cos(math.radians(a - 90)) * radius),
         int(cy + math.sin(math.radians(a - 90)) * radius))
        for a in range(0, 360, 72)
    ]


class Boss:
    def __init__(self, px: float, py: float, boss_level: int = 1):
        self.max_hp   = 800 + 100 * boss_level
        self.hp       = self.max_hp
        self.speed    = 65.0
        self.damage   = 3
        self.coins    = 200 + 50 * boss_level
        self.alive    = True
        self.pos      = pygame.Vector2(px, py)
        self.rect     = pygame.Rect(0, 0, _SIZE, _SIZE)
        self.rect.center = (int(px), int(py))

        self._inv_timer    = 0.0
        self._shoot_timer  = 1.0
        self._anim         = 0.0
        self._charge_timer = 0.0
        self._charging     = False
        self._hit_flash    = 0.0
        self._stuck_timer  = 0.0
        self._escape_dir   = pygame.Vector2(0, 0)
        self._escape_timer = 0.0
        self._last_pos     = None

    @property
    def phase(self) -> int:
        ratio = self.hp / self.max_hp
        if ratio > 0.60:
            return 1
        if ratio > 0.30:
            return 2
        return 3

    def update(self, dt: float, player_pos: pygame.Vector2,
               walls: list, level_w: int, level_h: int) -> tuple:
        if not self.alive:
            return [], []

        self._inv_timer   = max(0.0, self._inv_timer - dt)
        self._hit_flash   = max(0.0, self._hit_flash - dt)
        self._shoot_timer = max(0.0, self._shoot_timer - dt)
        self._anim       += dt

        if self.phase >= 2:
            self._charge_timer -= dt
            if self._charge_timer <= 0:
                if self._charging:
                    self._charging = False
                    self._charge_timer = 3.5 if self.phase == 2 else 2.0
                else:
                    self._charging = True
                    self._charge_timer = _CHARGE_DURATION

        effective_speed = _CHARGE_SPEED if self._charging else self.speed
        if self.phase == 3 and not self._charging:
            effective_speed = self.speed * 1.4

        self._move_toward(player_pos, effective_speed, dt, walls)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        new_bullets = []
        if self._shoot_timer <= 0:
            new_bullets = self._shoot(player_pos)
            self._shoot_timer = [1.8, 1.2, 0.8][self.phase - 1]

        return new_bullets, []

    def _shoot(self, player_pos: pygame.Vector2) -> list:
        dx = player_pos.x - self.pos.x
        dy = player_pos.y - self.pos.y
        base_angle = math.atan2(dy, dx)

        spreads = {1: [0], 2: [-20, 0, 20], 3: [-40, -20, 0, 20, 40]}[self.phase]
        speed = _BULLET_SPEED * (1.5 if self.phase == 3 else 1.0)

        bullets = []
        for deg in spreads:
            angle = base_angle + math.radians(deg)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            bullets.append(EnemyBullet(self.pos, vel, _BULLET_DAMAGE))
        return bullets

    def _move_toward(self, target: pygame.Vector2, speed: float, dt: float, walls: list):
        diff = target - self.pos
        if diff.length() < 2:
            return

        if self._last_pos is None:
            self._last_pos = pygame.Vector2(self.pos)

        desired = diff.normalize() * speed * dt

        # Blend in escape direction when stuck
        if self._escape_timer > 0:
            self._escape_timer -= dt
            blended = desired + self._escape_dir * speed * dt * 0.9
            move = blended.normalize() * speed * dt if blended.length() > 0 else desired
        else:
            move = desired

        prev_pos = pygame.Vector2(self.pos)
        new_rect = self.rect.move(move.x, move.y)
        if not any(new_rect.colliderect(w) for w in walls):
            self.pos += move
        else:
            new_rect_x = self.rect.move(move.x, 0)
            if not any(new_rect_x.colliderect(w) for w in walls):
                self.pos.x += move.x
            else:
                new_rect_y = self.rect.move(0, move.y)
                if not any(new_rect_y.colliderect(w) for w in walls):
                    self.pos.y += move.y

        # Stuck detection: if barely moved, pick a perpendicular escape direction
        actual_moved = (self.pos - prev_pos).length()
        if actual_moved < speed * dt * 0.15:
            self._stuck_timer += dt
            if self._stuck_timer > 0.4:
                perp = pygame.Vector2(-diff.y, diff.x)
                if perp.length() > 0:
                    perp = perp.normalize()
                if random.random() < 0.5:
                    perp = -perp
                self._escape_dir  = perp
                self._escape_timer = 0.8
                self._stuck_timer  = 0.0
        else:
            self._stuck_timer = max(0.0, self._stuck_timer - dt * 3)

        self._last_pos = pygame.Vector2(self.pos)

    def take_damage(self, amount: int) -> bool:
        if self._inv_timer > 0:
            return False
        self.hp -= amount
        self._inv_timer = _INV_WINDOW
        self._hit_flash = 0.12
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if not self.alive:
            return
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)

        from systems.gfx import glow

        if self._hit_flash > 0:
            body_color = (255, 255, 255)
            glow_color = (255, 255, 200)
        elif self._charging:
            body_color = _COLOR_P3
            glow_color = _GLOW_P3
        elif self.phase == 3:
            body_color = _COLOR_P3
            glow_color = _GLOW_P3
        elif self.phase == 2:
            body_color = _COLOR_P2
            glow_color = _GLOW_P2
        else:
            body_color = _COLOR_P1
            glow_color = _GLOW_P1

        pulse = 0.5 + 0.5 * math.sin(self._anim * 3.0)
        glow(surface, cx, cy, int(36 + pulse * 10), glow_color, int(70 + pulse * 40))

        radius = _SIZE // 2
        pts = _hex_points(cx, cy, radius)
        pygame.draw.polygon(surface, body_color, pts)
        outline_color = glow_color if not self._hit_flash else (255, 255, 255)
        pygame.draw.polygon(surface, outline_color, pts, 3)

        if self.phase >= 2:
            inner_r = int(radius * 0.55)
            pygame.draw.circle(surface, _COLOR_P3 if self.phase == 3 else _COLOR_P2,
                               (cx, cy), inner_r, 2)

        eye_angle = self._anim * 1.2
        ex = int(cx + math.cos(eye_angle) * 8)
        ey = int(cy + math.sin(eye_angle) * 8)
        pygame.draw.circle(surface, (255, 60, 30), (ex, ey), 6)
        pygame.draw.circle(surface, (255, 220, 200), (ex, ey), 3)

        self._draw_hp_bar(surface, cx, cy)

    def _draw_hp_bar(self, surface, cx, cy):
        bar_w = 80
        bar_h = 6
        bx = cx - bar_w // 2
        by = cy - _SIZE // 2 - 14
        pygame.draw.rect(surface, (40, 10, 10), (bx, by, bar_w, bar_h), border_radius=3)
        hp_ratio = max(0.0, self.hp / self.max_hp)
        bar_color = (200, 50, 50) if hp_ratio > 0.3 else (255, 200, 0)
        pygame.draw.rect(surface, bar_color,
                         (bx, by, int(bar_w * hp_ratio), bar_h), border_radius=3)
        pygame.draw.rect(surface, (200, 150, 200), (bx, by, bar_w, bar_h), 1, border_radius=3)


class Necromancer(Boss):
    def __init__(self, px: float, py: float, boss_level: int = 2):
        super().__init__(px, py, boss_level)
        self.max_hp  = 600 + 150 * boss_level
        self.hp      = self.max_hp
        self.speed   = 48.0
        self.coins   = 250 + 60 * boss_level
        self._spawn_timer = 3.0

    def update(self, dt: float, player_pos: pygame.Vector2,
               walls: list, level_w: int, level_h: int) -> tuple:
        bullets, _ = super().update(dt, player_pos, walls, level_w, level_h)

        new_zombies = []
        if self.alive:
            self._spawn_timer -= dt
            if self._spawn_timer <= 0:
                new_zombies = self._spawn_minion()
                self._spawn_timer = _SPAWN_COOLDOWNS[self.phase - 1]

        return bullets, new_zombies

    def _spawn_minion(self) -> list:
        from entities.zombie import Zombie
        angle = random.uniform(0, math.tau)
        sx = self.pos.x + math.cos(angle) * 90
        sy = self.pos.y + math.sin(angle) * 90
        ztype = ["basic", "fast", "tank"][self.phase - 1]
        z = Zombie(int(sx // TILE_SIZE), int(sy // TILE_SIZE), ztype)
        z._state = Zombie.CHASE
        z.pos = pygame.Vector2(sx, sy)
        z.rect.center = (int(sx), int(sy))
        return [z]

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if not self.alive:
            return
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)

        from systems.gfx import glow

        if self._hit_flash > 0:
            body_color = (255, 255, 255)
            glow_color = (220, 255, 220)
        elif self.phase == 3:
            body_color = _NECRO_C3
            glow_color = _NECRO_GL3
        elif self.phase == 2:
            body_color = _NECRO_C2
            glow_color = _NECRO_GL2
        else:
            body_color = _NECRO_C1
            glow_color = _NECRO_GL1

        pulse = 0.5 + 0.5 * math.sin(self._anim * 2.5)
        glow(surface, cx, cy, int(38 + pulse * 12), glow_color, int(60 + pulse * 50))

        radius = _SIZE // 2
        pts = _pent_points(cx, cy, radius)
        pygame.draw.polygon(surface, body_color, pts)
        outline_color = glow_color if not self._hit_flash else (200, 255, 200)
        pygame.draw.polygon(surface, outline_color, pts, 3)

        # Orbiting bone fragments
        bone_count = self.phase + 1
        bone_speed = 1.4 + self.phase * 0.6
        for i in range(bone_count):
            ba = self._anim * bone_speed + i * (math.tau / bone_count)
            bx = int(cx + math.cos(ba) * (radius + 10))
            by = int(cy + math.sin(ba) * (radius + 10))
            pygame.draw.circle(surface, (220, 220, 200), (bx, by), 4)
            pygame.draw.circle(surface, (150, 150, 120), (bx, by), 4, 1)

        # Skull eye sockets
        eye_offset = 7
        for ex_off in (-eye_offset, eye_offset):
            ex = cx + ex_off
            ey = cy - 4
            pygame.draw.circle(surface, (0, 0, 0), (ex, ey), 5)
            pygame.draw.circle(surface, glow_color, (ex, ey), 3)

        self._draw_hp_bar(surface, cx, cy)
