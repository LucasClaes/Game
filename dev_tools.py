"""
Dev Tools — Zombie Maze
Launch separately: python dev_tools.py
Apply in-place: writes save.json + signals running game to reload stats live.
Force relaunch:  writes save.json + kills + restarts main.py.
"""
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT       = os.path.dirname(os.path.abspath(__file__))
_SAVE_PATH  = os.path.join(_ROOT, "data", "save.json")
_FLAG_PATH  = os.path.join(_ROOT, "data", ".dev_reload")
_GEAR_PATH  = os.path.join(_ROOT, "data", "gear.json")
_PERKS_PATH = os.path.join(_ROOT, "data", "perks.json")
_SHOP_PATH  = os.path.join(_ROOT, "data", "shop.json")

_DEFAULT_SAVE = {
    "coins": 0, "current_level": 0,
    "upgrades": {"damage":0,"fire_rate":0,"speed":0,"health":0,"armor":0,
                 "ranged_unlock":0,"companion":0,"dash_unlock":0,"dash_upgrade":0},
    "bombs": 0, "shields": 0,
    "best_level": 0, "best_coins": 0,
    "music_vol": 0.4, "sfx_vol": 1.0,
    "gear": {}, "run_perks": [],
}

_UPGRADE_MAX = {
    "damage": 5, "fire_rate": 5, "speed": 5, "health": 3, "armor": 3,
    "ranged_unlock": 1, "companion": 2, "dash_unlock": 1, "dash_upgrade": 2,
}

_SLOTS = ["helm", "chest", "boots", "gloves"]

_game_proc = None


# ── Load helpers ───────────────────────────────────────────────────────────────
def _load_save() -> dict:
    try:
        with open(_SAVE_PATH) as f:
            data = json.load(f)
        merged = dict(_DEFAULT_SAVE)
        merged.update(data)
        merged["upgrades"] = dict(_DEFAULT_SAVE["upgrades"])
        merged["upgrades"].update(data.get("upgrades", {}))
        merged["gear"] = dict(data.get("gear", {}))
        merged["run_perks"] = list(data.get("run_perks", []))
        return merged
    except Exception:
        return dict(_DEFAULT_SAVE)


def _load_gear() -> dict:
    try:
        with open(_GEAR_PATH) as f:
            raw = json.load(f)
        by_slot = {s: [] for s in _SLOTS}
        for g in raw["gear"]:
            by_slot[g["slot"]].append((g["id"], g["name"]))
        return by_slot
    except Exception:
        return {s: [] for s in _SLOTS}


def _load_perks() -> list:
    try:
        with open(_PERKS_PATH) as f:
            return json.load(f)["perks"]
    except Exception:
        return []


