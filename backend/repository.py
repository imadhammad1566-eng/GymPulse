"""SQLAlchemy queries and serialized writes, used by API and dataset loader."""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models import Workout, WriteGate
from backend.schemas import WorkoutInput, WorkoutOut
from backend.importing import workout_identity


class WritesBlocked(Exception):
    pass


class WorkoutNotFound(Exception):
    pass


def acquire_gate(session: Session, allow_blocked: bool = False) -> WriteGate:
    # UPDATE takes a row lock on PostgreSQL, and a write lock on SQLite.
    # Every application write holds this same lock until commit/rollback.
    session.execute(update(WriteGate).where(WriteGate.id == 1).values(id=1))
    gate = session.get(WriteGate, 1, populate_existing=True)
    if gate is None:
        raise RuntimeError("Database is not initialized")
    if gate.blocked and not allow_blocked:
        raise WritesBlocked("Database maintenance is in progress. Please try again later.")
    return gate


def list_workouts(session: Session, exercise: str | None = None, muscle: str | None = None) -> list[Workout]:
    query = select(Workout)
    if exercise:
        query = query.where(Workout.exercise == " ".join(exercise.split()).title())
    if muscle:
        query = query.where(Workout.muscle == muscle)
    return list(session.scalars(query.order_by(Workout.performed_on.desc(), Workout.id.desc())))


def create_workout(session: Session, data: WorkoutInput) -> Workout:
    acquire_gate(session)
    row = Workout(**data.model_dump())
    session.add(row)
    session.flush()
    return row


def update_workout(session: Session, workout_id: int, data: WorkoutInput) -> Workout:
    acquire_gate(session)
    row = session.get(Workout, workout_id)
    if row is None:
        raise WorkoutNotFound("Workout not found")
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    session.flush()
    return row


def import_workouts(session: Session, rows: list[WorkoutInput]) -> tuple[int, int]:
    """One serialized transaction, including deduplication and all inserts."""
    acquire_gate(session)
    known = {
        workout_identity(WorkoutOut.model_validate(row))
        for row in list_workouts(session)
    }
    created = 0
    for row in rows:
        identity = workout_identity(row)
        if identity in known:
            continue
        session.add(Workout(**row.model_dump()))
        known.add(identity)
        created += 1
    session.flush()
    return created, len(rows) - created
