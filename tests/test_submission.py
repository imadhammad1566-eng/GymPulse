"""Source distribution checks use synthetic files, not local credentials."""
import zipfile

from bootstrap import requirement_digest
from scripts.package_submission import EXTRA_FILES, ROOT_FILES, build_package


def test_source_package_contains_runnable_files_but_not_private_data(tmp_path):
    for name in ROOT_FILES + EXTRA_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("safe sample\n", encoding="utf-8")
    source = tmp_path / "backend/main.py"
    source.parent.mkdir(exist_ok=True)
    source.write_text('"""Example source."""\n', encoding="utf-8")
    for name in (".env", ".streamlit/secrets.toml", "runtime/backup.json",
                 "venv/Lib/private.py", "data/private.csv"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("DO_NOT_SHIP_ME", encoding="utf-8")
    archive = build_package(tmp_path)
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        assert package.testzip() is None
        assert {"GymPulse/RUN_ME.cmd", "GymPulse/bootstrap.py", "GymPulse/START_HERE.md",
                "GymPulse/backend/main.py", "GymPulse/ALL_SOURCE_CODE.txt"} <= names
        assert "GymPulse/.env.example" in names
        assert not any("/runtime/" in name or "/venv/" in name for name in names)
        assert "GymPulse/.env" not in names
        assert "GymPulse/.streamlit/secrets.toml" not in names
        assert "GymPulse/data/private.csv" not in names
        assert all(b"DO_NOT_SHIP_ME" not in package.read(name) for name in names)
        assert "backend/main.py" in package.read("GymPulse/ALL_SOURCE_CODE.txt").decode()
    assert "NOT READY TO SEND" in (tmp_path / "submission/00_READ_FIRST.txt").read_text()


def test_bootstrap_fingerprint_tracks_both_dependency_files(tmp_path):
    requirements = tmp_path / "requirements.txt"
    lock = tmp_path / "requirements-lock.txt"
    requirements.write_text("example==1\n", encoding="utf-8")
    lock.write_text("transitive==1\n", encoding="utf-8")
    first = requirement_digest(tmp_path)
    assert requirement_digest(tmp_path) == first
    lock.write_text("transitive==2\n", encoding="utf-8")
    second = requirement_digest(tmp_path)
    assert second != first
    requirements.write_text("example==2\n", encoding="utf-8")
    assert requirement_digest(tmp_path) != second
