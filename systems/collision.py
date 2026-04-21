import pygame


def resolve_wall_collision(rect: pygame.Rect, walls: list[pygame.Rect], dx: float, dy: float):
    """Move rect by (dx, dy) while sliding along walls. Returns actual (dx, dy) applied."""
    # Try full movement
    new_rect = rect.move(dx, dy)
    if not any(new_rect.colliderect(w) for w in walls):
        rect.x += dx
        rect.y += dy
        return dx, dy

    # Try X only
    new_rect_x = rect.move(dx, 0)
    x_blocked = any(new_rect_x.colliderect(w) for w in walls)

    # Try Y only
    new_rect_y = rect.move(0, dy)
    y_blocked = any(new_rect_y.colliderect(w) for w in walls)

    actual_dx = 0 if x_blocked else dx
    actual_dy = 0 if y_blocked else dy

    rect.x += actual_dx
    rect.y += actual_dy
    return actual_dx, actual_dy


def clamp_to_bounds(rect: pygame.Rect, level_w: int, level_h: int):
    rect.x = max(0, min(rect.x, level_w - rect.width))
    rect.y = max(0, min(rect.y, level_h - rect.height))
