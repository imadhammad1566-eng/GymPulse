"""Simulated provider API responses only. No cloud credentials or resources."""
import asyncio
import json
from datetime import date, datetime, timezone

import httpx
import pytest
from sqlalchemy.orm import Session

from backend.database import Base, make_engine
from backend.models import Workout, WriteGate
from maintenance.backup import create_backup, load_backup, records, restore_and_verify
from maintenance.controller import should_replace
from maintenance.provider import ProviderError, RenderProvider, reconcile_creation


@pytest.mark.parametrize("status,authorized,expected", [
    ({"status": "available", "expiresAt": "2026-01-15T00:00:00Z"}, True, True),
    ({"status": "available", "expiresAt": "2026-01-15T00:00:00Z"}, False, False),
    ({"status": "unavailable"}, True, False),
    (None, True, False),
    ({"status": "available", "expiresAt": "2026-01-09T00:00:00Z"}, True, False),
])
def test_maintenance_decision_never_replaces_failed_or_expired_source(status, authorized, expected):
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    assert should_replace(status, now, authorized, now) is expected


def test_temporary_provider_failure_uses_bounded_retries(monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) < 3 else 200, json={"id": "dpg-test", "status": "available"})

    async def no_wait(seconds):
        pass

    monkeypatch.setattr("maintenance.provider.asyncio.sleep", no_wait)

    async def scenario():
        provider = RenderProvider("fake-test-key", httpx.MockTransport(respond))
        try:
            assert (await provider.database("dpg-test"))["status"] == "available"
        finally:
            await provider.close()
    asyncio.run(scenario())
    assert len(calls) == 3


def test_permission_error_does_not_retry_or_upgrade():
    calls = []

    def respond(request):
        calls.append(request.method)
        return httpx.Response(403, json={"message": "forbidden"})

    async def scenario():
        provider = RenderProvider("fake", httpx.MockTransport(respond))
        try:
            with pytest.raises(ProviderError, match="403"):
                await provider.database("dpg-test")
        finally:
            await provider.close()
    asyncio.run(scenario())
    assert calls == ["GET"]


def test_resume_after_interrupted_creation_reconciles_instead_of_creating():
    # Simulate a lost POST response, followed by a list response on controller restart.
    rows = [{"id": "dpg-created", "name": "gympulse-run-123", "owner": {"id": "tea-test"}}]
    assert reconcile_creation(rows, "gympulse-run-123", "tea-test") == "dpg-created"
    with pytest.raises(ProviderError, match="Uncertain"):
        reconcile_creation([], "gympulse-run-123", "tea-test")
    with pytest.raises(ProviderError, match="Uncertain"):
        reconcile_creation(rows + rows, "gympulse-run-123", "tea-test")
    with pytest.raises(ProviderError, match="Uncertain"):
        reconcile_creation(rows, "gympulse-run-123", "tea-someone-else")


def test_missing_invalid_and_wrong_source_backups_stop(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(ValueError, match="Missing or invalid"):
        load_backup(path, "source")
    path.write_text('{"sha256":"wrong", "payload":{}}', encoding="utf-8")
    with pytest.raises(ValueError, match="Missing or invalid"):
        load_backup(path, "source")


def test_backup_restoration_preserves_content_rule_and_identifiers(tmp_path, fixed_workout):
    source = make_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target = make_engine(f"sqlite:///{tmp_path / 'target.db'}")
    Base.metadata.create_all(source)
    with Session(source) as session:
        session.add(WriteGate(id=1, blocked=True))
        session.add(Workout(**fixed_workout.model_dump()))
        session.commit()
    path = tmp_path / "backup.json"
    backup = create_backup(source, "dpg-source", path, date(2026, 1, 12))
    result = restore_and_verify(target, backup)
    assert result == {"records_verified": 1, "rule_results_verified": 1, "identifier_probe": "passed", "reference_date": "2026-01-12"}
    assert records(target) == [fixed_workout]
    assert restore_and_verify(target, backup) == result  # resume does not duplicate data
    with pytest.raises(ValueError):
        load_backup(path, "wrong-source")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"]["records"][0]["weight_kg"] = 999
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ValueError):
        load_backup(path, "dpg-source")
    source.dispose()
    target.dispose()


def test_restore_refuses_unrelated_target_data(tmp_path, fixed_workout):
    from maintenance.backup import Backup
    from backend.processing import latest_recommendations
    target = make_engine(f"sqlite:///{tmp_path / 'unrelated.db'}")
    Base.metadata.create_all(target)
    with Session(target) as session:
        session.add(Workout(**fixed_workout.model_copy(update={"notes": "unrelated data"}).model_dump()))
        session.commit()
    backup = Backup(source_id="test", created_at=datetime.now(timezone.utc), reference_date=date(2026, 1, 12),
                    records=[fixed_workout], recommendations=latest_recommendations([fixed_workout], date(2026, 1, 12)))
    with pytest.raises(ValueError, match="not empty"):
        restore_and_verify(target, backup)
    assert records(target)[0].notes == "unrelated data"
    target.dispose()
