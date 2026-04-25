import json
import math
import os
import random
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, BLACK, YELLOW, RED, DARK_GRAY, CHAIN_AGGRO_RADIUS
from entities.player import Player
from entities.zombie import Zombie
from world.level import Level
from systems.camera import Camera
from systems.particles import ParticleSystem
from ui.hud import HUD
from ui.minimap import Minimap

_GEAR_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gear.json")
_GEAR_DEFS_CACHE: dict | None = None

def _get_gear_defs() -> dict:
    global _GEAR_DEFS_CACHE
    if _GEAR_DEFS_CACHE is None:
        try:
            with open(_GEAR_PATH) as f:
                raw = json.load(f)
            _GEAR_DEFS_CACHE = {g["id"]: g for g in raw["gear"]}
        except Exception:
            _GEAR_DEFS_CACHE = {}
    return _GEAR_DEFS_CACHE


class PlayingScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player = None
        self._level = None
        self._camera = Camera()
        self._bullets = []
        self._enemy_bullets = []
        self._boss = None
        self._companions = []
        self._player_data = None
        self._coins_earned_this_run = 0
        self._hud = HUD(font, big_font)
        self._minimap = Minimap()
        self._paused = False
        self._complete_delay = 0.0
        self._particles = ParticleSystem()
        self._flash_timer = 0.0
        self._flash_color = (200, 0, 0)
        self._was_swinging = False
        self._trap_timer = 0.0
        self._pause_btns: dict = {}
        # Gear / crates / barrels
        self._crates = []
        self._barrels = []
        self._pickup_text = ""
        self._pickup_timer = 0.0
        # Combo
        self._combo = 0
        self._combo_timer = 0.0
        self._kill_count = 0
        self._elapsed = 0.0
        self._damage_numbers = []
        # Perk runtime state
        self._iron_will_active = False
        self._second_wind_used = False
        self._vampiric_kills = 0
        self._adrenaline_timer = 0.0
        self._adrenaline_active = False
        self._overclock_timer = 0.0
        self._overclock_active = False
        self._prev_dashing = False
        # Challenge / difficulty
        self._challenge_modifier: str | None = None
        self._challenge_id: str | None = None
        self._challenge_reward: int = 0
        self._diff_coin_mult: float = 1.0
        self._took_damage: bool = False
        self._challenge_time_limit: float = 0.0
        # Achievement popups
        self._ach_popups: list = []

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._challenge_modifier = kwargs.get("challenge_modifier", None)
        self._challenge_id       = kwargs.get("challenge_id", None)
        self._challenge_reward   = kwargs.get("challenge_reward", 0)
        level_index = self._player_data.get("current_level", 0)

        is_boss = level_index > 0 and level_index % 4 == 0
        if is_boss:
            self._level = Level.generate_boss(level_index)
            boss_level = level_index // 4
            if boss_level >= 2:
                from entities.boss import Necromancer
                self._boss = Necromancer(
                    self._level.boss_spawn[0],
                    self._level.boss_spawn[1],
                    boss_level=boss_level,
                )
            else:
                from entities.boss import Boss
                self._boss = Boss(
                    self._level.boss_spawn[0],
                    self._level.boss_spawn[1],
                    boss_level=boss_level,
                )
        else:
            self._level = Level.generate(level_index)
            self._boss = None

        self._player = Player(
            self._level.player_start[0],
            self._level.player_start[1],
            self._player_data.get("upgrades", {}),
            player_data=self._player_data,
        )

        from entities.companion import Companion
        self._companions = [
            Companion(self._player, i)
            for i in range(self._player.companion_count)
        ]

        # Instantiate crates and barrels from level data
        from entities.crate import LootCrate
        from entities.barrel import Barrel
        self._crates = [LootCrate(tx, ty) for tx, ty in self._level.crate_tiles]
        self._barrels = [Barrel(tx, ty) for tx, ty in self._level.barrel_tiles]

        self._bullets = []
        self._enemy_bullets = []
        self._coins_earned_this_run = 0
        self._complete_delay = 0.0
        self._paused = False
        self._particles.clear()
        self._flash_timer = 0.0
        self._was_swinging = False
        self._trap_timer = 0.0
        self._pickup_text = ""
        self._pickup_timer = 0.0
        self._took_damage = False
        self._ach_popups = []

        # Combo reset
        self._combo = 0
        self._combo_timer = 0.0
        self._kill_count = 0
        self._elapsed = 0.0
        self._damage_numbers = []

        # Perk runtime reset per level
        perks = self._player_data.get("run_perks", [])
        self._iron_will_active = "iron_will" in perks
        self._second_wind_used = False
        self._vampiric_kills = 0
        self._adrenaline_timer = 0.0
        self._adrenaline_active = False
        self._overclock_timer = 0.0
        self._overclock_active = False
        self._prev_dashing = False

        # Apply difficulty multipliers
        from core.settings import DIFFICULTIES
        diff_idx = self._player_data.get("difficulty", 1)
        diff = DIFFICULTIES[diff_idx]
        self._diff_coin_mult = diff["coins"]
        for z in self._level.zombies:
            z.hp      = max(1, int(z.hp * diff["hp"]))
            z.max_hp  = z.hp
            z.speed  *= diff["speed"]
            z.damage  = max(1, int(z.damage * diff["damage"]))
        if self._boss:
            self._boss.hp     = max(1, int(self._boss.hp * diff["hp"]))
            self._boss.max_hp = self._boss.hp
            self._boss.speed *= diff["speed"]

        # Apply challenge modifier
        mod = self._challenge_modifier
        if mod == "one_hp":
            self._player.max_hp = 1
            self._player.hp = 1
        elif mod == "no_dash":
            self._player.dash_unlocked = False
        elif mod == "no_gear":
            # Rebuild player without gear bonuses
            _pd_no_gear = dict(self._player_data)
            _pd_no_gear["gear"] = {}
            self._player = Player(
                self._level.player_start[0],
                self._level.player_start[1],
                self._player_data.get("upgrades", {}),
                player_data=_pd_no_gear,
            )
        elif mod == "double_zombies":
            import random as _rnd
            from entities.zombie import Zombie as _Z
            existing = list(self._level.zombies)
            new_z = []
            for z in existing:
                tx = int(z.pos.x // 32) + _rnd.randint(-3, 3)
                ty = int(z.pos.y // 32) + _rnd.randint(-3, 3)
                tx = max(1, min(self._level.tile_w - 2, tx))
                ty = max(1, min(self._level.tile_h - 2, ty))
                new_z.append(_Z(tx, ty, z.zombie_type))
            self._level.zombies.extend(new_z)
        elif mod == "time_limit":
            self._challenge_time_limit = 180.0  # 3 minutes per level

        try:
            from systems.audio import audio
            audio.play_music("combat")
        except Exception:
            pass

    def _perks(self) -> list:
        return self._player_data.get("run_perks", []) if self._player_data else []

    def _take_player_damage(self, amount: int) -> bool:
        perks = self._perks()
        if "iron_will" in perks and self._iron_will_active:
            self._iron_will_active = False
            self._flash_timer = 0.4
            self._flash_color = (180, 255, 180)
            return False
        died = self._player.take_damage(amount)
        if died and "second_wind" in perks and not self._second_wind_used:
            self._second_wind_used = True
            self._player.hp = 1
            self._player.invincible_timer = self._player.INVINCIBLE_DURATION
            self._sfx("level_up")
            self._flash_timer = 0.5
            self._flash_color = (100, 220, 100)
            return False
        if not died and self._player.invincible_timer >= self._player.INVINCIBLE_DURATION:
            self._took_damage = True
            self._on_player_hurt(perks)
        return died

    def _on_player_hurt(self, perks: list):
        if "adrenaline" in perks and not self._adrenaline_active:
            self._adrenaline_active = True
            self._adrenaline_timer = 8.0
            self._player.speed *= 1.15
            self._flash_timer = 0.3
            self._flash_color = (255, 140, 0)
        self._combo = 0
        self._combo_timer = 0.0

    def update(self, events, dt):
        if self._player is None or self._level is None:
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._toggle_pause()
                elif event.key == pygame.K_q and not self._paused:
                    self._use_bomb()
                elif event.key == pygame.K_e and not self._paused:
                    self._use_shield()
            if self._paused and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._pause_btns.get("resume") and self._pause_btns["resume"].collidepoint(event.pos):
                    self._toggle_pause()
                elif self._pause_btns.get("menu") and self._pause_btns["menu"].collidepoint(event.pos):
                    self._go_to_main_menu()

        if self._paused:
            return

        self._elapsed += dt
        self._flash_timer = max(0.0, self._flash_timer - dt)
        self._pickup_timer = max(0.0, self._pickup_timer - dt)

        # Achievement popup timers
        for p in self._ach_popups:
            p["timer"] -= dt
        self._ach_popups = [p for p in self._ach_popups if p["timer"] > 0]

        # Challenge: time limit per level
        if self._challenge_modifier == "time_limit" and self._challenge_time_limit > 0:
            self._challenge_time_limit -= dt
            if self._challenge_time_limit <= 0:
                self._on_player_died()
                return

        for dn in self._damage_numbers:
            dn["timer"] -= dt
            dn["y"] -= 35 * dt
        self._damage_numbers = [dn for dn in self._damage_numbers if dn["timer"] > 0]

        if self._complete_delay > 0:
            self._complete_delay -= dt
            if self._complete_delay <= 0:
                self._finish_level()
            return

        # Perk timers
        perks = self._perks()
        if self._adrenaline_active:
            self._adrenaline_timer -= dt
            if self._adrenaline_timer <= 0:
                self._adrenaline_active = False
                self._player.speed /= 1.15

        if self._overclock_active:
            self._overclock_timer -= dt
            if self._overclock_timer <= 0:
                self._overclock_active = False
                self._player.swing_cooldown /= 0.70
                self._player.shoot_cooldown /= 0.70

        # Combo timer decay
        if self._combo_timer > 0:
            self._combo_timer -= dt
            if self._combo_timer <= 0:
                self._combo = 0

        keys = pygame.key.get_pressed()
        prev_bullet_count = len(self._bullets)
        self._player.handle_input(keys, events, self._bullets, self._camera.offset)
        if len(self._bullets) > prev_bullet_count:
            self._sfx("shoot")

        swing_now = self._player.is_swinging
        if swing_now and not self._was_swinging:
            self._sfx("melee")
        self._was_swinging = swing_now

        # Overclock: detect dash start
        dashing_now = self._player.is_dashing
        if dashing_now and not self._prev_dashing:
            self._sfx("dash")
        if dashing_now and not self._prev_dashing and "overclock" in perks and not self._overclock_active:
            self._overclock_active = True
            self._overclock_timer = 6.0
            self._player.swing_cooldown *= 0.70
            self._player.shoot_cooldown *= 0.70
            self._flash_timer = 0.3
            self._flash_color = (80, 200, 255)
        self._prev_dashing = dashing_now

        self._player.update(dt, keys, self._level.walls)
        self._level.update(dt)
        self._particles.update(dt)

        # Update crates
        for crate in self._crates:
            crate.update(dt)
            if crate.check_pickup(self._player.rect):
                self._open_crate(crate)
        self._crates = [c for c in self._crates if c.alive]

        # Magnet perk: auto-collect nearby coins
        if "magnet" in perks:
            magnet_rect = self._player.rect.inflate(128, 128)
            for coin in self._level.coins:
                if not coin.collected and magnet_rect.colliderect(coin.rect):
                    coin.collected = True
                    self._award_coins(10)
                    self._sfx("coin")
                    self._particles.emit(coin.rect.centerx, coin.rect.centery, 5, (255, 215, 0))

        # Update zombies
        for zombie in self._level.zombies:
            new_eb = zombie.update(dt, self._player.pos, self._level.walls,
                                   self._level.tile_grid, self._level.tile_w, self._level.tile_h,
                                   zombies=self._level.zombies)
            self._enemy_bullets.extend(new_eb)

        # Update boss
        if self._boss and self._boss.alive:
            new_eb, new_zom = self._boss.update(
                dt, self._player.pos, self._level.walls,
                self._level.pixel_w, self._level.pixel_h,
            )
            self._enemy_bullets.extend(new_eb)
            if new_zom and len(self._level.zombies) < 8:
                self._level.zombies.extend(new_zom)
            if not self._boss.alive:
                self._award_coins(self._boss.coins)
                self._level._force_open = True
                self._sfx("boss_roar")
                self._camera.shake(0.7, 12)
                self._flash_timer = 0.6
                self._flash_color = (255, 120, 0)
                # Guaranteed crate on boss kill
                from entities.crate import LootCrate
                bc = LootCrate.from_pixel(self._boss.pos.x, self._boss.pos.y)
                self._crates.append(bc)
                self._player_data["bosses_killed"] = self._player_data.get("bosses_killed", 0) + 1
                self._run_achievements()

        # Update enemy bullets
        for eb in self._enemy_bullets:
            eb.update(dt, self._level.walls, self._level.pixel_w, self._level.pixel_h)
        self._enemy_bullets = [eb for eb in self._enemy_bullets if eb.alive]

        # Enemy bullet vs player
        for eb in self._enemy_bullets:
            if eb.rect.colliderect(self._player.rect):
                died = self._take_player_damage(eb.damage)
                eb.alive = False
                if died:
                    self._on_player_died()
                    return
                else:
                    self._sfx("player_hurt")
                    self._camera.shake(0.2, 5)
                    self._flash_timer = 0.25
                    self._flash_color = (200, 0, 0)

        # Update companion bullets
        targets = list(self._level.zombies) + ([self._boss] if self._boss and self._boss.alive else [])
        for c in self._companions:
            new_bullets = c.update(targets, dt)
            self._bullets.extend(new_bullets)

        # Update player bullets
        for b in self._bullets:
            b.update(dt, self._level.walls, self._level.pixel_w, self._level.pixel_h)
        self._bullets = [b for b in self._bullets if b.alive]

        # Bullet vs barrel
        for barrel in self._barrels:
            if not barrel.alive:
                continue
            for bullet in self._bullets:
                if not bullet.alive:
                    continue
                if bullet.rect.colliderect(barrel.rect):
                    bullet.alive = False
                    coins = barrel.hit()
                    self._award_coins(coins)
                    self._sfx("enemy_die")
                    self._particles.emit(barrel.rect.centerx, barrel.rect.centery, 6, (160, 90, 30))
                    break
        self._barrels = [b for b in self._barrels if b.alive]

        # Bullet vs zombie collisions (pierce-aware)
        for zombie in self._level.zombies:
            for bullet in self._bullets:
                if not bullet.alive:
                    continue
                zid = id(zombie)
                if zid in bullet.pierce_hit:
                    continue
                if bullet.rect.colliderect(zombie.rect):
                    bullet.pierce_hit.add(zid)
                    if bullet.pierce <= 0:
                        bullet.alive = False
                    else:
                        bullet.pierce -= 1
                    killed = zombie.take_damage(bullet.damage)
                    self._spawn_damage_number(zombie.pos, bullet.damage)
                    if killed:
                        if self._on_zombie_killed(zombie):
                            return
                    else:
                        self._chain_aggro(zombie)

        # Bullet vs boss
        if self._boss and self._boss.alive:
            for bullet in self._bullets:
                if not bullet.alive:
                    continue
                if bullet.rect.colliderect(self._boss.rect):
                    bullet.alive = False
                    killed = self._boss.take_damage(bullet.damage)
                    if killed:
                        self._award_coins(self._boss.coins)
                        self._level._force_open = True
                        self._sfx("boss_roar")
                        self._camera.shake(0.7, 12)
                        self._flash_timer = 0.6
                        self._flash_color = (255, 120, 0)
                        from entities.crate import LootCrate
                        bc = LootCrate.from_pixel(self._boss.pos.x, self._boss.pos.y)
                        self._crates.append(bc)
                        self._player_data["bosses_killed"] = self._player_data.get("bosses_killed", 0) + 1
                        self._run_achievements()

        # Melee vs barrels
        if self._player.is_swinging:
            hb = self._player.get_melee_hitbox()
            for barrel in self._barrels:
                if not barrel.alive:
                    continue
                if hb.colliderect(barrel.rect):
                    coins = barrel.hit()
                    self._award_coins(coins)
                    self._sfx("enemy_die")
                    self._particles.emit(barrel.rect.centerx, barrel.rect.centery, 6, (160, 90, 30))

        # Melee vs zombies
        if self._player.is_swinging:
            hb = self._player.get_melee_hitbox()
            for zombie in self._level.zombies:
                if id(zombie) in self._player._hit_this_swing:
                    continue
                if hb.colliderect(zombie.rect):
                    self._player._hit_this_swing.add(id(zombie))
                    killed = zombie.take_damage(self._player.melee_damage)
                    self._spawn_damage_number(zombie.pos, self._player.melee_damage)
                    self._chain_aggro(zombie)
                    if killed:
                        if self._on_zombie_killed(zombie):
                            return
            # Melee vs boss
            if self._boss and self._boss.alive and id(self._boss) not in self._player._hit_this_swing:
                if hb.colliderect(self._boss.rect):
                    self._player._hit_this_swing.add(id(self._boss))
                    killed = self._boss.take_damage(self._player.melee_damage)
                    if killed:
                        self._award_coins(self._boss.coins)
                        self._level._force_open = True
                        self._sfx("boss_roar")
                        self._camera.shake(0.7, 12)
                        self._flash_timer = 0.6
                        self._flash_color = (255, 120, 0)
                        from entities.crate import LootCrate
                        bc = LootCrate.from_pixel(self._boss.pos.x, self._boss.pos.y)
                        self._crates.append(bc)
                        self._player_data["bosses_killed"] = self._player_data.get("bosses_killed", 0) + 1
                        self._run_achievements()

        # Remove dead zombies
        self._level.zombies = [z for z in self._level.zombies if z.alive]
        self._barrels = [b for b in self._barrels if b.alive]

        # Coin collection (normal proximity)
        for coin in self._level.coins:
            if not coin.collected and self._player.rect.colliderect(coin.rect):
                coin.collected = True
                self._award_coins(10)
                self._sfx("coin")
                self._particles.emit(coin.rect.centerx, coin.rect.centery, 5, (255, 215, 0))

        # Trap damage
        if self._level.trap_rects:
            on_trap = any(self._player.rect.colliderect(tr) for tr in self._level.trap_rects)
            if on_trap:
                self._trap_timer += dt
                if self._trap_timer >= 1.5:
                    self._trap_timer = 0.0
                    died = self._take_player_damage(1)
                    if died:
                        self._on_player_died()
                        return
                    self._sfx("player_hurt")
                    self._camera.shake(0.15, 4)
                    self._flash_timer = 0.25
                    self._flash_color = (200, 80, 0)
            else:
                self._trap_timer = 0.0

        # Zombie contact damage
        for zombie in self._level.zombies:
            if self._player.rect.colliderect(zombie.rect):
                died = self._take_player_damage(zombie.damage)
                if died:
                    self._on_player_died()
                    return
                else:
                    self._sfx("player_hurt")
                    self._camera.shake(0.2, 5)
                    self._flash_timer = 0.25
                    self._flash_color = (200, 0, 0)

        # Boss contact damage
        if self._boss and self._boss.alive:
            if self._player.rect.colliderect(self._boss.rect):
                died = self._take_player_damage(self._boss.damage)
                if died:
                    self._on_player_died()
                    return
                else:
                    self._sfx("player_hurt")
                    self._camera.shake(0.3, 7)
                    self._flash_timer = 0.35
                    self._flash_color = (200, 0, 0)

        # Level complete check
        if self._level.is_complete(self._player.rect) and self._complete_delay == 0:
            self._complete_delay = 0.8
            self._sfx("level_up")

        self._camera.update(self._player.pos, self._level.pixel_w, self._level.pixel_h, dt)

    def _spawn_damage_number(self, pos, amount, color=(255, 80, 80)):
        self._damage_numbers.append({
            "x": float(pos.x), "y": float(pos.y),
            "amount": amount, "timer": 1.2, "color": color,
        })

    def _on_zombie_killed(self, zombie) -> bool:
        perks = self._perks()
        self._award_coins(zombie.coin_drop)
        self._sfx("enemy_die")
        self._kill_count += 1
        self._player_data["total_kills"] = self._player_data.get("total_kills", 0) + 1
        self._run_achievements()

        _type_colors = {
            "fast": (255, 140, 30), "tank": (160, 60, 220),
            "ranged": (180, 80, 200), "exploder": (60, 220, 80),
            "healer": (200, 100, 220), "lurker": (0, 180, 180),
        }
        pcolor = _type_colors.get(zombie.zombie_type, (200, 60, 60))
        self._particles.emit(zombie.pos.x, zombie.pos.y, 12, pcolor)

        # Combo
        self._combo += 1
        self._combo_timer = 4.0

        # Vampiric
        if "vampiric" in perks:
            self._vampiric_kills += 1
            if self._vampiric_kills >= 10:
                self._vampiric_kills = 0
                self._player.hp = min(self._player.hp + 1, self._player.max_hp)
                self._particles.emit(int(self._player.pos.x), int(self._player.pos.y), 10, (60, 220, 80))
                self._flash_timer = 0.3
                self._flash_color = (60, 220, 80)

        # Explosive death perk
        if "explosive_death" in perks:
            self._sfx("bomb_explode")
            for other in self._level.zombies:
                if other is not zombie and other.alive:
                    if (other.pos - zombie.pos).length() <= 80:
                        other.take_damage(30)

        # Bounty hunter: elite zombie always drops a crate
        if "bounty_hunter" in perks and zombie.elite:
            from entities.crate import LootCrate
            self._crates.append(LootCrate.from_pixel(zombie.pos.x, zombie.pos.y))

        # Exploder AOE on death
        if zombie.death_data.get("explode"):
            exp_pos = zombie.death_data["pos"]
            exp_r   = zombie.death_data["radius"]
            exp_dmg = zombie.death_data["damage"]
            self._particles.emit(int(exp_pos.x), int(exp_pos.y), 20, (255, 200, 50))
            self._camera.shake(0.4, 8)
            self._flash_timer = 0.3
            self._flash_color = (255, 200, 50)
            if math.hypot(self._player.pos.x - exp_pos.x, self._player.pos.y - exp_pos.y) < exp_r:
                died = self._take_player_damage(exp_dmg)
                if died:
                    self._on_player_died()
                    return True

        return False

    def _open_crate(self, crate):
        crate.alive = False
        gear_defs = _get_gear_defs()
        if not gear_defs:
            return
        equipped = self._player_data.get("gear", {})
        slots = ["helm", "chest", "boots", "gloves"]

        # Weight toward unequipped slots
        unequipped = [g for g in gear_defs.values() if equipped.get(g["slot"]) != g["id"]]
        pool = unequipped if unequipped else list(gear_defs.values())
        piece = random.choice(pool)

        if "gear" not in self._player_data:
            self._player_data["gear"] = {}
        self._player_data["gear"][piece["slot"]] = piece["id"]

        found = self._player_data.setdefault("found_gear", [])
        if piece["id"] not in found:
            found.append(piece["id"])

        from core.save import write_save
        write_save(self._player_data)
        self._run_achievements()

        self._pickup_text = f"Found: {piece['name']}!"
        self._pickup_timer = 3.0
        self._sfx("crate_open")
        self._particles.emit(crate.rect.centerx, crate.rect.centery, 14, (255, 200, 50))
        self._flash_timer = 0.35
        self._flash_color = (160, 100, 255)

    def _dev_reload(self, player_data: dict):
        self._player_data = player_data
        if self._player is None:
            return
        from entities.player import Player
        from core.settings import TILE_SIZE
        tx = int(self._player.pos.x // TILE_SIZE)
        ty = int(self._player.pos.y // TILE_SIZE)
        self._player = Player(tx, ty, player_data.get("upgrades", {}),
                              player_data=player_data)
        self._flash_timer = 0.4
        self._flash_color = (50, 200, 255)
        self._pickup_text = "DEV: Reloaded!"
        self._pickup_timer = 2.0

    def _toggle_pause(self):
        self._paused = not self._paused
        try:
            from systems.audio import audio
            import pygame as _pg
            if self._paused:
                audio.fade_to_vol(0.0, 0.4, pause_at_zero=True)
            else:
                _pg.mixer.music.unpause()
                vol = self._player_data.get("music_vol", 0.4) if self._player_data else 0.4
                audio.fade_to_vol(vol, 0.4)
        except Exception:
            pass

    def _go_to_main_menu(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def _sfx(self, name: str):
        try:
            from systems.audio import audio
            audio.play(name)
        except Exception:
            pass

    def _run_achievements(self, extra: dict | None = None):
        from core.achievements import check_achievements
        from core.save import write_save

        def _popup(ach):
            self._ach_popups.append({"text": f"ACHIEVEMENT: {ach['name']}", "timer": 3.5})

        check_achievements(self._player_data, _popup, extra)
        write_save(self._player_data)

    def _chain_aggro(self, hit_zombie):
        for z in self._level.zombies:
            if z is not hit_zombie and (z.pos - hit_zombie.pos).length() <= CHAIN_AGGRO_RADIUS:
                z._state = Zombie.CHASE

    def _use_bomb(self):
        if not self._player.use_bomb():
            return
        self._player_data["bombs"] = self._player.bombs
        px, py = self._player.pos.x, self._player.pos.y
        blast_r = 200
        for z in list(self._level.zombies):
            if math.hypot(z.pos.x - px, z.pos.y - py) < blast_r:
                killed = z.take_damage(150)
                if killed:
                    self._on_zombie_killed(z)
        if self._boss and self._boss.alive:
            if math.hypot(self._boss.pos.x - px, self._boss.pos.y - py) < blast_r:
                killed = self._boss.take_damage(150)
                if killed:
                    self._award_coins(self._boss.coins)
                    self._level._force_open = True
                    self._sfx("boss_roar")
        self._level.zombies = [z for z in self._level.zombies if z.alive]
        self._sfx("bomb_explode")
        self._camera.shake(0.5, 10)
        self._flash_timer = 0.4
        self._flash_color = (255, 200, 50)
        from core.save import write_save
        write_save(self._player_data)

    def _use_shield(self):
        if self._player.use_shield():
            self._player_data["shields"] = self._player.shields
            from core.save import write_save
            write_save(self._player_data)
            self._sfx("shield_activate")

    def _award_coins(self, amount: int):
        perks = self._perks()
        amount = int(amount * self._diff_coin_mult)
        if "lucky_coins" in perks and random.random() < 0.5:
            amount *= 2
        mult = 1.0 + (self._combo // 5) * 0.5
        mult = min(mult, 3.0)
        amount = int(amount * mult)
        self._coins_earned_this_run += amount
        self._player_data["coins"] += amount
        from core.save import write_save
        write_save(self._player_data)

    def _on_player_died(self):
        self._sfx("player_hurt")
        self._player.lives -= 1
        if self._player.lives <= 0:
            self._sfx("game_over")
            from core.state_machine import GameState
            self._sm.switch_to(GameState.GAME_OVER, player_data=self._player_data,
                               coins_earned=self._coins_earned_this_run,
                               kill_count=self._kill_count, elapsed=self._elapsed)
        else:
            self._player.respawn(self._level.player_start[0], self._level.player_start[1])

    def _finish_level(self):
        from core.state_machine import GameState

        # Pacifist challenge: block exit if too many kills
        if self._challenge_modifier == "low_kills" and self._kill_count >= 10:
            self._flash_timer = 0.6
            self._flash_color = (200, 0, 0)
            self._pickup_text = "Too many kills! (need <10)"
            self._pickup_timer = 2.5
            self._complete_delay = 0.0
            return

        # Update best level
        level_num = self._level.number
        if level_num + 1 > self._player_data.get("best_level", 0):
            self._player_data["best_level"] = level_num + 1

        # Per-level achievement checks
        extra: dict = {}
        if not self._took_damage:
            extra["perfect_level"] = True
        extra["fast_level"] = self._elapsed
        self._run_achievements(extra)

        # Challenge completion tracking
        if self._challenge_id:
            wins = self._player_data.setdefault("challenge_wins", {})
            prev = wins.get(self._challenge_id, 0)
            wins[self._challenge_id] = max(prev, level_num + 1)
            self._player_data["coins"] = self._player_data.get("coins", 0) + self._challenge_reward

        from core.save import write_save
        write_save(self._player_data)

        self._sm.switch_to(GameState.LEVEL_COMPLETE,
                           player_data=self._player_data,
                           coins_earned=self._coins_earned_this_run,
                           level_num=self._level.number,
                           kill_count=self._kill_count, elapsed=self._elapsed,
                           challenge_modifier=self._challenge_modifier,
                           challenge_id=self._challenge_id,
                           challenge_reward=self._challenge_reward)

    def draw(self, surface: pygame.Surface):
        if self._level is None or self._player is None:
            return

        self._level.draw(surface, self._camera.offset, self._font)

        # Traps
        for tr in self._level.trap_rects:
            dr = tr.move(-self._camera.offset.x, -self._camera.offset.y)
            pygame.draw.rect(surface, (110, 25, 15), dr)
            pygame.draw.rect(surface, (200, 55, 30), dr, 2)
            cx, cy = dr.centerx, dr.centery
            for ddx, ddy in ((0, -7), (0, 7), (-7, 0), (7, 0)):
                pygame.draw.line(surface, (220, 80, 50), (cx, cy), (cx + ddx, cy + ddy), 2)

        # Barrels
        for barrel in self._barrels:
            barrel.draw(surface, self._camera.offset)

        # Crates
        for crate in self._crates:
            crate.draw(surface, self._camera.offset)

        self._particles.draw(surface, self._camera.offset)

        for bullet in self._bullets:
            bullet.draw(surface, self._camera.offset)

        for eb in self._enemy_bullets:
            eb.draw(surface, self._camera.offset)

        for zombie in self._level.zombies:
            zombie.draw(surface, self._camera.offset)

        if self._boss:
            self._boss.draw(surface, self._camera.offset)

        for c in self._companions:
            c.draw(surface, self._camera.offset)

        self._player.draw(surface, self._camera.offset)

        for dn in self._damage_numbers:
            alpha = int(min(255, dn["timer"] * 255))
            s = self._font.render(str(dn["amount"]), True, dn["color"])
            s.set_alpha(alpha)
            surface.blit(s, (int(dn["x"] - self._camera.offset.x) - s.get_width() // 2,
                             int(dn["y"] - self._camera.offset.y)))

        self._hud.draw(surface, self._player, self._level, len(self._level.coins),
                       player_data=self._player_data, boss=self._boss, combo=self._combo,
                       kill_count=self._kill_count, elapsed=self._elapsed)
        self._minimap.draw(surface, self._level, self._player, self._level.zombies,
                           crates=self._crates, barrels=self._barrels)

        # Crate pickup notification
        if self._pickup_timer > 0 and self._pickup_text:
            alpha = min(255, int(self._pickup_timer * 200))
            s = self._big.render(self._pickup_text, True, (255, 215, 50))
            s.set_alpha(alpha)
            surface.blit(s, (SCREEN_W // 2 - s.get_width() // 2, SCREEN_H // 2 - 60))

        # Achievement popups
        for j, popup in enumerate(reversed(self._ach_popups)):
            alpha = min(255, int(popup["timer"] * 120))
            ps = self._font.render(popup["text"], True, YELLOW)
            bg = pygame.Surface((ps.get_width() + 20, ps.get_height() + 8), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            py = 8 + j * (ps.get_height() + 12)
            bg.set_alpha(alpha)
            ps.set_alpha(alpha)
            surface.blit(bg, (SCREEN_W // 2 - bg.get_width() // 2, py))
            surface.blit(ps, (SCREEN_W // 2 - ps.get_width() // 2, py + 4))

        # Difficulty label (only when not Normal)
        diff_idx = self._player_data.get("difficulty", 1) if self._player_data else 1
        if diff_idx != 1:
            from core.settings import DIFFICULTIES
            _DIFF_COLORS = [(50, 200, 80), (200, 200, 200), (255, 140, 0), (220, 50, 50)]
            diff_name = DIFFICULTIES[diff_idx]["name"]
            dc = _DIFF_COLORS[diff_idx]
            ds = self._font.render(diff_name.upper(), True, dc)
            surface.blit(ds, (SCREEN_W // 2 - ds.get_width() // 2, 4))

        # Challenge modifier label
        if self._challenge_modifier:
            mod_s = self._font.render(f"[CHALLENGE]", True, (255, 180, 50))
            surface.blit(mod_s, (4, 4))

        if self._paused:
            self._draw_pause(surface)

        if self._complete_delay > 0:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((50, 200, 80, 60))
            surface.blit(overlay, (0, 0))
            msg = self._title.render("LEVEL CLEAR!", True, (100, 255, 130))
            surface.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2,
                               SCREEN_H // 2 - msg.get_height() // 2))

        if self._flash_timer > 0:
            alpha = int(min(self._flash_timer * 200, 140))
            fl = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            fl.fill((*self._flash_color, alpha))
            surface.blit(fl, (0, 0))

        from systems.gfx import get_scanlines
        surface.blit(get_scanlines(SCREEN_W, SCREEN_H), (0, 0))

    def _draw_pause(self, surface: pygame.Surface):
        from core.settings import BLUE, DARK_GRAY
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        msg = self._title.render("PAUSED", True, WHITE)
        surface.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2, SCREEN_H // 2 - 110))

        btn_w, btn_h = 220, 50
        bx = SCREEN_W // 2 - btn_w // 2
        resume_rect = pygame.Rect(bx, SCREEN_H // 2 - 20, btn_w, btn_h)
        menu_rect   = pygame.Rect(bx, SCREEN_H // 2 + 44, btn_w, btn_h)
        self._pause_btns = {"resume": resume_rect, "menu": menu_rect}

        for rect, label, color in [
            (resume_rect, "RESUME",    BLUE),
            (menu_rect,   "MAIN MENU", DARK_GRAY),
        ]:
            pygame.draw.rect(surface, color, rect, border_radius=8)
            pygame.draw.rect(surface, WHITE, rect, 2, border_radius=8)
            t = self._big.render(label, True, WHITE)
            surface.blit(t, (rect.centerx - t.get_width() // 2,
                             rect.centery - t.get_height() // 2))

        hint = self._font.render("ESC to resume", True, (120, 120, 140))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H // 2 + 108))

        mins = int(self._elapsed) // 60
        secs = int(self._elapsed) % 60
        stat1 = self._font.render(f"Kills this level: {self._kill_count}", True, (160, 160, 180))
        stat2 = self._font.render(f"Time: {mins}:{secs:02d}", True, (160, 160, 180))
        surface.blit(stat1, (SCREEN_W // 2 - stat1.get_width() // 2, SCREEN_H // 2 + 132))
        surface.blit(stat2, (SCREEN_W // 2 - stat2.get_width() // 2, SCREEN_H // 2 + 154))
