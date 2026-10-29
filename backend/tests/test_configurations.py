"""Contract tests for the public configuration catalogue."""

from fastapi.testclient import TestClient

from app.main import app


def test_configurations_default_hides_unapproved_demo() -> None:
    response = TestClient(app).get("/api/v1/exam-configurations")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_configurations_rejects_unapproved_query_by_default() -> None:
    response = TestClient(app).get("/api/v1/exam-configurations?status=all")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_configurations_validation_error_for_unknown_status() -> None:
    response = TestClient(app).get("/api/v1/exam-configurations?status=unknown")
    assert response.status_code == 422


def test_configurations_returns_demo_when_unapproved_is_enabled(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "ALLOW_UNAPPROVED_CONFIG", True)
    response = TestClient(app).get("/api/v1/exam-configurations?status=all")
    assert response.status_code == 200
    assert response.json()["items"][0]["slug"] == "ege-history-demo"
    assert response.json()["items"][0]["status"] == "draft"
