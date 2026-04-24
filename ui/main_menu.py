import json
import math
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE

_GEAR_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gear.json")
_SLOTS = ["helm", "chest", "boots", "gloves"]

def _load_gear_names() -> dict:
    try:
        with open(_GEAR_PATH) as f:
            raw = json.load(f)
        return {g["id"]: g["name"] for g in raw["gear"]}
    except Exception:
        return {}


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

            self._draw_gear_panel(surface, y_info + 50)

        # Controls hint
        hint = self._font.render("WASD/Arrows: Move   LMB/Space: Melee   RMB: Shoot   Shift: Dash", True, (100, 100, 120))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 36))

    def _draw_gear_panel(self, surface: pygame.Surface, y: int):
        gear_names = _load_gear_names()
        equipped = self._player_data.get("gear", {})
        slot_labels = {"helm": "HELM", "chest": "CHEST", "boots": "BOOTS", "gloves": "GLOVES"}

        card_w, card_h = 68, 44
        gap = 10
        total_w = len(_SLOTS) * card_w + (len(_SLOTS) - 1) * gap
        x0 = SCREEN_W // 2 - total_w // 2

        for i, slot in enumerate(_SLOTS):
            cx = x0 + i * (card_w + gap)
            gid = equipped.get(slot)
            bg = (25, 35, 55) if gid else (20, 20, 30)
            border = (80, 140, 200) if gid else (50, 50, 65)
            pygame.draw.rect(surface, bg, (cx, y, card_w, card_h), border_radius=4)
            pygame.draw.rect(surface, border, (cx, y, card_w, card_h), 1, border_radius=4)

            label_s = self._font.render(slot_labels[slot], True, (80, 90, 110))
            surface.blit(label_s, (cx + card_w // 2 - label_s.get_width() // 2, y + 3))

            name = gear_names.get(gid, "—") if gid else "—"
            name_color = YELLOW if gid else (55, 55, 70)
            name_s = self._font.render(name, True, name_color)
            # Scale down if too wide
            if name_s.get_width() > card_w - 4:
                scale = (card_w - 4) / name_s.get_width()
                name_s = pygame.transform.smoothscale(
                    name_s, (int(name_s.get_width() * scale), int(name_s.get_height() * scale))
                )
            surface.blit(name_s, (cx + card_w // 2 - name_s.get_width() // 2, y + 24))
