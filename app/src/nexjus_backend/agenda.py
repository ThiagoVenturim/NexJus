"""Agenda diaria de prazos.

Usa apenas `due_date` e `done` dos registros de prazos sincronizados. A classificacao segue a
mesma regra da extensao (classificarStatusPrazo): vencido, hoje, urgente (ate 3 dias) e no prazo.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import SyncRecord
from .schemas import AgendaItem, AgendaResponse, StatusPrazo

DIAS_URGENTE = 3


def classificar(due_date: date, hoje: date) -> tuple[StatusPrazo, int]:
    dias = (due_date - hoje).days
    if dias < 0:
        return "vencido", dias
    if dias == 0:
        return "hoje", 0
    if dias <= DIAS_URGENTE:
        return "urgente", dias
    return "no_prazo", dias


def build_agenda(session: Session, *, hoje: date, dias: int) -> AgendaResponse:
    limite = hoje + timedelta(days=dias)
    rows = session.execute(
        select(SyncRecord.record_id, SyncRecord.due_date)
        .where(
            SyncRecord.entity == "prazos",
            SyncRecord.deleted.is_(False),
            SyncRecord.due_date.is_not(None),
            SyncRecord.due_date <= limite,
            (SyncRecord.done.is_(None)) | (SyncRecord.done.is_(False)),
        )
        .order_by(SyncRecord.due_date, SyncRecord.record_id)
    ).all()

    grupos: dict[StatusPrazo, list[AgendaItem]] = {"vencido": [], "hoje": [], "urgente": [], "no_prazo": []}
    for record_id, due_date in rows:
        status, restantes = classificar(due_date, hoje)
        grupos[status].append(AgendaItem(id=record_id, due_date=due_date, dias_restantes=restantes, status=status))

    return AgendaResponse(
        hoje=hoje,
        dias=dias,
        vencidos=grupos["vencido"],
        vencendo_hoje=grupos["hoje"],
        urgentes=grupos["urgente"],
        proximos=grupos["no_prazo"],
        total_criticos=len(grupos["vencido"]) + len(grupos["hoje"]) + len(grupos["urgente"]),
    )
