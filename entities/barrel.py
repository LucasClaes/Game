import random
import pygame
from core.settings import TILE_SIZE


class Barrel:
    SIZE = 20

    def __init__(self, tile_x: int, tile_y: int):
        cx = tile_x * TILE_SIZE + TILE_SIZE // 2
        cy = tile_y * TILE_SIZE + TILE_SIZE // 2
        self.rect = pygame.Rect(cx - self.SIZE // 2, cy - self.SIZE // 2, self.SIZE, self.SIZE)
        self.alive = True

    def hit(self) -> int:
        self.alive = False
        return random.randint(2, 5)

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if not self.alive:
            return
        dr = self.rect.move(-int(offset.x), -int(offset.y))
        pygame.draw.rect(surface, (110, 65, 25), dr, border_radius=4)
        pygame.draw.rect(surface, (160, 100, 45), dr, 2, border_radius=4)
        # hoop lines
        hoop_y1 = dr.y + 5
        hoop_y2 = dr.bottom - 5
        pygame.draw.line(surface, (80, 45, 15), (dr.x + 2, hoop_y1), (dr.right - 2, hoop_y1), 2)
        pygame.draw.line(surface, (80, 45, 15), (dr.x + 2, hoop_y2), (dr.right - 2, hoop_y2), 2)
