import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "unlock_tree.json")
_CACHE: list | None = None


def get_nodes() -> list:
    global _CACHE
    if _CACHE is None:
        try:
            with open(_PATH) as f:
                _CACHE = json.load(f)["nodes"]
        except Exception:
            _CACHE = []
    return _CACHE


def is_unlocked(player_data: dict, node_id: str) -> bool:
    return node_id in player_data.get("unlocks", [])


def can_unlock(player_data: dict, node: dict) -> bool:
    if is_unlocked(player_data, node["id"]):
        return False
    if player_data.get("coins", 0) < node["cost"]:
        return False
    return all(is_unlocked(player_data, r) for r in node.get("requires", []))


def purchase(player_data: dict, node: dict) -> bool:
    if not can_unlock(player_data, node):
        return False
    player_data["coins"] -= node["cost"]
    player_data.setdefault("unlocks", []).append(node["id"])
    return True
