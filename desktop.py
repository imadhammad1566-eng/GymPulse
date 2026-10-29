"""Windows desktop launcher with a visible, owned server lifecycle."""
import os
import subprocess
import threading
import time
import tkinter as tk
import uuid
import webbrowser
from pathlib import Path
from tkinter import messagebox

import httpx
from dotenv import load_dotenv
from filelock import FileLock, Timeout

ROOT = Path(__file__).resolve().parent


def app_browser(url: str) -> None:
    """Use Edge's app window when installed; otherwise the default browser."""
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for browser in candidates:
        if browser.is_file():
            subprocess.Popen([str(browser), f"--app={url}"], cwd=ROOT)
            return
    webbrowser.open(url)


class DesktopApp:
    def __init__(self, window: tk.Tk):
        self.window = window
        self.process = None
        self.log = None
        self.closing = False
        self.ready = False
        self.result = None
        self.worker_done = threading.Event()
        self.stop_path = ROOT / "runtime" / f"desktop-stop-{uuid.uuid4().hex}"
        self.url = f'http://127.0.0.1:{os.getenv("FRONTEND_PORT", "8501")}'
        window.title("GymPulse")
        window.geometry("440x270")
        window.resizable(False, False)
        window.configure(bg="#101211")
        icon = ROOT / "runtime/gympulse.ico"
        if icon.exists():
            window.iconbitmap(str(icon))
        tk.Label(window, text="gympulse ↗", bg="#101211", fg="#c9fb69", font=("Segoe UI", 28, "bold")).pack(pady=(24, 10))
        self.status = tk.Label(window, text="Starting your training space…", wraplength=390,
                               bg="#101211", fg="#d4ddcf", font=("Segoe UI", 11))
        self.status.pack(pady=8)
        self.open_button = tk.Button(window, text="Open GymPulse", state="disabled", command=self.open,
                                     bg="#c9fb69", fg="#101211", font=("Segoe UI", 11, "bold"), width=23)
        self.open_button.pack(pady=8)
        self.close_button = tk.Button(window, text="Stop and close", command=self.close,
                                      bg="#252b24", fg="#ecf0e9", width=23)
        self.close_button.pack(pady=5)
        window.protocol("WM_DELETE_WINDOW", self.close)
        threading.Thread(target=self.start_services, daemon=True).start()
        window.after(200, self.tick)

    def start_services(self):
        try:
            lock_path = Path(os.getenv("GYMPULSE_START_LOCK", str(ROOT / "runtime/start.lock")))
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock = FileLock(str(lock_path), timeout=0)
            try:
                with lock:
                    already_running = False
            except Timeout:
                already_running = True
            if not already_running and not self.closing:
                self.log = (ROOT / "runtime/desktop.log").open("w", encoding="utf-8")
                self.process = subprocess.Popen(
                    [str(ROOT / "venv/Scripts/python.exe"), str(ROOT / "start.py"),
                     "--demo", "--no-console", "--stop-file", str(self.stop_path)],
                    cwd=ROOT, stdout=self.log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            deadline = time.monotonic() + 120
            with httpx.Client(timeout=2, trust_env=False) as client:
                while time.monotonic() < deadline and not self.closing:
                    if self.process and self.process.poll() is not None:
                        raise RuntimeError("GymPulse could not start. See runtime/desktop.log for details.")
                    try:
                        api_port = os.getenv("BACKEND_PORT", "8000")
                        api = client.get(f"http://127.0.0.1:{api_port}/health")
                        ui = client.get(self.url + "/_stcore/health")
                        if api.is_success and api.json().get("message") == "GymPulse API is running" and ui.text.strip() == "ok":
                            self.result = (True, already_running)
                            return
                    except (httpx.RequestError, ValueError):
                        pass
                    time.sleep(0.5)
            if not self.closing:
                raise RuntimeError("Startup timed out. Check runtime/desktop.log, then try again.")
        except Exception as error:
            self.result = (False, str(error))
        finally:
            self.worker_done.set()

    def tick(self):
        if self.closing:
            if self.worker_done.is_set() and (self.process is None or self.process.poll() is not None):
                if self.log:
                    self.log.close()
                self.stop_path.unlink(missing_ok=True)
                self.window.destroy()
                return
        elif self.result is not None:
            success, detail = self.result
            self.result = None
            if success:
                self.ready = True
                self.status.config(text="GymPulse is open. Keep this small window open while training." if not detail else "Using your already running GymPulse. Closing this launcher leaves it running.")
                self.open_button.config(state="normal")
                self.close_button.config(text="Close launcher" if detail else "Stop and close")
                self.open()
            else:
                self.status.config(text=detail)
                messagebox.showerror("GymPulse startup", detail, parent=self.window)
        if not self.closing and self.ready and self.process and self.process.poll() is not None:
            self.ready = False
            self.status.config(text="GymPulse stopped. Close this launcher and start it again.")
            self.open_button.config(state="disabled")
        self.window.after(200, self.tick)

    def open(self):
        try:
            app_browser(self.url)
        except OSError:
            messagebox.showerror("Open GymPulse", f"Open {self.url} in your browser.", parent=self.window)

    def close(self):
        if not self.closing:
            self.closing = True
            self.stop_path.touch()
            self.status.config(text="Stopping GymPulse…")
            self.open_button.config(state="disabled")
            self.close_button.config(state="disabled")


def main():
    os.chdir(ROOT)
    load_dotenv(ROOT / ".env")
    (ROOT / "runtime").mkdir(exist_ok=True)
    window = tk.Tk()
    DesktopApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
