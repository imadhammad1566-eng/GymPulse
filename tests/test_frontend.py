"""Render and operate Streamlit against the real API with isolated storage."""
from datetime import date

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.config import Settings
from backend.database import make_engine
from backend.main import create_app
from frontend.client import ApiError, GymClient


def test_frontend_logs_workout_and_renders_all_pages(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'frontend.db'}")
    with TestClient(create_app(Settings("unused", "admin", "", False), engine)) as api:
        def request(self, method, path, **kwargs):
            response = api.request(method, path, **kwargs)
            if response.is_error:
                raise ApiError(str(response.json()))
            return response.json() if response.content else None

        monkeypatch.setattr(GymClient, "request", request)
        monkeypatch.setenv("API_BASE_URL", "http://testserver")
        monkeypatch.setenv("APP_WRITE_TOKEN", "")
        app = AppTest.from_file("frontend/app.py", default_timeout=60).run()
        assert not app.exception
        assert app.metric[0].value == "0"
        app.sidebar.radio[0].set_value("Workout log").run()
        next(item for item in app.text_input if item.label == "Exercise").set_value("Bench Press")
        app.date_input[0].set_value(date(2026, 1, 10))
        next(item for item in app.button if item.label == "Save workout ↗").click().run()
        assert not app.exception
        assert api.get("/workouts").json()[0]["exercise"] == "Bench Press"
        next(item for item in app.number_input if item.label == "Recorded load (kg)").set_value(60.0)
        next(item for item in app.button if item.label == "Save changes").click().run()
        assert not app.exception
        assert api.get("/workouts").json()[0]["weight_kg"] == 60
        for page in ("Overview", "Progress", "Training coach"):
            app.sidebar.radio[0].set_value(page).run()
            assert not app.exception, f"UI error on {page}"


def test_frontend_displays_unreachable_backend(monkeypatch):
    def unavailable(self, method, path, **kwargs):
        raise ApiError("Backend unavailable for this test")

    monkeypatch.setattr(GymClient, "request", unavailable)
    monkeypatch.setenv("API_BASE_URL", "http://testserver")
    monkeypatch.setenv("APP_WRITE_TOKEN", "")
    app = AppTest.from_file("frontend/app.py", default_timeout=60).run()
    assert not app.exception
    assert "Backend unavailable" in app.error[0].value


def test_frontend_import_preview_and_confirmation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import streamlit
    from tests.test_importing import HEADER, ROW

    content = (HEADER + ROW).encode("utf-8")
    upload = SimpleNamespace(size=len(content), getvalue=lambda: content)
    monkeypatch.setattr(streamlit, "file_uploader", lambda *args, **kwargs: upload)
    monkeypatch.setenv("API_BASE_URL", "http://testserver")
    monkeypatch.setenv("APP_WRITE_TOKEN", "")
    engine = make_engine(f"sqlite:///{tmp_path / 'import-ui.db'}")
    with TestClient(create_app(Settings("unused", "admin", "", False), engine)) as api:
        def request(self, method, path, **kwargs):
            response = api.request(method, path, **kwargs)
            if response.is_error:
                raise ApiError(str(response.json()))
            return response.json() if response.content else None

        monkeypatch.setattr(GymClient, "request", request)
        app = AppTest.from_file("frontend/app.py", default_timeout=60).run()
        app.sidebar.radio[0].set_value("Workout log").run()
        assert not app.exception
        button = next(item for item in app.button if item.label == "Import workouts")
        assert button.disabled
        next(item for item in app.checkbox if item.label == "Import these workout records").check().run()
        next(item for item in app.button if item.label == "Import workouts").click().run()
        assert not app.exception
        assert len(api.get("/workouts").json()) == 1
        assert any("1 entries added" in item.value for item in app.success)
