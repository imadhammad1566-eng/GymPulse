"""Real request -> service -> SQLAlchemy -> isolated database -> response."""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.database import make_engine
from backend.main import create_app
from backend.models import Workout


def test_workout_api_persists_processes_and_protects_maintenance(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'api.db'}")
    settings = Settings("unused", "admin-test", "writer-test", False)
    auth = {"Authorization": "Bearer writer-test"}
    admin = {"Authorization": "Bearer admin-test"}
    data = dict(exercise="  bench   press ", muscle="Chest", performed_on="2026-01-10",
                sets=3, reps=8, target_reps=8, weight_kg=50, rpe=7.5, notes="API integration")
    with TestClient(create_app(settings, engine)) as client:
        assert client.get("/workouts").json() == []
        assert client.post("/workouts", json=data).status_code == 401
        response = client.post("/workouts", json=data, headers=auth)
        assert response.status_code == 201
        row = response.json()
        assert row["exercise"] == "Bench Press"
        assert client.get(f'/workouts/{row["id"]}').json() == row
        with Session(engine) as session:
            saved = session.get(Workout, row["id"])
            assert saved.weight_kg == 50 and saved.performed_on == date(2026, 1, 10)
        result = client.get("/recommendations", params={"as_of": "2026-01-12"}).json()
        assert result[0]["action"] == "increase" and result[0]["next_weight_kg"] == 52.5
        assert client.get("/summary").json()["total_volume_kg"] == 1200
        assert client.get("/workouts", params={"muscle": "Back"}).json() == []
        assert client.get("/workouts/999").status_code == 404
        assert client.post("/workouts", json=data | {"sets": 0}, headers=auth).status_code == 422
        assert client.put("/admin/maintenance", json={"blocked": True}).status_code == 401
        assert client.put("/admin/maintenance", json={"blocked": True}, headers=admin).json() == {"blocked": True}
        assert client.post("/workouts", json=data, headers=auth).status_code == 503
        assert client.delete(f'/workouts/{row["id"]}', headers=auth).status_code == 503
        assert client.post("/admin/write-probe", headers=admin).status_code == 200
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Workout)) == 1
        assert client.put("/admin/maintenance", json={"blocked": False}, headers=admin).status_code == 200
        assert client.delete(f'/workouts/{row["id"]}', headers=auth).status_code == 204
        assert client.get("/workouts").json() == []


def test_maintenance_flag_survives_backend_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'persistent.db'}"
    with TestClient(create_app(Settings(url, "secret", "", True))) as client:
        assert client.get("/status").json()["blocked"] is True
        assert client.put("/admin/maintenance", json={"blocked": False}, headers={"Authorization": "Bearer secret"}).status_code == 409
    with TestClient(create_app(Settings(url, "secret", "", False))) as client:
        # A redeploy alone never silently reopens the restored database's gate.
        assert client.get("/status").json()["blocked"] is True


def test_edit_and_import_are_atomic_authenticated_and_maintenance_aware(tmp_path):
    from tests.test_importing import HEADER, ROW
    engine = make_engine(f"sqlite:///{tmp_path / 'editing.db'}")
    auth = {"Authorization": "Bearer writer"}
    admin = {"Authorization": "Bearer admin"}
    with TestClient(create_app(Settings("unused", "admin", "writer", False), engine)) as client:
        payload = {"csv_text": HEADER + ROW + ROW}
        assert client.post("/imports/workouts", json=payload).status_code == 401
        result = client.post("/imports/workouts", json=payload, headers=auth)
        assert result.status_code == 200
        assert result.json() == {"created": 1, "skipped": 1}
        assert client.post("/imports/workouts", json=payload, headers=auth).json() == {"created": 0, "skipped": 2}
        invalid = HEADER + ROW.replace("bench press", "Back Squat") + ROW.replace(",7.5,", ",11,")
        assert client.post("/imports/workouts", json={"csv_text": invalid}, headers=auth).status_code == 422
        assert len(client.get("/workouts").json()) == 1
        existing = client.get("/workouts").json()[0]
        data = {key: value for key, value in existing.items() if key != "id"}
        edited = data | {"weight_kg": 60, "rpe": 9, "notes": "Corrected entry"}
        path = f'/workouts/{existing["id"]}'
        assert client.put(path, json=edited).status_code == 401
        assert client.put(path, json=edited, headers=auth).json()["id"] == existing["id"]
        assert client.get("/summary").json()["total_volume_kg"] == 1440
        assert client.get("/recommendations?as_of=2026-01-12").json()[0]["action"] == "deload"
        assert client.put(path, json=edited | {"sets": 0}, headers=auth).status_code == 422
        assert client.get(path).json()["sets"] == 3
        assert client.put("/workouts/99999", json=edited, headers=auth).status_code == 404
        with Session(engine) as session:
            assert session.get(Workout, existing["id"]).notes == "Corrected entry"
        client.put("/admin/maintenance", json={"blocked": True}, headers=admin)
        assert client.put(path, json=edited, headers=auth).status_code == 503
        assert client.post("/imports/workouts", json=payload, headers=auth).status_code == 503
