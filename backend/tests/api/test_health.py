from fastapi.testclient import TestClient

from vb.main import create_app


def test_health_returns_ok() -> None:
    response = TestClient(create_app()).get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
