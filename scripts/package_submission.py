"""Create a source-only review ZIP and an explicitly incomplete email draft."""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROOT_FILES = (
    "README.md", "START_HERE.md", "RUN_ME.cmd", "bootstrap.py", "desktop.py",
    "start.py", "start.ps1", "project.py", "requirements.txt",
    "requirements-lock.txt", "pytest.ini", "render.yaml", ".env.example", ".gitignore",
)
EXTRA_FILES = (
    ".github/workflows/tests.yml", ".streamlit/config.toml",
    ".vscode/launch.json", ".vscode/settings.json",
    "data/demo_workouts.csv", "data/import_template.csv",
    "maintenance/authorization.example.json",
)


def source_files(root: Path) -> list[Path]:
    """Allowlist source/configuration; never traverse the venv or runtime."""
    selected = {root / name for name in ROOT_FILES + EXTRA_FILES}
    for package in ("backend", "frontend", "maintenance", "scripts", "tests"):
        selected.update((root / package).rglob("*.py"))
    selected.update((root / "docs").glob("*.md"))
    return sorted(
        (path for path in selected if path.is_file() and not path.is_symlink()
         and "__pycache__" not in path.parts),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def build_package(root: Path = ROOT) -> Path:
    output = root / "submission"
    output.mkdir(exist_ok=True)
    files = source_files(root)
    missing = [name for name in ROOT_FILES + EXTRA_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing required source files: " + ", ".join(missing))
    review = [
        "GYMPULSE - SOURCE READING COPY\n",
        "Generated from the runnable modular project. Do not run this text file.\n",
        "Use RUN_ME.cmd in the extracted project to install and run it.\n\n",
    ]
    for path in files:
        if path.suffix in (".py", ".ps1", ".cmd"):
            name = path.relative_to(root).as_posix()
            review.extend(["\n" + "=" * 78 + "\n", name + "\n", "=" * 78 + "\n", path.read_text(encoding="utf-8"), "\n"])
    reading_copy = "".join(review)
    (output / "ALL_SOURCE_CODE.txt").write_text(reading_copy, encoding="utf-8")
    archive = output / "GymPulse-source.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path in files:
            package.write(path, "GymPulse/" + path.relative_to(root).as_posix())
        package.writestr("GymPulse/ALL_SOURCE_CODE.txt", reading_copy)
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise RuntimeError("Archive integrity check failed")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "GymPulse-source.zip.sha256").write_text(f"{checksum}  {archive.name}\n", encoding="ascii")
    (output / "00_READ_FIRST.txt").write_text(
        "DRAFT SUBMISSION FOLDER - NOT READY TO SEND\n\n"
        "The source ZIP is ready for local review, but it does not replace the three mandatory links.\n"
        "GitHub, Streamlit Community Cloud and Render publication are not completed.\n"
        "The real failed/fixed CI runs and authorized database replacement trial also remain pending.\n\n"
        "GymPulse-source.zip: extract, then open GymPulse/START_HERE.md.\n"
        "ALL_SOURCE_CODE.txt: all Python/launcher source in one reading file.\n"
        "EMAIL_DRAFT.txt: incomplete draft; do not send until real URLs and evidence are ready.\n"
        "No .env, virtual environment, runtime database, backup, controller log or private token is included.\n",
        encoding="utf-8",
    )
    (output / "LINKS.txt").write_text(
        "REQUIRED PUBLICATION LINKS - ALL PENDING\n\n"
        "GitHub repository: PENDING - not published\n"
        "Streamlit Community Cloud application: PENDING - not deployed\n"
        "Render backend/API documentation: PENDING - not deployed\n\n"
        "Do not send localhost/127.0.0.1 URLs or desktop shortcuts as public application links.\n",
        encoding="utf-8",
    )
    (output / "EMAIL_DRAFT.txt").write_text(
        "INCOMPLETE DRAFT - DO NOT SEND YET\n"
        "Replace pending fields only with verified live URLs; complete the required evidence first.\n\n"
        "To: kovacs.adam.eke@gmail.com\n"
        "Subject: Python Project Submission - GymPulse - [Your full name]\n\n"
        "Dear Professor Kovacs,\n\n"
        "Please find my GymPulse Python project below:\n\n"
        "GitHub repository: [PENDING]\n"
        "Streamlit application: [PENDING]\n"
        "Render backend/API documentation: [PENDING]\n\n"
        "The repository README documents installation, the programming paradigms, testing, "
        "CI debugging evidence and the authorized cloud database replacement trial.\n"
        "I have attached a supplementary source ZIP for local review.\n\n"
        "Kind regards,\n[Your full name]\n[Your student ID]\n",
        encoding="utf-8",
    )
    return archive


if __name__ == "__main__":
    archive = build_package()
    print(f"Source package created: {archive} ({archive.stat().st_size:,} bytes)")
    print("Submission folder remains DRAFT until real links and mandatory cloud/CI evidence exist.")
