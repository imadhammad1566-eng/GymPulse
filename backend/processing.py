"""Pure training decisions: deterministic, no I/O and no input mutation."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from backend.schemas import Recommendation, Summary, WorkoutOut


def round_load(weight: float, increment: float = 2.5) -> float:
    """Round half up to the nearest available total-load increment."""
    if weight <= 0 or increment <= 0:
        raise ValueError("Weight and increment must be positive")
    step = Decimal(str(increment))
    rounded = (Decimal(str(weight)) / step).quantize(Decimal("1"), ROUND_HALF_UP)
    return float(max(step, rounded * step))


def recommend(workout: WorkoutOut, as_of: date) -> Recommendation:
    """Apply recovery -> long break -> high effort -> progression -> hold order."""
    days = (as_of - workout.performed_on).days
    if days < 0:
        raise ValueError("Reference date must not precede the workout")
    weight = workout.weight_kg
    if days < 2:
        action, reason = "recover", "Wait at least two calendar days before repeating this lift."
    elif days >= 14:
        action, reason = "restart", "After a 14-day break, restart at roughly 90% of the last load."
        weight = round_load(weight * 0.9)
    elif workout.rpe >= 9:
        action, reason = "deload", "Effort was RPE 9 or above; reduce the load by roughly 10%."
        weight = round_load(weight * 0.9)
    elif workout.reps >= workout.target_reps and workout.rpe <= 7.5:
        action, reason = "increase", "All sets met the rep target at RPE 7.5 or below. Add 2.5 kg."
        weight = round_load(weight + 2.5)
    else:
        action, reason = "hold", "Repeat the load until every set meets the target at manageable effort."
    return Recommendation(
        exercise=workout.exercise, action=action, next_weight_kg=weight,
        reason=reason, days_since=days,
    )


def latest_recommendations(rows: list[WorkoutOut], as_of: date) -> list[Recommendation]:
    latest: dict[str, WorkoutOut] = {}
    for row in sorted(rows, key=lambda item: (item.performed_on, item.id)):
        if row.performed_on <= as_of:
            latest[row.exercise] = row
    return [recommend(latest[name], as_of) for name in sorted(latest)]


def summarize(rows: list[WorkoutOut], as_of: date) -> Summary:
    eligible = [row for row in rows if row.performed_on <= as_of]
    weeks: dict[str, float] = {}
    muscles: dict[str, float] = {}
    records: dict[str, float] = {}
    for row in eligible:
        volume = row.sets * row.reps * row.weight_kg
        monday = (row.performed_on - timedelta(days=row.performed_on.weekday())).isoformat()
        weeks[monday] = weeks.get(monday, 0) + volume
        muscles[row.muscle] = muscles.get(row.muscle, 0) + volume
        records[row.exercise] = max(records.get(row.exercise, 0), row.weight_kg)
    return Summary(
        total_workouts=len(eligible),
        training_days=len({row.performed_on for row in eligible}),
        total_volume_kg=round(sum(muscles.values()), 2),
        weekly_volume=[{"week": key, "volume_kg": round(value, 2)} for key, value in sorted(weeks.items())],
        muscle_volume=[{"muscle": key, "volume_kg": round(value, 2)} for key, value in sorted(muscles.items())],
        personal_records=[{"exercise": key, "weight_kg": value} for key, value in sorted(records.items())],
    )
