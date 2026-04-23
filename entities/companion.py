import math
import pygame
from entities.bullet import Bullet

_ORBIT_RADIUS  = 52
_ATTACK_RANGE  = 180
_FIRE_RATE     = 1.2
_BULLET_DAMAGE = 20
_BULLET_SPEED  = 380
_ORBIT_SPEED   = 1.6   # radians per second


class Companion:
    SIZE = 12

    def __init__(self, player, index: int = 0):
        self._player = player
        self.angle   = index * math.pi   # offset companions so they start opposite
        self._shoot_timer = index * 0.6  # stagger fire times
        self.pos = pygame.Vector2(player.pos)

    def update(self, targets: list, dt: float) -> list:
        self.angle += _ORBIT_SPEED * dt
        self.pos = self._player.pos + pygame.Vector2(
            math.cos(self.angle), math.sin(self.angle)
        ) * _ORBIT_RADIUS

        self._shoot_timer = max(0.0, self._shoot_timer - dt)
        if self._shoot_timer > 0:
            return []

        # Find nearest live target in range
        best = None
        best_dist = _ATTACK_RANGE
        for t in targets:
            if not getattr(t, "alive", True):
                continue
            d = (t.pos - self.pos).length()
            if d < best_dist:
                best_dist = d
                best = t

        if best is None:
            return []

        self._shoot_timer = _FIRE_RATE
        direction = (best.pos - self.pos).normalize()
        return [Bullet(self.pos, direction * _BULLET_SPEED, _BULLET_DAMAGE)]

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)
        half = self.SIZE // 2
        rect = pygame.Rect(cx - half, cy - half, self.SIZE, self.SIZE)
        from systems.gfx import glow
        glow(surface, cx, cy, 18, (0, 200, 220), 70)
        pygame.draw.rect(surface, (0, 210, 230), rect, border_radius=3)
        pygame.draw.rect(surface, (150, 255, 255), rect, 1, border_radius=3)
        # Direction dot
        tip_x = int(cx + math.cos(self.angle) * 7)
        tip_y = int(cy + math.sin(self.angle) * 7)
        pygame.draw.circle(surface, (255, 255, 255), (tip_x, tip_y), 2)
