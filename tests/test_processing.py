"""Expected values are calculated by hand from the documented rule."""
from datetime import date

import pytest
from pydantic import ValidationError

from backend.processing import latest_recommendations, recommend, round_load, summarize
from backend.schemas import WorkoutInput


@pytest.mark.parametrize("days,rpe,reps,action,weight", [
    (0, 7, 8, "recover", 50),
    (1, 9, 8, "recover", 50),
    (2, 7.5, 8, "increase", 52.5),
    (2, 8, 8, "hold", 50),
    (2, 7, 7, "hold", 50),
    (2, 9, 8, "deload", 45),
    (13, 7, 8, "increase", 52.5),
    (14, 7, 8, "restart", 45),
])
def test_training_rule_boundaries(fixed_workout, days, rpe, reps, action, weight):
    from datetime import timedelta
    row = fixed_workout.model_copy(update={"rpe": rpe, "reps": reps})
    original = row.model_dump()
    result = recommend(row, row.performed_on + timedelta(days=days))
    assert (result.action, result.next_weight_kg) == (action, weight)
    assert row.model_dump() == original  # pure function leaves its input intact


def test_invalid_rule_inputs_and_rounding(fixed_workout):
    with pytest.raises(ValueError, match="Reference date"):
        recommend(fixed_workout, date(2026, 1, 9))
    for changes in ({"rpe": 11}, {"weight_kg": 0}, {"weight_kg": float("nan")}, {"sets": 0}, {"reps": 51}, {"exercise": " "}):
        data = fixed_workout.model_dump(exclude={"id"}) | changes
        with pytest.raises(ValidationError):
            WorkoutInput.model_validate(data)
    assert round_load(46.25) == 47.5  # halfway rounds up, not banker's rounding
    assert round_load(0.4) == 2.5
    with pytest.raises(ValueError):
        round_load(-5)


def test_summary_and_latest_use_fixed_dataset(fixed_workout):
    later = fixed_workout.model_copy(update={"id": 8, "performed_on": date(2026, 1, 12), "weight_kg": 55})
    rows = [later, fixed_workout]
    summary = summarize(rows, date(2026, 1, 15))
    assert summary.total_volume_kg == 2520  # 3*8*50 + 3*8*55
    assert summary.training_days == 2
    assert summary.personal_records == [{"exercise": "Bench Press", "weight_kg": 55}]
    assert summary.weekly_volume == [{"week": "2026-01-05", "volume_kg": 1200}, {"week": "2026-01-12", "volume_kg": 1320}]
    assert latest_recommendations(rows, date(2026, 1, 15))[0].next_weight_kg == 57.5
    assert latest_recommendations(rows, date(2026, 1, 11))[0].action == "recover"
    assert summarize([], date(2026, 1, 15)).total_workouts == 0
