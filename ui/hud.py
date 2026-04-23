import pygame
from core.settings import SCREEN_W, SCREEN_H, RED, YELLOW, WHITE, DARK_GRAY, GREEN, BLUE, CYAN


class HUD:
    def __init__(self, font: pygame.font.Font, big_font: pygame.font.Font):
        self._font = font
        self._big = big_font

    def draw(self, surface: pygame.Surface, player, level, total_coins: int,
             player_data: dict = None, boss=None):
        self._draw_hp(surface, player)
        self._draw_lives(surface, player)
        self._draw_coins(surface, level)
        self._draw_level(surface, level)
        self._draw_weapon(surface, player)
        if player_data:
            self._draw_consumables(surface, player_data)
        if boss and boss.alive:
            self._draw_boss_bar(surface, boss)

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
        label = "MELEE  [LMB / Space]"
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
