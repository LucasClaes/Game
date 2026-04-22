import pygame
from core.settings import SCREEN_W, MINIMAP_SIZE, TILE_SIZE


class Minimap:
    _WALL_COLOR   = (80,  80, 100)
    _FLOOR_COLOR  = (25,  25,  40)
    _COIN_COLOR   = (255, 220,   0)
    _EXIT_COLOR   = (50,  200,  80)
    _ZOMBIE_COLOR = (220,  60,  60)
    _PLAYER_COLOR = (255, 255, 255)
    _BORDER_COLOR = (100, 100, 130)

    def __init__(self):
        self._cached_id = None
        self._bg_surf: pygame.Surface | None = None

    def draw(self, surface: pygame.Surface, level, player, zombies):
        scale_x = MINIMAP_SIZE / level.tile_w
        scale_y = MINIMAP_SIZE / level.tile_h
        ox = SCREEN_W - MINIMAP_SIZE - 12
        oy = 40

        if self._cached_id != id(level):
            self._bg_surf = self._build_bg(level, scale_x, scale_y)
            self._cached_id = id(level)
        surface.blit(self._bg_surf, (ox, oy))

        dot = max(2, int(min(scale_x, scale_y) * 0.8))
        sdot = max(1, int(min(scale_x, scale_y) * 0.5))

        # Exit
        ex = int(level.exit_rect.centerx / TILE_SIZE * scale_x + ox)
        ey = int(level.exit_rect.centery / TILE_SIZE * scale_y + oy)
        pygame.draw.rect(surface, self._EXIT_COLOR, (ex - dot, ey - dot, dot * 2, dot * 2))

        # Coins
        for coin in level.coins:
            if not coin.collected:
                cx = int(coin.rect.centerx / TILE_SIZE * scale_x + ox)
                cy = int(coin.rect.centery / TILE_SIZE * scale_y + oy)
                pygame.draw.circle(surface, self._COIN_COLOR, (cx, cy), sdot)

        # Zombies
        for z in zombies:
            if z.alive:
                zx = int(z.pos.x / TILE_SIZE * scale_x + ox)
                zy = int(z.pos.y / TILE_SIZE * scale_y + oy)
                pygame.draw.circle(surface, self._ZOMBIE_COLOR, (zx, zy), sdot)

        # Player
        px = int(player.pos.x / TILE_SIZE * scale_x + ox)
        py = int(player.pos.y / TILE_SIZE * scale_y + oy)
        pygame.draw.circle(surface, self._PLAYER_COLOR, (px, py), dot)

        pygame.draw.rect(surface, self._BORDER_COLOR,
                         (ox, oy, MINIMAP_SIZE, MINIMAP_SIZE), 1)

    def _build_bg(self, level, scale_x, scale_y) -> pygame.Surface:
        surf = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE))
        surf.fill(self._FLOOR_COLOR)
        for ty in range(level.tile_h):
            for tx in range(level.tile_w):
                if not level.tile_grid[ty][tx]:
                    mx = int(tx * scale_x)
                    my = int(ty * scale_y)
                    mw = max(1, int(scale_x))
                    mh = max(1, int(scale_y))
                    pygame.draw.rect(surf, self._WALL_COLOR, (mx, my, mw, mh))
        return surf
