import math
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, BLACK, YELLOW, RED, DARK_GRAY, CHAIN_AGGRO_RADIUS
from entities.player import Player
from entities.zombie import Zombie
from world.level import Level
from systems.camera import Camera
from systems.particles import ParticleSystem
from ui.hud import HUD
from ui.minimap import Minimap


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

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
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

        self._bullets = []
        self._enemy_bullets = []
        self._coins_earned_this_run = 0
        self._complete_delay = 0.0
        self._paused = False
        self._particles.clear()
        self._flash_timer = 0.0
        self._was_swinging = False
        self._trap_timer = 0.0
        try:
            from systems.audio import audio
            audio.play_music("combat")
        except Exception:
            pass

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

        self._flash_timer = max(0.0, self._flash_timer - dt)

        if self._complete_delay > 0:
            self._complete_delay -= dt
            if self._complete_delay <= 0:
                self._finish_level()
            return

        keys = pygame.key.get_pressed()
        prev_bullet_count = len(self._bullets)
        self._player.handle_input(keys, events, self._bullets, self._camera.offset)
        if len(self._bullets) > prev_bullet_count:
            self._sfx('shoot')

        swing_now = self._player.is_swinging
        if swing_now and not self._was_swinging:
            self._sfx('melee')
        self._was_swinging = swing_now

        self._player.update(dt, keys, self._level.walls)
        self._level.update(dt)
        self._particles.update(dt)

        # Update zombies
        for zombie in self._level.zombies:
            new_eb = zombie.update(dt, self._player.pos, self._level.walls,
                                   self._level.tile_grid, self._level.tile_w, self._level.tile_h)
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
                self._sfx('boss_roar')
                self._flash_timer = 0.6
                self._flash_color = (255, 120, 0)

        # Update enemy bullets
        for eb in self._enemy_bullets:
            eb.update(dt, self._level.walls, self._level.pixel_w, self._level.pixel_h)
        self._enemy_bullets = [eb for eb in self._enemy_bullets if eb.alive]

        # Enemy bullet vs player
        for eb in self._enemy_bullets:
            if eb.rect.colliderect(self._player.rect):
                died = self._player.take_damage(eb.damage)
                eb.alive = False
                if died:
                    self._on_player_died()
                    return
                else:
                    self._sfx('player_hurt')
                    self._flash_timer = 0.25
                    self._flash_color = (200, 0, 0)

        # Update companion bullets (added to self._bullets for unified collision)
        targets = list(self._level.zombies) + ([self._boss] if self._boss and self._boss.alive else [])
        for c in self._companions:
            new_bullets = c.update(targets, dt)
            self._bullets.extend(new_bullets)

        # Update player bullets
        for b in self._bullets:
            b.update(dt, self._level.walls, self._level.pixel_w, self._level.pixel_h)
        self._bullets = [b for b in self._bullets if b.alive]

        # Bullet vs zombie collisions
        for zombie in self._level.zombies:
            for bullet in self._bullets:
                if not bullet.alive:
                    continue
                if bullet.rect.colliderect(zombie.rect):
                    bullet.alive = False
                    killed = zombie.take_damage(bullet.damage)
                    if killed:
                        self._award_coins(zombie.coin_drop)
                        self._sfx('enemy_die')
                        self._particles.emit(zombie.pos.x, zombie.pos.y, 8, (200, 60, 60))
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
                        self._sfx('boss_roar')
                        self._flash_timer = 0.6
                        self._flash_color = (255, 120, 0)

        # Melee vs zombies
        if self._player.is_swinging:
            hb = self._player.get_melee_hitbox()
            for zombie in self._level.zombies:
                if id(zombie) in self._player._hit_this_swing:
                    continue
                if hb.colliderect(zombie.rect):
                    self._player._hit_this_swing.add(id(zombie))
                    killed = zombie.take_damage(self._player.melee_damage)
                    self._chain_aggro(zombie)
                    if killed:
                        self._award_coins(zombie.coin_drop)
                        self._sfx('enemy_die')
                        self._particles.emit(zombie.pos.x, zombie.pos.y, 8, (200, 60, 60))
            # Melee vs boss
            if self._boss and self._boss.alive and id(self._boss) not in self._player._hit_this_swing:
                if hb.colliderect(self._boss.rect):
                    self._player._hit_this_swing.add(id(self._boss))
                    killed = self._boss.take_damage(self._player.melee_damage)
                    if killed:
                        self._award_coins(self._boss.coins)
                        self._level._force_open = True
                        self._sfx('boss_roar')
                        self._flash_timer = 0.6
                        self._flash_color = (255, 120, 0)

        # Remove dead zombies
        self._level.zombies = [z for z in self._level.zombies if z.alive]

        # Coin collection
        for coin in self._level.coins:
            if not coin.collected and self._player.rect.colliderect(coin.rect):
                coin.collected = True
                self._award_coins(10)
                self._sfx('coin')
                self._particles.emit(coin.rect.centerx, coin.rect.centery, 5, (255, 215, 0))

        # Trap damage: timer only ticks while on a trap, resets when off
        if self._level.trap_rects:
            on_trap = any(self._player.rect.colliderect(tr) for tr in self._level.trap_rects)
            if on_trap:
                self._trap_timer += dt
                if self._trap_timer >= 1.5:
                    self._trap_timer = 0.0
                    died = self._player.take_damage(1)
                    if died:
                        self._on_player_died()
                        return
                    self._sfx('player_hurt')
                    self._flash_timer = 0.25
                    self._flash_color = (200, 80, 0)
            else:
                self._trap_timer = 0.0

        # Zombie contact damage
        for zombie in self._level.zombies:
            if self._player.rect.colliderect(zombie.rect):
                died = self._player.take_damage(zombie.damage)
                if died:
                    self._on_player_died()
                    return
                else:
                    self._sfx('player_hurt')
                    self._flash_timer = 0.25
                    self._flash_color = (200, 0, 0)

        # Boss contact damage
        if self._boss and self._boss.alive:
            if self._player.rect.colliderect(self._boss.rect):
                died = self._player.take_damage(self._boss.damage)
                if died:
                    self._on_player_died()
                    return
                else:
                    self._sfx('player_hurt')
                    self._flash_timer = 0.35
                    self._flash_color = (200, 0, 0)

        # Level complete check
        if self._level.is_complete(self._player.rect) and self._complete_delay == 0:
            self._complete_delay = 0.8
            self._sfx('level_up')

        self._camera.update(self._player.pos, self._level.pixel_w, self._level.pixel_h)

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
                    self._award_coins(z.coin_drop)
                    self._particles.emit(z.pos.x, z.pos.y, 12, (255, 140, 0))
        if self._boss and self._boss.alive:
            if math.hypot(self._boss.pos.x - px, self._boss.pos.y - py) < blast_r:
                killed = self._boss.take_damage(150)
                if killed:
                    self._award_coins(self._boss.coins)
                    self._level._force_open = True
                    self._sfx('boss_roar')
        self._level.zombies = [z for z in self._level.zombies if z.alive]
        self._flash_timer = 0.4
        self._flash_color = (255, 200, 50)
        from core.save import write_save
        write_save(self._player_data)

    def _use_shield(self):
        if self._player.use_shield():
            self._player_data["shields"] = self._player.shields
            from core.save import write_save
            write_save(self._player_data)

    def _award_coins(self, amount: int):
        self._coins_earned_this_run += amount
        self._player_data["coins"] += amount
        from core.save import write_save
        write_save(self._player_data)

    def _on_player_died(self):
        self._sfx('player_hurt')
        self._player.lives -= 1
        if self._player.lives <= 0:
            self._sfx('game_over')
            from core.state_machine import GameState
            self._sm.switch_to(GameState.GAME_OVER, player_data=self._player_data,
                               coins_earned=self._coins_earned_this_run)
        else:
            self._player.respawn(self._level.player_start[0], self._level.player_start[1])

    def _finish_level(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.LEVEL_COMPLETE,
                           player_data=self._player_data,
                           coins_earned=self._coins_earned_this_run,
                           level_num=self._level.number)

    def draw(self, surface: pygame.Surface):
        if self._level is None or self._player is None:
            return

        self._level.draw(surface, self._camera.offset, self._font)

        for tr in self._level.trap_rects:
            dr = tr.move(-self._camera.offset.x, -self._camera.offset.y)
            pygame.draw.rect(surface, (110, 25, 15), dr)
            pygame.draw.rect(surface, (200, 55, 30), dr, 2)
            cx, cy = dr.centerx, dr.centery
            for ddx, ddy in ((0, -7), (0, 7), (-7, 0), (7, 0)):
                pygame.draw.line(surface, (220, 80, 50), (cx, cy), (cx + ddx, cy + ddy), 2)

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

        self._hud.draw(surface, self._player, self._level, len(self._level.coins),
                       player_data=self._player_data, boss=self._boss)
        self._minimap.draw(surface, self._level, self._player, self._level.zombies)

        if self._paused:
            self._draw_pause(surface)

        if self._complete_delay > 0:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((50, 200, 80, 60))
            surface.blit(overlay, (0, 0))
            msg = self._title.render("LEVEL CLEAR!", True, (100, 255, 130))
            surface.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2,
                               SCREEN_H // 2 - msg.get_height() // 2))

        # Screen flash overlay
        if self._flash_timer > 0:
            alpha = int(min(self._flash_timer * 200, 140))
            fl = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            fl.fill((*self._flash_color, alpha))
            surface.blit(fl, (0, 0))

        # CRT scanlines
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
