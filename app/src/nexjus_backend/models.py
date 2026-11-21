"""Tabelas do backend.

O conteudo de cada registro (cliente, processo, prazo...) fica em `payload` como texto opaco.
O servidor nao interpreta esse texto; a extensao pode envia-lo ja criptografado (AES-GCM).
Para montar a agenda, prazos podem trazer apenas `due_date` e `done`, que nao identificam ninguem.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SyncRecord(Base):
    __tablename__ = "sync_records"
    __table_args__ = (UniqueConstraint("entity", "record_id", name="uq_sync_records_entity_record"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity: Mapped[str] = mapped_column(String(32), nullable=False)
    record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    done: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class SyncState(Base):
    """Linha unica com o contador global de alteracoes (cursor da sincronizacao)."""

    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
