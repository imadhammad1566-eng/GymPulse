"""CSV errors are explicit, duplicates are normalized, and parsing is pure."""
import pytest

from backend.importing import CsvImportError, parse_workout_csv, workout_identity

HEADER = "exercise,muscle,performed_on,sets,reps,target_reps,weight_kg,rpe,notes\n"
ROW = 'bench press,Chest,2026-01-10,3,8,8,50,7.5,"Good, controlled reps"\n'


def test_parse_export_preserves_values_and_ignores_ids():
    text = "\ufeffid," + HEADER + "123," + ROW
    result = parse_workout_csv(text)
    assert result[0].exercise == "Bench Press"
    assert result[0].notes == "Good, controlled reps"
    assert result[0].weight_kg == 50
    assert workout_identity(result[0]) == workout_identity(parse_workout_csv(HEADER + ROW)[0])
    assert text.startswith("\ufeffid,")  # original input was not modified


@pytest.mark.parametrize("text,message", [
    ("exercise,sets\nBench Press,3\n", "Missing columns"),
    (HEADER.rstrip() + ",mystery\n" + ROW.rstrip() + ",x\n", "Unknown columns"),
    (HEADER.rstrip() + ",sets\n" + ROW.rstrip() + ",3\n", "duplicate column"),
    (HEADER, "no workout rows"),
    (HEADER + "Bench Press,Chest\n", "Row 2"),
    (HEADER + ROW.replace(",7.5,", ",11,"), "Row 2: rpe"),
    (HEADER + ROW.replace(",50,", ",0,"), "Row 2: weight_kg"),
    (HEADER + '"unclosed quote', "Malformed CSV"),
    (HEADER + ROW * 501, "at most 500"),
], ids=["missing-columns", "unknown-column", "duplicate-header", "empty-file",
        "short-row", "invalid-rpe", "zero-load", "bad-quotes", "row-limit"])
def test_parse_rejects_invalid_files_before_writing(text, message):
    with pytest.raises(CsvImportError, match=message):
        parse_workout_csv(text)
