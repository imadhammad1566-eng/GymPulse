# Assignment coverage

This checklist maps the implementation to the assignment. Actual deployment, failed/fixed CI and authorized cloud replacement results are recorded in `EVIDENCE.md`. The README is the central documentation.

| Brief | Implementation / evidence |
|---|---|
| FastAPI, independently runnable Streamlit, SQLAlchemy | `backend/main.py`, `frontend/app.py`, `backend/models.py` |
| UI → API → processing → persistent database | Workout form → `POST /workouts` → `TrainingService.log_workout` → repository |
| Topic-specific processing | `backend/processing.py`, recovery and progressive overload rule |
| Procedural / functional / object-oriented | `MaintenanceController.replace` workflow; pure `recommend`/`summarize`; behavioral `TrainingService` and `GymClient` |
| At least 3 meaningful application routes | List/create/edit/detail/delete workouts, atomic CSV import, summary, recommendations |
| Input and response schemas; proper errors | Pydantic schemas; 201, 204, 401, 404, 409, 422, 503 responses |
| SQLAlchemy commits, rollbacks and sessions | Request dependency, service, repository; gate lock retained to transaction end |
| Data entry, chart, client failures, empty results | Four UI sections; Plotly charts; `ApiError` and empty-state handling |
| Logging and network timeouts | Named Python loggers; bounded HTTP operations and readiness polls |
| Shared pytest suite | `tests/`; parameterized rule and decision tests, API integration, restoration and resume tests |
| GitHub Actions | `.github/workflows/tests.yml`; SQLite temporary DBs plus isolated PostgreSQL service |
| Failed CI → fixed CI evidence | **Verified 2026-11-01:** 6 failed/37 passed, then 43 passed. Actual runs in `docs/EVIDENCE.md` |
| Virtual environment, pins and complete startup | `requirements.txt`, `start.py`, `start.ps1`, `project.py`, `.env.example` |
| Secrets excluded | `.gitignore`; env configuration; authenticated maintenance; optional app write token |
| Streamlit Community Cloud + Render | **Published:** GitHub, Streamlit and Render links in `docs/EVIDENCE.md` |
| Persistent cloud database | External PostgreSQL via `DATABASE_URL`; no cloud SQLite fallback in deployment configuration |
| Independent scheduled async controller | `python -m maintenance.controller`; actual awaited Render requests |
| Authorization, resource scope and permissions | Exact IDs/config match; single supported free plan; explicit deletion and quota attestations |
| Stop and drain writes; preserve freeze on redeploy | Transaction-wide database gate + persistent Render maintenance env variable |
| Current backup independent of cloud DB/backend | Typed JSON export + SHA-256 + UTC timestamp + source ID on controller computer |
| Restore contents, rule output and ID generation | `restore_and_verify`; fixed reference date; full field comparison; sequence reseed + insert probe |
| Free single-instance workflow | Isolated local PostgreSQL restore verified before source deletion, deletion polled before create |
| Create, restore, API switch, deploy, read and test write | `MaintenanceController.replace`, Render API adapter, protected committed write probe |
| Durable journal, process lock, bounded retries | Atomic fsynced JSON; `FileLock`; 3 read attempts, bounded polls; uncertain POST never repeated |
| Resume uncertain creation | Run-specific resource name and saved intent; reconcile exactly one match or stop |
| Actual complete cloud replacement trial | **Verified 2026-11-01:** actual authorized replacement; redacted journal and log in `CLOUD_REPLACEMENT.md` |
| README, datasets, decisions and AI disclosure | README, CSV dataset, presentation guide and evidence instructions |
| Optional extensions | None claimed. Plotly/CSV are ordinary features; no unverified bonus claims |

Cloud deployment, real CI failure/fix and the actual replacement trial were verified on 2026-11-01. See the evidence register for the actual results.
