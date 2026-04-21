from collections import deque


def bfs_path(tile_grid, tile_w: int, tile_h: int,
             start: tuple, goal: tuple) -> list:
    """
    BFS on tile grid. Returns list of (tx, ty) waypoints from start to goal
    (not including start). Empty list means no path or already at goal.
    tile_grid is indexed [row][col] i.e. [ty][tx]. True = walkable.
    """
    sx, sy = (max(0, min(start[0], tile_w - 1)),
              max(0, min(start[1], tile_h - 1)))
    gx, gy = (max(0, min(goal[0],  tile_w - 1)),
              max(0, min(goal[1],  tile_h - 1)))

    if (sx, sy) == (gx, gy):
        return []

    came_from = {(sx, sy): None}
    queue = deque([(sx, sy)])

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == (gx, gy):
            path = []
            pos = (gx, gy)
            while pos is not None:
                path.append(pos)
                pos = came_from[pos]
            path.reverse()
            return path[1:]  # drop start tile

        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in came_from:
                continue
            if not (0 <= nx < tile_w and 0 <= ny < tile_h):
                continue
            if not tile_grid[ny][nx]:
                continue
            came_from[(nx, ny)] = (cx, cy)
            queue.append((nx, ny))

    return []
