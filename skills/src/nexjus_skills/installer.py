"""Instala e remove as skills e agentes numa pasta de configuracao do Claude Code.

Layout de destino (o mesmo de `~/.claude` ou `<projeto>/.claude`):

    <destino>/skills/<nome>/SKILL.md
    <destino>/agents/<nome>.md
    <destino>/.nexjus-skills.json    manifesto com o hash de cada arquivo instalado

O manifesto permite atualizar arquivos que o usuario nao alterou e preservar os que ele editou.
Nada e apagado ou sobrescrito fora dos arquivos listados no manifesto, salvo com `force`.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import __version__
from .catalog import Item, load_all

MANIFESTO = ".nexjus-skills.json"


@dataclass
class Relatorio:
    destino: Path
    acoes: list[tuple[str, str]] = field(default_factory=list)
    """Pares (acao, caminho relativo). Acoes: criado, atualizado, sobrescrito, igual, preservado, removido."""

    @property
    def conflitos(self) -> list[str]:
        return [caminho for acao, caminho in self.acoes if acao == "preservado"]

    def contagem(self) -> dict[str, int]:
        total: dict[str, int] = {}
        for acao, _ in self.acoes:
            total[acao] = total.get(acao, 0) + 1
        return total


def default_target(project: str | os.PathLike[str] | None = None) -> Path:
    if project is not None:
        return Path(project).expanduser().resolve() / ".claude"
    return Path.home() / ".claude"


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _relativo(item: Item, arquivo: str) -> str:
    rel = PurePosixPath("skills", item.nome, arquivo) if item.tipo == "skill" else PurePosixPath("agents", arquivo)
    if ".." in rel.parts or rel.is_absolute():
        raise ValueError(f"caminho invalido no pacote: {rel}")
    return str(rel)


def _ler_manifesto(destino: Path) -> dict[str, str]:
    caminho = destino / MANIFESTO
    if not caminho.is_file():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    arquivos = dados.get("arquivos", {}) if isinstance(dados, dict) else {}
    return {str(k): str(v) for k, v in arquivos.items()} if isinstance(arquivos, dict) else {}


def _gravar_manifesto(destino: Path, arquivos: dict[str, str]) -> None:
    conteudo = {"pacote": "nexjus-skills", "versao": __version__, "arquivos": dict(sorted(arquivos.items()))}
    (destino / MANIFESTO).write_text(json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _gravar(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    with open(temporario, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)
    os.replace(temporario, caminho)


def _dentro(destino: Path, rel: str) -> Path:
    caminho = (destino / rel).resolve()
    if not caminho.is_relative_to(destino.resolve()):
        raise ValueError(f"caminho fora do destino: {rel}")
    return caminho


def _selecionar(itens: list[Item], nomes: list[str] | None) -> list[Item]:
    if not nomes:
        return itens
    conhecidos = {i.nome for i in itens}
    desconhecidos = sorted(set(nomes) - conhecidos)
    if desconhecidos:
        raise ValueError(f"skill ou agente desconhecido: {', '.join(desconhecidos)}")
    return [i for i in itens if i.nome in nomes]


def install(
    destino: Path,
    *,
    nomes: list[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
    itens: list[Item] | None = None,
) -> Relatorio:
    """Copia as skills e agentes para `destino`. Arquivos editados pelo usuario sao preservados."""
    selecionados = _selecionar(load_all() if itens is None else itens, nomes)
    manifesto = _ler_manifesto(destino)
    novo_manifesto = dict(manifesto)
    relatorio = Relatorio(destino)
    for item in selecionados:
        for arquivo, texto in item.arquivos.items():
            rel = _relativo(item, arquivo)
            caminho = _dentro(destino, rel)
            novo = _hash(texto)
            if not caminho.exists():
                acao = "criado"
            else:
                atual = _hash(caminho.read_text(encoding="utf-8"))
                if atual == novo:
                    acao = "igual"
                elif manifesto.get(rel) == atual:
                    acao = "atualizado"
                elif force:
                    acao = "sobrescrito"
                else:
                    relatorio.acoes.append(("preservado", rel))
                    continue
            relatorio.acoes.append((acao, rel))
            novo_manifesto[rel] = novo
            if not dry_run and acao != "igual":
                _gravar(caminho, texto)
    if not dry_run:
        destino.mkdir(parents=True, exist_ok=True)
        _gravar_manifesto(destino, novo_manifesto)
    return relatorio


def uninstall(destino: Path, *, force: bool = False, dry_run: bool = False) -> Relatorio:
    """Remove somente os arquivos instalados por este pacote e nao alterados depois (salvo `force`)."""
    manifesto = _ler_manifesto(destino)
    relatorio = Relatorio(destino)
    restantes: dict[str, str] = {}
    for rel, esperado in sorted(manifesto.items()):
        caminho = _dentro(destino, rel)
        if not caminho.is_file():
            continue
        if _hash(caminho.read_text(encoding="utf-8")) != esperado and not force:
            relatorio.acoes.append(("preservado", rel))
            restantes[rel] = esperado
            continue
        relatorio.acoes.append(("removido", rel))
        if not dry_run:
            caminho.unlink()
            pasta = caminho.parent
            while pasta != destino.resolve() and pasta.is_dir() and not any(pasta.iterdir()):
                pasta.rmdir()
                pasta = pasta.parent
    if not dry_run and manifesto:
        if restantes:
            _gravar_manifesto(destino, restantes)
        else:
            (destino / MANIFESTO).unlink(missing_ok=True)
    return relatorio
