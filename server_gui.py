import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import json
import os
import webbrowser
import sys

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "save.json")
SERVER_URL = "http://localhost:8000"

UPGRADES = [
    ("damage",        "Sharper Blade",  5),
    ("fire_rate",     "Swift Strikes",  5),
    ("speed",         "Running Shoes",  5),
    ("health",        "Extra Life",     3),
    ("ranged_unlock", "Slingshot",      1),
]


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Launcher")
        self.root.resizable(False, False)
        self.process = None
        self._build_ui()

    def _build_ui(self):
        # --- Server ---
        sf = ttk.LabelFrame(self.root, text="Web Server", padding=10)
        sf.pack(fill="x", padx=12, pady=(12, 6))

        self.status_var = tk.StringVar(value="Stopped")
        dot = ttk.Label(sf, textvariable=self.status_var, width=10)
        dot.pack(side="left")

        self.start_btn = ttk.Button(sf, text="Start", command=self._start)
        self.start_btn.pack(side="left", padx=4)

        self.stop_btn = ttk.Button(sf, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)

        ttk.Button(sf, text="Open in Browser",
                   command=lambda: webbrowser.open(SERVER_URL)).pack(side="left", padx=8)

        # --- Save data ---
        df = ttk.LabelFrame(self.root, text="Save Data", padding=10)
        df.pack(fill="x", padx=12, pady=6)

        self.fields = {}

        def _row(parent, label, key, lo, hi):
            r = ttk.Frame(parent)
            r.pack(fill="x", pady=3)
            ttk.Label(r, text=label, width=22, anchor="w").pack(side="left")
            var = tk.IntVar()
            ttk.Spinbox(r, from_=lo, to=hi, textvariable=var, width=7).pack(side="left")
            self.fields[key] = var

        _row(df, "Coins", "coins", 0, 99999)
        _row(df, "Current Level", "current_level", 0, 999)

        ttk.Separator(df, orient="horizontal").pack(fill="x", pady=6)
        ttk.Label(df, text="Upgrades", font=("", 9, "bold")).pack(anchor="w")

        for uid, name, max_lvl in UPGRADES:
            _row(df, f"  {name}", uid, 0, max_lvl)

        btn_row = ttk.Frame(df)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="Load from file", command=self._load).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Save to file",   command=self._save).pack(side="left", padx=4)

        self._load()

    # --- save data ---

    def _load(self):
        if not os.path.exists(SAVE_PATH):
            return
        with open(SAVE_PATH) as f:
            data = json.load(f)
        self.fields["coins"].set(data.get("coins", 0))
        self.fields["current_level"].set(data.get("current_level", 0))
        ups = data.get("upgrades", {})
        for uid, _, _ in UPGRADES:
            self.fields[uid].set(ups.get(uid, 0))

    def _save(self):
        data = {
            "coins": self.fields["coins"].get(),
            "current_level": self.fields["current_level"].get(),
            "upgrades": {uid: self.fields[uid].get() for uid, _, _ in UPGRADES},
        }
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", "Save data written to data/save.json")

    # --- server ---

    def _start(self):
        if self.process:
            return
        self.process = subprocess.Popen(
            [sys.executable, "-m", "pygbag", "main.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.status_var.set("Running")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        threading.Thread(target=self._monitor, daemon=True).start()

    def _monitor(self):
        self.process.wait()
        self.process = None
        self.root.after(0, self._on_stopped)

    def _on_stopped(self):
        self.status_var.set("Stopped")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _stop(self):
        if self.process:
            self.process.terminate()

    def _on_close(self):
        self._stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app._on_close)
    root.mainloop()
