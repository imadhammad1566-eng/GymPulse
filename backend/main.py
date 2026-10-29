"""FastAPI factory; the independent maintenance controller never runs here."""
import hmac
import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.database import Base, get_session, make_engine
from backend.models import Workout, WriteGate
from backend.importing import CsvImportError
from backend.repository import WorkoutNotFound, WritesBlocked, acquire_gate
from backend.schemas import CsvImportInput, ImportResult
from backend.schemas import GateInput, GateOut, Message, Recommendation, Summary, WorkoutInput, WorkoutOut
from backend.service import TrainingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    config = settings or Settings.from_env()
    db_engine = engine or make_engine(config.database_url)

    @asynccontextmanager
    async def lifespan(application):
        Base.metadata.create_all(db_engine)
        with Session(db_engine) as session:
            if session.get(WriteGate, 1) is None:
                session.add(WriteGate(id=1, blocked=config.maintenance_mode))
            elif config.maintenance_mode:
                acquire_gate(session, allow_blocked=True).blocked = True
            session.commit()
        yield
        db_engine.dispose()

    api = FastAPI(title="GymPulse API", version="1.0.0", lifespan=lifespan)
    api.state.engine = db_engine

    def session_dependency():
        with Session(db_engine) as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    api.dependency_overrides[get_session] = session_dependency

    def admin(authorization: str = Header(default="")):
        expected = f"Bearer {config.maintenance_token}"
        if not config.maintenance_token or not hmac.compare_digest(authorization, expected):
            raise HTTPException(401, "A valid maintenance token is required")

    def writer(authorization: str = Header(default="")):
        if config.write_token and not hmac.compare_digest(authorization, f"Bearer {config.write_token}"):
            raise HTTPException(401, "A valid application write token is required")

    @api.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        # Do not log exception text: it may include a connection URL or user data.
        logger.error("Database operation failed: %s", type(error).__name__)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable. Try again shortly."})

    @api.exception_handler(WritesBlocked)
    async def maintenance_error(request, error):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @api.exception_handler(WorkoutNotFound)
    async def missing_workout(request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @api.exception_handler(CsvImportError)
    async def invalid_csv(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @api.get("/health", response_model=Message)
    def health():
        return Message(message="GymPulse API is running")

    @api.get("/workouts", response_model=list[WorkoutOut])
    def workouts(exercise: str | None = None, muscle: str | None = None, session: Session = Depends(get_session)):
        return TrainingService(session).workouts(exercise, muscle)

    @api.post("/workouts", response_model=WorkoutOut, status_code=201, dependencies=[Depends(writer)])
    def log_workout(data: WorkoutInput, session: Session = Depends(get_session)):
        return TrainingService(session).log_workout(data)

    @api.put("/workouts/{workout_id}", response_model=WorkoutOut, dependencies=[Depends(writer)])
    def edit_workout(workout_id: int, data: WorkoutInput, session: Session = Depends(get_session)):
        return TrainingService(session).edit_workout(workout_id, data)

    @api.post("/imports/workouts", response_model=ImportResult, dependencies=[Depends(writer)])
    def import_workouts(data: CsvImportInput, session: Session = Depends(get_session)):
        return TrainingService(session).import_csv(data.csv_text)

    @api.get("/workouts/{workout_id}", response_model=WorkoutOut)
    def workout_detail(workout_id: int, session: Session = Depends(get_session)):
        row = session.get(Workout, workout_id)
        if row is None:
            raise HTTPException(404, "Workout not found")
        return WorkoutOut.model_validate(row)

    @api.delete("/workouts/{workout_id}", status_code=204, dependencies=[Depends(writer)])
    def delete_workout(workout_id: int, session: Session = Depends(get_session)):
        acquire_gate(session)
        row = session.get(Workout, workout_id)
        if row is None:
            raise HTTPException(404, "Workout not found")
        session.delete(row)
        session.commit()
        return Response(status_code=204)

    @api.get("/summary", response_model=Summary)
    def summary(as_of: date | None = None, session: Session = Depends(get_session)):
        return TrainingService(session).summary(as_of or date.today())

    @api.get("/recommendations", response_model=list[Recommendation])
    def recommendations(as_of: date | None = None, session: Session = Depends(get_session)):
        return TrainingService(session).recommendations(as_of or date.today())

    @api.get("/status", response_model=GateOut)
    def status(session: Session = Depends(get_session)):
        return GateOut(blocked=session.get(WriteGate, 1).blocked)

    @api.put("/admin/maintenance", response_model=GateOut, dependencies=[Depends(admin)])
    def maintenance(data: GateInput, session: Session = Depends(get_session)):
        if not data.blocked and config.maintenance_mode:
            raise HTTPException(409, "Redeploy with MAINTENANCE_MODE=false before reopening writes")
        gate = acquire_gate(session, allow_blocked=True)
        gate.blocked = data.blocked
        session.commit()
        logger.info("Maintenance write gate blocked=%s", data.blocked)
        return GateOut(blocked=data.blocked)

    @api.post("/admin/write-probe", response_model=Message, dependencies=[Depends(admin)])
    def write_probe(session: Session = Depends(get_session)):
        gate = acquire_gate(session, allow_blocked=True)
        if not gate.blocked:
            raise HTTPException(409, "Write probe requires maintenance mode")
        # A real INSERT+COMMIT verifies identifier generation; then remove the marker.
        marker = session.scalar(select(Workout).where(Workout.exercise == "__maintenance_probe__"))
        if marker is None:
            marker = Workout(exercise="__maintenance_probe__", muscle="Core", performed_on=date.today(),
                             sets=1, reps=1, target_reps=1, weight_kg=1, rpe=1, notes="controller probe")
            session.add(marker)
            session.commit()
        session.delete(marker)
        session.commit()
        return Message(message="Committed test write and cleanup succeeded")

    return api


app = create_app()
