"""Validated API contracts; reps is the minimum completed across working sets."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Muscle = Literal["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"]


class WorkoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exercise: str = Field(min_length=2, max_length=60)
    muscle: Muscle
    performed_on: date
    sets: int = Field(ge=1, le=12)
    reps: int = Field(ge=1, le=50)
    target_reps: int = Field(ge=1, le=50)
    weight_kg: float = Field(gt=0, le=600, allow_inf_nan=False)
    rpe: float = Field(ge=1, le=10, allow_inf_nan=False)
    notes: str = Field(default="", max_length=300)

    @field_validator("exercise")
    @classmethod
    def normalize_exercise(cls, value: str) -> str:
        return " ".join(value.split()).title()

    @field_validator("performed_on")
    @classmethod
    def no_future_workouts(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Workout date cannot be in the future")
        return value


class WorkoutOut(WorkoutInput):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(gt=0)


class Recommendation(BaseModel):
    exercise: str
    action: Literal["recover", "increase", "hold", "deload", "restart"]
    next_weight_kg: float
    reason: str
    days_since: int


class Summary(BaseModel):
    total_workouts: int
    training_days: int
    total_volume_kg: float
    weekly_volume: list[dict]
    muscle_volume: list[dict]
    personal_records: list[dict]


class GateInput(BaseModel):
    blocked: bool


class GateOut(BaseModel):
    blocked: bool


class Message(BaseModel):
    message: str


class CsvImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csv_text: str = Field(min_length=1, max_length=2_000_000)


class ImportResult(BaseModel):
    created: int = Field(ge=0)
    skipped: int = Field(ge=0)
