from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import make_settings
from nexjus_backend.main import create_app

TOKEN_FRAGMENT = "token-de-teste"


def test_health_is_public(app):
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_database_failure(app):
    app.state.engine.dispose()
    app.state.engine = create_app(make_settings(database_url="sqlite:////nao/existe/dir/x.db")).state.engine
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert "nao/existe" not in response.text


def test_without_token_configured_protected_routes_are_unavailable():
    app = create_app(make_settings(api_token=None))
    with TestClient(app) as client:
        assert client.get("/sync/changes", headers={"Authorization": "Bearer qualquer"}).status_code == 503


def test_short_token_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(api_token="curto")


def test_secrets_never_show_in_repr_or_safe_url():
    settings = make_settings(
        database_url="postgresql+psycopg://user:senha-secreta@127.0.0.1:5432/nexjus",
        smtp_password="senha-smtp",
    )
    assert "senha-secreta" not in settings.safe_database_url()
    assert TOKEN_FRAGMENT not in repr(settings)
    assert "senha-smtp" not in repr(settings)
    assert "senha-secreta" not in repr(settings)


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./outro.db")
    monkeypatch.setenv("NEXJUS_CORS_ORIGINS", "chrome-extension://abc, http://127.0.0.1:5173")
    from nexjus_backend.config import Settings

    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./outro.db"
    assert settings.cors_origin_list == ["chrome-extension://abc", "http://127.0.0.1:5173"]
    assert settings.api_token is None


def test_cors_allows_configured_origin_only():
    app = create_app(make_settings(cors_origins="chrome-extension://abc"))
    with TestClient(app) as client:
        ok = client.get("/health", headers={"Origin": "chrome-extension://abc"})
        other = client.get("/health", headers={"Origin": "https://exemplo.invalid"})
    assert ok.headers.get("access-control-allow-origin") == "chrome-extension://abc"
    assert "access-control-allow-origin" not in other.headers
