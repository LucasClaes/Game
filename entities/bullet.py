import pygame


class Bullet:
    RADIUS = 4

    def __init__(self, pos: pygame.Vector2, vel: pygame.Vector2, damage: int):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.damage = damage
        self.alive = True
        self.rect = pygame.Rect(0, 0, self.RADIUS * 2, self.RADIUS * 2)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def update(self, dt: float, walls: list, level_w: int, level_h: int):
        self.pos += self.vel * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if (self.pos.x < 0 or self.pos.x > level_w or
                self.pos.y < 0 or self.pos.y > level_h):
            self.alive = False
            return
        if any(self.rect.colliderect(w) for w in walls):
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        cx = int(self.pos.x - offset.x)
        cy = int(self.pos.y - offset.y)
        from systems.gfx import glow
        glow(surface, cx, cy, 10, (0, 220, 255), 90)
        pygame.draw.circle(surface, (180, 240, 255), (cx, cy), self.RADIUS)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(1, self.RADIUS - 2))
