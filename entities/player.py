import json
import math
import os
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

_GEAR_DEFS: dict | None = None
_CLASSES_DEFS: dict | None = None

def _load_gear_defs() -> dict:
    global _GEAR_DEFS
    if _GEAR_DEFS is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gear.json")
        with open(path) as f:
            raw = json.load(f)
        _GEAR_DEFS = {g["id"]: g for g in raw["gear"]}
    return _GEAR_DEFS

def _load_class_defs() -> dict:
    global _CLASSES_DEFS
    if _CLASSES_DEFS is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "classes.json")
        with open(path) as f:
            raw = json.load(f)
        _CLASSES_DEFS = {c["id"]: c for c in raw["classes"]}
    return _CLASSES_DEFS


class Player:
    SIZE = 26

    def __init__(self, tile_x: int, tile_y: int, upgrades: dict, player_data: dict = None):
        self.pos = pygame.Vector2(
            tile_x * TILE_SIZE + TILE_SIZE // 2,
            tile_y * TILE_SIZE + TILE_SIZE // 2,
        )
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self._float_x = float(self.rect.x)
        self._float_y = float(self.rect.y)

        spd   = upgrades.get("speed", 0)
        dmg   = upgrades.get("damage", 0)
        fr    = upgrades.get("fire_rate", 0)
        hp    = upgrades.get("health", 0)
        armor = upgrades.get("armor", 0)

        self.speed          = PLAYER_SPEED_BASE * (1.0 + spd * 0.10)
        self.melee_damage   = int(MELEE_DAMAGE_BASE * (1.0 + dmg * 0.20))
        self.bullet_damage  = int(BULLET_DAMAGE_BASE * (1.0 + dmg * 0.20))
        self.swing_cooldown = MELEE_COOLDOWN_BASE * (1.0 - min(fr * 0.15, 0.70))
        self.shoot_cooldown = SHOOT_COOLDOWN_BASE * (1.0 - min(fr * 0.20, 0.75))
        self.has_ranged     = upgrades.get("ranged_unlock", 0) >= 1
        self.companion_count = upgrades.get("companion", 0)
        self.damage_reduction = min(armor * 0.20, 0.60)

        self.dash_unlocked = upgrades.get("dash_unlock", 0) >= 1
        dash_lv = upgrades.get("dash_upgrade", 0)
        self.dash_speed = 420 + dash_lv * 60
        self.dash_duration = 0.18
        self.dash_cooldown = 2.0 - dash_lv * 0.4
        self._dash_timer = 0.0
        self._dash_cd_timer = 0.0
        self._dash_dir = pygame.Vector2(1, 0)

        pd = player_data or {}
        self.bombs   = pd.get("bombs", 0)
        self.shields = pd.get("shields", 0)
        self.shielded        = False
        self._shield_timer   = 0.0

        self.max_hp = PLAYER_HP_BASE
        self.hp = self.max_hp
        self.lives = PLAYER_LIVES_BASE + hp
        self.max_lives = self.lives

        self.bullet_pierce_count = 0
        self.execute_bonus = 0.0
        self.first_hit_immune_charges = 0
        self.hp_drain_interval = 0.0
        self.melee_range_mult      = 1.0
        self.melee_hitbox_mult     = 1.0
        self.bullet_count          = 1
        self.bullet_spread         = 0
        self.player_class          = "warrior"
        self._equipped_weapon_name = "FISTS"

        # Apply gear bonuses
        gear_defs = _load_gear_defs()
        for slot, gid in pd.get("gear", {}).items():
            piece = gear_defs.get(gid)
            if not piece:
                continue
            if slot == "weapon":
                self._equipped_weapon_name = piece.get("name", "FISTS")
            stat, val = piece["stat"], piece["value"]
            if stat == "bonus_hp":
                self.max_hp += int(val)
            elif stat == "bonus_armor":
                self.damage_reduction = min(self.damage_reduction + val, 0.60)
            elif stat == "bonus_melee":
                self.melee_damage = int(self.melee_damage * (1 + val))
            elif stat == "bonus_ranged":
                self.bullet_damage = int(self.bullet_damage * (1 + val))
            elif stat == "bonus_melee_ranged":
                self.melee_damage = int(self.melee_damage * (1 + val))
                self.bullet_damage = int(self.bullet_damage * (1 + val))
                if piece.get("hp_drain"):
                    self.hp_drain_interval = piece["hp_drain"]
            elif stat == "bonus_speed":
                self.speed *= (1 + val)
                if piece.get("bonus_dash_speed"):
                    self.dash_speed *= (1 + piece["bonus_dash_speed"])
            elif stat == "bonus_firerate":
                self.swing_cooldown *= (1 - val)
                self.shoot_cooldown *= (1 - val)
            elif stat == "bonus_dash":
                self.dash_cooldown *= (1 - val)
            elif stat == "first_hit_immune":
                self.first_hit_immune_charges += int(val)
            elif stat == "execute_bonus":
                self.execute_bonus = val
            if piece.get("melee_range_mult"):    self.melee_range_mult   = piece["melee_range_mult"]
            if piece.get("melee_hitbox_mult"):   self.melee_hitbox_mult  = piece["melee_hitbox_mult"]
            if piece.get("swing_cooldown_mult"): self.swing_cooldown    *= piece["swing_cooldown_mult"]
            if piece.get("bullet_count"):        self.bullet_count       = piece["bullet_count"]
            if piece.get("bullet_spread"):       self.bullet_spread      = piece["bullet_spread"]
            if piece.get("shoot_cooldown_mult"): self.shoot_cooldown    *= piece["shoot_cooldown_mult"]
            if piece.get("bullet_pierce_bonus"): self.bullet_pierce_count += piece["bullet_pierce_bonus"]
        self.hp = self.max_hp

        # Apply run perk stat bonuses
        run_perks = pd.get("run_perks", {})
        if isinstance(run_perks, list):
            run_perks = {pid: 1 for pid in run_perks}
        for perk_id, lv in run_perks.items():
            if lv <= 0:
                continue
            if perk_id == "juggernaut":
                self.max_hp += lv
                self.speed *= 0.85
            elif perk_id == "glass_cannon":
                mult = [1.40, 1.55, 1.75][min(lv - 1, 2)]
                self.melee_damage = int(self.melee_damage * mult)
                self.bullet_damage = int(self.bullet_damage * mult)
                self.max_hp = max(1, self.max_hp - 1)
            elif perk_id == "sharpshooter":
                self.bullet_pierce_count = [1, 2, 3][min(lv - 1, 2)]
        self.hp = self.max_hp

        # Apply class starting bonuses
        cls_defs = _load_class_defs()
        run_class = pd.get("run_class", "warrior")
        cls_data = cls_defs.get(run_class, cls_defs.get("warrior", {}))
        start = cls_data.get("starting", {})
        if start.get("free_dash"):           self.dash_unlocked = True
        if start.get("free_ranged"):         self.has_ranged = True
        if start.get("bonus_hp"):            self.max_hp += start["bonus_hp"]
        if start.get("bonus_speed"):         self.speed *= 1 + start["bonus_speed"]
        if start.get("bonus_armor"):         self.damage_reduction = min(self.damage_reduction + start["bonus_armor"], 0.60)
        if start.get("bullet_pierce_bonus"): self.bullet_pierce_count += start["bullet_pierce_bonus"]
        self.player_class = run_class
        self.hp = self.max_hp

        self.swing_timer = 0.0
        self.swing_cooldown_timer = 0.0
        self.shoot_timer = 0.0
        self.invincible_timer = 0.0
        self.INVINCIBLE_DURATION = 0.9

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

    @property
    def is_dashing(self) -> bool:
        return self._dash_timer > 0

    def _try_shoot(self, bullets: list):
        if not self.has_ranged or self.shoot_timer > 0:
            return
        if self.bullet_count == 1:
            angles = [self.facing]
        else:
            angles = [
                self.facing - self.bullet_spread / 2 + i * self.bullet_spread / (self.bullet_count - 1)
                for i in range(self.bullet_count)
            ]
        for angle in angles:
            direction = pygame.Vector2(1, 0).rotate(angle)
            spawn = self.pos + direction * (_PLAYER_RADIUS + 6)
            bullets.append(Bullet(spawn, direction * BULLET_SPEED, self.bullet_damage, pierce=self.bullet_pierce_count))
        self.shoot_timer = self.shoot_cooldown

    def use_bomb(self) -> bool:
        if self.bombs > 0:
            self.bombs -= 1
            return True
        return False

    def use_shield(self) -> bool:
        if self.shields > 0 and not self.shielded:
            self.shields -= 1
            self.shielded = True
            self._shield_timer = 5.0
            return True
        return False

    def update(self, dt: float, keys, walls: list):
        self._anim += dt
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.swing_cooldown_timer = max(0.0, self.swing_cooldown_timer - dt)
        self.shoot_timer = max(0.0, self.shoot_timer - dt)
        if self.shielded:
            self._shield_timer -= dt
            if self._shield_timer <= 0:
                self.shielded = False

        if self.is_swinging:
            self.swing_timer -= dt
            if self.swing_timer <= 0:
                self.is_swinging = False
                self.swing_cooldown_timer = self.swing_cooldown

        self._dash_timer = max(0.0, self._dash_timer - dt)
        self._dash_cd_timer = max(0.0, self._dash_cd_timer - dt)

        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        if (self.dash_unlocked and self._dash_timer <= 0 and self._dash_cd_timer <= 0
                and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])):
            if dx != 0 or dy != 0:
                self._dash_dir = pygame.Vector2(dx, dy).normalize()
            else:
                self._dash_dir = pygame.Vector2(1, 0).rotate(self.facing)
            self._dash_timer = self.dash_duration
            self._dash_cd_timer = self.dash_cooldown
            self.invincible_timer = max(self.invincible_timer, 0.3)

        from systems.collision import resolve_wall_collision
        if self._dash_timer > 0:
            self._float_x, self._float_y = resolve_wall_collision(
                self.rect, walls,
                self._dash_dir.x * self.dash_speed * dt,
                self._dash_dir.y * self.dash_speed * dt,
                self._float_x, self._float_y,
            )
        else:
            self._float_x, self._float_y = resolve_wall_collision(
                self.rect, walls,
                dx * self.speed * dt,
                dy * self.speed * dt,
                self._float_x, self._float_y,
            )
        self.pos.x = self.rect.centerx
        self.pos.y = self.rect.centery

    def get_melee_hitbox(self) -> pygame.Rect:
        range_px = MELEE_RANGE * self.melee_range_mult
        size_px  = int(MELEE_HITBOX_SIZE * self.melee_hitbox_mult)
        offset = pygame.Vector2(range_px, 0).rotate(self.facing)
        cx = self.pos.x + offset.x
        cy = self.pos.y + offset.y
        return pygame.Rect(cx - size_px // 2, cy - size_px // 2, size_px, size_px)

    def take_damage(self, amount: int) -> bool:
        if self.invincible_timer > 0:
            return False
        if self.shielded:
            # Shield absorbs the hit; give brief invincibility to prevent instant re-damage
            self.invincible_timer = 0.5
            return False
        amount = max(1, int(amount * (1.0 - self.damage_reduction)))
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
        self._float_x = float(self.rect.x)
        self._float_y = float(self.rect.y)
        self.hp = self.max_hp
        self.invincible_timer = self.INVINCIBLE_DURATION

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        if self.invincible_timer > 0 and int(self.invincible_timer * 8) % 2 == 0:
            return

        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)

        from systems.gfx import glow
        glow(surface, cx, cy, 22, _PLAYER_COLOR, 80)

        # Shield ring
        if self.shielded:
            pulse = 0.5 + 0.5 * math.sin(self._shield_timer * 8)
            glow(surface, cx, cy, 28, CYAN, int(80 + pulse * 60))
            pygame.draw.circle(surface, CYAN, (cx, cy), _PLAYER_RADIUS + 8, 2)

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
