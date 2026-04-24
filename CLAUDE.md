# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running & Building

```bash
# Install dependencies (once)
pip install pygame-ce

# Run
python main.py
```

Controls: WASD/Arrows to move, LMB or Space to melee swing, RMB to shoot (requires Slingshot upgrade), Shift to dash (requires Dash upgrade), Q to use bomb, E to use shield, ESC to pause.

## Architecture

### State machine
`core/state_machine.py` — `StateManager` holds `{GameState: Screen}`. Each screen implements `on_enter(**kwargs)`, `update(events, dt)`, `draw(surface)`. Screens call `state_manager.switch_to(state, **kwargs)` to transition; they never reference each other.

States: `MAIN_MENU → PLAYING ↔ LEVEL_COMPLETE ↔ SHOP`, `PLAYING → GAME_OVER → MAIN_MENU`, `MAIN_MENU → SETTINGS → MAIN_MENU`.

### PlayerData
A plain dict (`coins`, `current_level`, `upgrades: dict`, `best_level`, `best_coins`, `music_vol`, `sfx_vol`) is the only state that crosses screen boundaries. Loaded from `data/save.json` at startup, saved on every purchase and level completion via `core/save.py`.

### Player stats from upgrades
Upgrade multipliers are computed once in `Player.__init__` (not each frame). Speed +10%/level, damage +20%/level, cooldown reduced 15-20%/level. Ranged combat unlocked by buying the `ranged_unlock` upgrade. Dash unlocked by buying `dash_unlock`.

### Zombie AI
Wall-sliding vector chase (no library): tries full movement → X-only → Y-only. Zombies slide around corners naturally. Types (`basic`, `fast`, `tank`, `ranged`) defined in `core/settings.ZOMBIE_TYPES`. Ranged zombies stop and fire at the player when in range.

### Combat
- **Melee**: LMB/Space triggers a timed swing. `Player.get_melee_hitbox()` returns an offset rect in the facing direction (facing = angle toward mouse cursor). Zombies can only be hit once per swing.
- **Ranged**: RMB fires a `Bullet`. Bullets live in a list on `PlayingScreen`, swept each frame (`[b for b in bullets if b.alive]`).
- **Dash**: Shift dashes the player in their movement direction with brief invincibility.

### Coordinate system
Tile-based: `TILE_SIZE = 32` px. Level JSON uses integer tile coords, converted to pixel `pygame.Rect` at load time in `world/level.py`. A 960×640 screen = 30×20 tiles. Game renders at 960×640 and is upscaled to native resolution by `pygame.SCALED`.

### Camera
`systems/camera.py` — `Vector2` offset clamped to level pixel bounds. All world draws use `pos - camera.offset`. For levels that fit on screen (30×20 tiles) the offset stays (0,0).

### Music
Music tracks live in `assets/music/`. Each game state plays its own looping track via `audio.play_music(key)` in `on_enter()`. Transitions fade out the current track (800ms) then fade in the new one. `audio.update(dt)` must be called each frame from `core/game.py`.

Music attribution: "FREE Action Chiptune Music Pack" by Preston Peak, licensed CC-BY 4.0 (https://opengameart.org/content/free-action-chiptune-music-pack).

## Adding Levels

Edit `data/levels.json`. Wall format: `[tile_x, tile_y, width_tiles, height_tiles]`. Zombie types: `"basic"`, `"fast"`, `"tank"`, `"ranged"`. Traps: `"traps": [[tx, ty], ...]`.

```json
{
  "id": 3,
  "name": "My Level",
  "background_color": [25, 25, 35],
  "exit_requires_all_coins": true,
  "player_start": [1, 1],
  "exit": [28, 18],
  "walls": [[0,0,30,1], [0,19,30,1], [0,0,1,20], [29,0,1,20]],
  "coins": [[5, 5]],
  "zombies": [{"tile": [15, 10], "type": "basic"}],
  "traps": [[10, 10], [11, 10]],
  "instructions": []
}
```

## Adding Shop Upgrades

Edit `data/shop.json`. Add an entry with a unique `id`, then apply its effect in `Player.__init__` by reading `upgrades.get("your_id", 0)`.
