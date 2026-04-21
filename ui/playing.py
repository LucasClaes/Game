import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, BLACK, YELLOW, RED, DARK_GRAY
from entities.player import Player
from world.level import Level
from systems.camera import Camera
from ui.hud import HUD


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
        self._player_data = None
        self._coins_earned_this_run = 0
        self._hud = HUD(font, big_font)
        self._paused = False
        self._complete_delay = 0.0  # brief pause before switching on level complete

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        level_index = self._player_data.get("current_level", 0)

        try:
            self._level = Level.from_json(level_index)
        except (IndexError, KeyError):
            # No more levels — back to menu, reset progress
            self._player_data["current_level"] = 0
            from core.state_machine import GameState
            self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)
            return

        self._player = Player(
            self._level.player_start[0],
            self._level.player_start[1],
            self._player_data.get("upgrades", {}),
        )
        self._bullets = []
        self._coins_earned_this_run = 0
        self._complete_delay = 0.0
        self._paused = False

    def update(self, events, dt):
        if self._player is None or self._level is None:
            return

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._paused = not self._paused

        if self._paused:
            return

        if self._complete_delay > 0:
            self._complete_delay -= dt
            if self._complete_delay <= 0:
                self._finish_level()
            return

        keys = pygame.key.get_pressed()
        self._player.handle_input(keys, events, self._bullets, self._camera.offset)
        self._player.update(dt, keys, self._level.walls)
        self._level.update(dt)

        # Update zombies (with BFS pathfinding)
        for zombie in self._level.zombies:
            zombie.update(dt, self._player.pos, self._level.walls,
                          self._level.tile_grid, self._level.tile_w, self._level.tile_h)

        # Update bullets
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

        # Melee vs zombies
        if self._player.is_swinging:
            hb = self._player.get_melee_hitbox()
            for zombie in self._level.zombies:
                if id(zombie) in self._player._hit_this_swing:
                    continue
                if hb.colliderect(zombie.rect):
                    self._player._hit_this_swing.add(id(zombie))
                    killed = zombie.take_damage(self._player.melee_damage)
                    if killed:
                        self._award_coins(zombie.coin_drop)

        # Remove dead zombies
        self._level.zombies = [z for z in self._level.zombies if z.alive]

        # Coin collection
        for coin in self._level.coins:
            if not coin.collected and self._player.rect.colliderect(coin.rect):
                coin.collected = True
                self._award_coins(10)

        # Zombie contact damage
        for zombie in self._level.zombies:
            if self._player.rect.colliderect(zombie.rect):
                died = self._player.take_damage(zombie.damage)
                if died:
                    self._on_player_died()
                    return

        # Level complete check
        if self._level.is_complete(self._player.rect) and self._complete_delay == 0:
            self._complete_delay = 0.8

        self._camera.update(self._player.pos, self._level.pixel_w, self._level.pixel_h)

    def _award_coins(self, amount: int):
        self._coins_earned_this_run += amount
        self._player_data["coins"] += amount
        from core.save import write_save
        write_save(self._player_data)

    def _on_player_died(self):
        self._player.lives -= 1
        if self._player.lives <= 0:
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

        for bullet in self._bullets:
            bullet.draw(surface, self._camera.offset)

        for zombie in self._level.zombies:
            zombie.draw(surface, self._camera.offset)

        self._player.draw(surface, self._camera.offset)
        self._hud.draw(surface, self._player, self._level, len(self._level.coins))

        if self._paused:
            self._draw_pause(surface)

        if self._complete_delay > 0:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((50, 200, 80, 60))
            surface.blit(overlay, (0, 0))
            msg = self._title.render("LEVEL CLEAR!", True, (100, 255, 130))
            surface.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2,
                               SCREEN_H // 2 - msg.get_height() // 2))

    def _draw_pause(self, surface: pygame.Surface):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        msg = self._title.render("PAUSED", True, WHITE)
        surface.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2,
                           SCREEN_H // 2 - msg.get_height() // 2))
        hint = self._font.render("Press ESC to resume", True, (180, 180, 180))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2,
                            SCREEN_H // 2 + 60))
