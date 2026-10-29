"""Run the actual resumable controller with simulated provider HTTP responses."""
import asyncio
from datetime import date, datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from backend.database import Base, make_engine
from backend.models import Workout, WriteGate
from backend.processing import latest_recommendations
from maintenance.backup import create_backup, records
from maintenance.controller import Authorization, MaintenanceController
from maintenance.provider import RenderProvider
from maintenance.storage import atomic_json, read_json


def test_restart_after_create_timeout_adopts_target_without_second_post(tmp_path, fixed_workout, monkeypatch):
    run_id = UUID("2d76f5cf-7a15-4dcc-a46f-09fe2c7d2bd1")
    name = f"gympulse-{run_id.hex}"
    auth = Authorization(run_id=run_id, source_id="dpg-source", service_id="srv-backend", owner_id="tea-owner",
                         backend_url="https://example.onrender.com", maintenance_at=datetime(2026, 1, 12, tzinfo=timezone.utc),
                         plan="free", region="frankfurt", postgres_version="16", controller_cidr="203.0.113.1/32",
                         delete_source_authorized=True, permissions_and_quotas_confirmed=True)
    source = make_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target = make_engine(f"sqlite:///{tmp_path / 'target.db'}")
    Base.metadata.create_all(source)
    with Session(source) as session:
        session.add_all([WriteGate(id=1, blocked=True), Workout(**fixed_workout.model_dump())])
        session.commit()
    create_backup(source, "dpg-source", tmp_path / f"{run_id}.backup.json", date(2026, 1, 12))
    # Persistent state written BEFORE the lost create response.
    atomic_json(tmp_path / f"{run_id}.json", dict(authorization=auth.model_dump(mode="json"), run_id=str(run_id),
                stage="target_creation_submitted", resource_name=name, reference_date="2026-01-12", frozen=True,
                backup_ready=True, trial_verified=True, source_deleted=True, creation_submitted=True))
    calls = []
    instance = {"id": "dpg-adopted", "name": name, "owner": {"id": "tea-owner"}, "status": "available",
                "plan": "free", "region": "frankfurt", "version": "16"}

    def response(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/v1/postgres":
            assert request.method == "GET"  # Never issue another POST /postgres.
            return httpx.Response(200, json=[{"postgres": instance, "cursor": "last"}])
        if request.url.path.endswith("/connection-info"):
            return httpx.Response(200, json={"externalConnectionString": "postgresql://test@localhost/target", "internalConnectionString": "postgresql://test@internal/target"})
        if request.url.path == "/v1/postgres/dpg-adopted":
            return httpx.Response(200, json=instance)
        if request.method == "POST" and request.url.path.endswith("/deploys"):
            return httpx.Response(201, json={"id": "dep-test"})
        if request.method == "GET" and "/deploys/" in request.url.path:
            return httpx.Response(200, json={"status": "live"})
        if request.method == "PUT" and "/env-vars/" in request.url.path:
            return httpx.Response(200, json={})
        raise AssertionError(f"Unexpected mock provider call: {request.method} {request.url.path}")

    class LocalController(MaintenanceController):
        async def preflight(self, authorization):
            # Only prerequisite infrastructure is substituted in this unit test.
            pass

        async def backend(self, authorization, method, path, **kwargs):
            if path == "/workouts":
                return [row.model_dump(mode="json") for row in records(target)]
            if path == "/recommendations":
                return [row.model_dump(mode="json") for row in latest_recommendations(records(target), date(2026, 1, 12))]
            if path == "/admin/maintenance":
                with Session(target) as session:
                    session.get(WriteGate, 1).blocked = kwargs["json"]["blocked"]
                    session.commit()
                return {"blocked": False}
            assert path == "/admin/write-probe"
            return {"message": "simulated test write"}

    monkeypatch.setattr("maintenance.controller.make_engine", lambda url: target)

    async def scenario():
        provider = RenderProvider("fake", httpx.MockTransport(response))
        controller = LocalController(provider, tmp_path, "fake", "unused")
        try:
            await controller.replace(auth)
            call_count = len(calls)
            await controller.replace(auth)  # completed requests are consumed
            assert len(calls) == call_count
        finally:
            await provider.close()
    asyncio.run(scenario())
    assert read_json(tmp_path / f"{run_id}.json")["stage"] == "complete"
    assert read_json(tmp_path / "active.json")["database_id"] == "dpg-adopted"
    assert records(target) == [fixed_workout]
    assert not any(method == "DELETE" for method, path in calls)
    source.dispose()
    target.dispose()
