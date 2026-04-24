import math
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE


class MainMenuScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._buttons = ["PLAY", "SHOP", "SETTINGS", "QUIT"]
        self._selected = 0
        self._player_data = None
        self._anim = 0.0
        self._btn_rects = []

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._selected = 0
        try:
            from systems.audio import audio
            audio.play_music("menu")
        except Exception:
            pass

    def update(self, events, dt):
        self._anim += dt
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._buttons)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._buttons)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._activate(self._selected)
            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._btn_rects):
                    if rect.collidepoint(event.pos):
                        self._selected = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self._btn_rects):
                    if rect.collidepoint(event.pos):
                        self._activate(i)

    def _activate(self, index):
        from core.state_machine import GameState
        label = self._buttons[index]
        if label == "PLAY":
            self._sm.switch_to(GameState.PLAYING, player_data=self._player_data)
        elif label == "SHOP":
            self._sm.switch_to(GameState.SHOP, player_data=self._player_data, from_state="MAIN_MENU")
        elif label == "SETTINGS":
            self._sm.switch_to(GameState.SETTINGS, player_data=self._player_data, from_state="MAIN_MENU")
        elif label == "QUIT":
            pygame.quit()
            import sys; sys.exit()

    def draw(self, surface: pygame.Surface):
        surface.fill((15, 15, 25))

        title_surf = self._title.render("ZOMBIE MAZE", True, YELLOW)
        tx = SCREEN_W // 2 - title_surf.get_width() // 2
        ty = 80 + int(math.sin(self._anim) * 5)
        surface.blit(title_surf, (tx, ty))

        sub = self._font.render("Collect coins. Kill zombies. Survive.", True, (160, 160, 180))
        surface.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 155))

        # Buttons
        self._btn_rects = []
        btn_w, btn_h = 240, 50
        start_y = 210
        gap = 64
        for i, label in enumerate(self._buttons):
            bx = SCREEN_W // 2 - btn_w // 2
            by = start_y + i * gap
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            self._btn_rects.append(rect)
            selected = i == self._selected
            bg = BLUE if selected else DARK_GRAY
            pygame.draw.rect(surface, bg, rect, border_radius=8)
            pygame.draw.rect(surface, WHITE if selected else (80, 80, 80), rect, 2, border_radius=8)
            text = self._big.render(label, True, WHITE if selected else (180, 180, 180))
            surface.blit(text, (rect.centerx - text.get_width() // 2,
                                rect.centery - text.get_height() // 2))

        # Coin count
        y_info = start_y + len(self._buttons) * gap + 8
        if self._player_data:
            coin_surf = self._font.render(f"Bank: {self._player_data['coins']} coins", True, YELLOW)
            surface.blit(coin_surf, (SCREEN_W // 2 - coin_surf.get_width() // 2, y_info))

            best_lv = self._player_data.get("best_level", 0)
            best_c = self._player_data.get("best_coins", 0)
            if best_lv > 0 or best_c > 0:
                hs = self._font.render(f"Best: Level {best_lv}  |  {best_c} coins", True, (180, 160, 100))
                surface.blit(hs, (SCREEN_W // 2 - hs.get_width() // 2, y_info + 22))

        # Controls hint
        hint = self._font.render("WASD/Arrows: Move   LMB/Space: Melee   RMB: Shoot   Shift: Dash", True, (100, 100, 120))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 36))
