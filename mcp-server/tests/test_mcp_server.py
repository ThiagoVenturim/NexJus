"""Servidor MCP de ponta a ponta com o cliente MCP em memoria (sem stdio e sem rede)."""

from __future__ import annotations

import asyncio
import json

from mcp import Client
from mcp_helpers import NUMERO_1, make_service

from nexjus_mcp.cli import main as cli_main
from nexjus_mcp.server import build_server

FERRAMENTAS = {
    "calculate_deadline",
    "list_deadlines",
    "deadlines_this_week",
    "datajud_lookup_case",
    "case_movements",
    "clients_with_pending_items",
    "record_movement",
    "generate_agenda",
}


def _run(coro):
    return asyncio.run(coro)


def _json(result) -> dict:
    if result.structured_content is not None:
        data = result.structured_content
        return data.get("result", data) if isinstance(data, dict) and set(data) == {"result"} else data
    return json.loads(result.content[0].text)


def test_lista_ferramentas_e_recursos(tmp_path):
    service, _, _ = make_service(tmp_path)
    server = build_server(service)

    async def scenario():
        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            return tools, resources

    tools, resources = _run(scenario())
    nomes = {t.name for t in tools.tools}
    assert nomes == FERRAMENTAS
    por_nome = {t.name: t for t in tools.tools}
    assert por_nome["record_movement"].annotations.read_only_hint is False
    assert por_nome["list_deadlines"].annotations.read_only_hint is True
    assert {str(r.uri) for r in resources.resources} == {
        "nexjus://agenda",
        "nexjus://prazos/pendentes",
        "nexjus://regras",
    }


def test_chamadas_de_ferramentas(tmp_path):
    service, _, _ = make_service(tmp_path)
    server = build_server(service)

    async def scenario():
        async with Client(server) as client:
            calc = await client.call_tool(
                "calculate_deadline",
                {"regra": "ctb_jari", "data_publicacao_ou_notificacao": "2026-03-04", "uf": "SP"},
            )
            semana = await client.call_tool("deadlines_this_week", {})
            caso = await client.call_tool("datajud_lookup_case", {"numero": NUMERO_1})
            registro = await client.call_tool(
                "record_movement", {"processo": "proc-1", "descricao": "Despacho", "data": "2026-03-12"}
            )
            agenda = await client.call_tool("generate_agenda", {"dias": 7})
            return calc, semana, caso, registro, agenda

    calc, semana, caso, registro, agenda = _run(scenario())
    for result in (calc, semana, caso, registro, agenda):
        assert not result.is_error, result.content
    assert _json(calc)["data_vencimento"] == "2026-04-06"
    assert [p["id"] for p in _json(semana)["esta_semana"]] == ["prz-hoje", "prz-urgente", "prz-semana"]
    assert _json(caso)["tribunal"] == "TJSP"
    assert _json(registro)["registrado"]["ultimo_andamento"] == "Despacho"
    assert _json(agenda)["total_criticos"] == 4


def test_erros_viram_resultado_de_erro(tmp_path):
    service, _, _ = make_service(tmp_path, read_only=True)
    server = build_server(service)

    async def scenario():
        async with Client(server) as client:
            invalido = await client.call_tool(
                "calculate_deadline", {"regra": "cpc_5", "data_publicacao_ou_notificacao": "2026-02-30", "uf": "SP"}
            )
            bloqueado = await client.call_tool("record_movement", {"processo": "proc-1", "descricao": "x"})
            regra = await client.call_tool(
                "calculate_deadline",
                {"regra": "nao_existe", "data_publicacao_ou_notificacao": "2026-03-02", "uf": "SP"},
            )
            return invalido, bloqueado, regra

    invalido, bloqueado, regra = _run(scenario())
    assert invalido.is_error and "inexistente" in invalido.content[0].text
    assert bloqueado.is_error and "somente leitura" in bloqueado.content[0].text
    assert regra.is_error


def test_recursos(tmp_path):
    service, _, _ = make_service(tmp_path)
    server = build_server(service)

    async def scenario():
        async with Client(server) as client:
            agenda = await client.read_resource("nexjus://agenda")
            regras = await client.read_resource("nexjus://regras")
            pendentes = await client.read_resource("nexjus://prazos/pendentes")
            return agenda, regras, pendentes

    agenda, regras, pendentes = _run(scenario())
    assert "Agenda de prazos de" in agenda.contents[0].text
    tabela = {r["regra"]: r for r in json.loads(regras.contents[0].text)}
    assert tabela["cpc_15"]["dias_padrao"] == 15 and tabela["ctb_jari"]["contagem"] == "corridos"
    dados = json.loads(pendentes.contents[0].text)
    assert dados["total"] == 5
    assert "123.456.789-09" not in pendentes.contents[0].text


def test_cli_import_csv_e_check(tmp_path, monkeypatch, capsys):
    pasta = tmp_path / "csv"
    pasta.mkdir()
    (pasta / "processos.csv").write_text(
        "id,clienteId,veiculoId,numero,tipo,orgaoOuTribunal,fase,uf,municipio,ultimoAndamento,"
        f"dataUltimaMovimentacao,criadoEm\nproc-1,cli-1,,{NUMERO_1},judicial,TJSP,conhecimento,SP,,,,\n",
        encoding="utf-8",
    )
    destino = tmp_path / "dados.json"
    monkeypatch.setenv("NEXJUS_MCP_DATA_FILE", str(destino))
    monkeypatch.setenv("NEXJUS_DATAJUD_API_KEY", "chave-secreta-cli")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["import-csv", str(pasta)]) == 0
    assert json.loads(destino.read_text(encoding="utf-8"))["processos"][0]["numero"] == NUMERO_1
    assert cli_main(["import-csv", str(pasta)]) == 1
    assert cli_main(["check"]) == 0
    saida = capsys.readouterr()
    assert "processos=1" in saida.err
    assert "chave-secreta-cli" not in saida.err + saida.out
    assert saida.out == ""
