import json
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE, GREEN

_ACH_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "achievements.json")


def _load_achievements() -> list:
    try:
        with open(_ACH_PATH) as f:
            return json.load(f)["achievements"]
    except Exception:
        return []


class AchievementsScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._back_rect = None

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")

    def update(self, events, dt):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._back()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._back_rect and self._back_rect.collidepoint(event.pos):
                    self._back()

    def _back(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 10, 20))

        title = self._title.render("ACHIEVEMENTS", True, YELLOW)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 22))

        achs = _load_achievements()
        earned = self._player_data.get("achievements", []) if self._player_data else []

        total = len(achs)
        done  = sum(1 for a in achs if a["id"] in earned)
        prog_s = self._font.render(f"{done} / {total} unlocked", True, (160, 160, 180))
        surface.blit(prog_s, (SCREEN_W // 2 - prog_s.get_width() // 2, 88))

        cols = 2
        card_w, card_h = 420, 72
        gap_x, gap_y = 20, 12
        total_w = cols * card_w + (cols - 1) * gap_x
        x0 = SCREEN_W // 2 - total_w // 2
        y0 = 116

        for i, ach in enumerate(achs):
            col = i % cols
            row = i // cols
            cx = x0 + col * (card_w + gap_x)
            cy = y0 + row * (card_h + gap_y)

            unlocked = ach["id"] in earned

            bg     = (20, 45, 20) if unlocked else (20, 20, 30)
            border = GREEN        if unlocked else (50, 50, 65)
            pygame.draw.rect(surface, bg,     (cx, cy, card_w, card_h), border_radius=6)
            pygame.draw.rect(surface, border, (cx, cy, card_w, card_h), 2, border_radius=6)

            # Checkmark or lock icon
            icon_color = GREEN if unlocked else (80, 80, 100)
            icon_char  = "✓" if unlocked else "○"
            icon_s = self._big.render(icon_char, True, icon_color)
            surface.blit(icon_s, (cx + 10, cy + card_h // 2 - icon_s.get_height() // 2))

            name_color = WHITE if unlocked else (120, 120, 140)
            name_s = self._big.render(ach["name"], True, name_color)
            surface.blit(name_s, (cx + 44, cy + 8))

            desc_color = (160, 200, 160) if unlocked else (90, 90, 110)
            desc_s = self._font.render(ach["desc"], True, desc_color)
            surface.blit(desc_s, (cx + 44, cy + 36))

            if ach.get("reward", 0) > 0:
                rew_s = self._font.render(f"+{ach['reward']} coins", True,
                                          YELLOW if unlocked else (80, 70, 30))
                surface.blit(rew_s, (cx + card_w - rew_s.get_width() - 10, cy + 8))

            if not unlocked:
                from core.achievements import get_progress
                cur, tgt = get_progress(self._player_data or {}, ach)
                if tgt > 1:
                    bar_x = cx + 44
                    bar_y = cy + card_h - 14
                    bar_w = card_w - 54
                    frac = min(1.0, cur / tgt)
                    pygame.draw.rect(surface, (40, 40, 55), (bar_x, bar_y, bar_w, 6), border_radius=3)
                    if frac > 0:
                        pygame.draw.rect(surface, (80, 120, 200),
                                         (bar_x, bar_y, int(bar_w * frac), 6), border_radius=3)
                    prog_label = self._font.render(f"{cur}/{tgt}", True, (100, 100, 130))
                    surface.blit(prog_label, (cx + card_w - prog_label.get_width() - 10, cy + 50))

        # Back button
        btn_w, btn_h = 200, 44
        bx = SCREEN_W // 2 - btn_w // 2
        by = SCREEN_H - 56
        self._back_rect = pygame.Rect(bx, by, btn_w, btn_h)
        pygame.draw.rect(surface, DARK_GRAY, self._back_rect, border_radius=7)
        pygame.draw.rect(surface, WHITE,     self._back_rect, 2, border_radius=7)
        back_s = self._font.render("BACK  [ESC]", True, WHITE)
        surface.blit(back_s, (self._back_rect.centerx - back_s.get_width() // 2,
                               self._back_rect.centery - back_s.get_height() // 2))
