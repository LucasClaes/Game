import colorsys
import random
from collections import deque

from core.settings import (
    PROCGEN_BASE_W, PROCGEN_BASE_H, PROCGEN_GROWTH_W, PROCGEN_GROWTH_H,
    PROCGEN_MAX_W, PROCGEN_MAX_H, PROCGEN_BASE_ROOMS, PROCGEN_BASE_ZOMBIES,
    PROCGEN_ZOMBIE_GROWTH, PROCGEN_MAX_ZOMBIES, PROCGEN_MAX_ATTEMPTS,
)


def generate(level_num: int) -> dict:
    idx = level_num  # 0-indexed from level 0
    tile_w = min(PROCGEN_BASE_W + PROCGEN_GROWTH_W * idx, PROCGEN_MAX_W)
    tile_h = min(PROCGEN_BASE_H + PROCGEN_GROWTH_H * idx, PROCGEN_MAX_H)
    room_count = min(PROCGEN_BASE_ROOMS + idx, 20)

    for _ in range(PROCGEN_MAX_ATTEMPTS):
        result = _attempt(level_num, idx, tile_w, tile_h, room_count)
        if result is not None:
            return result

    return _fallback(level_num)


def generate_boss(level_num: int) -> dict:
    boss_level = level_num // 4  # 1 for level 4, 2 for level 8, etc.
    w, h = 34, 24
    walls = []

    # Perimeter walls
    walls += [[0, 0, w, 1], [0, h - 1, w, 1],
              [0, 0, 1, h], [w - 1, 0, 1, h]]

    # Four 2×2 pillar obstacles (symmetrical)
    for px, py in [(7, 5), (7, 17), (25, 5), (25, 17)]:
        walls.append([px, py, 2, 2])

    return {
        "id": level_num,
        "name": f"BOSS — Floor {level_num}",
        "background_color": [70, 8, 8],
        "is_boss_level": True,
        "player_start": [2, 12],
        "boss_spawn": [31, 12],
        "exit": [1, 11],
        "exit_requires_all_coins": False,
        "walls": walls,
        "coins": [],
        "zombies": [],
        "traps": [],
        "instructions": [],
    }


def _attempt(level_num, idx, tile_w, tile_h, room_count):
    walkable = [[False] * tile_w for _ in range(tile_h)]
    rooms = []

    for _ in range(room_count * 15):
        if len(rooms) >= room_count:
            break
        rw = random.randint(4, min(10, tile_w - 2))
        rh = random.randint(4, min(10, tile_h - 2))
        if tile_w - rw - 1 < 1 or tile_h - rh - 1 < 1:
            continue
        rx = random.randint(1, tile_w - rw - 1)
        ry = random.randint(1, tile_h - rh - 1)

        # Reject if overlapping an existing room (1-tile padding)
        if any(
            rx - 1 < ox + ow and rx + rw + 1 > ox and
            ry - 1 < oy + oh and ry + rh + 1 > oy
            for ox, oy, ow, oh in rooms
        ):
            continue

        rooms.append((rx, ry, rw, rh))
        for ty in range(ry, ry + rh):
            for tx in range(rx, rx + rw):
                walkable[ty][tx] = True

    if len(rooms) < 2:
        return None

    rooms.sort(key=lambda r: r[0] + r[1])
    centers = [_center(r) for r in rooms]

    for i in range(len(centers) - 1):
        _carve_l(walkable, centers[i], centers[i + 1])

    player_start = centers[0]
    exit_pos = centers[-1]

    reachable = _bfs(walkable, tile_w, tile_h, player_start)
    if not reachable[exit_pos[1]][exit_pos[0]]:
        return None

    exclude = [player_start, exit_pos]
    coin_candidates = [
        (tx, ty)
        for ty in range(tile_h)
        for tx in range(tile_w)
        if walkable[ty][tx] and reachable[ty][tx]
        and all(_mdist((tx, ty), e) >= 3 for e in exclude)
    ]
    coin_count = 5 + idx
    if len(coin_candidates) < coin_count:
        return None
    coin_positions = random.sample(coin_candidates, coin_count)

    # Traps on floor tiles (level 3+)
    trap_positions = []
    if idx >= 2:
        trap_candidates = [
            (tx, ty) for tx, ty in coin_candidates
            if (tx, ty) not in coin_positions
            and all(_mdist((tx, ty), e) >= 4 for e in exclude)
        ]
        trap_count = min(idx - 1, 6)
        if len(trap_candidates) >= trap_count:
            trap_positions = random.sample(trap_candidates, trap_count)

    zombie_candidates = [
        (tx, ty)
        for ty in range(1, tile_h - 1)
        for tx in range(1, tile_w - 1)
        if walkable[ty][tx] and reachable[ty][tx]
        and all(_mdist((tx, ty), e) >= 6 for e in exclude)
        and walkable[ty - 1][tx] and walkable[ty + 1][tx]
        and walkable[ty][tx - 1] and walkable[ty][tx + 1]
    ]
    zombie_count = min(
        PROCGEN_BASE_ZOMBIES + PROCGEN_ZOMBIE_GROWTH * idx,
        PROCGEN_MAX_ZOMBIES,
        len(zombie_candidates),
    )
    zombie_positions = random.sample(zombie_candidates, zombie_count) if zombie_count > 0 else []

    return {
        "id": level_num,
        "name": f"Depth {idx + 1}",
        "background_color": _bg_color(idx),
        "exit_requires_all_coins": True,
        "player_start": list(player_start),
        "exit": list(exit_pos),
        "walls": _build_walls(walkable, tile_w, tile_h),
        "coins": [[cx, cy] for cx, cy in coin_positions],
        "zombies": _make_zombies(zombie_positions, idx),
        "traps": [[tx, ty] for tx, ty in trap_positions],
        "instructions": [],
    }


