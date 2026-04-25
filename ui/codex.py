import json
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE, GREEN

_PERKS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "perks.json")
_GEAR_PATH  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gear.json")

_SLOT_ORDER = ["helm", "chest", "boots", "gloves"]
_SLOT_LABELS = {"helm": "HELM", "chest": "CHEST", "boots": "BOOTS", "gloves": "GLOVES"}


def _load_perks() -> list:
    try:
        with open(_PERKS_PATH) as f:
            return json.load(f)["perks"]
    except Exception:
        return []


def _load_gear() -> list:
    try:
        with open(_GEAR_PATH) as f:
            return json.load(f)["gear"]
    except Exception:
        return []


class CodexScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._tab = 0  # 0=PERKS, 1=GEAR
        self._tab_rects: list = []
        self._back_rect = None

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._tab = 0

    def update(self, events, dt):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._back()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._tab = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._tab = 1
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._back_rect and self._back_rect.collidepoint(event.pos):
                    self._back()
                for i, rect in enumerate(self._tab_rects):
                    if rect.collidepoint(event.pos):
                        self._tab = i

    def _back(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 10, 20))

        title = self._title.render("CODEX", True, YELLOW)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 18))

        # Tabs
        tab_names = ["PERKS", "GEAR"]
        tab_w, tab_h = 160, 34
        tab_gap = 10
        total_tab_w = len(tab_names) * tab_w + (len(tab_names) - 1) * tab_gap
        tab_x0 = SCREEN_W // 2 - total_tab_w // 2
        tab_y = 80
        self._tab_rects = []
        for i, name in enumerate(tab_names):
            rect = pygame.Rect(tab_x0 + i * (tab_w + tab_gap), tab_y, tab_w, tab_h)
            self._tab_rects.append(rect)
            selected = i == self._tab
            pygame.draw.rect(surface, BLUE if selected else (25, 25, 45), rect, border_radius=6)
            pygame.draw.rect(surface, WHITE if selected else (60, 60, 80), rect, 2, border_radius=6)
            t = self._font.render(name, True, WHITE if selected else (140, 140, 160))
            surface.blit(t, (rect.centerx - t.get_width() // 2,
                              rect.centery - t.get_height() // 2))

        content_y = tab_y + tab_h + 14

        if self._tab == 0:
            self._draw_perks(surface, content_y)
        else:
            self._draw_gear(surface, content_y)

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

    def _draw_perks(self, surface: pygame.Surface, y0: int):
        perks = _load_perks()
        seen  = self._player_data.get("seen_perks", []) if self._player_data else []

        cols = 2
        card_w, card_h = 420, 64
        gap_x, gap_y = 20, 8
        total_w = cols * card_w + (cols - 1) * gap_x
        x0 = SCREEN_W // 2 - total_w // 2

        for i, perk in enumerate(perks):
            col = i % cols
            row = i // cols
            cx = x0 + col * (card_w + gap_x)
            cy = y0 + row * (card_h + gap_y)

            revealed = perk["id"] in seen
            bg     = (22, 40, 22) if revealed else (20, 20, 30)
            border = GREEN        if revealed else (50, 50, 65)
            pygame.draw.rect(surface, bg,     (cx, cy, card_w, card_h), border_radius=6)
            pygame.draw.rect(surface, border, (cx, cy, card_w, card_h), 2, border_radius=6)

            if revealed:
                name_s = self._big.render(perk["name"], True, WHITE)
                desc_s = self._font.render(perk["desc"], True, (150, 190, 150))
                surface.blit(name_s, (cx + 12, cy + 8))
                surface.blit(desc_s, (cx + 12, cy + 36))
            else:
                lock_s = self._big.render(perk["name"], True, (55, 55, 70))
                surface.blit(lock_s, (cx + 12, cy + 8))
                hint_s = self._font.render("— not yet encountered —", True, (50, 50, 65))
                surface.blit(hint_s, (cx + 12, cy + 36))

    def _draw_gear(self, surface: pygame.Surface, y0: int):
        gear_list = _load_gear()
        found    = self._player_data.get("found_gear", []) if self._player_data else []
        equipped = self._player_data.get("gear", {}) if self._player_data else {}

        # Group by slot
        by_slot: dict[str, list] = {s: [] for s in _SLOT_ORDER}
        for g in gear_list:
            by_slot[g["slot"]].append(g)

        cols = 2
        card_w, card_h = 420, 64
        gap_x, gap_y = 20, 8
        total_w = cols * card_w + (cols - 1) * gap_x
        x0 = SCREEN_W // 2 - total_w // 2

        row = 0
        for slot in _SLOT_ORDER:
            items = by_slot[slot]
            for i, piece in enumerate(items):
                col = i % cols
                if i > 0 and col == 0:
                    row += 1
                cx = x0 + col * (card_w + gap_x)
                cy = y0 + row * (card_h + gap_y)

                is_found    = piece["id"] in found
                is_equipped = equipped.get(piece["slot"]) == piece["id"]

                if is_equipped:
                    bg, border = (20, 40, 65), (80, 150, 220)
                elif is_found:
                    bg, border = (22, 38, 22), GREEN
                else:
                    bg, border = (20, 20, 30), (50, 50, 65)

                pygame.draw.rect(surface, bg,     (cx, cy, card_w, card_h), border_radius=6)
                pygame.draw.rect(surface, border, (cx, cy, card_w, card_h), 2, border_radius=6)

                slot_s = self._font.render(_SLOT_LABELS[piece["slot"]], True, (80, 90, 110))
                surface.blit(slot_s, (cx + 12, cy + 6))

                if is_found or is_equipped:
                    name_color = (80, 180, 240) if is_equipped else WHITE
                    name_s = self._big.render(piece["name"], True, name_color)
                    surface.blit(name_s, (cx + 12, cy + 26))
                    desc_s = self._font.render(piece["desc"], True, (150, 180, 160))
                    surface.blit(desc_s, (cx + card_w // 2, cy + 26))
                    if is_equipped:
                        eq_s = self._font.render("[EQUIPPED]", True, (80, 150, 220))
                        surface.blit(eq_s, (cx + card_w - eq_s.get_width() - 10, cy + 6))
                else:
                    lock_s = self._big.render("???", True, (50, 50, 65))
                    surface.blit(lock_s, (cx + 12, cy + 26))
                    hint_s = self._font.render("— find in a crate to reveal —", True, (45, 45, 58))
                    surface.blit(hint_s, (cx + card_w // 2, cy + 26))

            row += 1
