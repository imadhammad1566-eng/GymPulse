"""Start backend, frontend and read-only maintenance checks; Ctrl+C stops all."""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from filelock import FileLock, Timeout

ROOT = Path(__file__).resolve().parent


def main() -> int:
    os.chdir(ROOT)
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Seed synthetic data only if the database is empty")
    parser.add_argument("--stop-file", type=Path, help="Desktop launcher shutdown signal")
    parser.add_argument("--no-console", action="store_true", help="Hide component consoles for the Windows desktop launcher")
    args = parser.parse_args()
    children = []
    backend_port = os.getenv("BACKEND_PORT", "8000")
    frontend_port = os.getenv("FRONTEND_PORT", "8501")
    os.environ.setdefault("API_BASE_URL", f"http://127.0.0.1:{backend_port}")
    Path("runtime").mkdir(exist_ok=True)
    lock_path = Path(os.getenv("GYMPULSE_START_LOCK", "runtime/start.lock"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path), timeout=0)
    try:
        with lock:
            if args.demo:
                from scripts.seed import seed_demo
                print(f"Demo entries loaded: {seed_demo()}", flush=True)
            commands = [
                [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", os.getenv("BACKEND_HOST", "127.0.0.1"), "--port", backend_port],
                [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", frontend_port, "--server.address", "127.0.0.1", "--server.headless", "true", "--browser.gatherUsageStats", "false"],
                [sys.executable, "-m", "maintenance.controller"],
            ]
            for command in commands:
                flags = subprocess.CREATE_NO_WINDOW if args.no_console and os.name == "nt" else 0
                children.append(subprocess.Popen(
                    command, cwd=ROOT, creationflags=flags,
                    stdout=sys.stdout, stderr=sys.stderr,
                ))
            print(f"\nGymPulse: http://127.0.0.1:{frontend_port}\nAPI docs: http://127.0.0.1:{backend_port}/docs\nCtrl+C stops all three components. No replacement is authorized.\n", flush=True)
            while all(child.poll() is None for child in children):
                if args.stop_file and args.stop_file.exists():
                    return 0
                time.sleep(0.5)
            print("A component exited; stopping the complete system.", flush=True)
            return 1
    except Timeout:
        print("GymPulse is already running from this folder.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                if os.name == "nt":
                    # A Windows venv executable can launch a second interpreter.
                    # Stop only this recorded component's tree, not other apps.
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW, check=False,
                    )
                else:
                    child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
