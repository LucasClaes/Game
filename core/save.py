import json
import sys
import os

_SAVE_PATH = "data/save.json"

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
}


def load_save() -> dict:
    if sys.platform == "emscripten":
        try:
            from platform import window
            raw = window.localStorage.getItem("zom_save")
            if raw:
                data = json.loads(raw)
                # fill in any missing keys from default
                merged = dict(_DEFAULT)
                merged.update(data)
                merged["upgrades"] = dict(_DEFAULT["upgrades"])
                merged["upgrades"].update(data.get("upgrades", {}))
                return merged
        except Exception:
            pass
        return dict(_DEFAULT)
    else:
        try:
            with open(_SAVE_PATH) as f:
                data = json.load(f)
                merged = dict(_DEFAULT)
                merged.update(data)
                merged["upgrades"] = dict(_DEFAULT["upgrades"])
                merged["upgrades"].update(data.get("upgrades", {}))
                return merged
        except (FileNotFoundError, json.JSONDecodeError):
            return dict(_DEFAULT)


def write_save(data: dict):
    if sys.platform == "emscripten":
        try:
            from platform import window
            window.localStorage.setItem("zom_save", json.dumps(data))
        except Exception:
            pass
    else:
        os.makedirs(os.path.dirname(_SAVE_PATH), exist_ok=True)
        with open(_SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)
