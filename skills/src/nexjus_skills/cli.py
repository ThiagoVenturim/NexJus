"""Linha de comando: `nexjus-skills list|validate|install|uninstall|check`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .catalog import load_all, validate_all
from .guardrails import conferir_texto
from .installer import Relatorio, default_target, install, uninstall


def _destino(args: argparse.Namespace) -> Path:
    if args.target:
        return Path(args.target).expanduser().resolve()
    return default_target(args.project)


def _imprimir(relatorio: Relatorio, dry_run: bool) -> None:
    for acao, caminho in relatorio.acoes:
        if acao != "igual":
            print(f"{acao:12} {caminho}")
    resumo = ", ".join(f"{n} {acao}" for acao, n in sorted(relatorio.contagem().items())) or "nada a fazer"
    prefixo = "[simulacao] " if dry_run else ""
    print(f"{prefixo}{relatorio.destino}: {resumo}")
    if relatorio.conflitos:
        print("Arquivos editados localmente foram preservados. Use --force para sobrescrever.", file=sys.stderr)


def _cmd_list(_: argparse.Namespace) -> int:
    for item in load_all():
        print(f"{item.tipo:7} {item.nome:26} {item.descricao[:90]}")
    return 0


def _cmd_validate(_: argparse.Namespace) -> int:
    erros = validate_all()
    for erro in erros:
        print(erro, file=sys.stderr)
    if not erros:
        print(f"{len(load_all())} itens validos")
    return 1 if erros else 0


def _cmd_install(args: argparse.Namespace) -> int:
    erros = validate_all()
    if erros:
        for erro in erros:
            print(erro, file=sys.stderr)
        return 1
    try:
        relatorio = install(_destino(args), nomes=args.only, force=args.force, dry_run=args.dry_run)
    except ValueError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    _imprimir(relatorio, args.dry_run)
    if not args.dry_run:
        print("Configure o servidor MCP 'nexjus' no cliente (veja mcp-server/README.md) para usar as ferramentas.")
    return 1 if relatorio.conflitos else 0


def _cmd_uninstall(args: argparse.Namespace) -> int:
    relatorio = uninstall(_destino(args), force=args.force, dry_run=args.dry_run)
    _imprimir(relatorio, args.dry_run)
    return 1 if relatorio.conflitos else 0


def _cmd_check(args: argparse.Namespace) -> int:
    codigo = 0
    for nome in args.files:
        try:
            texto = sys.stdin.read() if nome == "-" else Path(nome).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"{nome}: nao foi possivel ler ({exc.strerror})", file=sys.stderr)
            codigo = 2
            continue
        achados = conferir_texto(texto, minuta=not args.not_draft)
        for achado in achados:
            print(f"{nome}: {achado}")
        if achados:
            codigo = max(codigo, 1)
        else:
            print(f"{nome}: nada a apontar")
    return codigo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexjus-skills", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("list", help="lista as skills e agentes do pacote").set_defaults(func=_cmd_list)
    sub.add_parser("validate", help="valida frontmatter, secoes e ferramentas MCP").set_defaults(func=_cmd_validate)

    for nome, func, ajuda in (
        ("install", _cmd_install, "instala em ~/.claude (ou --project/--target)"),
        ("uninstall", _cmd_uninstall, "remove o que foi instalado por este pacote"),
    ):
        p = sub.add_parser(nome, help=ajuda)
        grupo = p.add_mutually_exclusive_group()
        grupo.add_argument("--project", help="pasta do projeto; instala em <projeto>/.claude")
        grupo.add_argument("--target", help="pasta de destino exata (equivalente a ~/.claude)")
        p.add_argument("--force", action="store_true", help="sobrescreve ou remove arquivos editados localmente")
        p.add_argument("--dry-run", action="store_true", help="mostra o que seria feito sem gravar")
        if nome == "install":
            p.add_argument("--only", nargs="+", metavar="NOME", help="instala so estas skills ou agentes")
        p.set_defaults(func=func)

    p = sub.add_parser("check", help="confere uma minuta ou relatorio gerado (dados pessoais, pendencias, fontes)")
    p.add_argument("files", nargs="+", help="arquivos de texto ou - para a entrada padrao")
    p.add_argument("--not-draft", action="store_true", help="nao exige o aviso de minuta (resumos e relatorios)")
    p.set_defaults(func=_cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
