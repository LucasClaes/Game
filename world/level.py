import json
import math
import os
import pygame
from core.settings import TILE_SIZE
from entities.coin import Coin
from entities.zombie import Zombie

_LEVELS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "levels.json")

# ── palette ──────────────────────────────────────────────────────────────────
_FLOOR_BASE   = (30,  32,  44)
_WALL_FACE    = (55,  58,  76)
_WALL_HI      = (82,  86, 112)
_WALL_SHADOW  = (28,  29,  40)
_OUTER_BG     = (14,  14,  22)


def _tile_shade(tx: int, ty: int) -> int:
    """Deterministic per-tile brightness variation ±7."""
    return ((tx * 7 + ty * 13 + (tx ^ ty) * 3) % 15) - 7


def _draw_wall(surf: pygame.Surface, wall: pygame.Rect):
    pygame.draw.rect(surf, _WALL_FACE, wall)
    # Horizontal mortar lines every 8 px
    y = wall.y + 7
    while y < wall.bottom - 1:
        pygame.draw.line(surf, _WALL_SHADOW, (wall.x + 1, y), (wall.right - 1, y), 1)
        y += 8
    # Top-left highlight
    pygame.draw.line(surf, _WALL_HI, wall.topleft, (wall.right - 1, wall.top), 2)
    pygame.draw.line(surf, _WALL_HI, wall.topleft, (wall.left, wall.bottom - 1), 2)
    # Bottom-right shadow
    pygame.draw.line(surf, _WALL_SHADOW,
                     (wall.left, wall.bottom - 1), (wall.right - 1, wall.bottom - 1), 2)
    pygame.draw.line(surf, _WALL_SHADOW,
                     (wall.right - 1, wall.top), (wall.right - 1, wall.bottom - 1), 2)


