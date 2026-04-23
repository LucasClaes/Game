"""Lightweight glow / visual-effects helpers. Surfaces are cached by key."""
import pygame

_cache: dict = {}


def glow(surface: pygame.Surface, cx: int, cy: int,
         radius: int, color: tuple, alpha: int = 100):
    """Additive glow circle centred at (cx, cy). Uses BLEND_RGBA_ADD."""
    key = (radius, color[0], color[1], color[2], alpha)
    if key not in _cache:
        sz = radius * 2
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        for r in range(radius, 0, -3):
            a = int(alpha * (r / radius) ** 0.6)
            pygame.draw.circle(s, (color[0], color[1], color[2], a),
                               (radius, radius), r)
        _cache[key] = s
    surf = _cache[key]
    surface.blit(surf, (cx - radius, cy - radius),
                 special_flags=pygame.BLEND_RGBA_ADD)


def clear_cache():
    """Call if pygame display is re-created."""
    _cache.clear()


_scanlines_surf: pygame.Surface | None = None


def get_scanlines(w: int, h: int) -> pygame.Surface:
    global _scanlines_surf
    if _scanlines_surf is None or _scanlines_surf.get_size() != (w, h):
        _scanlines_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 2):
            pygame.draw.line(_scanlines_surf, (0, 0, 0, 40), (0, y), (w, y))
    return _scanlines_surf
