"""Every test uses disposable files, never the configured application database."""
import os
from datetime import date

import pytest

# Set before collection imports backend.main: even its dormant default app must
# never capture a deployed URL or an actual secret from the developer's .env.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_WRITE_TOKEN"] = ""
os.environ["MAINTENANCE_TOKEN"] = ""

from backend.schemas import WorkoutOut


@pytest.fixture
def fixed_workout():
    return WorkoutOut(id=7, exercise="Bench Press", muscle="Chest", performed_on=date(2026, 1, 10),
                      sets=3, reps=8, target_reps=8, weight_kg=50, rpe=7.5, notes="fixed fixture")
