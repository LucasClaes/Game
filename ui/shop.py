import json
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, GREEN, BLUE, GRAY, RED


_SHOP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "shop.json")

_TAB_CATS = {"STATS": "stats", "ABILITIES": "abilities", "ITEMS": "items"}
_TABS = ["STATS", "ABILITIES", "ITEMS"]


class ShopScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._all_upgrades = []
        self._tab_idx = 0
        self._tab_sel = [0, 0, 0]
        self._feedback = ""
        self._feedback_color = GREEN
        self._feedback_timer = 0.0
        self._tab_rects = []
        self._item_rects = []
        self._back_rect = None
        self._load_upgrades()

    def _load_upgrades(self):
        with open(_SHOP_PATH) as f:
            self._all_upgrades = json.load(f)["upgrades"]

    def _tab_items(self) -> list:
        cat = _TAB_CATS[_TABS[self._tab_idx]]
        return [u for u in self._all_upgrades if u.get("category") == cat]

    def _switch_tab(self, idx: int):
        self._tab_idx = idx % len(_TABS)
        items = self._tab_items()
        if items:
            self._tab_sel[self._tab_idx] = min(self._tab_sel[self._tab_idx], len(items) - 1)

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._tab_idx = 0
        self._tab_sel = [0, 0, 0]
        self._feedback = ""
        try:
            from systems.audio import audio
            audio.play_music("shop")
        except Exception:
            pass

    def update(self, events, dt):
        self._feedback_timer = max(0.0, self._feedback_timer - dt)
        items = self._tab_items()
        n = len(items)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self._switch_tab(self._tab_idx - 1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._switch_tab(self._tab_idx + 1)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    if n: self._tab_sel[self._tab_idx] = (self._tab_sel[self._tab_idx] - 1) % n
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    if n: self._tab_sel[self._tab_idx] = (self._tab_sel[self._tab_idx] + 1) % n
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if n: self._try_purchase(self._tab_sel[self._tab_idx])
                elif event.key == pygame.K_ESCAPE:
                    self._back()
            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._tab_rects):
                    if rect.collidepoint(event.pos):
                        self._switch_tab(i)
                        break
                for i, rect in enumerate(self._item_rects):
                    if rect.collidepoint(event.pos):
                        self._tab_sel[self._tab_idx] = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self._tab_rects):
                    if rect.collidepoint(event.pos):
                        self._switch_tab(i)
                        return
                if self._back_rect and self._back_rect.collidepoint(event.pos):
                    self._back()
                    return
                for i, rect in enumerate(self._item_rects):
                    if rect.collidepoint(event.pos):
                        self._try_purchase(i)

    def _current_level(self, upg: dict) -> int:
        uid = upg["id"]
        if upg.get("consumable"):
            return self._player_data.get(uid, 0) // upg.get("grant", 1)
        return self._player_data["upgrades"].get(uid, 0)

    def _try_purchase(self, index: int):
        items = self._tab_items()
        if not items or index >= len(items):
            return
        upg = items[index]
        uid = upg["id"]
        cur_lv = self._current_level(upg)
        if cur_lv >= upg["max_level"]:
            self._set_feedback("Already maxed!", False)
            return
        cost = upg["costs"][cur_lv]
        if self._player_data["coins"] < cost:
            self._set_feedback("Not enough coins!", False)
            return
        self._player_data["coins"] -= cost
        if upg.get("consumable"):
            self._player_data[uid] = self._player_data.get(uid, 0) + upg.get("grant", 1)
        else:
            self._player_data["upgrades"][uid] = cur_lv + 1
        from core.save import write_save
        write_save(self._player_data)
        self._set_feedback(f"Purchased: {upg['name']}!", True)

    def _set_feedback(self, msg: str, success: bool):
        self._feedback = msg
        self._feedback_color = GREEN if success else RED
        self._feedback_timer = 2.0

    def _back(self):
        from core.state_machine import GameState
        self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 10, 20))

        title = self._title.render("SHOP", True, YELLOW)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 22))

        if self._player_data:
            coins_surf = self._big.render(f"Coins: {self._player_data['coins']}", True, YELLOW)
            surface.blit(coins_surf, (SCREEN_W // 2 - coins_surf.get_width() // 2, 76))

        # Tab headers
        tab_h = 34
        tab_gap = 8
        tab_w = (min(700, SCREEN_W - 40) - tab_gap * 2) // 3
        tab_total = tab_w * 3 + tab_gap * 2
        tab_x0 = SCREEN_W // 2 - tab_total // 2
        tab_y = 112

        self._tab_rects = []
        for i, name in enumerate(_TABS):
            rect = pygame.Rect(tab_x0 + i * (tab_w + tab_gap), tab_y, tab_w, tab_h)
            self._tab_rects.append(rect)
            selected = i == self._tab_idx
            bg = BLUE if selected else (25, 25, 45)
            border = WHITE if selected else (60, 60, 80)
            pygame.draw.rect(surface, bg, rect, border_radius=6)
            pygame.draw.rect(surface, border, rect, 2, border_radius=6)
            t = self._font.render(name, True, WHITE if selected else (140, 140, 160))
            surface.blit(t, (rect.centerx - t.get_width() // 2,
                             rect.centery - t.get_height() // 2))

        # Items
        items = self._tab_items()
        item_w = 700
        n = len(items)
        start_x = SCREEN_W // 2 - item_w // 2
        start_y = tab_y + tab_h + 8
        available = SCREEN_H - start_y - 64  # leave room for back button
        item_h = max(44, min(70, (available - (n - 1) * 4) // max(n, 1)))
        gap = item_h + 4

        self._item_rects = []
        for i, upg in enumerate(items):
            rect = pygame.Rect(start_x, start_y + i * gap, item_w, item_h)
            self._item_rects.append(rect)
            selected = i == self._tab_sel[self._tab_idx]
            uid = upg["id"]
            cur_lv = self._current_level(upg) if self._player_data else 0
            maxed = cur_lv >= upg["max_level"]
            affordable = (self._player_data and not maxed and
                          self._player_data["coins"] >= upg["costs"][cur_lv])

            bg = (30, 50, 90) if selected else DARK_GRAY
            border = WHITE if selected else (70, 70, 70)
            if maxed:
                bg, border = (20, 50, 20), GREEN
            elif not affordable:
                bg = (40, 20, 20)

            pygame.draw.rect(surface, bg, rect, border_radius=7)
            pygame.draw.rect(surface, border, rect, 2, border_radius=7)

            name_s = self._font.render(upg["name"], True, WHITE)
            desc_s = self._font.render(upg["description"], True, (160, 160, 180))
            surface.blit(name_s, (rect.x + 14, rect.y + 6))
            surface.blit(desc_s, (rect.x + 14, rect.y + 28))

            if upg.get("consumable"):
                stock = self._player_data.get(uid, 0) if self._player_data else 0
                max_stock = upg["max_level"] * upg.get("grant", 1)
                lv_text = f"Stock: {stock}/{max_stock}"
            else:
                lv_text = f"Lv {cur_lv}/{upg['max_level']}"
            lv_color = GREEN if maxed else (WHITE if selected else GRAY)
            lv_s = self._font.render(lv_text, True, lv_color)
            surface.blit(lv_s, (rect.right - lv_s.get_width() - 110, rect.y + 6))

            if maxed:
                cost_text, cost_color = "MAX", GREEN
            else:
                cost_text = f"{upg['costs'][cur_lv]} coins"
                cost_color = YELLOW if affordable else RED
            cost_s = self._font.render(cost_text, True, cost_color)
            surface.blit(cost_s, (rect.right - cost_s.get_width() - 14, rect.y + 24))

        # Feedback
        if self._feedback_timer > 0:
            fb_s = self._font.render(self._feedback, True, self._feedback_color)
            fb_s.set_alpha(min(255, int(self._feedback_timer * 255)))
            surface.blit(fb_s, (SCREEN_W // 2 - fb_s.get_width() // 2, SCREEN_H - 90))

        # Back / main menu button
        btn_w, btn_h = 200, 44
        bx = SCREEN_W // 2 - btn_w // 2
        by = SCREEN_H - 58
        self._back_rect = pygame.Rect(bx, by, btn_w, btn_h)
        pygame.draw.rect(surface, DARK_GRAY, self._back_rect, border_radius=7)
        pygame.draw.rect(surface, WHITE, self._back_rect, 2, border_radius=7)
        back_s = self._font.render("MAIN MENU  [ESC]", True, WHITE)
        surface.blit(back_s, (self._back_rect.centerx - back_s.get_width() // 2,
                               self._back_rect.centery - back_s.get_height() // 2))

        # Tab navigation hint
        nav = self._font.render("A/D or ← → to switch tabs", True, (70, 70, 90))
        surface.blit(nav, (SCREEN_W // 2 - nav.get_width() // 2, SCREEN_H - 28))
