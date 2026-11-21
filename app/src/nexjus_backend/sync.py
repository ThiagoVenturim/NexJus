"""Sincronizacao entre maquinas.

Modelo: cada maquina envia alteracoes (push) e busca as alteracoes das outras (pull) a partir
de um cursor. Cada alteracao aceita recebe um numero de sequencia global crescente (`seq`).
Conflitos usam "a ultima escrita vence" pelo `updated_at`; em empate, a versao do servidor fica.
Exclusoes viram marcadores (tombstones) sem payload, para que nenhum dado pessoal permaneca.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import SyncRecord, SyncState
from .schemas import Accepted, Change, ChangesResponse, PushRequest, PushResponse, RecordOut


class SyncError(ValueError):
    """Alteracao invalida; a mensagem nunca inclui o payload."""


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


def current_cursor(session: Session) -> int:
    value = session.scalar(select(SyncState.last_seq).where(SyncState.id == 1))
    return int(value or 0)


def next_seq(session: Session) -> int:
    """Incrementa o contador global. No Postgres o UPDATE trava a linha e serializa os pushes."""
    value = session.scalar(
        update(SyncState).where(SyncState.id == 1).values(last_seq=SyncState.last_seq + 1).returning(SyncState.last_seq)
    )
    if value is None:
        session.add(SyncState(id=1, last_seq=1))
        session.flush()
        return 1
    return int(value)


def record_out(record: SyncRecord) -> RecordOut:
    return RecordOut(
        entity=record.entity,
        id=record.record_id,
        seq=record.seq,
        updated_at=record.updated_at.replace(tzinfo=UTC),
        deleted=record.deleted,
        device_id=record.device_id,
        payload=record.payload,
        due_date=record.due_date,
        done=record.done,
    )


def _validate(change: Change, *, now: datetime, max_payload_bytes: int, max_skew: timedelta) -> datetime:
    updated_at = to_utc_naive(change.updated_at)
    if updated_at > now + max_skew:
        raise SyncError(f"{change.entity}/{change.id}: updated_at no futuro; verifique o relogio da maquina")
    if len(change.payload.encode("utf-8")) > max_payload_bytes:
        raise SyncError(f"{change.entity}/{change.id}: payload maior que o limite de {max_payload_bytes} bytes")
    if change.entity != "prazos" and (change.due_date is not None or change.done is not None):
        raise SyncError(f"{change.entity}/{change.id}: due_date e done so valem para prazos")
    return updated_at


def apply_push(
    session: Session,
    request: PushRequest,
    *,
    max_payload_bytes: int,
    max_clock_skew_seconds: int,
    now: datetime | None = None,
) -> PushResponse:
    now = to_utc_naive(now or datetime.now(UTC))
    skew = timedelta(seconds=max_clock_skew_seconds)
    validated = [
        (change, _validate(change, now=now, max_payload_bytes=max_payload_bytes, max_skew=skew))
        for change in request.changes
    ]

    accepted: list[Accepted] = []
    stale: list[RecordOut] = []
    for change, updated_at in validated:
        existing = session.scalar(
            select(SyncRecord).where(SyncRecord.entity == change.entity, SyncRecord.record_id == change.id)
        )
        if existing is not None and existing.updated_at >= updated_at:
            stale.append(record_out(existing))
            continue

        seq = next_seq(session)
        record = existing or SyncRecord(entity=change.entity, record_id=change.id)
        record.seq = seq
        record.updated_at = updated_at
        record.deleted = change.deleted
        record.device_id = request.device_id
        if change.deleted:
            record.payload = ""
            record.due_date = None
            record.done = None
        else:
            record.payload = change.payload
            record.due_date = change.due_date
            record.done = change.done
        if existing is None:
            session.add(record)
        session.flush()
        accepted.append(Accepted(entity=change.entity, id=change.id, seq=seq))

    return PushResponse(accepted=accepted, stale=stale, cursor=current_cursor(session))


def list_changes(session: Session, *, since: int, limit: int, exclude_device: str | None = None) -> ChangesResponse:
    """Alteracoes com seq maior que `since`, em ordem.

    O cursor devolvido e o maior seq lido, mesmo quando a linha e da propria maquina e foi omitida.
    Como o contador e incrementado sob trava, os seq ficam visiveis em ordem e nenhum e pulado.
    """
    query = select(SyncRecord).where(SyncRecord.seq > since).order_by(SyncRecord.seq).limit(limit + 1)
    rows = list(session.scalars(query))
    has_more = len(rows) > limit
    rows = rows[:limit]
    cursor = rows[-1].seq if rows else since
    visible = [row for row in rows if not exclude_device or row.device_id != exclude_device]
    return ChangesResponse(changes=[record_out(row) for row in visible], cursor=cursor, has_more=has_more)
