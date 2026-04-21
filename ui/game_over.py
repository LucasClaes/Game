import pygame
from core.settings import SCREEN_W, SCREEN_H, BLACK, WHITE, RED, DARK_GRAY, YELLOW


class GameOverScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._coins_earned = 0
        self._btn_rect = None

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._coins_earned = kwargs.get("coins_earned", 0)

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
        if self._player_data:
            self._player_data["current_level"] = 0
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((20, 5, 5))

        title = self._title.render("GAME OVER", True, RED)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 130))

        if self._coins_earned > 0:
            earned = self._font.render(f"+{self._coins_earned} coins earned this run", True, YELLOW)
            surface.blit(earned, (SCREEN_W // 2 - earned.get_width() // 2, 230))

        if self._player_data:
            bank = self._font.render(f"Bank total: {self._player_data['coins']} coins", True, YELLOW)
            surface.blit(bank, (SCREEN_W // 2 - bank.get_width() // 2, 260))

        btn_w, btn_h = 260, 52
        bx = SCREEN_W // 2 - btn_w // 2
        by = 340
        self._btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
        pygame.draw.rect(surface, DARK_GRAY, self._btn_rect, border_radius=8)
        pygame.draw.rect(surface, WHITE, self._btn_rect, 2, border_radius=8)
        label = self._big.render("MAIN MENU", True, WHITE)
        surface.blit(label, (self._btn_rect.centerx - label.get_width() // 2,
                              self._btn_rect.centery - label.get_height() // 2))

        hint = self._font.render("Press ENTER or SPACE to continue", True, (120, 80, 80))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 40))
