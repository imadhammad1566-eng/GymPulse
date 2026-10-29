"""Persistent workout records and a transaction-wide write gate."""
from datetime import date

from sqlalchemy import Boolean, Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise: Mapped[str] = mapped_column(String(60), index=True)
    muscle: Mapped[str] = mapped_column(String(20))
    performed_on: Mapped[date] = mapped_column(Date, index=True)
    sets: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int] = mapped_column(Integer)
    target_reps: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Float)
    rpe: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(String(300), default="")


class WriteGate(Base):
    __tablename__ = "write_gate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