def _center(room):
    rx, ry, rw, rh = room
    return (rx + rw // 2, ry + rh // 2)


def _mdist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _carve_l(walkable, a, b):
    ax, ay = a
    bx, by = b
    if random.random() < 0.5:
        for tx in range(min(ax, bx), max(ax, bx) + 1):
            walkable[ay][tx] = True
        for ty in range(min(ay, by), max(ay, by) + 1):
            walkable[ty][bx] = True
    else:
        for ty in range(min(ay, by), max(ay, by) + 1):
            walkable[ty][ax] = True
        for tx in range(min(ax, bx), max(ax, bx) + 1):
            walkable[by][tx] = True


def _bfs(walkable, tile_w, tile_h, start):
    reachable = [[False] * tile_w for _ in range(tile_h)]
    sx, sy = start
    if not walkable[sy][sx]:
        return reachable
    q = deque([(sx, sy)])
    reachable[sy][sx] = True
    while q:
        cx, cy = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < tile_w and 0 <= ny < tile_h and walkable[ny][nx] and not reachable[ny][nx]:
                reachable[ny][nx] = True
                q.append((nx, ny))
    return reachable


def _build_walls(walkable, tile_w, tile_h):
    walls = []
    for ty in range(tile_h):
        tx = 0
        while tx < tile_w:
            if not walkable[ty][tx]:
                start_tx = tx
                while tx < tile_w and not walkable[ty][tx]:
                    tx += 1
                walls.append([start_tx, ty, tx - start_tx, 1])
            else:
                tx += 1
    return walls


def _make_zombies(positions, idx):
    t = min(idx / 10.0, 1.0)
    ranged_w = min(t * 0.3, 0.25) if idx >= 3 else 0.0
    weights = [max(0.15, 1.0 - t * 0.8 - ranged_w), t * 0.35, t * 0.35, ranged_w]
    types = ["basic", "fast", "tank", "ranged"]
    return [
        {"tile": list(pos), "type": random.choices(types, weights=weights, k=1)[0]}
        for pos in positions
    ]


def _bg_color(idx):
    hue = (0.65 - idx * 0.04) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.45, 0.15)
    return [int(r * 255), int(g * 255), int(b * 255)]


def _fallback(level_num):
    return {
        "id": level_num,
        "name": "Lost Depths",
        "background_color": [20, 20, 30],
        "exit_requires_all_coins": False,
        "player_start": [2, 2],
        "exit": [7, 7],
        "walls": [
            [0, 0, 10, 1], [0, 9, 10, 1],
            [0, 0, 1, 10], [9, 0, 1, 10],
        ],
        "coins": [],
        "zombies": [],
        "traps": [],
        "instructions": [],
    }
