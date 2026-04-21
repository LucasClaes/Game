import math
import pygame
from core.settings import TILE_SIZE


class Coin:
    RADIUS = 8

    def __init__(self, tile_x: int, tile_y: int):
        cx = tile_x * TILE_SIZE + TILE_SIZE // 2
        cy = tile_y * TILE_SIZE + TILE_SIZE // 2
        self.pos = pygame.Vector2(cx, cy)
        self.rect = pygame.Rect(cx - self.RADIUS, cy - self.RADIUS,
                                self.RADIUS * 2, self.RADIUS * 2)
        self.collected = False
        self._anim = 0.0

    def update(self, dt: float):
        self._anim += dt

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if self.collected:
            return
        bob  = math.sin(self._anim * 4.0) * 2.5
        spin = math.cos(self._anim * 2.5)   # -1..1 → coin spinning
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y + bob)

        pulse = 0.5 + 0.5 * math.sin(self._anim * 3.5)

        from systems.gfx import glow
        glow(surface, cx, cy, int(13 + pulse * 5), (255, 210, 0), int(55 + pulse * 45))

        # Coin body — width varies with spin to simulate a 3-D rotation
        w = max(2, int(self.RADIUS * abs(spin)))
        body_color   = (255, 210, 0)
        shine_color  = (255, 240, 120)
        shadow_color = (180, 140, 0)

        pygame.draw.ellipse(surface, body_color,
                            (cx - w, cy - self.RADIUS, w * 2, self.RADIUS * 2))
        # Highlight stripe
        if w > 3:
            hl_w = max(1, w // 3)
            pygame.draw.ellipse(surface, shine_color,
                                (cx - hl_w, cy - self.RADIUS + 1, hl_w * 2, self.RADIUS - 2))
        # Rim
        pygame.draw.ellipse(surface, shadow_color,
                            (cx - w, cy - self.RADIUS, w * 2, self.RADIUS * 2), 1)
