import json
import os

_ACH_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "achievements.json")
_CACHE: list | None = None


def _load() -> list:
    global _CACHE
    if _CACHE is None:
        try:
            with open(_ACH_PATH) as f:
                _CACHE = json.load(f)["achievements"]
        except Exception:
            _CACHE = []
    return _CACHE


def check_achievements(player_data: dict, callback, extra_stats: dict | None = None) -> list:
    """Check all achievements; unlock any newly earned ones.

    extra_stats: transient stats not saved (e.g. fast_level seconds, perfect_level flag).
    callback(ach): called for each newly unlocked achievement dict.
    Returns list of newly unlocked achievement IDs.
    """
    earned = player_data.setdefault("achievements", [])
    newly = []
    extra = extra_stats or {}

    for ach in _load():
        if ach["id"] in earned:
            continue
        cond = ach["condition"]
        target = ach["target"]
        unlocked = False

        if cond == "total_kills":
            unlocked = player_data.get("total_kills", 0) >= target
        elif cond == "bosses_killed":
            unlocked = player_data.get("bosses_killed", 0) >= target
        elif cond == "best_level":
            unlocked = player_data.get("best_level", 0) >= target
        elif cond == "coins":
            unlocked = player_data.get("coins", 0) >= target
        elif cond == "upgrades_sum":
            total = sum(player_data.get("upgrades", {}).values())
            unlocked = total >= target
        elif cond == "gear_slots":
            slots_filled = len([v for v in player_data.get("gear", {}).values() if v])
            unlocked = slots_filled >= target
        elif cond == "fast_level":
            val = extra.get("fast_level")
            if val is not None:
                unlocked = val <= target
        elif cond == "perfect_level":
            unlocked = bool(extra.get("perfect_level"))

        if unlocked:
            earned.append(ach["id"])
            newly.append(ach["id"])
            if ach.get("reward", 0) > 0:
                player_data["coins"] = player_data.get("coins", 0) + ach["reward"]
            callback(ach)

    return newly


def get_progress(player_data: dict, ach: dict, extra_stats: dict | None = None) -> tuple[int, int]:
    """Return (current, target) for display purposes."""
    extra = extra_stats or {}
    cond = ach["condition"]
    target = ach["target"]
    if cond == "total_kills":
        return player_data.get("total_kills", 0), target
    if cond == "bosses_killed":
        return player_data.get("bosses_killed", 0), target
    if cond == "best_level":
        return player_data.get("best_level", 0), target
    if cond == "coins":
        return player_data.get("coins", 0), target
    if cond == "upgrades_sum":
        return sum(player_data.get("upgrades", {}).values()), target
    if cond == "gear_slots":
        return len([v for v in player_data.get("gear", {}).values() if v]), target
    if cond == "fast_level":
        val = extra.get("fast_level")
        return (int(val) if val is not None else 0), target
    if cond == "perfect_level":
        return (1 if extra.get("perfect_level") else 0), target
    return 0, target
