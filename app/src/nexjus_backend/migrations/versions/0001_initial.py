"""Tabelas iniciais de sincronizacao.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity", sa.String(length=32), nullable=False),
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("entity", "record_id", name="uq_sync_records_entity_record"),
    )
    op.create_index("ix_sync_records_seq", "sync_records", ["seq"])
    op.create_index("ix_sync_records_due_date", "sync_records", ["due_date"])

    sync_state = op.create_table(
        "sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_seq", sa.BigInteger(), nullable=False),
    )
    op.bulk_insert(sync_state, [{"id": 1, "last_seq": 0}])


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_index("ix_sync_records_due_date", table_name="sync_records")
    op.drop_index("ix_sync_records_seq", table_name="sync_records")
    op.drop_table("sync_records")
