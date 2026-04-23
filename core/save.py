import json
import sys
import os

_SAVE_PATH    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "save.json")
_SAVE_API_URL = "http://localhost:8001/"

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


def _merge(data: dict) -> dict:
    merged = dict(_DEFAULT)
    merged.update(data)
    merged["upgrades"] = dict(_DEFAULT["upgrades"])
    merged["upgrades"].update(data.get("upgrades", {}))
    return merged


def load_save() -> dict:
    if sys.platform == "emscripten":
        try:
            from platform import window
            raw = window.localStorage.getItem("zom_save")
            if raw:
                return _merge(json.loads(raw))
        except Exception:
            pass
        return dict(_DEFAULT)
    else:
        try:
            with open(_SAVE_PATH) as f:
                return _merge(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return dict(_DEFAULT)


def write_save(data: dict):
    if sys.platform == "emscripten":
        payload = json.dumps(data)
        # Keep localStorage in sync for mid-session reads
        try:
            from platform import window
            window.localStorage.setItem("zom_save", payload)
        except Exception:
            pass
        # POST back to server_gui.py so the file stays up to date
        try:
            from platform import window
            xhr = window.XMLHttpRequest.new()
            xhr.open("POST", _SAVE_API_URL, True)  # async — cross-origin POST with CORS is fine
            xhr.setRequestHeader("Content-Type", "application/json")
            xhr.send(payload)
        except Exception:
            pass
    else:
        os.makedirs(os.path.dirname(_SAVE_PATH), exist_ok=True)
        with open(_SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)
