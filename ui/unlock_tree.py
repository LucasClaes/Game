import pygame
from core.settings import SCREEN_W, SCREEN_H, WHITE, YELLOW, DARK_GRAY, BLUE
from core.unlock_tree import get_nodes, can_unlock, is_unlocked, purchase

_TYPE_LABELS = {"feature": "FEATURES", "class": "CLASSES", "gear": "GEAR", "challenge": "CHALLENGES"}
_TYPE_COLORS = {
    "feature":   (80,  140, 220),
    "class":     (200, 140,  60),
    "gear":      (180,  80, 200),
    "challenge": ( 80, 200, 120),
}
_TYPE_ORDER = ["feature", "class", "gear", "challenge"]


class UnlockTreeScreen:
    def __init__(self, state_manager, font, big_font, title_font):
        self._sm = state_manager
        self._font = font
        self._big = big_font
        self._title = title_font
        self._player_data = None
        self._node_rects: dict[str, pygame.Rect] = {}
        self._hovered: str | None = None
        self._message = ""
        self._msg_timer = 0.0

    def on_enter(self, **kwargs):
        self._player_data = kwargs.get("player_data")
        self._message = ""
        self._msg_timer = 0.0
        self._hovered = None

    def update(self, events, dt):
        self._msg_timer = max(0.0, self._msg_timer - dt)
        if self._msg_timer <= 0:
            self._message = ""

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                from core.state_machine import GameState
                self._sm.switch_to(GameState.MAIN_MENU, player_data=self._player_data)
            elif event.type == pygame.MOUSEMOTION:
                self._hovered = None
                for nid, rect in self._node_rects.items():
                    if rect.collidepoint(event.pos):
                        self._hovered = nid
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for nid, rect in self._node_rects.items():
                    if rect.collidepoint(event.pos):
                        self._try_purchase(nid)
                        return

    def _try_purchase(self, node_id: str):
        nodes = get_nodes()
        node = next((n for n in nodes if n["id"] == node_id), None)
        if not node:
            return
        if is_unlocked(self._player_data, node_id):
            self._show("Already unlocked!")
            return
        if not can_unlock(self._player_data, node):
            coins = (self._player_data or {}).get("coins", 0)
            reqs  = node.get("requires", [])
            missing = [r for r in reqs if not is_unlocked(self._player_data, r)]
            if coins < node["cost"]:
                self._show(f"Need {node['cost']} coins (have {coins})")
            elif missing:
                self._show(f"Requires: {', '.join(missing)}")
            return
        if purchase(self._player_data, node):
            from core.save import write_save
            write_save(self._player_data)
            self._show(f"Unlocked: {node['name']}!")

    def _show(self, msg: str):
        self._message = msg
        self._msg_timer = 2.5

    def draw(self, surface: pygame.Surface):
        surface.fill((15, 15, 25))

        title_s = self._title.render("UNLOCK TREE", True, YELLOW)
        surface.blit(title_s, (SCREEN_W // 2 - title_s.get_width() // 2, 20))

        coins = (self._player_data or {}).get("coins", 0)
        coin_s = self._big.render(f"Coins: {coins}", True, YELLOW)
        surface.blit(coin_s, (SCREEN_W // 2 - coin_s.get_width() // 2, 64))

        nodes = get_nodes()
        groups: dict[str, list] = {}
        for n in nodes:
            groups.setdefault(n["type"], []).append(n)

        node_w, node_h = 220, 140
        gap_x, gap_y = 14, 10
        row_y = 104
        self._node_rects = {}

        for ttype in _TYPE_ORDER:
            group = groups.get(ttype)
            if not group:
                continue

            lbl_s = self._font.render(_TYPE_LABELS[ttype], True, _TYPE_COLORS[ttype])
            surface.blit(lbl_s, (SCREEN_W // 2 - lbl_s.get_width() // 2, row_y))
            row_y += lbl_s.get_height() + 5

            total_w = len(group) * node_w + (len(group) - 1) * gap_x
            gx0 = SCREEN_W // 2 - total_w // 2

            for gi, node in enumerate(group):
                nx = gx0 + gi * (node_w + gap_x)
                rect = pygame.Rect(nx, row_y, node_w, node_h)
                self._node_rects[node["id"]] = rect

                unlocked   = is_unlocked(self._player_data, node["id"])
                affordable = can_unlock(self._player_data, node) if self._player_data else False
                hovered    = self._hovered == node["id"]

                if unlocked:
                    bg, border = (18, 40, 18), (55, 170, 55)
                elif affordable and hovered:
                    bg, border = (28, 40, 58), YELLOW
                elif affordable:
                    bg, border = (22, 32, 52), (90, 130, 190)
                else:
                    bg, border = (20, 20, 28), (48, 48, 62)

                pygame.draw.rect(surface, bg, rect, border_radius=8)
                pygame.draw.rect(surface, border, rect, 2, border_radius=8)

                tc = WHITE if (unlocked or affordable) else (75, 75, 88)
                y = row_y + 10

                name_s = self._font.render(node["name"], True, YELLOW if unlocked else tc)
                surface.blit(name_s, (rect.centerx - name_s.get_width() // 2, y))
                y += name_s.get_height() + 5

                # Wrap desc
                words = node["desc"].split()
                line, lines = "", []
                for w in words:
                    test = (line + " " + w).strip()
                    if self._font.size(test)[0] <= node_w - 12:
                        line = test
                    else:
                        if line:
                            lines.append(line)
                        line = w
                if line:
                    lines.append(line)
                for dl in lines:
                    ds = self._font.render(dl, True, tc)
                    surface.blit(ds, (nx + 6, y))
                    y += ds.get_height() + 2

                # Bottom row
                if unlocked:
                    ok_s = self._font.render("✓ OWNED", True, (55, 190, 55))
                    surface.blit(ok_s, (rect.centerx - ok_s.get_width() // 2,
                                        row_y + node_h - 22))
                else:
                    if node.get("requires"):
                        req_s = self._font.render("Req: " + ", ".join(node["requires"]),
                                                  True, (95, 95, 115))
                        surface.blit(req_s, (nx + 6, row_y + node_h - 38))
                    cost_col = YELLOW if affordable else (110, 90, 50)
                    cost_s = self._font.render(f"{node['cost']} coins", True, cost_col)
                    surface.blit(cost_s, (rect.centerx - cost_s.get_width() // 2,
                                          row_y + node_h - 22))

            row_y += node_h + gap_y + 8

        if self._message:
            msg_s = self._big.render(self._message, True, YELLOW)
            surface.blit(msg_s, (SCREEN_W // 2 - msg_s.get_width() // 2, SCREEN_H - 56))

        back_s = self._font.render("ESC: Back", True, (78, 78, 98))
        surface.blit(back_s, (SCREEN_W // 2 - back_s.get_width() // 2, SCREEN_H - 26))
