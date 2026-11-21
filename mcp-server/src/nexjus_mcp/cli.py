"""Linha de comando: `nexjus-mcp serve`, `nexjus-mcp import-csv` e `nexjus-mcp check`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import Settings
from .store import JsonStore, StoreError, importar_csv_dir


def _configurar_log() -> None:
    # stdout e o canal do protocolo MCP; logs vao sempre para stderr.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _serve(settings: Settings) -> int:
    from .server import build_server
    from .service import NexJusService

    service = NexJusService(settings)
    logging.getLogger(__name__).info("Servidor MCP do NexJus iniciado (privacidade: %s)", settings.privacy)
    build_server(service).run("stdio")
    return 0


def _import_csv(settings: Settings, directory: str, output: str | None, force: bool) -> int:
    destino = Path(output or settings.data_file)
    if destino.exists() and not force:
        print(f"{destino} ja existe. Use --force para substituir.", file=sys.stderr)
        return 1
    db = importar_csv_dir(directory)
    JsonStore(destino).save(db)
    contagem = ", ".join(f"{nome}: {len(itens)}" for nome, itens in db.items())
    print(f"Arquivo gravado em {destino} ({contagem}).", file=sys.stderr)
    return 0


def _check(settings: Settings) -> int:
    try:
        db = JsonStore(settings.data_file).load()
    except StoreError as exc:
        print(f"Arquivo de dados: erro ({exc})", file=sys.stderr)
        return 1
    print(f"Arquivo de dados: {settings.data_file}", file=sys.stderr)
    print("Registros: " + ", ".join(f"{nome}={len(itens)}" for nome, itens in db.items()), file=sys.stderr)
    print(f"DataJud: {'configurado' if settings.datajud_api_key else 'sem chave'}", file=sys.stderr)
    print(f"Backend: {'configurado' if settings.backend_configured else 'nao configurado'}", file=sys.stderr)
    print(f"Privacidade: {settings.privacy}; somente leitura: {settings.read_only}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nexjus-mcp", description="Servidor MCP local do NexJus")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="inicia o servidor MCP em stdio (padrao)")
    imp = sub.add_parser("import-csv", help="monta o arquivo de dados a partir dos CSV exportados pela extensao")
    imp.add_argument("directory", help="pasta com clientes.csv, veiculos.csv, processos.csv e prazos.csv")
    imp.add_argument("--output", help="arquivo JSON de destino (padrao: NEXJUS_MCP_DATA_FILE)")
    imp.add_argument("--force", action="store_true", help="substitui o arquivo de destino se existir")
    sub.add_parser("check", help="mostra a configuracao sem exibir segredos")
    args = parser.parse_args(argv)

    _configurar_log()
    settings = Settings()
    if args.command == "import-csv":
        return _import_csv(settings, args.directory, args.output, args.force)
    if args.command == "check":
        return _check(settings)
    return _serve(settings)


if __name__ == "__main__":
    raise SystemExit(main())
