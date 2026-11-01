# Real evidence register

**Do not submit with mandatory fields pending.** This file records actual external results only. Local tests and simulations are not substitutes for GitHub Actions or the real cloud replacement trial. Link this file from README rather than duplicating reports.

## Deployment — verified 2026-11-01

| Item | Actual result |
|---|---|
| GitHub repository | https://github.com/imadhammad1566-eng/GymPulse — source published |
| Streamlit Community Cloud URL | https://gympulse-3thrmayy9enkkchobq4qqm.streamlit.app/ - opened by owner |
| Render API URL /docs | https://gympulse-api-o9jt.onrender.com/docs — Render deployment confirmed live; public API returned saved workouts on 2026-11-01 |
| DB source ID, plan, region, PostgreSQL version | dpg-dbjk48vb9u1s73e95hkg-a; free; frankfurt; PostgreSQL 16. Replaced source dpg-dbh8t0g473hc7398uhu0-a |
| Workout entered via deployed UI and retrieved from API | Verified 2026-11-01: API returned two Bench Press entries, IDs 1 and 2; each 3 sets, 8 reps, 40 kg, RPE 7 |
| Same record verified after backend redeploy | Verified 2026-11-01: deploy dep-dbjjm8ijnfac73871ep0 became live; both workout records (IDs 1 and 2) matched the complete pre-redeploy contents |

## Required failed CI then fixed CI — verified 2026-11-01

Use a branch that is not connected to Render deployment. Keep automatic deploy disabled for this exercise. Existing tests already detect the fault; do not add a fake failing test or skip a real assertion.

1. Push the working project to GitHub and verify the `GymPulse tests` workflow runs.
2. Create branch `ci-boundary-demo`.
3. In `backend/processing.py` deliberately change `if days < 2:` to `if days <= 2:`. Do not change the tests.
4. Commit and push. Wait for GitHub Actions to fail the existing two-day boundary cases.
5. Fix the condition back to `< 2`, commit, and push. Wait for the same suite to pass.
6. Record both real run URLs below. Submit only the fixed code. Retain branch history if helpful.

| Evidence | Actual link / result |
|---|---|
| Failed Actions run | https://github.com/imadhammad1566-eng/GymPulse/actions/runs/41310063016 - 6 failed, 37 passed |
| Successful Actions run after fix | https://github.com/imadhammad1566-eng/GymPulse/actions/runs/41310197558 - 43 passed; PostgreSQL integration test ran |
| Fault commit | https://github.com/imadhammad1566-eng/GymPulse/commit/f189061cda75fa03aff41c2c945e17a666862f92 |
| Fix commit | https://github.com/imadhammad1566-eng/GymPulse/commit/31f19f3fab930037ba56c360e9561544c2e7b212 |

Observed in the actual GitHub logs: **symptom** — two-day workouts incorrectly return recovery; **cause** — inclusive comparison puts the boundary in the wrong branch; **fix** — restore `< 2`; **verification** — existing parameterized cases and the entire shared suite pass. The faulty run failed two API integration cases and four two-day boundary cases. Tests were unchanged. The corrected branch matches main. Draft PR: https://github.com/imadhammad1566-eng/GymPulse/pull/1 .

## Required actual cloud replacement - verified 2026-11-01

Follow README's maintenance setup and obtain explicit owner authorization for the exact source deletion. Use only the synthetic coursework app. Confirm the free plan/API operations remain available to your account before authorizing the run. If limits prevent the supported path, get the instructor's prior agreement to an alternative; do not substitute a simulation.

Add a distinctive new workout after initial seeding, and record its values. Trigger a scheduled, authorized replacement while the source is accessible. From that **same run**, retain:

| Required observation | Actual result / linked redacted file |
|---|---|
| Run UUID; authorized source/backend/workspace | 2f71d08d-b63b-447f-8873-b46792e9ad5d; exact resources and approval recorded in [cloud report](CLOUD_REPLACEMENT.md) |
| Scheduled asynchronous status/expiry log | Actual scheduler checks before replacement and against the new database afterward; see cloud report |
| Writes frozen and in-progress writes drained | Verified by transaction-level maintenance freeze before backup; persistent provider maintenance setting retained across deployments |
| Backup UTC timestamp, source ID and checksum | 2026-11-01T13:44:01.083169Z; dpg-dbh8t0g473hc7398uhu0-a; SHA-256 f47637d57b83388bc5c46c2003de0fb5fb70f8611a2fba445b391a25c731cdf9 |
| Post-seed workout included in backup | Post-initialization synthetic marker ID 3, added after initial synthetic records 1 and 2, is present in the actual same-run backup |
| Isolated local PostgreSQL restore verified before deletion | {"identifier_probe": "passed", "records_verified": 3, "reference_date": "2026-11-01", "rule_results_verified": 2} |
| Explicit source deletion authorization and deletion confirmation | Owner approved the exact source after the preliminary restore. Same-run journal confirms deletion only after fresh backup and local restore |
| New provider-assigned DB ID, plan, region, version | dpg-dbjk48vb9u1s73e95hkg-a; free; frankfurt; PostgreSQL 16 |
| Target full-content/rule/identifier verification | {"identifier_probe": "passed", "records_verified": 3, "reference_date": "2026-11-01", "rule_results_verified": 2} |
| DATABASE_URL changed and deployment live | Connection-switch deployment dep-dbjk4mqjnfac73886e5g confirmed live |
| Backend API contents/rule results compared | Full record and recommendation comparison passed against the backup after connection switch and committed probe |
| Committed controlled write and cleanup, normal writes still frozen | Authenticated write-probe committed and cleaned up; controller reverified contents before reopening normal writes |
| New active ID saved, completion recorded, writes reopened | Persisted dpg-dbjk48vb9u1s73e95hkg-a; final stage complete; reopening deployment dep-dbjk5loae00c73efr3ug live |
| Next scheduler check monitors the new DB | Actual asynchronous check returned available for dpg-dbjk48vb9u1s73e95hkg-a |
| Redacted controller log and journal | [Actual cloud replacement report](CLOUD_REPLACEMENT.md) |

Before publishing evidence, manually review it: no API keys, passwords, authorization headers, connection URLs, personal information or raw secrets settings. Prefer a redacted journal and verification results over publishing a database backup. If publishing a synthetic backup, review every field first.

## Local verification

Run `venv\Scripts\python.exe -m pytest` and save the actual result when final verification is complete. The optional PostgreSQL test is expected to skip locally without `TEST_POSTGRES_URL`, but must run in CI. Local verification results may be stored in `LOCAL_VERIFICATION.md`; they do not fill any cloud/CI field above.
