# Open and run GymPulse

## Windows quick start for the reviewer

1. Extract the entire ZIP. Do not run files from inside the ZIP viewer.
2. Install Python **3.12** if it is not already installed. The initial package installation needs internet access.
3. Open the extracted `GymPulse` folder in VS Code using **File → Open Folder**.
4. Double-click **RUN_ME.cmd** in Windows Explorer, or run it from the VS Code terminal.
5. First setup creates a fresh `venv` and installs the pinned dependencies. Then the desktop control window opens and launches the dashboard. Keep the control window open while using the app.

The application is at `http://127.0.0.1:8501`; API documentation is at `http://127.0.0.1:8000/docs`. These are local addresses, not public submission links. Stop and close the desktop control window when done. Keep the setup console open until the app closes.

Sample workouts are loaded only into an empty database. The archive contains no student's runtime database or virtual environment. No cloud database replacement is authorized by this startup.

## Manual alternative

From the extracted project root:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe start.py --demo
```

Open the local dashboard in your browser. Ctrl+C stops this terminal-based startup.

To prepare and test in one command:

```powershell
py -3.12 bootstrap.py --test
```

The ordinary test suite uses isolated databases; the optional PostgreSQL check needs a dedicated test server, supplied by the GitHub Actions configuration. See `README.md` and `docs/LOCAL_VERIFICATION.md` for actual recorded verification.

## Read the code

- `start.py`: starts and stops the separate components.
- `desktop.py`: Tkinter launcher and browser app window.
- `frontend/`: dashboard and HTTP client.
- `backend/`: API, validation, processing, service and SQLAlchemy storage.
- `maintenance/`: independent cloud status checks, backups and authorized replacement.
- `tests/`: one shared pytest suite.
- `docs/`: presentation guide, requirements checklist and evidence register.

`ALL_SOURCE_CODE.txt`, when included in the release ZIP, is a generated single-file reading copy. The original files are the runnable project; the reading copy is not an executable.

## Submission status

This ZIP is a supplementary local source package. The assignment still requires real GitHub, Streamlit Community Cloud and Render links, actual CI evidence and a documented authorized cloud replacement trial. Pending entries in `docs/EVIDENCE.md` must not be presented as completed results.
