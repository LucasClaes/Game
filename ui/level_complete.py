import json
import os
import random
import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, GREEN, BLUE

_PERKS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "perks.json")
_MAX_PERKS = 4


def _load_perks() -> list:
    try:
        with open(_PERKS_PATH) as f:
            return json.load(f)["perks"]
    except Exception:
        return []


class LevelCompleteScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._coins_earned = 0
        self._level_num = 0
        self._buttons = ["CONTINUE", "SHOP", "MAIN MENU"]
        self._selected = 0
        self._btn_rects = []
        # Perk selection
        self._perk_phase = False
        self._offered_perks: list = []
        self._perk_sel = 0
        self._perk_rects: list = []
        self._kill_count = 0
        self._elapsed = 0.0
        self._challenge_modifier: str | None = None
        self._challenge_id: str | None = None
        self._challenge_reward: int = 0

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._coins_earned = kwargs.get("coins_earned", 0)
        self._level_num = kwargs.get("level_num", 0)
        self._kill_count = kwargs.get("kill_count", 0)
        self._elapsed = kwargs.get("elapsed", 0.0)
        self._challenge_modifier = kwargs.get("challenge_modifier", None)
        self._challenge_id       = kwargs.get("challenge_id", None)
        self._challenge_reward   = kwargs.get("challenge_reward", 0)
        self._selected = 0
        self._perk_sel = 0
        self._perk_rects = []
        self._setup_perk_phase()
        try:
            from systems.audio import audio
            audio.play_music("levelcomplete")
        except Exception:
            pass

    def _setup_perk_phase(self):
        owned = self._player_data.get("run_perks", []) if self._player_data else []
        if len(owned) >= _MAX_PERKS:
            self._perk_phase = False
            return
        all_perks = _load_perks()
        available = [p for p in all_perks if p["id"] not in owned]
        if not available:
            self._perk_phase = False
            return
        count = min(3, len(available))
        self._offered_perks = random.sample(available, count)
        self._perk_phase = True

        # Track seen perks
        if self._player_data:
            seen = self._player_data.setdefault("seen_perks", [])
            for p in self._offered_perks:
                if p["id"] not in seen:
                    seen.append(p["id"])
            from core.save import write_save
            write_save(self._player_data)

    def update(self, events, dt):
        if self._perk_phase:
            self._update_perk(events)
        else:
            self._update_buttons(events)

    def _update_perk(self, events):
        n = len(self._offered_perks)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self._perk_sel = (self._perk_sel - 1) % n
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._perk_sel = (self._perk_sel + 1) % n
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._pick_perk(self._perk_sel)
            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._perk_rects):
                    if rect.collidepoint(event.pos):
                        self._perk_sel = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self._perk_rects):
                    if rect.collidepoint(event.pos):
                        self._pick_perk(i)

    def _pick_perk(self, index: int):
        perk = self._offered_perks[index]
        perks = self._player_data.setdefault("run_perks", [])
        if perk["id"] not in perks:
            perks.append(perk["id"])
        try:
            from systems.audio import audio
            audio.play("perk_get")
        except Exception:
            pass
        self._perk_phase = False

    def _update_buttons(self, events):
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
        ck = dict(challenge_modifier=self._challenge_modifier,
                  challenge_id=self._challenge_id,
                  challenge_reward=self._challenge_reward)
        if label == "CONTINUE":
            self._sm.switch_to(GameState.PLAYING, player_data=self._player_data, **ck)
        elif label == "SHOP":
            if self._challenge_modifier == "no_shop":
                # Skip shop in no_shop challenge
                self._sm.switch_to(GameState.PLAYING, player_data=self._player_data, **ck)
            else:
                self._sm.switch_to(GameState.SHOP, player_data=self._player_data,
                                   from_state="LEVEL_COMPLETE", level_num=next_level)
        elif label == "MAIN MENU":
            from core.save import write_save
            write_save(self._player_data)
            self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)

    def draw(self, surface: pygame.Surface):
        surface.fill((5, 20, 10))

        title = self._title.render("LEVEL CLEAR!", True, GREEN)
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 30))

        lv = self._font.render(f"Level {self._level_num + 1} complete", True, WHITE)
        surface.blit(lv, (SCREEN_W // 2 - lv.get_width() // 2, 110))

        earned = self._font.render(f"+{self._coins_earned} coins", True, YELLOW)
        surface.blit(earned, (SCREEN_W // 2 - earned.get_width() // 2, 134))

        if self._player_data:
            bank = self._font.render(f"Bank: {self._player_data['coins']} coins", True, YELLOW)
            surface.blit(bank, (SCREEN_W // 2 - bank.get_width() // 2, 158))

        if self._perk_phase:
            self._draw_perks(surface)
        else:
            self._draw_buttons(surface)

    def _draw_perks(self, surface: pygame.Surface):
        sub = self._big.render("CHOOSE A PERK", True, (160, 220, 160))
        surface.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 196))

        n = len(self._offered_perks)
        card_w, card_h = 250, 130
        gap = 16
        total_w = n * card_w + (n - 1) * gap
        x0 = SCREEN_W // 2 - total_w // 2
        card_y = 238

        self._perk_rects = []
        for i, perk in enumerate(self._offered_perks):
            cx = x0 + i * (card_w + gap)
            rect = pygame.Rect(cx, card_y, card_w, card_h)
            self._perk_rects.append(rect)
            selected = i == self._perk_sel
            bg = (30, 60, 40) if selected else (18, 32, 22)
            border = GREEN if selected else (40, 70, 45)
            pygame.draw.rect(surface, bg, rect, border_radius=8)
            pygame.draw.rect(surface, border, rect, 2, border_radius=8)

            name_s = self._big.render(perk["name"], True, WHITE if selected else (180, 200, 180))
            surface.blit(name_s, (rect.centerx - name_s.get_width() // 2, rect.y + 14))

            # Word-wrap desc across 2 lines max
            words = perk["desc"].split()
            lines, line = [], []
            for w in words:
                test = " ".join(line + [w])
                if self._font.size(test)[0] > card_w - 20:
                    if line:
                        lines.append(" ".join(line))
                    line = [w]
                else:
                    line.append(w)
            if line:
                lines.append(" ".join(line))
            for j, ln in enumerate(lines[:3]):
                ls = self._font.render(ln, True, (140, 170, 145))
                surface.blit(ls, (rect.centerx - ls.get_width() // 2, rect.y + 58 + j * 20))

        hint = self._font.render("A/D or  ←→  to browse   ENTER to pick", True, (60, 90, 65))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, card_y + card_h + 14))

    def _draw_buttons(self, surface: pygame.Surface):
        mins = int(self._elapsed) // 60
        secs = int(self._elapsed) % 60
        kills_s = self._font.render(f"Kills: {self._kill_count}   Time: {mins}:{secs:02d}", True, (160, 200, 160))
        surface.blit(kills_s, (SCREEN_W // 2 - kills_s.get_width() // 2, 186))

        btn_w, btn_h = 240, 52
        start_y = 230
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

        owned = self._player_data.get("run_perks", []) if self._player_data else []
        if owned:
            perk_names = {p["id"]: p["name"] for p in _load_perks()}
            label_parts = [perk_names.get(pid, pid) for pid in owned]
            perks_s = self._font.render("Perks: " + "  +  ".join(label_parts), True, (100, 160, 110))
            surface.blit(perks_s, (SCREEN_W // 2 - perks_s.get_width() // 2, start_y + len(self._buttons) * gap + 6))
