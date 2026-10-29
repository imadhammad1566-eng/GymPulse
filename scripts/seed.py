"""Load disclosed synthetic demo rows once, without overwriting existing data."""
import csv
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.database import Base, make_engine
from backend.models import Workout, WriteGate
from backend.repository import WritesBlocked, acquire_gate, create_workout
from backend.schemas import WorkoutInput


def seed_demo() -> int:
    config = Settings.from_env()
    engine = make_engine(config.database_url)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            if session.get(WriteGate, 1) is None:
                session.add(WriteGate(id=1, blocked=config.maintenance_mode))
                session.commit()
            gate = acquire_gate(session, allow_blocked=True)
            if session.scalar(select(func.count()).select_from(Workout)):
                return 0
            if gate.blocked:
                raise WritesBlocked("Cannot seed an empty database during maintenance")
            count = 0
            with (Path(__file__).resolve().parents[1] / "data/demo_workouts.csv").open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    days = int(row.pop("days_ago"))
                    row["performed_on"] = (date.today() - timedelta(days=days)).isoformat()
                    create_workout(session, WorkoutInput.model_validate(row))
                    count += 1
            session.commit()
            return count
    finally:
        engine.dispose()


if __name__ == "__main__":
    print(f"Loaded {seed_demo()} synthetic entries (existing data is left intact).")
