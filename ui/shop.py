import json
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, GREEN, BLUE, GRAY, RED


_SHOP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "shop.json")


class ShopScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._from_state = "MAIN_MENU"
        self._next_level = 0
        self._upgrades = []
        self._selected = 0
        self._feedback = ""
        self._feedback_timer = 0.0
        self._item_rects = []
        self._back_rect = None
        self._load_upgrades()

    def _load_upgrades(self):
        with open(_SHOP_PATH) as f:
            data = json.load(f)
        self._upgrades = data["upgrades"]

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._from_state = kwargs.get("from_state", "MAIN_MENU")
        self._next_level = kwargs.get("level_num", 0)
        self._selected = 0
        self._feedback = ""

    def update(self, events, dt):
        self._feedback_timer = max(0.0, self._feedback_timer - dt)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._upgrades)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._upgrades)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._try_purchase(self._selected)
                elif event.key == pygame.K_ESCAPE:
                    self._back()
            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._item_rects):
                    if rect.collidepoint(event.pos):
                        self._selected = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._back_rect and self._back_rect.collidepoint(event.pos):
                    self._back()
                    return
                for i, rect in enumerate(self._item_rects):
                    if rect.collidepoint(event.pos):
                        self._try_purchase(i)

    def _try_purchase(self, index):
        upg = self._upgrades[index]
        uid = upg["id"]
        current_level = self._player_data["upgrades"].get(uid, 0)
        max_level = upg["max_level"]
        if current_level >= max_level:
            self._set_feedback("Already maxed!", False)
            return
        cost = upg["costs"][current_level]
        if self._player_data["coins"] < cost:
            self._set_feedback("Not enough coins!", False)
            return
        self._player_data["coins"] -= cost
        self._player_data["upgrades"][uid] = current_level + 1
        from core.save import write_save
        write_save(self._player_data)
        self._set_feedback(f"Purchased: {upg['name']}!", True)

    def _set_feedback(self, msg: str, success: bool):
        self._feedback = msg
        self._feedback_color = GREEN if success else RED
        self._feedback_timer = 2.0

    def _back(self):
        from core.state_machine import GameState
        if self._from_state == "LEVEL_COMPLETE":
            self._sm.switch_to(GameState.PLAYING, player_data=self._player_data)
        else:
            self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 10, 20))

        title = self._title.render("SHOP", True, YELLOW)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 30))

        if self._player_data:
            coins_surf = self._big.render(f"Coins: {self._player_data['coins']}", True, YELLOW)
            surface.blit(coins_surf, (SCREEN_W // 2 - coins_surf.get_width() // 2, 90))

        item_w = 700
        item_h = 62
        start_x = SCREEN_W // 2 - item_w // 2
        start_y = 140
        gap = 68

        self._item_rects = []
        for i, upg in enumerate(self._upgrades):
            rect = pygame.Rect(start_x, start_y + i * gap, item_w, item_h)
            self._item_rects.append(rect)
            selected = i == self._selected
            uid = upg["id"]
            cur_lv = self._player_data["upgrades"].get(uid, 0) if self._player_data else 0
            maxed = cur_lv >= upg["max_level"]
            affordable = (self._player_data and
                          not maxed and
                          self._player_data["coins"] >= upg["costs"][cur_lv])

            bg = (30, 50, 90) if selected else DARK_GRAY
            border = WHITE if selected else (70, 70, 70)
            if maxed:
                bg = (20, 50, 20)
                border = GREEN
            elif not affordable and not maxed:
                bg = (40, 20, 20)

            pygame.draw.rect(surface, bg, rect, border_radius=7)
            pygame.draw.rect(surface, border, rect, 2, border_radius=7)

            # Name + description
            name_s = self._font.render(upg["name"], True, WHITE)
            desc_s = self._font.render(upg["description"], True, (160, 160, 180))
            surface.blit(name_s, (rect.x + 14, rect.y + 8))
            surface.blit(desc_s, (rect.x + 14, rect.y + 32))

            # Level indicator
            lv_text = f"Lv {cur_lv}/{upg['max_level']}"
            lv_color = GREEN if maxed else (WHITE if selected else GRAY)
            lv_s = self._font.render(lv_text, True, lv_color)
            surface.blit(lv_s, (rect.right - lv_s.get_width() - 110, rect.y + 8))

            # Cost
            if maxed:
                cost_text = "MAX"
                cost_color = GREEN
            else:
                cost_text = f"{upg['costs'][cur_lv]} coins"
                cost_color = YELLOW if affordable else RED
            cost_s = self._font.render(cost_text, True, cost_color)
            surface.blit(cost_s, (rect.right - cost_s.get_width() - 14, rect.y + 26))

        # Feedback
        if self._feedback_timer > 0:
            alpha = min(255, int(self._feedback_timer * 255))
            fb_s = self._font.render(self._feedback, True, self._feedback_color)
            fb_s.set_alpha(alpha)
            surface.blit(fb_s, (SCREEN_W // 2 - fb_s.get_width() // 2,
                                 start_y + len(self._upgrades) * gap + 10))

        # Back button
        btn_w, btn_h = 160, 44
        bx = SCREEN_W // 2 - btn_w // 2
        by = SCREEN_H - 60
        self._back_rect = pygame.Rect(bx, by, btn_w, btn_h)
        pygame.draw.rect(surface, DARK_GRAY, self._back_rect, border_radius=7)
        pygame.draw.rect(surface, WHITE, self._back_rect, 2, border_radius=7)
        back_s = self._font.render("BACK  [ESC]", True, WHITE)
        surface.blit(back_s, (self._back_rect.centerx - back_s.get_width() // 2,
                               self._back_rect.centery - back_s.get_height() // 2))
