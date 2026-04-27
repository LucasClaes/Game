import json
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE

_CLASSES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "classes.json")
_CLASSES_CACHE: list | None = None


def _load_classes() -> list:
    global _CLASSES_CACHE
    if _CLASSES_CACHE is None:
        with open(_CLASSES_PATH) as f:
            _CLASSES_CACHE = json.load(f)["classes"]
    return _CLASSES_CACHE


def _wrap(font, text: str, max_w: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class ClassSelectScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._selected = 0
        self._card_rects: list[pygame.Rect] = []

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._selected = 0
        if self._player_data:
            run_class = self._player_data.get("run_class", "warrior")
            for i, cls in enumerate(_load_classes()):
                if cls["id"] == run_class:
                    self._selected = i
                    break

    def _available(self, cls: dict) -> bool:
        req = cls.get("requires_unlock")
        if not req:
            return True
        return req in (self._player_data or {}).get("unlocks", [])

    def update(self, events, dt):
        classes = _load_classes()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self._selected = (self._selected - 1) % len(classes)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._selected = (self._selected + 1) % len(classes)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._confirm()
                elif event.key == pygame.K_ESCAPE:
                    self._go_back()
            elif event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._card_rects):
                    if rect.collidepoint(event.pos):
                        self._selected = i
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self._card_rects):
                    if rect.collidepoint(event.pos):
                        self._selected = i
                        self._confirm()
                        return

    def _confirm(self):
        cls = _load_classes()[self._selected]
        if not self._available(cls):
            return
        from core.state_machine import GameState
        if self._player_data is not None:
            self._player_data["run_class"] = cls["id"]
        self._sm.switch_to(GameState.PLAYING, player_data=self._player_data)

    def _go_back(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((15, 15, 25))

        title_s = self._title.render("SELECT CLASS", True, YELLOW)
        surface.blit(title_s, (SCREEN_W // 2 - title_s.get_width() // 2, 22))

        hint_s = self._font.render("Click a class to start — locked classes require Unlock Tree", True, (100, 100, 120))
        surface.blit(hint_s, (SCREEN_W // 2 - hint_s.get_width() // 2, 76))

        classes = _load_classes()
        card_w, card_h = 200, 360
        gap = 12
        total_w = card_w * len(classes) + gap * (len(classes) - 1)
        cx0 = SCREEN_W // 2 - total_w // 2
        card_y = 100
        self._card_rects = []

        for i, cls in enumerate(classes):
            cx = cx0 + i * (card_w + gap)
            rect = pygame.Rect(cx, card_y, card_w, card_h)
            self._card_rects.append(rect)
            available = self._available(cls)
            selected = i == self._selected

            if selected and available:
                bg, border = (28, 42, 64), YELLOW
            elif selected:
                bg, border = (25, 25, 38), (100, 100, 130)
            elif available:
                bg, border = (20, 26, 38), (55, 80, 110)
            else:
                bg, border = (18, 18, 26), (45, 45, 58)

            pygame.draw.rect(surface, bg, rect, border_radius=10)
            pygame.draw.rect(surface, border, rect, 2, border_radius=10)

            tc = WHITE if available else (80, 80, 95)
            y = card_y + 14

            name_s = self._big.render(cls["name"], True, YELLOW if (selected and available) else tc)
            surface.blit(name_s, (rect.centerx - name_s.get_width() // 2, y))
            y += name_s.get_height() + 6

            desc_s = self._font.render(cls["desc"], True, tc)
            surface.blit(desc_s, (rect.centerx - desc_s.get_width() // 2, y))
            y += desc_s.get_height() + 14

            lbl_color = (140, 140, 160) if available else (90, 90, 105)
            lbl_s = self._font.render("STARTING", True, lbl_color)
            surface.blit(lbl_s, (cx + 10, y))
            y += lbl_s.get_height() + 4

            _START_LABELS = {
                "free_dash": "Free dash",
                "free_ranged": "Free ranged",
                "free_shield": "Free shield",
                "bonus_hp": lambda v: f"+{v} max HP",
                "bonus_speed": lambda v: f"+{int(v*100)}% speed",
                "bonus_armor": lambda v: f"+{int(v*100)}% armor",
                "bullet_pierce_bonus": lambda v: f"+{v} pierce",
            }
            for key, val in cls.get("starting", {}).items():
                spec = _START_LABELS.get(key)
                if spec is None:
                    continue
                line = spec(val) if callable(spec) else spec
                ls = self._font.render(f"  {line}", True, tc)
                surface.blit(ls, (cx + 10, y))
                y += ls.get_height() + 2
            y += 10

            lbl_s = self._font.render("PASSIVE", True, lbl_color)
            surface.blit(lbl_s, (cx + 10, y))
            y += lbl_s.get_height() + 4

            for line in _wrap(self._font, cls.get("passive_desc", ""), card_w - 20):
                ls = self._font.render(line, True, tc)
                surface.blit(ls, (cx + 10, y))
                y += ls.get_height() + 2

            if not available:
                lock_s = self._big.render("LOCKED", True, (160, 55, 55))
                surface.blit(lock_s, (rect.centerx - lock_s.get_width() // 2,
                                      card_y + card_h - 44))
                req = cls.get("requires_unlock", "")
                req_s = self._font.render(f"Req: {req}", True, (120, 75, 75))
                surface.blit(req_s, (rect.centerx - req_s.get_width() // 2,
                                     card_y + card_h - 22))
            elif selected:
                sel_s = self._big.render("SELECTED", True, YELLOW)
                surface.blit(sel_s, (rect.centerx - sel_s.get_width() // 2,
                                     card_y + card_h - 36))

        back_s = self._font.render("ESC: Back", True, (80, 80, 100))
        surface.blit(back_s, (SCREEN_W // 2 - back_s.get_width() // 2, SCREEN_H - 28))
