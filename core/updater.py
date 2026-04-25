import json
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

_REPO    = "LucasClaes/Game"
_API_URL = f"https://api.github.com/repos/{_REPO}/releases/latest"


def check_and_update(current_version: str) -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        req = urllib.request.Request(_API_URL, headers={"User-Agent": "ZombieMaze-Updater"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        latest = data["tag_name"]
        if latest == current_version:
            return

        download_url = next(
            (a["browser_download_url"] for a in data["assets"]
             if a["name"].endswith("-windows.zip")),
            None,
        )
        if not download_url:
            return

        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        answer = messagebox.askyesno(
            "Update Available",
            f"Version {latest} is available (you have {current_version}).\n\n"
            "Download and install now?\nThe game will restart automatically.",
        )
        root.destroy()
        if not answer:
            return

        import tkinter.ttk as ttk
        prog_root = tk.Tk()
        prog_root.title("Downloading update...")
        prog_root.geometry("340x90")
        prog_root.resizable(False, False)
        lbl = tk.Label(prog_root, text="Downloading...", font=("Segoe UI", 11))
        lbl.pack(pady=14)
        bar = ttk.Progressbar(prog_root, length=300, mode="determinate")
        bar.pack()
        prog_root.update()

        tmp_dir  = Path(tempfile.mkdtemp())
        zip_path = tmp_dir / "update.zip"

        def _progress(count, block_size, total_size):
            if total_size > 0:
                bar["value"] = min(100, count * block_size / total_size * 100)
            prog_root.update()

        urllib.request.urlretrieve(download_url, zip_path, reporthook=_progress)
        lbl.config(text="Installing...")
        bar["value"] = 100
        prog_root.update()

        extract_dir = tmp_dir / "extracted"
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(extract_dir)

        new_game_dir = extract_dir / "ZombieMaze"
        install_dir  = Path(sys.executable).parent

        bat = (
            "@echo off\r\n"
            "timeout /t 2 /nobreak > nul\r\n"
            f'xcopy /E /Y /I "{new_game_dir}" "{install_dir}" > nul\r\n'
            f'start "" "{install_dir}\\ZombieMaze.exe"\r\n'
            'del "%~f0"\r\n'
        )
        bat_path = tmp_dir / "update.bat"
        bat_path.write_text(bat)

        prog_root.destroy()
        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
        sys.exit(0)

    except Exception:
        pass
