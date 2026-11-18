"""Dev login: every request is the same fixed learner, and a prod app refuses to start with it."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vb.core.config import Settings, get_settings
from vb.core.db import get_session
from vb.main import create_app


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """An API client whose requests use the test session, so nothing outlives the test."""
    app = create_app()

    def test_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = test_session
    with TestClient(app) as test_client:
        yield test_client


def test_me_returns_the_dev_learner(client: TestClient) -> None:
    response = client.get("/v1/me")
    assert response.status_code == 200
    assert response.json()["email"] == "dev@localhost"


def test_me_returns_the_same_learner_every_time(client: TestClient) -> None:
    assert client.get("/v1/me").json()["id"] == client.get("/v1/me").json()["id"]


def test_a_prod_app_with_the_dev_login_refuses_to_start() -> None:
    with pytest.raises(RuntimeError, match="not allowed when environment=prod"):
        create_app(Settings(environment="prod", auth_mode="dev"))


def test_cognito_mode_says_login_is_not_available_yet(client: TestClient) -> None:
    app = client.app
    assert hasattr(app, "dependency_overrides")
    app.dependency_overrides[get_settings] = lambda: Settings(auth_mode="cognito")
    assert client.get("/v1/me").status_code == 501