# ── App ───────────────────────────────────────────────────────────────────────
class DevTools:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Dev Tools — Zombie Maze")
        root.resizable(False, False)

        self._gear_by_slot = _load_gear()
        self._all_perks    = _load_perks()

        # ── Widgets store ─────────────────────────────────────────────────────
        self._coins_var   = tk.IntVar(value=0)
        self._level_var   = tk.IntVar(value=0)
        self._upgrade_vars: dict[str, tk.IntVar] = {}
        self._bombs_var   = tk.IntVar(value=0)
        self._shields_var = tk.IntVar(value=0)
        self._gear_vars:  dict[str, tk.StringVar] = {}
        self._perk_vars:  dict[str, tk.BooleanVar] = {}
        self._mode_var    = tk.StringVar(value="inplace")

        self._build_ui()
        self._load_from_save()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=8, pady=4)

        # PLAYER
        pf = ttk.LabelFrame(self.root, text="PLAYER")
        pf.grid(row=0, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Label(pf, text="Coins:").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(pf, textvariable=self._coins_var, from_=0, to=999999,
                    width=10).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(pf, text="Level:").grid(row=0, column=2, sticky="w", padx=(16, 0))
        ttk.Spinbox(pf, textvariable=self._level_var, from_=0, to=100,
                    width=6).grid(row=0, column=3, sticky="w", padx=4)

        # UPGRADES
        uf = ttk.LabelFrame(self.root, text="UPGRADES")
        uf.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)
        upg_layout = [
            ("damage", "Damage (0-5)"),
            ("fire_rate", "Fire Rate (0-5)"),
            ("speed", "Speed (0-5)"),
            ("health", "Health (0-3)"),
            ("armor", "Armor (0-3)"),
            ("ranged_unlock", "Ranged (0/1)"),
            ("companion", "Companion (0-2)"),
            ("dash_unlock", "Dash (0/1)"),
            ("dash_upgrade", "Dash II (0-2)"),
        ]
        for idx, (key, label) in enumerate(upg_layout):
            row, col = divmod(idx, 3)
            var = tk.IntVar(value=0)
            self._upgrade_vars[key] = var
            ttk.Label(uf, text=label).grid(row=row, column=col * 2, sticky="w", padx=4, pady=2)
            ttk.Spinbox(uf, textvariable=var, from_=0, to=_UPGRADE_MAX.get(key, 5),
                        width=4).grid(row=row, column=col * 2 + 1, sticky="w", padx=4)

        # CONSUMABLES
        cf = ttk.LabelFrame(self.root, text="CONSUMABLES")
        cf.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Label(cf, text="Bombs (0-9):").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(cf, textvariable=self._bombs_var, from_=0, to=9,
                    width=4).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(cf, text="Shields (0-6):").grid(row=0, column=2, sticky="w", padx=(16, 0))
        ttk.Spinbox(cf, textvariable=self._shields_var, from_=0, to=6,
                    width=4).grid(row=0, column=3, sticky="w", padx=4)

        # GEAR
        gf = ttk.LabelFrame(self.root, text="GEAR")
        gf.grid(row=3, column=0, columnspan=2, sticky="ew", **pad)
        for col, slot in enumerate(_SLOTS):
            ttk.Label(gf, text=slot.upper()).grid(row=0, column=col, padx=8)
            var = tk.StringVar(value="— none —")
            self._gear_vars[slot] = var
            options = ["— none —"] + [name for _, name in self._gear_by_slot[slot]]
            om = ttk.OptionMenu(gf, var, "— none —", *options)
            om.config(width=14)
            om.grid(row=1, column=col, padx=4, pady=4)

        # RUN PERKS
        pkf = ttk.LabelFrame(self.root, text="RUN PERKS  (max 4 active)")
        pkf.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)
        for idx, perk in enumerate(self._all_perks):
            row, col = divmod(idx, 3)
            var = tk.BooleanVar(value=False)
            self._perk_vars[perk["id"]] = var
            cb = ttk.Checkbutton(pkf, text=perk["name"], variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=6, pady=2)

        # APPLY MODE
        mf = ttk.LabelFrame(self.root, text="APPLY MODE")
        mf.grid(row=5, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Radiobutton(mf, text="Apply in-place  (live reload, no relaunch)",
                        variable=self._mode_var, value="inplace").grid(row=0, column=0, sticky="w", padx=6)
        ttk.Radiobutton(mf, text="Force relaunch  (restarts main.py)",
                        variable=self._mode_var, value="relaunch").grid(row=1, column=0, sticky="w", padx=6)

        # BUTTONS
        bf = ttk.Frame(self.root)
        bf.grid(row=6, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text="APPLY / SAVE", command=self._apply,
                   width=20).grid(row=0, column=0, padx=6)
        ttk.Button(bf, text="MAX ALL UPGRADES", command=self._max_upgrades,
                   width=20).grid(row=0, column=1, padx=6)
        ttk.Button(bf, text="RELOAD FROM SAVE", command=self._load_from_save,
                   width=20).grid(row=0, column=2, padx=6)

    # ── Data helpers ──────────────────────────────────────────────────────────
    def _load_from_save(self):
        data = _load_save()
        self._coins_var.set(data.get("coins", 0))
        self._level_var.set(data.get("current_level", 0))
        upg = data.get("upgrades", {})
        for key, var in self._upgrade_vars.items():
            var.set(upg.get(key, 0))
        self._bombs_var.set(data.get("bombs", 0))
        self._shields_var.set(data.get("shields", 0))

        gear = data.get("gear", {})
        id_to_name = {gid: name
                      for slot_list in self._gear_by_slot.values()
                      for gid, name in slot_list}
        for slot, var in self._gear_vars.items():
            gid = gear.get(slot)
            var.set(id_to_name.get(gid, "— none —") if gid else "— none —")

        owned_perks = set(data.get("run_perks", []))
        for pid, var in self._perk_vars.items():
            var.set(pid in owned_perks)

    def _build_save_dict(self) -> dict:
        data = _load_save()  # start from current save so we preserve best/vol etc.

        data["coins"] = self._coins_var.get()
        data["current_level"] = self._level_var.get()

        for key, var in self._upgrade_vars.items():
            data["upgrades"][key] = var.get()

        data["bombs"]   = self._bombs_var.get()
        data["shields"] = self._shields_var.get()

        name_to_id = {name: gid
                      for slot_list in self._gear_by_slot.values()
                      for gid, name in slot_list}
        data["gear"] = {}
        for slot, var in self._gear_vars.items():
            chosen = var.get()
            if chosen != "— none —" and chosen in name_to_id:
                data["gear"][slot] = name_to_id[chosen]

        active_perks = [pid for pid, var in self._perk_vars.items() if var.get()]
        if len(active_perks) > 4:
            messagebox.showwarning("Dev Tools", "Max 4 perks — only first 4 will be saved.")
            active_perks = active_perks[:4]
        data["run_perks"] = active_perks

        return data

    def _write_save(self, data: dict):
        os.makedirs(os.path.dirname(_SAVE_PATH), exist_ok=True)
        with open(_SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _apply(self):
        data = self._build_save_dict()
        self._write_save(data)

        if self._mode_var.get() == "relaunch":
            self._do_relaunch()
        else:
            self._do_inplace_reload()

    def _do_inplace_reload(self):
        try:
            with open(_FLAG_PATH, "w") as f:
                f.write("reload")
        except Exception as e:
            messagebox.showerror("Dev Tools", f"Failed to write reload flag:\n{e}")
            return
        self.root.title("Dev Tools — APPLIED ✓")
        self.root.after(1500, lambda: self.root.title("Dev Tools — Zombie Maze"))

    def _do_relaunch(self):
        global _game_proc
        if _game_proc and _game_proc.poll() is None:
            _game_proc.terminate()
            try:
                _game_proc.wait(timeout=3)
            except Exception:
                _game_proc.kill()
        _game_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=_ROOT,
        )
        self.root.title("Dev Tools — RELAUNCHED ✓")
        self.root.after(1500, lambda: self.root.title("Dev Tools — Zombie Maze"))

    def _max_upgrades(self):
        for key, var in self._upgrade_vars.items():
            var.set(_UPGRADE_MAX.get(key, 5))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = DevTools(root)
    root.mainloop()
