def equip(player_data: dict, slot: str, gear_id: str) -> bool:
    if gear_id not in player_data.get("inventory", []):
        return False
    player_data.setdefault("gear", {})[slot] = gear_id
    return True


def unequip(player_data: dict, slot: str):
    player_data.setdefault("gear", {}).pop(slot, None)
