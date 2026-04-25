import json
import os
import copy

_SAVE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "save.json")

_DEFAULT = {
    "coins": 0,
    "current_level": 0,
    "upgrades": {
        "damage": 0,
        "fire_rate": 0,
        "speed": 0,
        "health": 0,
        "ranged_unlock": 0,
    },
    "bombs": 0,
    "shields": 0,
    "best_level": 0,
    "best_coins": 0,
    "music_vol": 0.4,
    "sfx_vol": 1.0,
    "gear": {},
    "run_perks": [],
    "total_kills": 0,
    "bosses_killed": 0,
    "achievements": [],
    "challenge_wins": {},
    "seen_perks": [],
    "found_gear": [],
    "difficulty": 1,
}


def _merge(data: dict) -> dict:
    merged = dict(_DEFAULT)
    merged.update(data)
    merged["upgrades"] = dict(_DEFAULT["upgrades"])
    merged["upgrades"].update(data.get("upgrades", {}))
    merged["gear"] = dict(data.get("gear", {}))
    merged["run_perks"] = list(data.get("run_perks", []))
    merged["achievements"] = list(data.get("achievements", []))
    merged["challenge_wins"] = dict(data.get("challenge_wins", {}))
    merged["seen_perks"] = list(data.get("seen_perks", []))
    merged["found_gear"] = list(data.get("found_gear", []))
    return merged


def load_save() -> dict:
    try:
        with open(_SAVE_PATH) as f:
            return _merge(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return copy.deepcopy(_DEFAULT)


def default_save() -> dict:
    return copy.deepcopy(_DEFAULT)


def write_save(data: dict):
    os.makedirs(os.path.dirname(_SAVE_PATH), exist_ok=True)
    with open(_SAVE_PATH, "w") as f:
        json.dump(data, f, indent=2)
