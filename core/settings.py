SCREEN_W = 960
SCREEN_H = 640
FPS = 60
TILE_SIZE = 32

PLAYER_SPEED_BASE = 180        # pixels per second
PLAYER_HP_BASE = 3
PLAYER_LIVES_BASE = 3
MELEE_RANGE = 48               # pixels from player center to hitbox center
MELEE_HITBOX_SIZE = 44         # width/height of melee hitbox rect
MELEE_DURATION = 0.15          # seconds swing is active
MELEE_COOLDOWN_BASE = 0.5      # seconds between swings
BULLET_SPEED = 420             # pixels per second
SHOOT_COOLDOWN_BASE = 0.35     # seconds between shots
BULLET_DAMAGE_BASE = 15
MELEE_DAMAGE_BASE = 25

ZOMBIE_TYPES = {
    "basic": {"hp": 60,  "speed": 90,  "damage": 1, "coin_drop": 5},
    "fast":  {"hp": 35,  "speed": 175, "damage": 2, "coin_drop": 12},
    "tank":  {"hp": 220, "speed": 50,  "damage": 3, "coin_drop": 25},
}

AGGRO_RADIUS       = 200   # px — zombie detection range
CHAIN_AGGRO_RADIUS = 80    # px — radius for alerting nearby zombies on hit

# Colors
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
GRAY       = (80,  80,  80)
DARK_GRAY  = (40,  40,  40)
RED        = (220, 50,  50)
GREEN      = (50,  200, 80)
DARK_GREEN = (30,  130, 50)
YELLOW     = (255, 220, 0)
BLUE       = (60,  120, 220)
ORANGE     = (255, 140, 0)
PURPLE     = (160, 60,  200)
CYAN       = (0,   200, 220)

# Procedural generation
PROCGEN_BASE_W        = 30
PROCGEN_BASE_H        = 20
PROCGEN_GROWTH_W      = 4
PROCGEN_GROWTH_H      = 3
PROCGEN_MAX_W         = 80
PROCGEN_MAX_H         = 60
PROCGEN_BASE_ROOMS    = 5
PROCGEN_BASE_ZOMBIES  = 3
PROCGEN_ZOMBIE_GROWTH = 2
PROCGEN_MAX_ZOMBIES   = 25
PROCGEN_MAX_ATTEMPTS  = 20
MINIMAP_SIZE          = 160
