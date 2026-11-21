"""Catalogo das skills e agentes empacotados e validacao do formato.

Skills seguem o formato de Agent Skills do Claude (`<nome>/SKILL.md` com frontmatter `name` e
`description`). Agentes seguem o formato de subagentes do Claude Code (`<nome>.md` com frontmatter
`name`, `description` e `tools`). As ferramentas do servidor MCP do NexJus aparecem como
`mcp__nexjus__<ferramenta>`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import resources
from importlib.resources.abc import Traversable

from .guardrails import AVISO_MINUTA

MCP_SERVER = "nexjus"
MCP_TOOLS: frozenset[str] = frozenset(
    {
        "calculate_deadline",
        "list_deadlines",
        "deadlines_this_week",
        "datajud_lookup_case",
        "case_movements",
        "clients_with_pending_items",
        "record_movement",
        "generate_agenda",
    }
)
"""Ferramentas expostas por `nexjus-mcp serve`. Os testes conferem contra o servidor real."""

MCP_WRITE_TOOLS: frozenset[str] = frozenset({"record_movement"})

SECOES_SKILL = ("## Quando usar", "## Passo a passo", "## Formato da resposta", "## Limites e LGPD")
SECOES_AGENTE = ("## Limites e LGPD",)
SKILLS_DE_MINUTA = frozenset({"traffic-defense-drafter", "petition-drafter"})

_NOME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_REF_MCP = re.compile(r"mcp__([a-z0-9_-]+)__([a-z0-9_]+)")
_PALAVRAS_RESERVADAS = ("anthropic", "claude")


@dataclass(frozen=True)
class Item:
    tipo: str  # "skill" ou "agente"
    nome: str
    meta: dict[str, str]
    corpo: str
    arquivos: dict[str, str] = field(default_factory=dict)
    """Caminho relativo -> conteudo de todos os arquivos que serao instalados."""

    @property
    def descricao(self) -> str:
        return self.meta.get("description", "")

    def ferramentas_mcp(self) -> set[str]:
        texto = "\n".join(self.arquivos.values())
        return {m.group(2) for m in _REF_MCP.finditer(texto) if m.group(1) == MCP_SERVER}


def parse_frontmatter(texto: str) -> tuple[dict[str, str], str]:
    """Le o frontmatter simples (`chave: valor`, uma por linha) entre linhas `---`."""
    texto = texto.replace("\r\n", "\n")
    if not texto.startswith("---\n"):
        raise ValueError("arquivo sem frontmatter (deve comecar com ---)")
    fim = texto.find("\n---\n", 4)
    if fim < 0:
        raise ValueError("frontmatter sem a linha --- de fechamento")
    meta: dict[str, str] = {}
    for numero, linha in enumerate(texto[4:fim].split("\n"), start=2):
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        chave, sep, valor = linha.partition(":")
        if not sep or not chave.strip() or chave != chave.strip():
            raise ValueError(f"linha {numero} do frontmatter invalida: use 'chave: valor'")
        meta[chave.strip()] = valor.strip()
    return meta, texto[fim + 5 :]


def _assets() -> Traversable:
    return resources.files("nexjus_skills").joinpath("assets")


def _ler_arvore(pasta: Traversable, prefixo: str = "") -> dict[str, str]:
    arquivos: dict[str, str] = {}
    for item in sorted(pasta.iterdir(), key=lambda t: t.name):
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        rel = f"{prefixo}{item.name}"
        if item.is_dir():
            arquivos.update(_ler_arvore(item, rel + "/"))
        else:
            arquivos[rel] = item.read_text(encoding="utf-8")
    return arquivos


def load_skills() -> list[Item]:
    itens = []
    for pasta in sorted(_assets().joinpath("skills").iterdir(), key=lambda t: t.name):
        if not pasta.is_dir() or pasta.name.startswith((".", "_")):
            continue
        arquivos = _ler_arvore(pasta)
        meta, corpo = parse_frontmatter(arquivos.get("SKILL.md", ""))
        itens.append(Item("skill", pasta.name, meta, corpo, arquivos))
    return itens


def load_agents() -> list[Item]:
    itens = []
    for arquivo in sorted(_assets().joinpath("agents").iterdir(), key=lambda t: t.name):
        if not arquivo.name.endswith(".md"):
            continue
        texto = arquivo.read_text(encoding="utf-8")
        meta, corpo = parse_frontmatter(texto)
        itens.append(Item("agente", arquivo.name[:-3], meta, corpo, {arquivo.name: texto}))
    return itens


def load_all() -> list[Item]:
    return load_skills() + load_agents()


def _validar_comum(item: Item) -> list[str]:
    erros = []
    nome = item.meta.get("name", "")
    if nome != item.nome:
        erros.append(f"name '{nome}' difere do nome do arquivo '{item.nome}'")
    if not _NOME.match(nome) or len(nome) > 64:
        erros.append("name deve ter ate 64 caracteres: letras minusculas, numeros e hifens")
    if any(p in nome for p in _PALAVRAS_RESERVADAS):
        erros.append("name nao pode conter palavras reservadas")
    if not item.descricao:
        erros.append("description vazia")
    elif len(item.descricao) > 1024:
        erros.append("description com mais de 1024 caracteres")
    for ferramenta in sorted(item.ferramentas_mcp() - MCP_TOOLS):
        erros.append(f"ferramenta MCP inexistente: mcp__{MCP_SERVER}__{ferramenta}")
    return erros


def _ferramentas_declaradas(valor: str) -> list[str]:
    return [p.strip() for p in valor.split(",") if p.strip()]


def validate_item(item: Item) -> list[str]:
    erros = _validar_comum(item)
    secoes = SECOES_SKILL if item.tipo == "skill" else SECOES_AGENTE
    for secao in secoes:
        if secao not in item.corpo:
            erros.append(f"secao obrigatoria ausente: {secao}")
    if item.tipo == "skill":
        if "SKILL.md" not in item.arquivos:
            erros.append("SKILL.md ausente")
        if item.nome in SKILLS_DE_MINUTA and AVISO_MINUTA not in " ".join(item.corpo.split()):
            erros.append("skill de minuta sem o aviso de revisao (AVISO_MINUTA) literal")
        liberadas = set(_ferramentas_declaradas(item.meta.get("allowed-tools", "")))
        for ferramenta in sorted(MCP_WRITE_TOOLS):
            if f"mcp__{MCP_SERVER}__{ferramenta}" in liberadas:
                erros.append(f"allowed-tools nao pode liberar a ferramenta de escrita {ferramenta} sem confirmacao")
    else:
        declaradas = _ferramentas_declaradas(item.meta.get("tools", ""))
        if not declaradas:
            erros.append("agente sem a lista tools no frontmatter")
        usadas = {f"mcp__{MCP_SERVER}__{f}" for f in item.ferramentas_mcp()}
        faltando = sorted(usadas - set(declaradas))
        if faltando:
            erros.append(f"ferramentas citadas no corpo e ausentes de tools: {', '.join(faltando)}")
    return [f"{item.tipo} {item.nome}: {e}" for e in erros]


def validate_all(itens: list[Item] | None = None) -> list[str]:
    itens = load_all() if itens is None else itens
    erros: list[str] = []
    vistos: set[tuple[str, str]] = set()
    for item in itens:
        chave = (item.tipo, item.nome)
        if chave in vistos:
            erros.append(f"{item.tipo} {item.nome}: nome duplicado")
        vistos.add(chave)
        erros.extend(validate_item(item))
    return erros
