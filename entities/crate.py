import math
import pygame
from core.settings import TILE_SIZE


class LootCrate:
    BOB_SPEED = 2.0

    def __init__(self, tile_x: int, tile_y: int):
        cx = tile_x * TILE_SIZE + TILE_SIZE // 2
        cy = tile_y * TILE_SIZE + TILE_SIZE // 2
        self.rect = pygame.Rect(cx - 12, cy - 12, 24, 24)
        self.alive = True
        self._t = 0.0

    @classmethod
    def from_pixel(cls, px: float, py: float) -> "LootCrate":
        c = cls.__new__(cls)
        c.rect = pygame.Rect(int(px) - 12, int(py) - 12, 24, 24)
        c.alive = True
        c._t = 0.0
        return c

    def update(self, dt: float):
        self._t += dt

    def check_pickup(self, player_rect: pygame.Rect) -> bool:
        return self.alive and self.rect.colliderect(player_rect.inflate(8, 8))

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if not self.alive:
            return
        pulse = int(abs(math.sin(self._t * self.BOB_SPEED * math.pi)) * 55)
        color = (180 + pulse, 130 + pulse // 2, 10)
        pos = self.rect.move(-int(offset.x), -int(offset.y))
        pygame.draw.rect(surface, color, pos, border_radius=4)
        pygame.draw.rect(surface, (255, 220, 80), pos, 2, border_radius=4)
        # lid line
        lid_y = pos.y + 8
        pygame.draw.line(surface, (255, 220, 80), (pos.x + 3, lid_y), (pos.right - 3, lid_y), 1)
        # glow
        from systems.gfx import glow
        glow(surface, pos.centerx, pos.centery, 18, (255, 200, 50), 50 + pulse)
