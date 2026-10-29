"""Pure CSV parsing: validate the whole file before a transaction can write."""
import csv
import io

from pydantic import ValidationError

from backend.schemas import WorkoutInput

MAX_IMPORT_ROWS = 500


class CsvImportError(ValueError):
    """A readable file/row validation error."""


def parse_workout_csv(content: str) -> list[WorkoutInput]:
    """Accept app exports or the template; imported identifiers are ignored."""
    required = set(WorkoutInput.model_fields) - {"notes"}
    allowed = set(WorkoutInput.model_fields) | {"id"}
    try:
        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise CsvImportError("CSV has duplicate column names")
        missing = required - set(headers)
        unknown = set(headers) - allowed
        if missing:
            raise CsvImportError("Missing columns: " + ", ".join(sorted(missing)))
        if unknown:
            raise CsvImportError("Unknown columns: " + ", ".join(sorted(unknown)))
        results = []
        for row in reader:
            row_number = reader.line_num
            if len(results) >= MAX_IMPORT_ROWS:
                raise CsvImportError(f"Import at most {MAX_IMPORT_ROWS} rows at a time")
            if None in row or any(value is None for value in row.values()):
                raise CsvImportError(f"Row {row_number}: wrong number of columns")
            row.pop("id", None)
            try:
                results.append(WorkoutInput.model_validate(row))
            except ValidationError as error:
                details = "; ".join(
                    f'{".".join(map(str, item["loc"]))}: {item["msg"]}'
                    for item in error.errors()[:3]
                )
                raise CsvImportError(f"Row {row_number}: {details}") from None
        if not results:
            raise CsvImportError("CSV contains no workout rows")
        return results
    except csv.Error:
        raise CsvImportError("Malformed CSV: check quotes and separators") from None


def workout_identity(workout: WorkoutInput) -> tuple:
    """Exact normalized record identity for repeatable imports; no I/O."""
    return tuple(workout.model_dump(exclude={"id"}).items())
