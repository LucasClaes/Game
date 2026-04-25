import datetime
import json
import math
import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE, DIFFICULTIES

_GEAR_PATH       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gear.json")
_CHALLENGES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "challenges.json")
_SLOTS = ["helm", "chest", "boots", "gloves"]

_DIFF_COLORS = [(50, 200, 80), (200, 200, 200), (255, 140, 0), (220, 50, 50)]


def _load_gear_names() -> dict:
    try:
        with open(_GEAR_PATH) as f:
            raw = json.load(f)
        return {g["id"]: g["name"] for g in raw["gear"]}
    except Exception:
        return {}


def _load_challenges() -> list:
    try:
        with open(_CHALLENGES_PATH) as f:
            return json.load(f)["challenges"]
    except Exception:
        return []


def _today_challenge(challenges: list) -> dict | None:
    if not challenges:
        return None
    epoch = datetime.date(1970, 1, 1)
    days  = (datetime.date.today() - epoch).days
    return challenges[days % len(challenges)]


class MainMenuScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm          = state_manager
        self._font        = font
        self._big         = big_font
        self._title       = title_font
        self._buttons     = ["PLAY", "CHALLENGE", "SHOP", "CODEX", "ACHIEVEMENTS", "SETTINGS", "QUIT"]
        self._selected    = 0
        self._player_data = None
        self._anim        = 0.0
        self._btn_rects   : list = []
        self._diff_arrows : dict = {}   # "left" / "right" rects
        self._challenge_overlay = False
        self._challenge_btns    : dict = {}

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._selected = 0
        self._challenge_overlay = False
        try:
            from systems.audio import audio
            audio.play_music("menu")
        except Exception:
            pass

    def _diff_idx(self) -> int:
        return self._player_data.get("difficulty", 1) if self._player_data else 1

    def _set_diff(self, delta: int):
        if not self._player_data:
            return
        idx = (self._diff_idx() + delta) % len(DIFFICULTIES)
        self._player_data["difficulty"] = idx
        from core.save import write_save
        write_save(self._player_data)

    def update(self, events, dt):
        self._anim += dt

        if self._challenge_overlay:
            self._update_challenge_overlay(events)
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._buttons)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._buttons)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if self._selected == -1:
                        self._set_diff(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self._selected == -1:
                        self._set_diff(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._activate(self._selected)
            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._btn_rects):
                    if rect.collidepoint(event.pos):
                        self._selected = i
                for key, rect in self._diff_arrows.items():
                    if rect.collidepoint(event.pos):
                        self._selected = -1
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for key, rect in self._diff_arrows.items():
                    if rect.collidepoint(event.pos):
                        self._set_diff(-1 if key == "left" else 1)
                        return
                for i, rect in enumerate(self._btn_rects):
                    if rect.collidepoint(event.pos):
                        self._activate(i)
                        return

    def _update_challenge_overlay(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._challenge_overlay = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._challenge_btns.get("play") and self._challenge_btns["play"].collidepoint(event.pos):
                    self._start_challenge()
                elif self._challenge_btns.get("back") and self._challenge_btns["back"].collidepoint(event.pos):
                    self._challenge_overlay = False

    def _start_challenge(self):
        challenges = _load_challenges()
        today = _today_challenge(challenges)
        if today is None:
            return
        from core.state_machine import GameState
        pd = self._player_data.copy() if self._player_data else {}
        pd["current_level"] = 0
        pd["run_perks"] = []
        self._sm.switch_to(GameState.PLAYING, player_data=pd,
                           challenge_modifier=today["modifier"],
                           challenge_id=today["id"],
                           challenge_reward=today["reward"])

    def _activate(self, index):
        from core.state_machine import GameState
        label = self._buttons[index]
        if label == "PLAY":
            self._sm.switch_to(GameState.PLAYING, player_data=self._player_data)
        elif label == "CHALLENGE":
            self._challenge_overlay = True
        elif label == "SHOP":
            self._sm.switch_to(GameState.SHOP, player_data=self._player_data, from_state="MAIN_MENU")
        elif label == "CODEX":
            self._sm.switch_to(GameState.CODEX, player_data=self._player_data)
        elif label == "ACHIEVEMENTS":
            self._sm.switch_to(GameState.ACHIEVEMENTS, player_data=self._player_data)
        elif label == "SETTINGS":
            self._sm.switch_to(GameState.SETTINGS, player_data=self._player_data, from_state="MAIN_MENU")
        elif label == "QUIT":
            pygame.quit()
            import sys; sys.exit()

    def draw(self, surface: pygame.Surface):
        surface.fill((15, 15, 25))

        title_surf = self._title.render("ZOMBIE MAZE", True, YELLOW)
        tx = SCREEN_W // 2 - title_surf.get_width() // 2
        ty = 38 + int(math.sin(self._anim) * 4)
        surface.blit(title_surf, (tx, ty))

        sub = self._font.render("Collect coins. Kill zombies. Survive.", True, (160, 160, 180))
        surface.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 108))

        # Difficulty selector
        diff_idx   = self._diff_idx()
        diff       = DIFFICULTIES[diff_idx]
        diff_color = _DIFF_COLORS[diff_idx]
        sel_y      = 132

        arr_w = 28
        name_s = self._big.render(diff["name"], True, diff_color)
        total_w = arr_w * 2 + name_s.get_width() + 16
        sx0 = SCREEN_W // 2 - total_w // 2

        left_rect  = pygame.Rect(sx0, sel_y, arr_w, 28)
        right_rect = pygame.Rect(sx0 + total_w - arr_w, sel_y, arr_w, 28)
        self._diff_arrows = {"left": left_rect, "right": right_rect}

        pygame.draw.rect(surface, DARK_GRAY, left_rect,  border_radius=4)
        pygame.draw.rect(surface, DARK_GRAY, right_rect, border_radius=4)
        larr = self._font.render("◄", True, WHITE)
        rarr = self._font.render("►", True, WHITE)
        surface.blit(larr, (left_rect.centerx  - larr.get_width() // 2, left_rect.centery  - larr.get_height() // 2))
        surface.blit(rarr, (right_rect.centerx - rarr.get_width() // 2, right_rect.centery - rarr.get_height() // 2))
        surface.blit(name_s, (sx0 + arr_w + 8, sel_y + 14 - name_s.get_height() // 2))

        diff_hint = self._font.render("Difficulty", True, (100, 100, 120))
        surface.blit(diff_hint, (SCREEN_W // 2 - diff_hint.get_width() // 2, sel_y - 14))

        # Buttons
        self._btn_rects = []
        btn_w, btn_h = 240, 42
        start_y = 174
        gap     = 52
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

        # Stats
        y_info = start_y + len(self._buttons) * gap + 4
        if self._player_data:
            coin_surf = self._font.render(f"Bank: {self._player_data['coins']} coins", True, YELLOW)
            surface.blit(coin_surf, (SCREEN_W // 2 - coin_surf.get_width() // 2, y_info))

            best_lv = self._player_data.get("best_level", 0)
            best_c  = self._player_data.get("best_coins", 0)
            if best_lv > 0 or best_c > 0:
                hs = self._font.render(f"Best: Level {best_lv}  |  {best_c} coins", True, (180, 160, 100))
                surface.blit(hs, (SCREEN_W // 2 - hs.get_width() // 2, y_info + 20))

        # Controls hint
        hint = self._font.render("WASD: Move   LMB/Space: Melee   RMB: Shoot   Shift: Dash", True, (100, 100, 120))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 28))

        if self._challenge_overlay:
            self._draw_challenge_overlay(surface)

    def _draw_challenge_overlay(self, surface: pygame.Surface):
        challenges = _load_challenges()
        today = _today_challenge(challenges)

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        box_w, box_h = 520, 300
        bx = SCREEN_W // 2 - box_w // 2
        by = SCREEN_H // 2 - box_h // 2
        pygame.draw.rect(surface, (15, 20, 35), (bx, by, box_w, box_h), border_radius=12)
        pygame.draw.rect(surface, YELLOW,       (bx, by, box_w, box_h), 2, border_radius=12)

        hdr = self._big.render("TODAY'S CHALLENGE", True, YELLOW)
        surface.blit(hdr, (SCREEN_W // 2 - hdr.get_width() // 2, by + 20))

        if today:
            name_s = self._title.render(today["name"], True, WHITE)
            surface.blit(name_s, (SCREEN_W // 2 - name_s.get_width() // 2, by + 60))
            desc_s = self._font.render(today["desc"], True, (180, 180, 200))
            surface.blit(desc_s, (SCREEN_W // 2 - desc_s.get_width() // 2, by + 118))
            rew_s = self._font.render(f"Reward: +{today['reward']} coins on completion", True, YELLOW)
            surface.blit(rew_s, (SCREEN_W // 2 - rew_s.get_width() // 2, by + 148))

            wins = self._player_data.get("challenge_wins", {}) if self._player_data else {}
            if today["id"] in wins:
                done_s = self._font.render(f"Best: level {wins[today['id']]} reached", True, (100, 200, 100))
                surface.blit(done_s, (SCREEN_W // 2 - done_s.get_width() // 2, by + 172))
        else:
            ns = self._font.render("No challenges available.", True, (140, 140, 160))
            surface.blit(ns, (SCREEN_W // 2 - ns.get_width() // 2, by + 100))

        btn_w, btn_h = 180, 44
        gap = 20
        total_btn = btn_w * 2 + gap
        b0 = SCREEN_W // 2 - total_btn // 2

        play_rect = pygame.Rect(b0,            by + box_h - 68, btn_w, btn_h)
        back_rect = pygame.Rect(b0 + btn_w + gap, by + box_h - 68, btn_w, btn_h)
        self._challenge_btns = {"play": play_rect, "back": back_rect}

        pygame.draw.rect(surface, BLUE,      play_rect, border_radius=7)
        pygame.draw.rect(surface, DARK_GRAY, back_rect, border_radius=7)
        pygame.draw.rect(surface, WHITE, play_rect, 2, border_radius=7)
        pygame.draw.rect(surface, WHITE, back_rect, 2, border_radius=7)

        ps = self._big.render("PLAY", True, WHITE)
        bs = self._big.render("BACK", True, WHITE)
        surface.blit(ps, (play_rect.centerx - ps.get_width() // 2, play_rect.centery - ps.get_height() // 2))
        surface.blit(bs, (back_rect.centerx - bs.get_width() // 2, back_rect.centery - bs.get_height() // 2))