# ── Level ─────────────────────────────────────────────────────────────────────
class Level:
    def __init__(self):
        self.number = 0
        self.name = ""
        self.background_color = (30, 30, 30)
        self.walls: list[pygame.Rect] = []
        self.coins: list[Coin] = []
        self.zombies: list[Zombie] = []
        self.player_start = (1, 1)
        self.exit_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        self.exit_requires_all_coins = True
        self.instructions: list[tuple] = []
        self.trap_rects: list[pygame.Rect] = []
        self.crate_tiles: list[tuple] = []
        self.barrel_tiles: list[tuple] = []
        self.tile_w = 30
        self.tile_h = 20
        self.tile_grid: list[list[bool]] = []
        self._bg_surf: pygame.Surface | None = None
        self._exit_anim = 0.0
        self.is_boss = False
        self.boss_spawn = None   # pixel coords tuple, set for boss levels
        self._force_open = False

    # ── geometry ──────────────────────────────────────────────────────────────
    @property
    def pixel_w(self) -> int:
        return self.tile_w * TILE_SIZE

    @property
    def pixel_h(self) -> int:
        return self.tile_h * TILE_SIZE

    @property
    def coins_remaining(self) -> int:
        return sum(1 for c in self.coins if not c.collected)

    @property
    def exit_open(self) -> bool:
        if self._force_open:
            return True
        if self.is_boss:
            return False  # boss levels only open when boss is killed
        return not self.exit_requires_all_coins or self.coins_remaining == 0

    def is_complete(self, player_rect: pygame.Rect) -> bool:
        return self.exit_open and player_rect.colliderect(self.exit_rect)

    # ── loading ───────────────────────────────────────────────────────────────
    @classmethod
    def from_json(cls, level_index: int) -> "Level":
        with open(_LEVELS_PATH) as f:
            data = json.load(f)
        return cls._from_dict(data["levels"][level_index], level_index)

    @classmethod
    def generate(cls, level_num: int, difficulty: int = 1) -> "Level":
        from world.procgen import generate as _gen
        return cls._from_dict(_gen(level_num, difficulty), level_num)

    @classmethod
    def generate_boss(cls, level_num: int) -> "Level":
        from world.procgen import generate_boss as _gen_boss
        return cls._from_dict(_gen_boss(level_num), level_num)

    @classmethod
    def _from_dict(cls, raw: dict, level_index: int = 0) -> "Level":
        level = cls()
        level.number = raw.get("id", level_index)
        level.name = raw.get("name", f"Level {level_index + 1}")
        level.background_color = tuple(raw.get("background_color", [30, 30, 30]))
        level.exit_requires_all_coins = raw.get("exit_requires_all_coins", True)
        ps = raw["player_start"]
        level.player_start = (ps[0], ps[1])

        for w in raw.get("walls", []):
            level.walls.append(pygame.Rect(
                w[0] * TILE_SIZE, w[1] * TILE_SIZE,
                w[2] * TILE_SIZE, w[3] * TILE_SIZE,
            ))

        if level.walls:
            level.tile_w = max(r.right  for r in level.walls) // TILE_SIZE
            level.tile_h = max(r.bottom for r in level.walls) // TILE_SIZE

        for c in raw.get("coins", []):
            level.coins.append(Coin(c[0], c[1]))
        for z in raw.get("zombies", []):
            tile = z["tile"]
            level.zombies.append(Zombie(tile[0], tile[1], z.get("type", "basic"),
                                        elite=z.get("elite", False)))

        for t in raw.get("traps", []):
            level.trap_rects.append(pygame.Rect(
                t[0] * TILE_SIZE, t[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE
            ))

        level.crate_tiles = [(c[0], c[1]) for c in raw.get("crates", [])]
        level.barrel_tiles = [(b[0], b[1]) for b in raw.get("barrels", [])]

        ex = raw["exit"]
        level.exit_rect = pygame.Rect(ex[0] * TILE_SIZE, ex[1] * TILE_SIZE,
                                      TILE_SIZE, TILE_SIZE)
        for inst in raw.get("instructions", []):
            tile = inst["tile"]
            level.instructions.append(
                (inst["text"], tile[0] * TILE_SIZE, tile[1] * TILE_SIZE))

        level.is_boss = raw.get("is_boss_level", False)
        if "boss_spawn" in raw:
            bs = raw["boss_spawn"]
            level.boss_spawn = (
                bs[0] * TILE_SIZE + TILE_SIZE // 2,
                bs[1] * TILE_SIZE + TILE_SIZE // 2,
            )

        level.tile_grid = level._build_tile_grid()
        level._bg_surf = level._build_bg_surface()
        return level

    @classmethod
    def level_count(cls) -> int:
        with open(_LEVELS_PATH) as f:
            return len(json.load(f)["levels"])

    # ── tile grid for pathfinding ──────────────────────────────────────────────
    def _build_tile_grid(self) -> list:
        grid = [[True] * self.tile_w for _ in range(self.tile_h)]
        for wall in self.walls:
            tx1 = wall.x // TILE_SIZE
            ty1 = wall.y // TILE_SIZE
            tx2 = wall.right  // TILE_SIZE
            ty2 = wall.bottom // TILE_SIZE
            for ty in range(ty1, ty2):
                for tx in range(tx1, tx2):
                    if 0 <= ty < self.tile_h and 0 <= tx < self.tile_w:
                        grid[ty][tx] = False
        return grid

    # ── pre-rendered background texture ───────────────────────────────────────
    def _build_bg_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.pixel_w, self.pixel_h))
        surf.fill(_OUTER_BG)

        # Floor tiles
        for ty in range(self.tile_h):
            for tx in range(self.tile_w):
                v = _tile_shade(tx, ty)
                r = _FLOOR_BASE[0] + v
                g = _FLOOR_BASE[1] + v
                b = _FLOOR_BASE[2] + v + 4
                tile_r = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(surf, (r, g, b), tile_r)
                # Subtle grid lines
                pygame.draw.rect(surf, (r - 5, g - 5, b - 3), tile_r, 1)

        # Walls on top
        for wall in self.walls:
            _draw_wall(surf, wall)

        return surf

    # ── per-frame update ──────────────────────────────────────────────────────
    def update(self, dt: float):
        self._exit_anim += dt
        for c in self.coins:
            c.update(dt)
        self.zombies = [z for z in self.zombies if z.alive]

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, offset: pygame.Vector2,
             font: pygame.font.Font):
        # Background texture (single blit)
        if self._bg_surf:
            surface.blit(self._bg_surf, (-offset.x, -offset.y))
        else:
            surface.fill(self.background_color)

        # Coins
        for coin in self.coins:
            coin.draw(surface, offset)

        # Exit portal
        self._draw_exit(surface, offset)

        # Instructions
        for text, px, py in self.instructions:
            surf = font.render(text, True, (190, 190, 210))
            surface.blit(surf, (px - offset.x, py - offset.y))

    def _draw_exit(self, surface: pygame.Surface, offset: pygame.Vector2):
        ex = self.exit_rect
        cx = int(ex.centerx - offset.x)
        cy = int(ex.centery - offset.y)
        t  = self._exit_anim

        from systems.gfx import glow

        if self.exit_open:
            pulse = 0.5 + 0.5 * math.sin(t * 3.5)
            glow(surface, cx, cy, int(22 + pulse * 8), (50, 220, 100), int(80 + pulse * 60))
            pygame.draw.circle(surface, (50, 200, 90), (cx, cy), int(13 + pulse * 2))
            pygame.draw.circle(surface, (130, 255, 160), (cx, cy),
                               int(13 + pulse * 2), 2)
            # Rotating triangle markers
            for i in range(3):
                angle = t * 90 + i * 120
                rad = math.radians(angle)
                mx_ = cx + int(math.cos(rad) * 20)
                my_ = cy + int(math.sin(rad) * 20)
                pygame.draw.circle(surface, (160, 255, 190), (mx_, my_), 3)
        else:
            flash = abs(math.sin(t * 1.8))
            c = int(35 + flash * 20)
            draw_r = ex.move(-offset.x, -offset.y)
            pygame.draw.rect(surface, (c, c + 18, c), draw_r, border_radius=4)
            pygame.draw.rect(surface, (60, 90, 60), draw_r, 1, border_radius=4)
            # Lock icon (two small rects)
            lx, ly = draw_r.centerx, draw_r.centery
            pygame.draw.rect(surface, (100, 130, 100),
                             (lx - 5, ly - 2, 10, 8), border_radius=1)
            pygame.draw.arc(surface, (100, 130, 100),
                            (lx - 4, ly - 8, 8, 9), 0, math.pi, 2)
