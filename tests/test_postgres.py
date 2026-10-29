"""CI-only PostgreSQL check in two randomly named, disposable schemas."""
import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.database import Base, make_engine
from backend.models import Workout, WriteGate
from maintenance.backup import create_backup, restore_and_verify


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="Optional locally: set TEST_POSTGRES_URL to an isolated PostgreSQL 16 test service; CI always runs this")
def test_postgres_export_restore_and_sequence(tmp_path, fixed_workout):
    url = os.environ["TEST_POSTGRES_URL"]
    root = make_engine(url)
    schemas = ["gymtest_" + uuid4().hex for _ in range(2)]
    engines = []
    try:
        with root.begin() as connection:
            for name in schemas:
                connection.exec_driver_sql(f'CREATE SCHEMA "{name}"')
        for name in schemas:
            parsed = make_url(url).update_query_dict({"options": f"-csearch_path={name}"})
            engines.append(make_engine(parsed.render_as_string(hide_password=False)))
        source, target = engines
        Base.metadata.create_all(source)
        with Session(source) as session:
            session.add(WriteGate(id=1, blocked=True))
            session.add(Workout(**fixed_workout.model_dump()))
            session.commit()
        backup = create_backup(source, "postgres-test", tmp_path / "postgres.json", date(2026, 1, 12))
        assert restore_and_verify(target, backup)["identifier_probe"] == "passed"
        assert restore_and_verify(target, backup)["records_verified"] == 1
        with Session(target) as session:
            new = Workout(**fixed_workout.model_dump(exclude={"id"}))
            session.add(new)
            session.commit()
            assert new.id > fixed_workout.id
    finally:
        for engine in engines:
            engine.dispose()
        with root.begin() as connection:
            for name in schemas:
                # Names are locally generated UUIDs, never external identifiers.
                connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
        root.dispose()
