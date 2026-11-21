"""Execucao offline das skills contra o servidor MCP real, com um modelo simulado (sem LLM e sem rede).

O StubModel faz o papel do Claude: chama as ferramentas que a skill indica, copia os dados devolvidos
para a resposta no formato pedido e, nas minutas, termina com o aviso. Os testes conferem que as
ferramentas citadas existem e respondem e que a resposta nao vaza dado pessoal.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from mcp import Client
from skills_helpers import CPF_FICTICIO, EMAIL_FICTICIO, NUMERO, make_service

from nexjus_mcp.server import build_server
from nexjus_skills.catalog import MCP_WRITE_TOOLS, SKILLS_DE_MINUTA, Item, load_skills
from nexjus_skills.guardrails import AVISO_MINUTA, conferir_texto

ARGUMENTOS: dict[str, dict[str, Any]] = {
    "calculate_deadline": {"regra": "cpc_15", "data_publicacao_ou_notificacao": "2026-03-02", "uf": "SP"},
    "list_deadlines": {"hoje": "2026-03-12"},
    "deadlines_this_week": {"hoje": "2026-03-12"},
    "clients_with_pending_items": {"hoje": "2026-03-12"},
    "generate_agenda": {"hoje": "2026-03-12"},
    "case_movements": {"processo": "proc-1", "fonte": "local"},
    "datajud_lookup_case": {"numero": NUMERO},
}


def _dados(result) -> Any:
    if result.structured_content is not None:
        data = result.structured_content
        return data.get("result", data) if isinstance(data, dict) and set(data) == {"result"} else data
    return json.loads(result.content[0].text)


class StubModel:
    """Modelo deterministico: segue a lista de ferramentas da skill e monta a resposta com os dados."""

    def __init__(self, skill: Item) -> None:
        self.skill = skill
        self.chamadas: list[str] = []

    async def responder(self, client: Client) -> str:
        partes = [f"# {self.skill.nome}"]
        for ferramenta in sorted(self.skill.ferramentas_mcp() - MCP_WRITE_TOOLS):
            resultado = await client.call_tool(ferramenta, ARGUMENTOS[ferramenta])
            assert not resultado.is_error, f"{ferramenta}: {resultado.content}"
            self.chamadas.append(ferramenta)
            partes.append(f"Dados de {ferramenta}: {json.dumps(_dados(resultado), ensure_ascii=False)}")
        partes.append("## Fontes\n- NexJus (servidor MCP local), dados do escritorio.")
        if self.skill.nome in SKILLS_DE_MINUTA:
            partes.append(AVISO_MINUTA)
        return "\n\n".join(partes)


def _executar(tmp_path, skill: Item, **settings) -> tuple[str, StubModel]:
    server = build_server(make_service(tmp_path, **settings))
    modelo = StubModel(skill)

    async def cenario():
        async with Client(server) as client:
            return await modelo.responder(client)

    return asyncio.run(cenario()), modelo


@pytest.mark.parametrize("skill", load_skills(), ids=lambda s: s.nome)
def test_skill_roda_offline_sem_vazar_dados_pessoais(tmp_path, skill: Item):
    resposta, modelo = _executar(tmp_path, skill)
    assert modelo.chamadas, "a skill indica ferramentas do servidor MCP"
    assert CPF_FICTICIO not in resposta
    assert EMAIL_FICTICIO not in resposta
    assert "Maria da Silva Oliveira" not in resposta
    assert "chave-ficticia" not in resposta
    assert conferir_texto(resposta, minuta=skill.nome in SKILLS_DE_MINUTA) == []


def test_modo_completo_e_pego_pela_conferencia(tmp_path):
    """No modo completo o servidor nao mascara textos livres; a conferencia da minuta aponta o CPF."""
    triagem = next(s for s in load_skills() if s.nome == "daily-triage")
    resposta, _ = _executar(tmp_path, triagem, privacy="completo")
    achados = conferir_texto(resposta, minuta=False)
    assert achados
    assert {a.tipo for a in achados} == {"dado pessoal"}
    assert all(CPF_FICTICIO not in str(a) for a in achados)


def test_minuta_simulada_sem_aviso_e_fontes_e_barrada(tmp_path):
    defesa = next(s for s in load_skills() if s.nome == "traffic-defense-drafter")
    resposta, _ = _executar(tmp_path, defesa)
    ruim = resposta.replace(AVISO_MINUTA, "").replace("## Fontes", "Referencias") + "\nConforme Sumula 312 do STJ."
    tipos = {a.tipo for a in conferir_texto(ruim)}
    assert tipos == {"citacao sem fonte", "aviso ausente"}
