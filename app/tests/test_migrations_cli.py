from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from nexjus_backend import cli
from nexjus_backend.models import Base
from nexjus_backend.sync import current_cursor


def _sqlite_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'nexjus.db').as_posix()}"


def test_alembic_upgrade_matches_models(tmp_path, monkeypatch):
    url = _sqlite_url(tmp_path)
    monkeypatch.setenv("NEXJUS_DATABASE_URL", url)
    cli.get_settings.cache_clear()
    try:
        assert cli.main(["migrate"]) == 0
    finally:
        cli.get_settings.cache_clear()

    engine = create_engine(url)
    try:
        assert {"sync_records", "sync_state", "alembic_version"} <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert diff == []
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            assert current_cursor(session) == 0
    finally:
        engine.dispose()


def test_alembic_downgrade(tmp_path):
    from alembic import command

    url = _sqlite_url(tmp_path)
    config = cli.alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    engine = create_engine(url)
    try:
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()


def test_agenda_command_prints_digest(tmp_path, monkeypatch, capsys):
    url = _sqlite_url(tmp_path)
    monkeypatch.setenv("NEXJUS_DATABASE_URL", url)
    cli.get_settings.cache_clear()
    try:
        assert cli.main(["migrate"]) == 0
        assert cli.main(["agenda", "--hoje", "2026-11-20", "--send"]) == 0
    finally:
        cli.get_settings.cache_clear()
    assert "Nenhum prazo em aberto" in capsys.readouterr().out
