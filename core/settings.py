VERSION = "v1.0.0"

DIFFICULTIES = [
    {"name": "Easy",      "hp": 0.70, "speed": 0.80, "damage": 0.75, "coins": 0.85, "crate_chance": 0.00, "spawn_count_mult": 0.85},
    {"name": "Normal",    "hp": 1.00, "speed": 1.00, "damage": 1.00, "coins": 1.00, "crate_chance": 0.01, "spawn_count_mult": 1.00},
    {"name": "Hard",      "hp": 1.40, "speed": 1.20, "damage": 1.25, "coins": 1.50, "crate_chance": 0.03, "spawn_count_mult": 1.15},
    {"name": "Nightmare", "hp": 2.00, "speed": 1.50, "damage": 1.75, "coins": 2.50, "crate_chance": 0.06, "spawn_count_mult": 1.35},
]

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
    "basic":    {"hp": 60,  "speed": 90,  "damage": 1, "coin_drop": 5},
    "fast":     {"hp": 35,  "speed": 175, "damage": 2, "coin_drop": 12},
    "tank":     {"hp": 220, "speed": 50,  "damage": 3, "coin_drop": 25},
    "ranged":   {"hp": 45,  "speed": 55,  "damage": 1, "coin_drop": 18,
                 "shoot_range": 192, "shoot_cooldown": 2.0},
    "exploder": {"hp": 30,  "speed": 140, "damage": 1, "coin_drop": 3},
    "healer":   {"hp": 40,  "speed": 70,  "damage": 1, "coin_drop": 8,
                 "heal_radius": 80, "heal_amount": 15, "heal_interval": 2.0},
    "lurker":   {"hp": 50,  "speed": 120, "damage": 2, "coin_drop": 10,
                 "lurk_aggro": 120},
    # New enemy types
    "crawler":  {"hp": 25,  "speed": 110, "damage": 1, "coin_drop": 3},
    "spitter":  {"hp": 50,  "speed": 0,   "damage": 1, "coin_drop": 8,
                 "shoot_range": 240, "shoot_cooldown": 3.0},
    "bomber":   {"hp": 80,  "speed": 70,  "damage": 0, "coin_drop": 15,
                 "explode_radius": 110, "explode_damage": 60},
    "shielder": {"hp": 90,  "speed": 60,  "damage": 1, "coin_drop": 20},
    "phaser":   {"hp": 60,  "speed": 80,  "damage": 2, "coin_drop": 22,
                 "phase_cooldown": 4.0, "phase_dist": 96},
    "summoner": {"hp": 100, "speed": 50,  "damage": 1, "coin_drop": 28,
                 "summon_cooldown": 5.0, "summon_cap": 3},
    "vortex":   {"hp": 80,  "speed": 40,  "damage": 1, "coin_drop": 30,
                 "vortex_radius": 200, "vortex_strength": 60},
    "behemoth": {"hp": 350, "speed": 35,  "damage": 4, "coin_drop": 50,
                 "slam_cooldown": 5.0, "slam_radius": 140, "slam_damage": 80},
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
