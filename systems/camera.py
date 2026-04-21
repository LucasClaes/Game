import pygame
from core.settings import SCREEN_W, SCREEN_H


class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

    def update(self, player_pos: pygame.Vector2, level_w: int, level_h: int):
        target_x = player_pos.x - SCREEN_W / 2
        target_y = player_pos.y - SCREEN_H / 2
        self.offset.x = max(0, min(target_x, level_w - SCREEN_W))
        self.offset.y = max(0, min(target_y, level_h - SCREEN_H))

    def apply(self, pos) -> tuple:
        return (pos[0] - self.offset.x, pos[1] - self.offset.y)

    def apply_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-self.offset.x, -self.offset.y)
