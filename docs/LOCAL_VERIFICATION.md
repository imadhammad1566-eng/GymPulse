# Local verification

Application verified on Windows with Python 3.12.10 on 28 October 2026; desktop launcher checks added on 29 October 2026.

| Check | Actual result |
|---|---|
| `venv\Scripts\python.exe -m pip install -r requirements.txt` | Installed successfully |
| `venv\Scripts\python.exe -m pip check` | No broken requirements found |
| Extracted source ZIP: `python -m pytest -q --tb=short` | **42 passed, 1 skipped**, 38.42 seconds, using the existing verified Python 3.12 environment |
| Optional skipped check | PostgreSQL export/restore/sequence check: no local `TEST_POSTGRES_URL`; CI is configured to provide PostgreSQL 16 |
| Syntax compilation | `compileall` succeeded for application, controller, utilities and tests |
| Dashboard tests | Form saved and edited a workout through actual FastAPI + isolated SQLAlchemy DB; all four pages rendered without exceptions; CSV preview/confirmation/import and backend-unavailable feedback verified |
| CSV validation | Missing/unknown/duplicate columns, malformed quotes, invalid values, ragged rows and the 500-row limit verified; UTF-8 BOM and quoted commas accepted |
| Import/edit integration | Exact duplicates skipped on repeat import; invalid files saved no rows; updates preserved IDs and changed summaries/rules; application authorization and maintenance gate enforced |
| Controller startup | `python -m maintenance.controller --once` exited 0; missing cloud configuration logged as checks disabled, no replacement authorized |
| Complete startup | `python start.py --demo` started backend, frontend and maintenance monitor; 17 synthetic exercise entries loaded |
| Live `GET /workouts` | HTTP 200; 17 records |
| Live `GET /summary` | HTTP 200; 17 exercise entries |
| Live dashboard `/` | HTTP 200 |
| Live Streamlit `/_stcore/health` | `ok` |
| Complete system restart | Seed loaded 0 new rows; API still returned the original 17 records; dashboard returned HTTP 200 |
| Duplicate startup protection | A second startup from the same folder was refused by the process lock |
| Component failure cleanup | Stopping the owned backend caused the startup supervisor to stop the frontend and monitor; verification servers were stopped after checks |
| Desktop shortcut | Installed `GymPulse.lnk` on the Windows desktop, targeting the project virtual environment's windowless Python launcher |
| Native desktop smoke | Hidden Tk control window reached backend/frontend readiness, called the app-open callback, then stopped its owned process trees; both isolated server ports were closed after shutdown (23.5 seconds) |
| Windows shutdown | Stops only recorded component process trees, including virtual-environment interpreter wrappers; a pre-existing GymPulse session is reused and left running |
| Submission package | ZIP extracted into a separate review folder; its actual code passed the shared suite. Archive CRC integrity and exclusion of private runtime/settings files verified |
| Bootstrap | `python bootstrap.py --setup-only` completed against the existing venv; pinned packages satisfied, `pip check` clean and imports succeeded. A fresh download/install on another computer was not separately exercised |

The suite emitted one upstream Starlette/AnyIO deprecation warning about a moved `BlockingPortal` alias; no test failed. It is recorded rather than suppressed.

UI verification used Streamlit's test renderer and HTTP checks, not a visual browser screenshot. No live cloud API, deployed database, paid resource, GitHub Actions run or actual cloud replacement was used in these tests. Those mandatory external results remain pending in [EVIDENCE.md](EVIDENCE.md).
