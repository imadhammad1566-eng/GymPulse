# Actual failed-then-fixed GitHub Actions evidence

Verified on 2026-11-01 in the isolated `ci-boundary-demo` branch. The published main branch retained the correct training rule throughout.

- [Fault commit](https://github.com/imadhammad1566-eng/GymPulse/commit/f189061cda75fa03aff41c2c945e17a666862f92): changed `if days < 2:` to `if days <= 2:` in `backend/processing.py`. No tests were changed.
- [Failed GitHub Actions run](https://github.com/imadhammad1566-eng/GymPulse/actions/runs/41310063016): **6 failed, 37 passed**. Four two-day boundary cases and two API integration cases detected the regression.
- [Fix commit](https://github.com/imadhammad1566-eng/GymPulse/commit/31f19f3fab930037ba56c360e9561544c2e7b212): restored `if days < 2:` without changing the tests.
- [Successful GitHub Actions run](https://github.com/imadhammad1566-eng/GymPulse/actions/runs/41310197558): **43 passed**, including the real PostgreSQL integration test; one dependency deprecation warning.
- [Evidence pull request](https://github.com/imadhammad1566-eng/GymPulse/pull/1): retained as a draft to preserve the demonstration history; it is not required for deployment.

## Diagnosis

The faulty inclusive comparison classified workouts exactly two days old as recovery. Existing cases expected progression, holding the load, or deloading according to reps and RPE. Restoring the strict comparison allowed those workouts to reach the correct decision branches. The complete unchanged suite then passed in GitHub Actions with its PostgreSQL 16 service.

The real failure summary named these tests:

```text
FAILED tests/test_api.py::test_workout_api_persists_processes_and_protects_maintenance
FAILED tests/test_api.py::test_edit_and_import_are_atomic_authenticated_and_maintenance_aware
FAILED tests/test_processing.py::test_training_rule_boundaries[2-7.5-8-increase-52.5]
FAILED tests/test_processing.py::test_training_rule_boundaries[2-8-8-hold-50]
FAILED tests/test_processing.py::test_training_rule_boundaries[2-7-7-hold-50]
FAILED tests/test_processing.py::test_training_rule_boundaries[2-9-8-deload-45]
6 failed, 37 passed, 1 warning
```
