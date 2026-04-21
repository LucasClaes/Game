import math
import pygame
from core.settings import (
    TILE_SIZE, PLAYER_SPEED_BASE, PLAYER_HP_BASE, PLAYER_LIVES_BASE,
    MELEE_RANGE, MELEE_HITBOX_SIZE, MELEE_DURATION, MELEE_COOLDOWN_BASE,
    BULLET_SPEED, SHOOT_COOLDOWN_BASE, BULLET_DAMAGE_BASE, MELEE_DAMAGE_BASE,
    WHITE, YELLOW, CYAN,
)
from entities.bullet import Bullet

_PLAYER_COLOR   = (74,  144, 226)
_PLAYER_RING    = (160, 210, 255)
_PLAYER_RADIUS  = 13


class Player:
    SIZE = 26

    def __init__(self, tile_x: int, tile_y: int, upgrades: dict):
        self.pos = pygame.Vector2(
            tile_x * TILE_SIZE + TILE_SIZE // 2,
            tile_y * TILE_SIZE + TILE_SIZE // 2,
        )
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        spd = upgrades.get("speed", 0)
        dmg = upgrades.get("damage", 0)
        fr  = upgrades.get("fire_rate", 0)
        hp  = upgrades.get("health", 0)

        self.speed = PLAYER_SPEED_BASE * (1.0 + spd * 0.10)
        self.melee_damage = int(MELEE_DAMAGE_BASE * (1.0 + dmg * 0.20))
        self.bullet_damage = int(BULLET_DAMAGE_BASE * (1.0 + dmg * 0.20))
        self.swing_cooldown = MELEE_COOLDOWN_BASE * (1.0 - min(fr * 0.15, 0.70))
        self.shoot_cooldown = SHOOT_COOLDOWN_BASE * (1.0 - min(fr * 0.20, 0.75))
        self.has_ranged = upgrades.get("ranged_unlock", 0) >= 1

        self.max_hp = PLAYER_HP_BASE
        self.hp = self.max_hp
        self.lives = PLAYER_LIVES_BASE + hp
        self.max_lives = self.lives

        self.swing_timer = 0.0
        self.swing_cooldown_timer = 0.0
        self.shoot_timer = 0.0
        self.invincible_timer = 0.0
        self.INVINCIBLE_DURATION = 1.2

        self.is_swinging = False
        self.facing = 0.0
        self._hit_this_swing: set = set()
        self._anim = 0.0

    def handle_input(self, keys, events, bullets: list, camera_offset: pygame.Vector2):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._try_swing()
                elif event.button == 3:
                    self._try_shoot(bullets)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_z):
                    self._try_swing()

        mx, my = pygame.mouse.get_pos()
        world_mx = mx + camera_offset.x
        world_my = my + camera_offset.y
        diff = pygame.Vector2(world_mx - self.pos.x, world_my - self.pos.y)
        if diff.length() > 1:
            self.facing = math.degrees(math.atan2(diff.y, diff.x))

    def _try_swing(self):
        if self.swing_cooldown_timer <= 0 and not self.is_swinging:
            self.is_swinging = True
            self.swing_timer = MELEE_DURATION
            self._hit_this_swing.clear()

    def _try_shoot(self, bullets: list):
        if not self.has_ranged or self.shoot_timer > 0:
            return
        direction = pygame.Vector2(1, 0).rotate(self.facing)
        spawn = self.pos + direction * (_PLAYER_RADIUS + 6)
        bullets.append(Bullet(spawn, direction * BULLET_SPEED, self.bullet_damage))
        self.shoot_timer = self.shoot_cooldown

    def update(self, dt: float, keys, walls: list):
        self._anim += dt
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.swing_cooldown_timer = max(0.0, self.swing_cooldown_timer - dt)
        self.shoot_timer = max(0.0, self.shoot_timer - dt)

        if self.is_swinging:
            self.swing_timer -= dt
            if self.swing_timer <= 0:
                self.is_swinging = False
                self.swing_cooldown_timer = self.swing_cooldown

        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        from systems.collision import resolve_wall_collision
        resolve_wall_collision(self.rect, walls, dx * self.speed * dt, dy * self.speed * dt)
        self.pos.x = self.rect.centerx
        self.pos.y = self.rect.centery

    def get_melee_hitbox(self) -> pygame.Rect:
        offset = pygame.Vector2(MELEE_RANGE, 0).rotate(self.facing)
        cx = self.pos.x + offset.x
        cy = self.pos.y + offset.y
        half = MELEE_HITBOX_SIZE // 2
        return pygame.Rect(cx - half, cy - half, MELEE_HITBOX_SIZE, MELEE_HITBOX_SIZE)

    def take_damage(self, amount: int) -> bool:
        if self.invincible_timer > 0:
            return False
        self.hp -= amount
        self.invincible_timer = self.INVINCIBLE_DURATION
        if self.hp <= 0:
            self.hp = 0
            return True
        return False

    def respawn(self, tile_x: int, tile_y: int):
        self.pos = pygame.Vector2(
            tile_x * TILE_SIZE + TILE_SIZE // 2,
            tile_y * TILE_SIZE + TILE_SIZE // 2,
        )
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.hp = self.max_hp
        self.invincible_timer = self.INVINCIBLE_DURATION

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if self.invincible_timer > 0 and int(self.invincible_timer * 8) % 2 == 0:
            return

        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)

        from systems.gfx import glow
        glow(surface, cx, cy, 22, _PLAYER_COLOR, 80)

        # Body
        pygame.draw.circle(surface, _PLAYER_COLOR, (cx, cy), _PLAYER_RADIUS)
        pygame.draw.circle(surface, _PLAYER_RING, (cx, cy), _PLAYER_RADIUS, 2)

        # Direction arrow
        dir_vec = pygame.Vector2(1, 0).rotate(self.facing)
        tip = (int(cx + dir_vec.x * (_PLAYER_RADIUS + 6)),
               int(cy + dir_vec.y * (_PLAYER_RADIUS + 6)))
        pygame.draw.line(surface, WHITE, (cx, cy), tip, 2)
        pygame.draw.circle(surface, WHITE, tip, 3)

        # Melee arc overlay
        if self.is_swinging:
            hb = self.get_melee_hitbox()
            hb_s = hb.move(-offset.x, -offset.y)
            arc_surf = pygame.Surface((hb_s.width, hb_s.height), pygame.SRCALPHA)
            arc_surf.fill((255, 220, 0, 80))
            surface.blit(arc_surf, hb_s.topleft)
            pygame.draw.rect(surface, YELLOW, hb_s, 2)
            glow(surface, hb_s.centerx, hb_s.centery, 26, (255, 220, 0), 60)
