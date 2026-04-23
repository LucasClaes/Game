import math
import random
import pygame


class Particle:
    __slots__ = ('pos', 'vel', 'life', 'max_life', 'color', 'size')

    def __init__(self, x: float, y: float, color: tuple):
        self.pos = pygame.Vector2(x, y)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(60, 200)
        self.vel = pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        self.life = random.uniform(0.3, 0.65)
        self.max_life = self.life
        self.color = color
        self.size = random.randint(2, 5)


class ParticleSystem:
    def __init__(self):
        self._particles: list[Particle] = []

    def emit(self, x: float, y: float, count: int, color: tuple):
        for _ in range(count):
            self._particles.append(Particle(x, y, color))

    def update(self, dt: float):
        for p in self._particles:
            p.pos += p.vel * dt
            p.vel *= 0.85
            p.life -= dt
        self._particles = [p for p in self._particles if p.life > 0]

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2):
        for p in self._particles:
            ratio = p.life / p.max_life
            size = max(1, int(p.size * ratio))
            x = int(p.pos.x - offset.x)
            y = int(p.pos.y - offset.y)
            pygame.draw.rect(surface, p.color, (x, y, size, size))

    def clear(self):
        self._particles.clear()
