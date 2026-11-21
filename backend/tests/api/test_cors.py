"""CORS: only the listed web origins may call the API from a browser."""

from fastapi.testclient import TestClient

from vb.main import create_app


def preflight(origin: str) -> dict[str, str]:
    """What a browser asks before a cross-origin request: 'may this origin call GET /v1/me?'"""
    response = TestClient(create_app()).options(
        "/v1/me", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    return dict(response.headers)


def test_the_local_web_app_is_allowed() -> None:
    assert preflight("http://localhost:5173").get("access-control-allow-origin") == "http://localhost:5173"


def test_any_other_origin_is_not_allowed() -> None:
    assert "access-control-allow-origin" not in preflight("https://evil.example")
