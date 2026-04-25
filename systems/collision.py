import pygame


def resolve_wall_collision(
    rect: pygame.Rect,
    walls: list[pygame.Rect],
    dx: float,
    dy: float,
    float_x: float,
    float_y: float,
) -> tuple[float, float]:
    """Move rect by (dx, dy) sliding along walls. Returns updated (float_x, float_y)."""
    # X pass
    float_x += dx
    rect.x = int(float_x)
    for wall in walls:
        if rect.colliderect(wall):
            if dx > 0:
                rect.right = wall.left
            elif dx < 0:
                rect.left = wall.right
            float_x = float(rect.x)

    # Y pass — uses updated rect.x so Y test doesn't see stale X overlap
    float_y += dy
    rect.y = int(float_y)
    for wall in walls:
        if rect.colliderect(wall):
            if dy > 0:
                rect.bottom = wall.top
            elif dy < 0:
                rect.top = wall.bottom
            float_y = float(rect.y)

    return float_x, float_y


def clamp_to_bounds(rect: pygame.Rect, level_w: int, level_h: int):
    rect.x = max(0, min(rect.x, level_w - rect.width))
    rect.y = max(0, min(rect.y, level_h - rect.height))
