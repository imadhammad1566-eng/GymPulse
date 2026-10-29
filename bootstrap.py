"""Prepare a fresh checkout using only Python's standard library."""
import argparse
import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def requirement_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for name in ("requirements.txt", "requirements-lock.txt"):
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    return digest.hexdigest()


def prepare_environment(root: Path) -> Path:
    """Create an unshared venv and install the pinned requirements once."""
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Install Python 3.12 and run RUN_ME.cmd again. This project was tested on Python 3.12.")
    environment = root / "venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("Creating the project virtual environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    marker = environment / ".gympulse-requirements.sha256"
    expected = requirement_digest(root)
    if not marker.exists() or marker.read_text(encoding="ascii").strip() != expected:
        print("Installing pinned dependencies. Internet is needed on first setup...", flush=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check",
             "--no-compile", "-r", "requirements.txt"], cwd=root, check=True,
        )
        subprocess.run([str(python), "-m", "pip", "check"], cwd=root, check=True)
        marker.write_text(expected + "\n", encoding="ascii")
    subprocess.run(
        [str(python), "-c", "import fastapi, streamlit, sqlalchemy, httpx"],
        cwd=root, check=True,
    )
    return python


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--test", action="store_true", help="Prepare the environment and run the shared test suite")
    args = parser.parse_args()
    try:
        python = prepare_environment(ROOT)
        if args.test:
            return subprocess.call([str(python), "-m", "pytest"], cwd=ROOT)
        if args.setup_only:
            print("Setup complete. Run RUN_ME.cmd to open GymPulse.")
            return 0
        command = [str(python), "desktop.py"] if os.name == "nt" else [str(python), "start.py", "--demo"]
        return subprocess.call(command, cwd=ROOT)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Setup could not complete: {error}", file=sys.stderr)
        print("See START_HERE.md for manual installation instructions.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
