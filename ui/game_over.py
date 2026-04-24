import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, RED, DARK_GRAY, YELLOW, GREEN


class GameOverScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._coins_earned = 0
        self._btn_rect = None
        self._best_level = 0
        self._best_coins = 0
        self._is_new_best = False

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._coins_earned = kwargs.get("coins_earned", 0)

        try:
            from systems.audio import audio
            audio.play_music("gameover")
        except Exception:
            pass

        level_reached = self._player_data.get("current_level", 0)
        coins_total = self._player_data.get("coins", 0)
        prev_best_level = self._player_data.get("best_level", 0)
        prev_best_coins = self._player_data.get("best_coins", 0)

        self._best_level = max(level_reached, prev_best_level)
        self._best_coins = max(coins_total, prev_best_coins)
        self._is_new_best = (level_reached > prev_best_level or coins_total > prev_best_coins)

        if self._is_new_best:
            self._player_data["best_level"] = self._best_level
            self._player_data["best_coins"] = self._best_coins
            from core.save import write_save
            write_save(self._player_data)

    def update(self, events, dt):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self._go_to_menu()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._btn_rect and self._btn_rect.collidepoint(event.pos):
                    self._go_to_menu()

    def _go_to_menu(self):
        from core.state_machine import GameState
        from core.save import default_save, write_save
        fresh = default_save()
        fresh["best_level"] = self._best_level
        fresh["best_coins"] = self._best_coins
        fresh["music_vol"] = self._player_data.get("music_vol", 0.4)
        fresh["sfx_vol"] = self._player_data.get("sfx_vol", 1.0)
        write_save(fresh)
        self._sm.switch_to(GameState.MAIN_MENU, player_data=fresh)

    def draw(self, surface: pygame.Surface):
        surface.fill((20, 5, 5))

        title = self._title.render("GAME OVER", True, RED)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))

        level_reached = self._player_data.get("current_level", 0) if self._player_data else 0
        coins_total = self._player_data.get("coins", 0) if self._player_data else 0

        run_s = self._font.render(
            f"Run:  Level {level_reached}  |  {coins_total} coins total", True, (200, 160, 160))
        surface.blit(run_s, (SCREEN_W // 2 - run_s.get_width() // 2, 195))

        if self._coins_earned > 0:
            earned = self._font.render(f"+{self._coins_earned} coins earned this run", True, YELLOW)
            surface.blit(earned, (SCREEN_W // 2 - earned.get_width() // 2, 220))

        if self._is_new_best:
            nb = self._big.render("NEW BEST!", True, GREEN)
            surface.blit(nb, (SCREEN_W // 2 - nb.get_width() // 2, 255))

        best_col = GREEN if self._is_new_best else (140, 160, 140)
        best_s = self._font.render(
            f"Best: Level {self._best_level}  |  {self._best_coins} coins", True, best_col)
        surface.blit(best_s, (SCREEN_W // 2 - best_s.get_width() // 2, 290))

        reset_s = self._font.render("All progress lost. Back to square one.", True, (140, 60, 60))
        surface.blit(reset_s, (SCREEN_W // 2 - reset_s.get_width() // 2, 330))

        btn_w, btn_h = 260, 52
        bx = SCREEN_W // 2 - btn_w // 2
        by = 390
        self._btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
        pygame.draw.rect(surface, DARK_GRAY, self._btn_rect, border_radius=8)
        pygame.draw.rect(surface, WHITE, self._btn_rect, 2, border_radius=8)
        label = self._big.render("MAIN MENU", True, WHITE)
        surface.blit(label, (self._btn_rect.centerx - label.get_width() // 2,
                              self._btn_rect.centery - label.get_height() // 2))

        hint = self._font.render("Press ENTER or SPACE to continue", True, (120, 80, 80))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 40))

        from systems.gfx import get_scanlines
        surface.blit(get_scanlines(SCREEN_W, SCREEN_H), (0, 0))
