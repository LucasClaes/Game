import random
import pygame
from core.settings import SCREEN_W, SCREEN_H


class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)
        self._shake_timer = 0.0
        self._shake_intensity = 0.0

    def shake(self, duration: float, intensity: float):
        # Only upgrade — don't downgrade a stronger ongoing shake
        if intensity >= self._shake_intensity or self._shake_timer <= 0:
            self._shake_timer = duration
            self._shake_intensity = intensity

    def update(self, player_pos: pygame.Vector2, level_w: int, level_h: int, dt: float = 0.0):
        target_x = player_pos.x - SCREEN_W / 2
        target_y = player_pos.y - SCREEN_H / 2
        self.offset.x = max(0, min(target_x, level_w - SCREEN_W))
        self.offset.y = max(0, min(target_y, level_h - SCREEN_H))

        if self._shake_timer > 0:
            self._shake_timer = max(0.0, self._shake_timer - dt)
            sx = random.uniform(-self._shake_intensity, self._shake_intensity)
            sy = random.uniform(-self._shake_intensity, self._shake_intensity)
            self.offset.x += sx
            self.offset.y += sy

    def apply(self, pos) -> tuple:
        return (pos[0] - self.offset.x, pos[1] - self.offset.y)

    def apply_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-self.offset.x, -self.offset.y)
