import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE


class SettingsScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._from_state = "MAIN_MENU"
        self._items = ["Music Volume", "SFX Volume"]
        self._selected = 0

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._from_state = kwargs.get("from_state", "MAIN_MENU")
        self._selected = 0

    def _get_val(self, idx: int) -> int:
        key = "music_vol" if idx == 0 else "sfx_vol"
        default = 0.4 if idx == 0 else 1.0
        return round(self._player_data.get(key, default) * 10) * 10

    def _set_val(self, idx: int, val: int):
        key = "music_vol" if idx == 0 else "sfx_vol"
        clamped = max(0, min(100, val))
        self._player_data[key] = clamped / 100.0
        try:
            from systems.audio import audio
            if idx == 0:
                audio.set_music_volume(clamped / 100.0)
            else:
                audio.set_sfx_volume(clamped / 100.0)
        except Exception:
            pass
        from core.save import write_save
        write_save(self._player_data)

    def update(self, events, dt):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._items)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._items)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._set_val(self._selected, self._get_val(self._selected) - 10)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._set_val(self._selected, self._get_val(self._selected) + 10)
                elif event.key == pygame.K_ESCAPE:
                    self._back()
            if event.type == pygame.MOUSEMOTION:
                for i in range(len(self._items)):
                    row_y = 220 + i * 110
                    if row_y <= event.pos[1] <= row_y + 80:
                        self._selected = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                bx = SCREEN_W // 2 - 160
                for i in range(len(self._items)):
                    by = 220 + i * 110 + 38
                    if bx <= event.pos[0] <= bx + 320 and by - 10 <= event.pos[1] <= by + 28:
                        raw = int((event.pos[0] - bx) / 320 * 100)
                        rounded = max(0, min(100, round(raw / 10) * 10))
                        self._set_val(i, rounded)

    def _back(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 12, 22))

        title = self._title.render("SETTINGS", True, YELLOW)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))

        for i, label in enumerate(self._items):
            val = self._get_val(i)
            selected = i == self._selected
            y = 220 + i * 110
            color = WHITE if selected else (140, 140, 160)
            lbl = self._big.render(label, True, color)
            surface.blit(lbl, (SCREEN_W // 2 - lbl.get_width() // 2, y))

            bar_w, bar_h = 320, 18
            bx = SCREEN_W // 2 - bar_w // 2
            by = y + 38
            pygame.draw.rect(surface, DARK_GRAY, (bx, by, bar_w, bar_h), border_radius=4)
            fill_w = int(bar_w * val / 100)
            bar_col = BLUE if selected else (50, 80, 150)
            if fill_w > 0:
                pygame.draw.rect(surface, bar_col, (bx, by, fill_w, bar_h), border_radius=4)
            border_col = WHITE if selected else (80, 80, 80)
            pygame.draw.rect(surface, border_col, (bx, by, bar_w, bar_h), 2, border_radius=4)
            pct = self._font.render(f"{val}%", True, YELLOW if selected else (160, 160, 160))
            surface.blit(pct, (bx + bar_w + 12, by + 1))

        hint = self._font.render("W/S: Select   A/D or Arrows: Adjust   ESC: Back", True, (80, 80, 100))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 40))
