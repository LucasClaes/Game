import pygame
from core.settings import SCREEN_W, SCREEN_H, RED, YELLOW, WHITE, DARK_GRAY, GREEN, BLUE, CYAN


class HUD:
    def __init__(self, font: pygame.font.Font, big_font: pygame.font.Font):
        self._font = font
        self._big = big_font

    def draw(self, surface: pygame.Surface, player, level, total_coins: int,
             player_data: dict = None, boss=None, combo: int = 0,
             kill_count: int = 0, elapsed: float = 0.0):
        self._draw_hp(surface, player)
        self._draw_lives(surface, player)
        self._draw_coins(surface, level)
        self._draw_level(surface, level)
        self._draw_weapon(surface, player)
        if player_data:
            self._draw_consumables(surface, player_data)
        if boss and boss.alive:
            self._draw_boss_bar(surface, boss)
        if combo >= 3:
            self._draw_combo(surface, combo)
        self._draw_stats(surface, kill_count, elapsed)
        if player_data and player_data.get("run_perks"):
            self._draw_perks(surface, player_data["run_perks"])

    def _draw_hp(self, surface, player):
        bar_w = 140
        bar_h = 14
        x, y = 12, 12
        pygame.draw.rect(surface, DARK_GRAY, (x, y, bar_w, bar_h), border_radius=3)
        ratio = max(0, player.hp / player.max_hp)
        hp_color = GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        pygame.draw.rect(surface, hp_color, (x, y, int(bar_w * ratio), bar_h), border_radius=3)
        pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), 1, border_radius=3)
        label = self._font.render("HP", True, WHITE)
        surface.blit(label, (x + bar_w + 6, y))

    def _draw_lives(self, surface, player):
        x, y = 12, 32
        for i in range(player.lives):
            pygame.draw.circle(surface, RED, (x + i * 18, y + 7), 6)
            pygame.draw.circle(surface, WHITE, (x + i * 18, y + 7), 6, 1)

    def _draw_coins(self, surface, level):
        total = len(level.coins)
        collected = total - level.coins_remaining
        if level.is_boss:
            coins_text = "BOSS FIGHT"
            color = (255, 80, 80)
        else:
            coins_text = f"Coins: {collected}/{total}"
            color = YELLOW
        coins_s = self._font.render(coins_text, True, color)
        surface.blit(coins_s, (SCREEN_W - coins_s.get_width() - 12, 12))

    def _draw_level(self, surface, level):
        name_surf = self._font.render(f"Level {level.number + 1}: {level.name}", True, WHITE)
        surface.blit(name_surf, (SCREEN_W // 2 - name_surf.get_width() // 2, 10))

    def _draw_weapon(self, surface, player):
        weapon_name = getattr(player, "_equipped_weapon_name", "FISTS")
        label = f"{weapon_name}  [LMB / Space]"
        color = YELLOW
        if player.has_ranged:
            label += "   |   RANGED  [RMB]"
            color = CYAN
        surf = self._font.render(label, True, color)
        surface.blit(surf, (12, SCREEN_H - 28))

    def _draw_consumables(self, surface, player_data):
        y = SCREEN_H - 56
        bombs = player_data.get("bombs", 0)
        shields = player_data.get("shields", 0)
        if bombs > 0:
            s = self._font.render(f"Q: Bomb ×{bombs}", True, YELLOW)
            surface.blit(s, (12, y))
            y -= 24
        if shields > 0:
            s = self._font.render(f"E: Shield ×{shields}", True, CYAN)
            surface.blit(s, (12, y))

    def _draw_combo(self, surface, combo: int):
        mult = 1.0 + (combo // 5) * 0.5
        text = f"x{mult:.1f} COMBO  ({combo} kills)"
        s = self._font.render(text, True, (255, 160, 30))
        surface.blit(s, (SCREEN_W // 2 - s.get_width() // 2, 32))

    def _draw_stats(self, surface, kill_count: int, elapsed: float):
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        time_str = f"{mins}:{secs:02d}"
        kills_str = f"Kills: {kill_count}"
        kills_surf = self._font.render(kills_str, True, (200, 200, 200))
        time_surf  = self._font.render(time_str,  True, (180, 180, 220))
        surface.blit(kills_surf, (SCREEN_W - kills_surf.get_width() - 12, SCREEN_H - 52))
        surface.blit(time_surf,  (SCREEN_W - time_surf.get_width()  - 12, SCREEN_H - 28))

    def _draw_perks(self, surface, run_perks):
        x, y = 12, 52
        # run_perks is dict {id: level} or legacy list
        if isinstance(run_perks, list):
            items = [(pid, 1) for pid in run_perks]
        else:
            items = list(run_perks.items())
        _sup = {1: "¹", 2: "²", 3: "³"}
        for pid, lv in items:
            label = pid[:3].upper() + _sup.get(lv, str(lv))
            badge_surf = self._font.render(label, True, (255, 200, 80))
            bw = badge_surf.get_width() + 8
            pygame.draw.rect(surface, (60, 50, 20), (x, y, bw, 18), border_radius=3)
            pygame.draw.rect(surface, (180, 140, 40), (x, y, bw, 18), 1, border_radius=3)
            surface.blit(badge_surf, (x + 4, y + 1))
            x += bw + 4

    def _draw_boss_bar(self, surface, boss):
        bar_w = 400
        bar_h = 22
        x = SCREEN_W // 2 - bar_w // 2
        y = 36
        pygame.draw.rect(surface, (60, 10, 10), (x, y, bar_w, bar_h), border_radius=4)
        ratio = max(0.0, boss.hp / boss.max_hp)
        bar_color = (200, 40, 40) if ratio > 0.3 else (255, 200, 0)
        pygame.draw.rect(surface, bar_color, (x, y, int(bar_w * ratio), bar_h), border_radius=4)
        pygame.draw.rect(surface, (220, 130, 200), (x, y, bar_w, bar_h), 2, border_radius=4)
        label = self._font.render(f"BOSS  {boss.hp}/{boss.max_hp}", True, WHITE)
        surface.blit(label, (SCREEN_W // 2 - label.get_width() // 2, y + 3))
