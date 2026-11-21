"""Linha de comando: migracoes, servidor, agenda diaria e agendador."""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date
from pathlib import Path

from .agenda import build_agenda
from .alerts import render_digest, send_daily_alert
from .config import Settings, get_settings
from .db import build_engine, build_sessionmaker

logger = logging.getLogger("nexjus_backend")


def alembic_config(database_url: str):
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.attributes["database_url"] = database_url
    return config


def migrate(settings: Settings) -> None:
    from alembic import command

    logger.info("Aplicando migracoes em %s", settings.safe_database_url())
    command.upgrade(alembic_config(settings.database_url), "head")


def run_agenda(settings: Settings, *, hoje: date | None = None, send: bool = False) -> str:
    engine = build_engine(settings.database_url)
    try:
        with build_sessionmaker(engine)() as session:
            agenda = build_agenda(session, hoje=hoje or date.today(), dias=settings.agenda_dias)
    finally:
        engine.dispose()
    if send:
        send_daily_alert(agenda, settings)
    _assunto, corpo = render_digest(agenda)
    return corpo


def run_scheduler(settings: Settings) -> None:  # pragma: no cover - laco infinito
    import schedule

    schedule.every().day.at(settings.agenda_hora).do(run_agenda, settings, send=True)
    logger.info("Agenda diaria programada para %s", settings.agenda_hora)
    while True:
        schedule.run_pending()
        time.sleep(30)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nexjus-backend", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="aplica as migracoes do Alembic")
    serve = sub.add_parser("serve", help="aplica as migracoes e sobe a API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    agenda = sub.add_parser("agenda", help="mostra a agenda do dia; --send envia o alerta por e-mail")
    agenda.add_argument("--send", action="store_true")
    agenda.add_argument("--hoje", type=date.fromisoformat, default=None, help="data no formato YYYY-MM-DD")
    sub.add_parser("scheduler", help="envia o alerta todo dia em NEXJUS_AGENDA_HORA")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    if args.command == "migrate":
        migrate(settings)
    elif args.command == "serve":  # pragma: no cover - sobe o servidor
        import uvicorn

        migrate(settings)
        uvicorn.run("nexjus_backend.main:app", host=args.host, port=args.port)
    elif args.command == "agenda":
        print(run_agenda(settings, hoje=args.hoje, send=args.send), end="")
    elif args.command == "scheduler":  # pragma: no cover
        run_scheduler(settings)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
