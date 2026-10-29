# Real evidence register

**Do not submit with mandatory fields pending.** This file records actual external results only. Local tests and simulations are not substitutes for GitHub Actions or the real cloud replacement trial. Link this file from README rather than duplicating reports.

## Deployment — pending

| Item | Actual result |
|---|---|
| GitHub repository | Pending |
| Streamlit Community Cloud URL | Pending |
| Render API URL /docs | Pending |
| DB source ID, plan, region, PostgreSQL version | Pending |
| Workout entered via deployed UI and retrieved from API | Pending |
| Same record verified after backend redeploy | Pending |

## Required failed CI then fixed CI — pending

Use a branch that is not connected to Render deployment. Keep automatic deploy disabled for this exercise. Existing tests already detect the fault; do not add a fake failing test or skip a real assertion.

1. Push the working project to GitHub and verify the `GymPulse tests` workflow runs.
2. Create branch `ci-boundary-demo`.
3. In `backend/processing.py` deliberately change `if days < 2:` to `if days <= 2:`. Do not change the tests.
4. Commit and push. Wait for GitHub Actions to fail the existing two-day boundary cases.
5. Fix the condition back to `< 2`, commit, and push. Wait for the same suite to pass.
6. Record both real run URLs below. Submit only the fixed code. Retain branch history if helpful.

| Evidence | Actual link / result |
|---|---|
| Failed Actions run | Pending |
| Successful Actions run after fix | Pending |
| Fault commit | Pending |
| Fix commit | Pending |

Expected explanation, confirm against actual logs: **symptom** — two-day workouts incorrectly return recovery; **cause** — inclusive comparison puts the boundary in the wrong branch; **fix** — restore `< 2`; **verification** — existing parameterized cases and the entire shared suite pass. If the observed result differs, document what actually happened.

## Required actual cloud replacement — pending

Follow README's maintenance setup and obtain explicit owner authorization for the exact source deletion. Use only the synthetic coursework app. Confirm the free plan/API operations remain available to your account before authorizing the run. If limits prevent the supported path, get the instructor's prior agreement to an alternative; do not substitute a simulation.

Add a distinctive new workout after initial seeding, and record its values. Trigger a scheduled, authorized replacement while the source is accessible. From that **same run**, retain:

| Required observation | Actual result / linked redacted file |
|---|---|
| Run UUID; authorized source/backend/workspace | Pending |
| Scheduled asynchronous status/expiry log | Pending |
| Writes frozen and in-progress writes drained | Pending |
| Backup UTC timestamp, source ID and checksum | Pending |
| Post-seed workout included in backup | Pending |
| Isolated local PostgreSQL restore verified before deletion | Pending |
| Explicit source deletion authorization and deletion confirmation | Pending |
| New provider-assigned DB ID, plan, region, version | Pending |
| Target full-content/rule/identifier verification | Pending |
| DATABASE_URL changed and deployment live | Pending |
| Backend API contents/rule results compared | Pending |
| Committed controlled write and cleanup, normal writes still frozen | Pending |
| New active ID saved, completion recorded, writes reopened | Pending |
| Next scheduler check monitors the new DB | Pending |
| Redacted controller log and journal | Pending |

Before publishing evidence, manually review it: no API keys, passwords, authorization headers, connection URLs, personal information or raw secrets settings. Prefer a redacted journal and verification results over publishing a database backup. If publishing a synthetic backup, review every field first.

## Local verification

Run `venv\Scripts\python.exe -m pytest` and save the actual result when final verification is complete. The optional PostgreSQL test is expected to skip locally without `TEST_POSTGRES_URL`, but must run in CI. Local verification results may be stored in `LOCAL_VERIFICATION.md`; they do not fill any cloud/CI field above.
