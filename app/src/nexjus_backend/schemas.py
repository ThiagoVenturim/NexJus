"""Contratos JSON da API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Mesmos nomes das colecoes do NexJusDatabase da extensao (extension/src/types/models.ts).
Entity = Literal["clientes", "veiculos", "processos", "prazos", "feriadosLocais"]
StatusPrazo = Literal["vencido", "hoje", "urgente", "no_prazo"]

_ID_PATTERN = r"^[A-Za-z0-9_.:-]{1,64}$"


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: Entity
    id: str = Field(pattern=_ID_PATTERN)
    updated_at: datetime
    deleted: bool = False
    payload: str = ""
    due_date: date | None = None
    done: bool | None = None


class PushRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(pattern=_ID_PATTERN)
    changes: list[Change]


class RecordOut(BaseModel):
    entity: Entity
    id: str
    seq: int
    updated_at: datetime
    deleted: bool
    device_id: str
    payload: str
    due_date: date | None = None
    done: bool | None = None


class Accepted(BaseModel):
    entity: Entity
    id: str
    seq: int


class PushResponse(BaseModel):
    accepted: list[Accepted]
    stale: list[RecordOut]
    cursor: int


class ChangesResponse(BaseModel):
    changes: list[RecordOut]
    cursor: int
    has_more: bool


class AgendaItem(BaseModel):
    id: str
    due_date: date
    dias_restantes: int
    status: StatusPrazo


class AgendaResponse(BaseModel):
    hoje: date
    dias: int
    vencidos: list[AgendaItem]
    vencendo_hoje: list[AgendaItem]
    urgentes: list[AgendaItem]
    proximos: list[AgendaItem]
    total_criticos: int
