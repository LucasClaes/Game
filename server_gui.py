import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import json
import os
import webbrowser
import sys
import http.server
import socketserver

SAVE_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "save.json")
GAME_URL     = "http://localhost:8000"
LOADER_PORT  = 8002   # sets localStorage then redirects to game
SAVE_API_PORT = 8001  # receives in-game POST saves

UPGRADES = [
    ("damage",        "Sharper Blade",  5),
    ("fire_rate",     "Swift Strikes",  5),
    ("speed",         "Running Shoes",  5),
    ("health",        "Extra Life",     3),
    ("ranged_unlock", "Slingshot",      1),
]


# ── Save API (port 8001) — receives POST saves from the in-game write_save ──

class _SaveAPIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, "w") as f:
                json.dump(data, f, indent=2)
            self.send_response(200)
            self._cors()
            self.end_headers()
        except Exception:
            self.send_response(400)
            self._cors()
            self.end_headers()


# ── Loader page (port 8002) — injects save into localStorage, redirects to game ──

class _LoaderHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        try:
            with open(SAVE_PATH) as f:
                raw = f.read()
            # Double-encode so it becomes a safe JS string literal
            js_string = json.dumps(raw)
        except FileNotFoundError:
            js_string = '"{}"'

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body>
<script>
try {{ localStorage.setItem('zom_save', {js_string}); }} catch(e) {{}}
location.replace('{GAME_URL}/');
</script>
<p>Loading game&hellip;</p>
</body></html>"""

        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _ReuseServer(socketserver.TCPServer):
    allow_reuse_address = True


def _serve(port, handler):
    with _ReuseServer(("", port), handler) as srv:
        srv.serve_forever()


# ── GUI ──

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Launcher")
        self.root.resizable(False, False)
        self.process = None
        threading.Thread(target=_serve, args=(SAVE_API_PORT, _SaveAPIHandler), daemon=True).start()
        threading.Thread(target=_serve, args=(LOADER_PORT,   _LoaderHandler),  daemon=True).start()
        self._build_ui()

    def _build_ui(self):
        sf = ttk.LabelFrame(self.root, text="Web Server", padding=10)
        sf.pack(fill="x", padx=12, pady=(12, 6))

        self.status_var = tk.StringVar(value="Stopped")
        ttk.Label(sf, textvariable=self.status_var, width=10).pack(side="left")

        self.start_btn = ttk.Button(sf, text="Start", command=self._start)
        self.start_btn.pack(side="left", padx=4)

        self.stop_btn = ttk.Button(sf, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)

        ttk.Button(sf, text="Open in Browser",
                   command=lambda: webbrowser.open(f"http://localhost:{LOADER_PORT}/")).pack(side="left", padx=8)

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
        messagebox.showinfo("Saved", "Saved. Click 'Open in Browser' to reload the game with new data.")

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
