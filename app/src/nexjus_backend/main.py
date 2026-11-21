"""Aplicacao FastAPI do backend opcional do NexJus."""

from __future__ import annotations

import hmac
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import __version__
from .agenda import build_agenda
from .config import Settings, get_settings
from .db import build_engine, build_sessionmaker, session_scope
from .schemas import AgendaResponse, ChangesResponse, PushRequest, PushResponse
from .sync import SyncError, apply_push, list_changes

_bearer = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.sessionmaker)


def require_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    settings: Settings = request.app.state.settings
    if settings.api_token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "NEXJUS_API_TOKEN nao configurado no servidor")
    expected = settings.api_token.get_secret_value().encode("utf-8")
    given = (credentials.credentials if credentials else "").encode("utf-8")
    if not hmac.compare_digest(given, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido", headers={"WWW-Authenticate": "Bearer"})


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(
        title="NexJus backend",
        description="Backend opcional do NexJus: sincronizacao entre maquinas, agenda e alertas de prazos.",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/health", tags=["health"])
    def health(request: Request):
        try:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "error", "database": "unavailable"}, status_code=503)
        return {"status": "ok", "database": "ok", "version": __version__}

    protected = [Depends(require_token)]

    @app.post("/sync/push", response_model=PushResponse, dependencies=protected, tags=["sync"])
    def sync_push(body: PushRequest, session: SessionDep) -> PushResponse:
        if len(body.changes) > settings.max_push_changes:
            raise HTTPException(413, f"Envie no maximo {settings.max_push_changes} alteracoes")
        try:
            return apply_push(
                session,
                body,
                max_payload_bytes=settings.max_payload_bytes,
                max_clock_skew_seconds=settings.max_clock_skew_seconds,
            )
        except SyncError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/sync/changes", response_model=ChangesResponse, dependencies=protected, tags=["sync"])
    def sync_changes(
        session: SessionDep,
        since: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=1000)] = 500,
        device_id: Annotated[str | None, Query(pattern=r"^[A-Za-z0-9_.:-]{1,64}$")] = None,
    ) -> ChangesResponse:
        return list_changes(session, since=since, limit=limit, exclude_device=device_id)

    @app.get("/agenda", response_model=AgendaResponse, dependencies=protected, tags=["agenda"])
    def agenda(
        session: SessionDep,
        hoje: date | None = None,
        dias: Annotated[int | None, Query(ge=1, le=60)] = None,
    ) -> AgendaResponse:
        return build_agenda(session, hoje=hoje or date.today(), dias=dias or settings.agenda_dias)

    return app


def __getattr__(name: str):
    # `uvicorn nexjus_backend.main:app` cria a aplicacao so quando for importada por nome.
    if name == "app":
        return create_app()
    raise AttributeError(name)
