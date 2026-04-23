import math
import pygame
from core.settings import TILE_SIZE
from entities.enemy_bullet import EnemyBullet

_BULLET_SPEED  = 220
_BULLET_DAMAGE = 2
_SIZE          = 56
_INV_WINDOW    = 0.14
_CHARGE_SPEED  = 210
_CHARGE_DURATION = 0.45

_COLOR_P1 = (130, 50,  200)
_COLOR_P2 = (210, 100, 30)
_COLOR_P3 = (220, 40,  40)
_GLOW_P1  = (160, 80,  240)
_GLOW_P2  = (240, 140, 60)
_GLOW_P3  = (255, 70,  50)


def _hex_points(cx, cy, radius):
    return [
        (int(cx + math.cos(math.radians(a)) * radius),
         int(cy + math.sin(math.radians(a)) * radius))
        for a in range(0, 360, 60)
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
        self._shoot_timer  = 1.0   # initial delay before first shot
        self._anim         = 0.0
        self._charge_timer = 0.0
        self._charging     = False
        self._hit_flash    = 0.0

    @property
    def phase(self) -> int:
        ratio = self.hp / self.max_hp
        if ratio > 0.60:
            return 1
        if ratio > 0.30:
            return 2
        return 3

    def update(self, dt: float, player_pos: pygame.Vector2,
               walls: list, level_w: int, level_h: int) -> list:
        if not self.alive:
            return []

        self._inv_timer   = max(0.0, self._inv_timer - dt)
        self._hit_flash   = max(0.0, self._hit_flash - dt)
        self._shoot_timer = max(0.0, self._shoot_timer - dt)
        self._anim       += dt

        # Charge logic (phase 2+)
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
            if self.phase == 1:
                self._shoot_timer = 1.8
            elif self.phase == 2:
                self._shoot_timer = 1.2
            else:
                self._shoot_timer = 0.8

        return new_bullets

    def _shoot(self, player_pos: pygame.Vector2) -> list:
        dx = player_pos.x - self.pos.x
        dy = player_pos.y - self.pos.y
        base_angle = math.atan2(dy, dx)

        if self.phase == 1:
            spreads = [0]
        elif self.phase == 2:
            spreads = [-20, 0, 20]
        else:
            spreads = [-40, -20, 0, 20, 40]

        bullets = []
        for deg in spreads:
            angle = base_angle + math.radians(deg)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * _BULLET_SPEED
            bullets.append(EnemyBullet(self.pos, vel, _BULLET_DAMAGE))
        return bullets

    def _move_toward(self, target: pygame.Vector2, speed: float, dt: float, walls: list):
        diff = target - self.pos
        if diff.length() < 2:
            return
        move = diff.normalize() * speed * dt
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

        # Phase indicator ring
        if self.phase >= 2:
            inner_r = int(radius * 0.55)
            pygame.draw.circle(surface, _COLOR_P3 if self.phase == 3 else _COLOR_P2,
                               (cx, cy), inner_r, 2)

        # Eye
        eye_angle = self._anim * 1.2
        ex = int(cx + math.cos(eye_angle) * 8)
        ey = int(cy + math.sin(eye_angle) * 8)
        pygame.draw.circle(surface, (255, 60, 30), (ex, ey), 6)
        pygame.draw.circle(surface, (255, 220, 200), (ex, ey), 3)

        # HP bar (above sprite)
        bar_w = 80
        bar_h = 6
        bx = cx - bar_w // 2
        by = cy - radius - 14
        pygame.draw.rect(surface, (40, 10, 10), (bx, by, bar_w, bar_h), border_radius=3)
        hp_ratio = max(0.0, self.hp / self.max_hp)
        bar_color = (200, 50, 50) if hp_ratio > 0.3 else (255, 200, 0)
        pygame.draw.rect(surface, bar_color,
                         (bx, by, int(bar_w * hp_ratio), bar_h), border_radius=3)
        pygame.draw.rect(surface, (200, 150, 200), (bx, by, bar_w, bar_h), 1, border_radius=3)
