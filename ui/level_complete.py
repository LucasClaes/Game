import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, GREEN, BLUE


class LevelCompleteScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._coins_earned = 0
        self._level_num = 0
        self._buttons = ["CONTINUE", "SHOP"]
        self._selected = 0
        self._btn_rects = []

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._coins_earned = kwargs.get("coins_earned", 0)
        self._level_num = kwargs.get("level_num", 0)
        self._selected = 0
        try:
            from systems.audio import audio
            audio.play_music("levelcomplete")
        except Exception:
            pass

    def update(self, events, dt):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._buttons)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._buttons)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._activate(self._selected)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self._btn_rects):
                    if rect.collidepoint(event.pos):
                        self._activate(i)
            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._btn_rects):
                    if rect.collidepoint(event.pos):
                        self._selected = i

    def _activate(self, index):
        from core.state_machine import GameState
        label = self._buttons[index]
        next_level = self._level_num + 1
        self._player_data["current_level"] = next_level
        if label == "CONTINUE":
            self._sm.switch_to(GameState.PLAYING, player_data=self._player_data)
        elif label == "SHOP":
            self._sm.switch_to(GameState.SHOP, player_data=self._player_data,
                               from_state="LEVEL_COMPLETE", level_num=next_level)

    def draw(self, surface: pygame.Surface):
        surface.fill((5, 20, 10))

        title = self._title.render("LEVEL CLEAR!", True, GREEN)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 110))

        lv = self._font.render(f"Level {self._level_num + 1} complete", True, WHITE)
        surface.blit(lv, (SCREEN_W // 2 - lv.get_width() // 2, 200))

        earned = self._font.render(f"+{self._coins_earned} coins", True, YELLOW)
        surface.blit(earned, (SCREEN_W // 2 - earned.get_width() // 2, 230))

        if self._player_data:
            bank = self._font.render(f"Bank: {self._player_data['coins']} coins", True, YELLOW)
            surface.blit(bank, (SCREEN_W // 2 - bank.get_width() // 2, 262))

        btn_w, btn_h = 240, 52
        start_y = 330
        gap = 66
        self._btn_rects = []
        for i, label in enumerate(self._buttons):
            bx = SCREEN_W // 2 - btn_w // 2
            by = start_y + i * gap
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            self._btn_rects.append(rect)
            selected = i == self._selected
            bg = BLUE if selected else DARK_GRAY
            pygame.draw.rect(surface, bg, rect, border_radius=8)
            pygame.draw.rect(surface, WHITE if selected else (80, 80, 80), rect, 2, border_radius=8)
            text = self._big.render(label, True, WHITE if selected else (160, 160, 160))
            surface.blit(text, (rect.centerx - text.get_width() // 2,
                                rect.centery - text.get_height() // 2))
