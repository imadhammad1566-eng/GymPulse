# 15-minute presentation guide

Use your own words. Practice explaining code before the presentation; understand every submitted component.

## 0–4 minutes: demonstrate the app

1. Start the system in advance with `venv\Scripts\python.exe start.py --demo`.
2. Show Overview: weekly volume and training balance are calculated from stored entries, not invented numbers.
3. Log Bench Press: 3 sets, minimum 8 reps, target 8 reps, 50 kg, RPE 7.5, a date two days ago.
4. Explain the data path: the form calls the API; the service validates and coordinates saving through SQLAlchemy; the UI then fetches fresh statistics.
5. Training coach: choose today. Expect **increase to 52.5 kg**, provided this is the latest Bench Press entry. Choose a new exercise name if the demo has a later entry.
6. Show that a refresh preserves the entry and Progress reflects it.

## 4–8 minutes: explain the code

- `recommend` is pure: same workout + same date → same output; no HTTP, files or database calls.
- The order matters. A workout from yesterday returns recovery even when its reps and effort would otherwise permit progression.
- `TrainingService` is a meaningful class: it coordinates data access, commits and calculations. Pydantic/ORM classes alone would not satisfy the object-oriented requirement.
- `replace` is a procedural workflow divided into reusable operations: preflight, freeze, backup, trial restore, delete, create, restore, switch, verify, reopen.
- Explain one README design decision and its accepted limitation.

## 8–12 minutes: verification and maintenance

- Run `venv\Scripts\python.exe -m pytest` and explain the distinct test functions and parameterized cases.
- Show both actual GitHub CI URLs after completing the exercise in `EVIDENCE.md`.
- Show the actual cloud replacement trial's redacted controller log and journal. Do not present a local simulation as cloud evidence.
- Point out the backup timestamp/source ID, trial verification, newly assigned instance ID, backend content comparison and committed write probe.
- Explain why maintenance cannot be implemented just by disabling a UI button: clients can call the API directly, and multiple API workers may be running.

## 12–15 minutes: practical change

Example: change the progression effort threshold from 7.5 to 8.0.

1. Predict the effect: the `(2 days, RPE 8, reps 8)` case changes from hold to increase.
2. Find the condition in `backend/processing.py`.
3. Update that boundary expectation and the documented rule/UI explanation together.
4. Run the full suite and demonstrate that case through the API.

Other likely questions:

- Why a 2-day boundary? It is a simple calendar-day planning heuristic, not a physiological recovery model.
- Why reps per set? The minimum across sets ensures that meeting the target means all sets met it. Volume is therefore a conservative estimate when actual reps vary.
- Why a local controller? It keeps backups/run state available independently of the backend and free cloud DB.
- What if creation times out? The journal already records the intent and unique name. On resume, list resources and adopt exactly one match; otherwise stop.
- What if the source is already unavailable? Stop. This normal workflow requires an accessible source; separate recovery approval and a verified prior backup are needed.
- What can still fail? Provider limits, revoked permissions, changed API behavior or unavailable local PostgreSQL. The controller stops and retains the freeze and backup.
