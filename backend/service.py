"""Application service coordinates queries and pure processing."""
import logging
from datetime import date

from sqlalchemy.orm import Session

from backend import repository
from backend.importing import parse_workout_csv
from backend.processing import latest_recommendations, summarize
from backend.schemas import ImportResult, Recommendation, Summary, WorkoutInput, WorkoutOut

logger = logging.getLogger(__name__)


class TrainingService:
    def __init__(self, session: Session):
        self.session = session

    def log_workout(self, data: WorkoutInput) -> WorkoutOut:
        row = repository.create_workout(self.session, data)
        self.session.commit()
        logger.info("Workout saved id=%s exercise=%s", row.id, row.exercise)
        return WorkoutOut.model_validate(row)

    def workouts(self, exercise: str | None = None, muscle: str | None = None) -> list[WorkoutOut]:
        return [WorkoutOut.model_validate(row) for row in repository.list_workouts(self.session, exercise, muscle)]

    def edit_workout(self, workout_id: int, data: WorkoutInput) -> WorkoutOut:
        row = repository.update_workout(self.session, workout_id, data)
        self.session.commit()
        logger.info("Workout updated id=%s", row.id)
        return WorkoutOut.model_validate(row)

    def import_csv(self, content: str) -> ImportResult:
        rows = parse_workout_csv(content)
        created, skipped = repository.import_workouts(self.session, rows)
        self.session.commit()
        logger.info("CSV import completed created=%s skipped=%s", created, skipped)
        return ImportResult(created=created, skipped=skipped)

    def recommendations(self, as_of: date) -> list[Recommendation]:
        return latest_recommendations(self.workouts(), as_of)

    def summary(self, as_of: date) -> Summary:
        return summarize(self.workouts(), as_of)
