"""Formato das skills e agentes e coerencia com o servidor MCP real."""

from __future__ import annotations

import asyncio
import re

import pytest
from mcp import Client
from skills_helpers import make_service

from nexjus_mcp.server import build_server
from nexjus_skills.catalog import (
    MCP_TOOLS,
    MCP_WRITE_TOOLS,
    SKILLS_DE_MINUTA,
    Item,
    load_agents,
    load_all,
    load_skills,
    parse_frontmatter,
    validate_all,
    validate_item,
)
from nexjus_skills.guardrails import AVISO_MINUTA, MARCADOR_CONFERIR

SKILLS = {
    "case-summarizer",
    "deadline-checker",
    "daily-triage",
    "traffic-defense-drafter",
    "petition-drafter",
    "client-report",
    "document-checklist",
    "jurisprudence-researcher",
}
AGENTES = {"assistente-prazos", "redator-minutas", "pesquisador-jurisprudencia"}
_EMOJI = re.compile("[\U0001f000-\U0001faff\U00002600-\U000027bf\U00002b00-\U00002bff\ufe0f\u200d]")


def test_catalogo_tem_as_skills_e_agentes_da_issue():
    assert {s.nome for s in load_skills()} == SKILLS
    assert {a.nome for a in load_agents()} == AGENTES


def test_todos_os_itens_sao_validos():
    assert validate_all() == []


def test_ferramentas_conhecidas_batem_com_o_servidor_mcp(tmp_path):
    server = build_server(make_service(tmp_path))

    async def listar():
        async with Client(server) as client:
            return await client.list_tools()

    tools = asyncio.run(listar())
    nomes = {t.name for t in tools.tools}
    assert nomes == set(MCP_TOOLS)
    escrita = {t.name for t in tools.tools if t.annotations and t.annotations.read_only_hint is False}
    assert escrita == set(MCP_WRITE_TOOLS)


@pytest.mark.parametrize("item", load_all(), ids=lambda i: i.nome)
def test_cada_item_tem_grounding_lgpd_e_ferramenta(item: Item):
    texto = "\n".join(item.arquivos.values())
    assert item.ferramentas_mcp(), "todo item usa pelo menos uma ferramenta do servidor MCP"
    assert "conselho juridico definitivo" in texto
    assert MARCADOR_CONFERIR in texto
    assert "Nunca invente" in texto
    assert "CPF" in texto
    assert ".env" in texto
    assert texto.isascii(), "o repositorio usa texto sem acentos"
    assert not _EMOJI.search(texto)


def test_skills_de_minuta_trazem_aviso_e_secao_fontes():
    for skill in load_skills():
        if skill.nome in SKILLS_DE_MINUTA:
            assert AVISO_MINUTA in skill.corpo
            assert "## Fontes" in skill.corpo


def test_ferramenta_de_escrita_so_com_confirmacao():
    for item in load_all():
        if MCP_WRITE_TOOLS & item.ferramentas_mcp():
            assert "confirma" in item.corpo, item.nome
    assert all(not (MCP_WRITE_TOOLS & s.ferramentas_mcp()) for s in load_skills() if s.nome in SKILLS_DE_MINUTA)


def test_parse_frontmatter():
    meta, corpo = parse_frontmatter("---\nname: x\ndescription: a: b\n---\ncorpo\n")
    assert meta == {"name": "x", "description": "a: b"}
    assert corpo == "corpo\n"
    with pytest.raises(ValueError, match="sem frontmatter"):
        parse_frontmatter("name: x\n")
    with pytest.raises(ValueError, match="fechamento"):
        parse_frontmatter("---\nname: x\n")
    with pytest.raises(ValueError, match="invalida"):
        parse_frontmatter("---\nsem dois pontos\n---\n")


def _skill(nome: str, meta: dict[str, str], corpo: str) -> Item:
    return Item("skill", nome, meta, corpo, {"SKILL.md": corpo})


def test_validacao_aponta_problemas():
    corpo_ok = "\n".join(["## Quando usar", "## Passo a passo", "## Formato da resposta", "## Limites e LGPD"])
    erros = validate_item(_skill("x-y", {"name": "outro", "description": ""}, "mcp__nexjus__nao_existe"))
    texto = "\n".join(erros)
    assert "difere do nome" in texto
    assert "description vazia" in texto
    assert "mcp__nexjus__nao_existe" in texto
    assert "secao obrigatoria ausente: ## Quando usar" in texto

    meta = {"name": "x-claude", "description": "d", "allowed-tools": "mcp__nexjus__record_movement"}
    texto = "\n".join(validate_item(_skill("x-claude", meta, corpo_ok)))
    assert "palavras reservadas" in texto
    assert "ferramenta de escrita record_movement" in texto

    meta = {"name": "petition-drafter", "description": "d"}
    minuta = "\n".join(validate_item(_skill("petition-drafter", meta, corpo_ok)))
    assert "AVISO_MINUTA" in minuta

    agente = Item("agente", "a", {"name": "a", "description": "d"}, "mcp__nexjus__list_deadlines", {"a.md": ""})
    texto = "\n".join(validate_item(agente))
    assert "sem a lista tools" in texto
    assert "secao obrigatoria ausente: ## Limites e LGPD" in texto

    agente = Item(
        "agente", "a", {"name": "a", "description": "d", "tools": "Read"}, "## Limites e LGPD",
        {"a.md": "mcp__nexjus__list_deadlines"},
    )
    assert any("ausentes de tools" in e for e in validate_item(agente))

    dup = _skill("x", {"name": "x", "description": "d"}, corpo_ok)
    assert any("duplicado" in e for e in validate_all([dup, dup]))
