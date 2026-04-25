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
        # Gear tab UI state
        self._slot_rects: dict = {}
        self._inv_rects: list = []   # [(gear_id, rect), ...]
        self._selected_slot: str | None = None
        self._inv_scroll = 0

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._tab = 0
        self._selected_slot = None
        self._inv_scroll = 0

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
                    return
                for i, rect in enumerate(self._tab_rects):
                    if rect.collidepoint(event.pos):
                        self._tab = i
                        return
                if self._tab == 1:
                    self._handle_gear_click(event.pos)
            if event.type == pygame.MOUSEWHEEL and self._tab == 1:
                self._inv_scroll = max(0, self._inv_scroll - event.y * 30)

    def _handle_gear_click(self, pos):
        from core.inventory import equip, unequip
        from core.save import write_save

        # Click on equipped slot → unequip
        for slot, rect in self._slot_rects.items():
            if rect.collidepoint(pos):
                equipped = self._player_data.get("gear", {})
                if equipped.get(slot):
                    unequip(self._player_data, slot)
                    write_save(self._player_data)
                return

        # Click on inventory item → equip into its slot
        for gear_id, rect in self._inv_rects:
            if rect.collidepoint(pos):
                gear_list = _load_gear()
                gear_map = {g["id"]: g for g in gear_list}
                piece = gear_map.get(gear_id)
                if piece:
                    equip(self._player_data, piece["slot"], gear_id)
                    write_save(self._player_data)
                return

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
        owned = self._player_data.get("run_perks", {}) if self._player_data else {}
        if isinstance(owned, list):
            owned = {pid: 1 for pid in owned}

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
            lv = owned.get(perk["id"], 0)
            bg     = (22, 40, 22) if revealed else (20, 20, 30)
            border = GREEN        if revealed else (50, 50, 65)
            if lv > 0:
                bg, border = (40, 38, 10), (200, 160, 30)
            pygame.draw.rect(surface, bg,     (cx, cy, card_w, card_h), border_radius=6)
            pygame.draw.rect(surface, border, (cx, cy, card_w, card_h), 2, border_radius=6)

            if revealed:
                lv_label = f"  Lv {lv}/3" if lv > 0 else ""
                name_s = self._big.render(perk["name"] + lv_label, True, WHITE)
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
        gear_map  = {g["id"]: g for g in gear_list}
        inventory = self._player_data.get("inventory", []) if self._player_data else []
        equipped  = self._player_data.get("gear", {}) if self._player_data else {}

        # Left column: equipped slots
        slot_col_w = 200
        slot_x = 30
        slot_h = 60
        slot_gap = 8
        self._slot_rects = {}

        for row, slot in enumerate(_SLOT_ORDER):
            rect = pygame.Rect(slot_x, y0 + row * (slot_h + slot_gap), slot_col_w, slot_h)
            self._slot_rects[slot] = rect
            eq_id = equipped.get(slot)
            piece = gear_map.get(eq_id) if eq_id else None

            bg = (20, 40, 65) if piece else (20, 20, 30)
            border = (80, 150, 220) if piece else (50, 50, 70)
            pygame.draw.rect(surface, bg, rect, border_radius=6)
            pygame.draw.rect(surface, border, rect, 2, border_radius=6)

            slot_s = self._font.render(_SLOT_LABELS[slot], True, (80, 90, 110))
            surface.blit(slot_s, (rect.x + 8, rect.y + 6))
            if piece:
                name_s = self._big.render(piece["name"], True, (80, 180, 240))
                surface.blit(name_s, (rect.x + 8, rect.y + 26))
                un_s = self._font.render("[click to unequip]", True, (60, 100, 160))
                surface.blit(un_s, (rect.x + 8, rect.y + 44))
            else:
                empty_s = self._font.render("[Empty]", True, (60, 60, 80))
                surface.blit(empty_s, (rect.x + 8, rect.y + 26))

        # Right column: inventory grid
        inv_x = slot_x + slot_col_w + 20
        inv_w = SCREEN_W - inv_x - 20
        card_w = inv_w
        card_h = 52
        card_gap = 6

        # Group inventory by slot
        by_slot: dict[str, list] = {s: [] for s in _SLOT_ORDER}
        for gid in inventory:
            piece = gear_map.get(gid)
            if piece:
                by_slot[piece["slot"]].append(piece)

        self._inv_rects = []
        row = 0
        for slot in _SLOT_ORDER:
            if not by_slot[slot]:
                continue
            label_s = self._font.render(_SLOT_LABELS[slot], True, (80, 90, 110))
            surface.blit(label_s, (inv_x, y0 + row * (card_h + card_gap) - self._inv_scroll))
            row_y = y0 + row * (card_h + card_gap) + 16 - self._inv_scroll
            for piece in by_slot[slot]:
                rect = pygame.Rect(inv_x, row_y, card_w, card_h - 16)
                is_equipped = equipped.get(slot) == piece["id"]
                bg = (20, 40, 65) if is_equipped else (22, 38, 22)
                border = (80, 150, 220) if is_equipped else GREEN
                if rect.bottom > y0 and rect.top < SCREEN_H - 70:
                    pygame.draw.rect(surface, bg, rect, border_radius=5)
                    pygame.draw.rect(surface, border, rect, 2, border_radius=5)
                    name_s = self._big.render(piece["name"], True,
                                              (80, 180, 240) if is_equipped else WHITE)
                    surface.blit(name_s, (rect.x + 8, rect.y + 4))
                    desc_s = self._font.render(piece["desc"], True, (140, 180, 150))
                    surface.blit(desc_s, (rect.x + 8, rect.y + 22))
                    if is_equipped:
                        eq_s = self._font.render("[EQUIPPED]", True, (80, 150, 220))
                        surface.blit(eq_s, (rect.right - eq_s.get_width() - 8, rect.y + 4))
                    else:
                        click_s = self._font.render("[click to equip]", True, (60, 130, 80))
                        surface.blit(click_s, (rect.right - click_s.get_width() - 8, rect.y + 4))
                self._inv_rects.append((piece["id"], rect))
                row_y += card_h - 14
            row += 1

        if not any(by_slot.values()):
            none_s = self._font.render("No gear in inventory — find crates in runs!", True, (70, 70, 90))
            surface.blit(none_s, (inv_x, y0 + 20))
