"""Typed, checksummed application export and reusable restore/verification."""
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models import Workout, WriteGate
from backend.processing import latest_recommendations
from backend.schemas import Recommendation, WorkoutOut
from maintenance.storage import atomic_json, read_json


class Backup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format_version: Literal[1] = 1
    source_id: str
    created_at: datetime
    reference_date: date
    records: list[WorkoutOut]
    recommendations: list[Recommendation]

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError("Backup timestamp must include a time zone")
        return value


def fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def records(engine: Engine) -> list[WorkoutOut]:
    with Session(engine) as session:
        return [WorkoutOut.model_validate(row) for row in session.scalars(select(Workout).order_by(Workout.id))]


def create_backup(engine: Engine, source_id: str, path: Path, reference_date: date) -> Backup:
    with Session(engine) as session:
        gate = session.get(WriteGate, 1)
        if gate is None or not gate.blocked:
            raise ValueError("Block and drain application writes before backing up")
    rows = records(engine)
    backup = Backup(source_id=source_id, created_at=datetime.now(timezone.utc), reference_date=reference_date,
                    records=rows, recommendations=latest_recommendations(rows, reference_date))
    payload = backup.model_dump(mode="json")
    atomic_json(path, {"sha256": fingerprint(payload), "payload": payload})
    return load_backup(path, source_id)


def load_backup(path: Path, source_id: str) -> Backup:
    try:
        envelope = read_json(path)
        if fingerprint(envelope["payload"]) != envelope["sha256"]:
            raise ValueError("Backup checksum mismatch")
        backup = Backup.model_validate(envelope["payload"])
        if backup.source_id != source_id:
            raise ValueError("Backup source identifier does not match authorization")
        if len({row.id for row in backup.records}) != len(backup.records):
            raise ValueError("Backup contains duplicate identifiers")
        expected = latest_recommendations(backup.records, backup.reference_date)
        if expected != backup.recommendations:
            raise ValueError("Backup's domain-rule result does not match")
        return backup
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError("Missing or invalid backup; replacement must stop") from error


def restore_and_verify(engine: Engine, backup: Backup) -> dict:
    """Restore only into an empty or already identical target; never erase data."""
    Base.metadata.create_all(engine)
    current = records(engine)
    expected = sorted(backup.records, key=lambda row: row.id)
    if current and current != expected:
        raise ValueError("Restore target is not empty or does not match this run")
    with Session(engine) as session:
        gate = session.get(WriteGate, 1)
        if gate is None:
            session.add(WriteGate(id=1, blocked=True))
        else:
            gate.blocked = True
        if not current:
            session.add_all(Workout(**row.model_dump()) for row in expected)
        session.commit()
        if engine.dialect.name == "postgresql":
            # Explicit IDs must advance the PostgreSQL identifier sequence.
            session.execute(text("SELECT setval(pg_get_serial_sequence('workouts', 'id'), "
                                 "COALESCE((SELECT MAX(id) FROM workouts), 1), "
                                 "EXISTS(SELECT 1 FROM workouts))"))
            session.commit()
    actual = records(engine)
    if actual != expected:
        raise ValueError("Restored field contents do not match the backup")
    if latest_recommendations(actual, backup.reference_date) != backup.recommendations:
        raise ValueError("Restored domain-rule output does not match")
    with Session(engine) as session:
        probe = Workout(exercise="Restore Probe", muscle="Core", performed_on=backup.reference_date,
                        sets=1, reps=1, target_reps=1, weight_kg=1, rpe=1, notes="rolled back")
        session.add(probe)
        session.flush()
        if probe.id <= max((row.id for row in expected), default=0):
            raise ValueError("Identifier generation was not preserved")
        session.rollback()
    return {"records_verified": len(actual), "rule_results_verified": len(backup.recommendations),
            "identifier_probe": "passed", "reference_date": backup.reference_date.isoformat()}
