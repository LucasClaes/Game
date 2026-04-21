import pygame
from core.settings import SCREEN_W, SCREEN_H, RED, YELLOW, WHITE, DARK_GRAY, GREEN, BLUE, CYAN


class HUD:
    def __init__(self, font: pygame.font.Font, big_font: pygame.font.Font):
        self._font = font
        self._big = big_font

    def draw(self, surface: pygame.Surface, player, level, total_coins: int):
        self._draw_hp(surface, player)
        self._draw_lives(surface, player)
        self._draw_coins(surface, level)
        self._draw_level(surface, level)
        self._draw_weapon(surface, player)

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
        coins_text = self._font.render(f"Coins: {collected}/{total}", True, YELLOW)
        surface.blit(coins_text, (SCREEN_W - coins_text.get_width() - 12, 12))

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
