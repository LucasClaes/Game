import math
import pygame
from core.settings import TILE_SIZE, WHITE, ZOMBIE_TYPES, AGGRO_RADIUS

_PATH_INTERVAL = 0.45  # seconds between BFS recalculations

# Visual style per zombie type
_STYLE = {
    "basic":    {"color": (220, 60,  60),  "glow": (255, 80,  80),  "glow_r": 20, "shape": "rect"},
    "fast":     {"color": (255, 140, 30),  "glow": (255, 170, 60),  "glow_r": 17, "shape": "diamond"},
    "tank":     {"color": (160, 60,  220), "glow": (190, 90,  255), "glow_r": 26, "shape": "circle"},
    "ranged":   {"color": (180, 80,  200), "glow": (200, 110, 255), "glow_r": 18, "shape": "diamond"},
    "exploder": {"color": (60,  220, 80),  "glow": (80,  255, 100), "glow_r": 18, "shape": "circle"},
    "healer":   {"color": (200, 100, 220), "glow": (220, 130, 255), "glow_r": 20, "shape": "cross"},
    "lurker":   {"color": (0,   180, 180), "glow": (0,   220, 220), "glow_r": 16, "shape": "diamond"},
}


class Zombie:
    SIZE  = 28
    IDLE  = 0
    CHASE = 1

    def __init__(self, tile_x: int, tile_y: int, zombie_type: str = "basic", elite: bool = False):
        stats = ZOMBIE_TYPES.get(zombie_type, ZOMBIE_TYPES["basic"])
        self.pos = pygame.Vector2(
            tile_x * TILE_SIZE + TILE_SIZE // 2,
            tile_y * TILE_SIZE + TILE_SIZE // 2,
        )
        self.speed = float(stats["speed"])
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]
        self.damage = stats["damage"]
        self.coin_drop = stats["coin_drop"]
        self.zombie_type = zombie_type
        self.elite = elite
        if elite:
            self.hp = self.hp * 2
            self.max_hp = self.hp
            self.speed *= 1.3
            self.coin_drop = 3
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.alive = True
        self._state = Zombie.IDLE
        self._hit_flash = 0.0
        self._invincible = 0.0
        self._path: list = []
        self._path_timer: float = 0.0
        self._anim = 0.0
        self._shoot_range = stats.get("shoot_range", 0)
        self._shoot_cooldown = stats.get("shoot_cooldown", 2.0)
        self._shoot_timer = self._shoot_cooldown

        # Exploder
        self.death_data = {}  # populated on death for exploder

        # Healer
        self._heal_radius   = stats.get("heal_radius",   0)
        self._heal_amount   = stats.get("heal_amount",   0)
        self._heal_interval = stats.get("heal_interval", 2.0)
        self._heal_timer    = 0.0
        self._healing_flash = 0.0  # green flash when healing fires

        # Lurker
        self._lurk_aggro = stats.get("lurk_aggro", AGGRO_RADIUS)
        self._hidden = zombie_type == "lurker"

    def update(self, dt: float, player_pos: pygame.Vector2,
               walls: list, tile_grid=None, tile_w: int = 30, tile_h: int = 20,
               zombies: list = None) -> list:
        if not self.alive:
            return []
        self._hit_flash = max(0.0, self._hit_flash - dt)
        self._invincible = max(0.0, self._invincible - dt)
        self._anim += dt
        self._depenetrate(walls)

        # Aggro detection: switch to CHASE when player is close enough
        aggro_dist = self._lurk_aggro if self.zombie_type == "lurker" else AGGRO_RADIUS
        if self._state == Zombie.IDLE:
            if (player_pos - self.pos).length() <= aggro_dist:
                self._state = Zombie.CHASE
                self._hidden = False  # lurker reveals itself on aggro

        if self._state == Zombie.IDLE:
            return []

        # Ranged zombie: stop and shoot when in range
        if self.zombie_type == "ranged" and self._shoot_range > 0:
            dist = (player_pos - self.pos).length()
            if dist <= self._shoot_range:
                self._shoot_timer -= dt
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                if self._shoot_timer <= 0:
                    self._shoot_timer = self._shoot_cooldown
                    direction = (player_pos - self.pos).normalize()
                    from entities.enemy_bullet import EnemyBullet
                    return [EnemyBullet(self.pos, direction * 200, 1)]
                return []

        self._path_timer -= dt
        if tile_grid is not None and (self._path_timer <= 0 or not self._path):
            self._path_timer = _PATH_INTERVAL
            start = (int(self.pos.x // TILE_SIZE), int(self.pos.y // TILE_SIZE))
            goal  = (int(player_pos.x // TILE_SIZE), int(player_pos.y // TILE_SIZE))
            from systems.pathfinding import bfs_path
            self._path = bfs_path(tile_grid, tile_w, tile_h, start, goal)

        # Follow next waypoint or fall back to direct chase
        if self._path:
            tx, ty = self._path[0]
            target = pygame.Vector2(tx * TILE_SIZE + TILE_SIZE // 2,
                                    ty * TILE_SIZE + TILE_SIZE // 2)
            if (target - self.pos).length() < TILE_SIZE * 0.55:
                self._path.pop(0)
            else:
                self._move_toward(target, dt, walls)
        else:
            self._move_toward(player_pos, dt, walls)

        self.rect.center = (int(self.pos.x), int(self.pos.y))

        # Healer: periodically restore HP to nearby zombies
        if self.zombie_type == "healer" and self._heal_radius > 0:
            self._heal_timer -= dt
            self._healing_flash = max(0.0, self._healing_flash - dt)
            if self._heal_timer <= 0 and zombies is not None:
                self._heal_timer = self._heal_interval
                for z in zombies:
                    if z is not self and z.alive:
                        if (z.pos - self.pos).length() <= self._heal_radius:
                            z.hp = min(z.max_hp, z.hp + self._heal_amount)
                            z._hit_flash = 0.0
                            self._healing_flash = 0.3

        return []

    def _depenetrate(self, walls: list):
        for wall in walls:
            if not self.rect.colliderect(wall):
                continue
            ox_left  = self.rect.right  - wall.left
            ox_right = wall.right  - self.rect.left
            oy_top   = self.rect.bottom - wall.top
            oy_bot   = wall.bottom - self.rect.top
            min_push = min(ox_left, ox_right, oy_top, oy_bot)
            if min_push <= 0:
                continue
            if min_push == ox_left:
                self.pos.x -= ox_left
            elif min_push == ox_right:
                self.pos.x += ox_right
            elif min_push == oy_top:
                self.pos.y -= oy_top
            else:
                self.pos.y += oy_bot
            self.rect.center = (int(self.pos.x), int(self.pos.y))

    def _move_toward(self, target: pygame.Vector2, dt: float, walls: list):
        diff = target - self.pos
        if diff.length() < 1:
            return
        move = diff.normalize() * self.speed * dt

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
        if self._invincible > 0:
            return False
        self._state = Zombie.CHASE  # always aggro when hit
        self.hp -= amount
        self._hit_flash = 0.12
        self._invincible = 0.14
        if self.hp <= 0:
            self.alive = False
            if self.zombie_type == "exploder":
                self.death_data = {
                    "explode": True,
                    "pos": self.pos.copy(),
                    "radius": 80,
                    "damage": 50,
                }
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if not self.alive:
            return
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)
        style = _STYLE.get(self.zombie_type, _STYLE["basic"])
        body_color = WHITE if self._hit_flash > 0 else style["color"]

        from systems.gfx import glow
        if self.zombie_type == "exploder":
            danger  = 1.0 - (self.hp / self.max_hp)
            pulse_r = int(style["glow_r"] + danger * 14 + math.sin(self._anim * 6) * 4)
            glow(surface, cx, cy, pulse_r, style["glow"], int(65 + danger * 80))
        else:
            glow(surface, cx, cy, style["glow_r"], style["glow"], 65)

        shape = style["shape"]
        half = self.SIZE // 2

        # Lurker: draw faint ghost outline only while hidden
        if self.zombie_type == "lurker" and self._hidden:
            s = pygame.Surface((self.SIZE * 3, self.SIZE * 3), pygame.SRCALPHA)
            sp = [(self.SIZE * 3 // 2,          self.SIZE * 3 // 2 - half),
                  (self.SIZE * 3 // 2 + half,   self.SIZE * 3 // 2),
                  (self.SIZE * 3 // 2,          self.SIZE * 3 // 2 + half),
                  (self.SIZE * 3 // 2 - half,   self.SIZE * 3 // 2)]
            pygame.draw.polygon(s, (0, 220, 220, 40), sp)
            surface.blit(s, (cx - self.SIZE * 3 // 2, cy - self.SIZE * 3 // 2))
            return  # skip rest of draw for hidden lurker

        if shape == "circle":
            pygame.draw.circle(surface, body_color, (cx, cy), half)
            pygame.draw.circle(surface, (220, 180, 255), (cx, cy), half, 2)
        elif shape == "diamond":
            pts = [(cx, cy - half), (cx + half, cy),
                   (cx, cy + half), (cx - half, cy)]
            pygame.draw.polygon(surface, body_color, pts)
            pygame.draw.polygon(surface, (255, 200, 100), pts, 2)
        elif shape == "cross":
            bar_thickness = 8
            color_to_use = (100, 255, 100) if self._healing_flash > 0 else body_color
            pygame.draw.rect(surface, color_to_use,
                             (cx - half, cy - bar_thickness // 2, self.SIZE, bar_thickness))
            pygame.draw.rect(surface, color_to_use,
                             (cx - bar_thickness // 2, cy - half, bar_thickness, self.SIZE))
            pygame.draw.rect(surface, (220, 150, 255),
                             (cx - half, cy - bar_thickness // 2, self.SIZE, bar_thickness), 1)
            pygame.draw.rect(surface, (220, 150, 255),
                             (cx - bar_thickness // 2, cy - half, bar_thickness, self.SIZE), 1)
        else:
            draw_rect = self.rect.move(-offset.x, -offset.y)
            pygame.draw.rect(surface, body_color, draw_rect, border_radius=5)
            pygame.draw.rect(surface, (255, 130, 130), draw_rect, 2, border_radius=5)
            # eye dots
            ex = int(cx + math.cos(self._anim * 0.5) * 3)
            pygame.draw.circle(surface, (255, 230, 230), (cx - 5, cy - 4), 3)
            pygame.draw.circle(surface, (255, 230, 230), (cx + 5, cy - 4), 3)
            pygame.draw.circle(surface, (60, 0, 0), (cx - 5, cy - 4), 1)
            pygame.draw.circle(surface, (60, 0, 0), (cx + 5, cy - 4), 1)

        # Elite outline
        if self.elite:
            elite_r = pygame.Rect(cx - half - 3, cy - half - 3, self.SIZE + 6, self.SIZE + 6)
            pygame.draw.rect(surface, (255, 220, 0), elite_r, 2, border_radius=7)

        # HP bar
        bar_w = self.SIZE + 4
        bar_h = 4
        bx = cx - bar_w // 2
        by = cy - half - 9
        pygame.draw.rect(surface, (30, 10, 10), (bx, by, bar_w, bar_h), border_radius=2)
        hp_ratio = max(0, self.hp / self.max_hp)
        bar_color = (200, 60, 60) if hp_ratio > 0.4 else (255, 200, 0)
        pygame.draw.rect(surface, bar_color,
                         (bx, by, int(bar_w * hp_ratio), bar_h), border_radius=2)
