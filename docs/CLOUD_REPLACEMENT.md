# Actual cloud database replacement - verified 2026-11-01

The real scheduled controller replaced the free PostgreSQL 16 database in Frankfurt after explicit owner approval. This is a real cloud run, not simulated test output.

The initial cloud dataset contained two synthetic Bench Press entries (IDs 1 and 2). A separate synthetic maintenance marker (ID 3) was added afterward. All three records were included in the same-run backup and restored. The controller compared every workout field and the deterministic recommendation results, checked identifier generation, verified the live API, performed a committed write/cleanup probe while normal writes remained frozen, then reopened writes.

The former database was deleted only after the checksummed backup and isolated local PostgreSQL restore had passed. A new provider-assigned database ID was recorded. The next scheduler check monitored that new ID successfully.

## Resources and backup

| Item | Actual result |
|---|---|
| Run UUID | 2f71d08d-b63b-447f-8873-b46792e9ad5d |
| Source database | dpg-dbh8t0g473hc7398uhu0-a |
| Replacement database | dpg-dbjk48vb9u1s73e95hkg-a |
| Backend | srv-dbh8t99srm7s73f4sj8g |
| Plan / region / major version | free / frankfurt / 16 |
| Backup UTC timestamp | 2026-11-01T13:44:01.083169Z |
| Backup SHA-256 | f47637d57b83388bc5c46c2003de0fb5fb70f8611a2fba445b391a25c731cdf9 |
| Local restore | {"identifier_probe": "passed", "records_verified": 3, "reference_date": "2026-11-01", "rule_results_verified": 2} |
| Cloud restore | {"identifier_probe": "passed", "records_verified": 3, "reference_date": "2026-11-01", "rule_results_verified": 2} |
| Connection-switch deploy | dep-dbjk4mqjnfac73886e5g |
| Write-reopening deploy | dep-dbjk5loae00c73efr3ug |
| Final stage | complete |

## Redacted durable journal

```json
{
  "authorization": {
    "backend_url": "https://gympulse-api-o9jt.onrender.com",
    "controller_cidr": "[redacted controller IPv4 /32]",
    "delete_source_authorized": true,
    "maintenance_at": "2026-11-01T13:43:46.366866Z",
    "owner_id": "tea-dbh8p80u01pc73ajj820",
    "permissions_and_quotas_confirmed": true,
    "plan": "free",
    "postgres_version": "16",
    "region": "frankfurt",
    "run_id": "2f71d08d-b63b-447f-8873-b46792e9ad5d",
    "service_id": "srv-dbh8t99srm7s73f4sj8g",
    "source_id": "dpg-dbh8t0g473hc7398uhu0-a"
  },
  "backup_created_at": "2026-11-01T13:44:01.083169+00:00",
  "backup_ready": true,
  "creation_submitted": true,
  "deploy_reopen": "dep-dbjk5loae00c73efr3ug",
  "deploy_reopen_done": true,
  "deploy_reopen_submitted": true,
  "deploy_switch": "dep-dbjk4mqjnfac73886e5g",
  "deploy_switch_done": true,
  "deploy_switch_submitted": true,
  "frozen": true,
  "reference_date": "2026-11-01",
  "resource_name": "gympulse-2f71d08db63b447f8873b46792e9ad5d",
  "restore_result": {
    "identifier_probe": "passed",
    "records_verified": 3,
    "reference_date": "2026-11-01",
    "rule_results_verified": 2
  },
  "run_id": "2f71d08d-b63b-447f-8873-b46792e9ad5d",
  "source_deleted": true,
  "stage": "complete",
  "switch_verified": true,
  "target_id": "dpg-dbjk48vb9u1s73e95hkg-a",
  "target_restored": true,
  "trial_result": {
    "identifier_probe": "passed",
    "records_verified": 3,
    "reference_date": "2026-11-01",
    "rule_results_verified": 2
  },
  "trial_verified": true,
  "updated_at": "2026-11-01T13:48:59.146953+00:00"
}
```

## Controller log

Log timestamps use Europe/Paris local time. The backup and journal timestamps explicitly include their UTC offset.

```text
2026-11-01 14:43:34,945 INFO maintenance.controller Async status check database=dpg-dbh8t0g473hc7398uhu0-a status=available expiresAt=2026-11-28T00:08:34.601479Z
2026-11-01 14:43:45,358 INFO maintenance.controller Async status check database=dpg-dbh8t0g473hc7398uhu0-a status=available expiresAt=2026-11-28T00:08:34.601479Z
2026-11-01 14:43:55,777 INFO maintenance.controller Async status check database=dpg-dbh8t0g473hc7398uhu0-a status=available expiresAt=2026-11-28T00:08:34.601479Z
2026-11-01 14:43:56,758 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=started
2026-11-01 14:43:59,777 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=writes_frozen
2026-11-01 14:44:01,101 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=backup_saved
2026-11-01 14:44:01,534 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=isolated_restore_verified
2026-11-01 14:44:01,914 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=source_deletion_submitted
2026-11-01 14:44:03,080 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=source_deletion_confirmed
2026-11-01 14:44:03,087 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=target_creation_submitted
2026-11-01 14:44:04,662 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=target_recorded
2026-11-01 14:44:58,700 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=target_restored_verified
2026-11-01 14:44:58,944 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=target_restored_verified
2026-11-01 14:44:59,634 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=target_restored_verified
2026-11-01 14:46:53,347 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=target_restored_verified
2026-11-01 14:47:02,794 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=switch_and_test_write_verified
2026-11-01 14:47:03,094 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=switch_and_test_write_verified
2026-11-01 14:47:03,658 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=switch_and_test_write_verified
2026-11-01 14:48:57,945 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=switch_and_test_write_verified
2026-11-01 14:48:59,152 INFO maintenance.controller run=2f71d08d-b63b-447f-8873-b46792e9ad5d stage=complete
2026-11-01 14:49:09,564 INFO maintenance.controller Async status check database=dpg-dbjk48vb9u1s73e95hkg-a status=available expiresAt=2026-12-01T13:44:03.781756Z
```

The raw backup, private settings and unredacted authorization remain outside the source package in ignored local runtime storage. No credentials or database connection URLs are included here.
