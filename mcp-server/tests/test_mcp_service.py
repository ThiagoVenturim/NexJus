"""Ferramentas do servidor MCP sobre dados ficticios, sem rede."""

from __future__ import annotations

import json

import httpx
import pytest
from mcp_helpers import BACKEND_TOKEN, NUMERO_1, make_service

from nexjus_mcp.datajud import limpar_digitos
from nexjus_mcp.service import ToolError
from nexjus_mcp.store import JsonStore

SENSIVEIS = ("123.456.789-09", "987.654.321-00", "98765-4321", "maria@example.com", "12345678901", "da Silva Oliveira")


def _sem_dados_sensiveis(resultado: dict) -> None:
    texto = json.dumps(resultado, ensure_ascii=False)
    for dado in SENSIVEIS:
        assert dado not in texto, dado


def test_list_deadlines_status_e_privacidade(tmp_path):
    service, _, _ = make_service(tmp_path)
    res = service.list_deadlines()
    ids = [p["id"] for p in res["prazos"]]
    assert ids == ["prz-vencido", "prz-hoje", "prz-urgente", "prz-semana", "prz-futuro"]
    status = {p["id"]: p["status"] for p in res["prazos"]}
    assert status == {
        "prz-vencido": "vencido",
        "prz-hoje": "hoje",
        "prz-urgente": "urgente",
        "prz-semana": "urgente",
        "prz-futuro": "no_prazo",
    }
    assert res["registros_com_data_invalida"] == 1
    hoje = res["prazos"][1]
    assert hoje["cliente"]["nome"] == "Maria S. O."
    assert "[cpf]" in hoje["titulo"]
    assert res["prazos"][2]["processo"]["placa"] == "BRA***9"
    _sem_dados_sensiveis(res)


def test_list_deadlines_filtros(tmp_path):
    service, _, _ = make_service(tmp_path)
    assert [p["id"] for p in service.list_deadlines(status=["vencido", "hoje"])["prazos"]] == [
        "prz-vencido",
        "prz-hoje",
    ]
    assert [p["id"] for p in service.list_deadlines(status=["concluido"])["prazos"]] == ["prz-feito"]
    assert {p["id"] for p in service.list_deadlines(processo="proc-2")["prazos"]} == {"prz-urgente", "prz-semana"}
    assert {p["id"] for p in service.list_deadlines(processo=limpar_digitos(NUMERO_1))["prazos"]} == {
        "prz-vencido",
        "prz-hoje",
        "prz-futuro",
    }
    assert {p["id"] for p in service.list_deadlines(cliente_id="cli-2")["prazos"]} == {"prz-urgente", "prz-semana"}
    limitado = service.list_deadlines(limite=2)
    assert len(limitado["prazos"]) == 2 and limitado["truncado"] and limitado["total"] == 5
    with pytest.raises(ToolError, match="Status invalido"):
        service.list_deadlines(status=["perdido"])
    with pytest.raises(ToolError, match="nao encontrado"):
        service.list_deadlines(processo="proc-x")


def test_privacidade_completo_ainda_omite_documentos(tmp_path):
    service, _, _ = make_service(tmp_path, privacy="completo")
    res = service.list_deadlines()
    texto = json.dumps(res, ensure_ascii=False)
    assert "Maria da Silva Oliveira" in texto
    assert "BRA2E19" in texto
    for dado in ("987.654.321-00", "maria@example.com", "12345678901", "98765-4321"):
        assert dado not in texto


def test_deadlines_this_week(tmp_path):
    service, _, _ = make_service(tmp_path)
    res = service.deadlines_this_week()
    assert (res["semana_inicio"], res["semana_fim"]) == ("2026-03-09", "2026-03-15")
    assert [p["id"] for p in res["vencidos"]] == ["prz-vencido"]
    assert [p["id"] for p in res["esta_semana"]] == ["prz-hoje", "prz-urgente", "prz-semana"]
    assert res["quantidade_por_dia"] == {"2026-03-12": 1, "2026-03-14": 1, "2026-03-15": 1}
    outra = service.deadlines_this_week(hoje="2026-03-16")
    assert [p["id"] for p in outra["esta_semana"]] == []
    assert len(outra["vencidos"]) == 4


def test_calculate_deadline_usa_feriados_locais_do_arquivo(tmp_path):
    service, _, _ = make_service(tmp_path)
    # Publicacao na sexta 22/01/2027; a segunda 25/01/2027 e feriado local do arquivo, entao o dia 1 e 26/01.
    res = service.calculate_deadline("cpc_5", "2027-01-22", "SP", municipio="Sao Paulo")
    assert res["data_inicio_contagem"] == "2027-01-26"
    assert {"data": "2027-01-25", "motivo": "feriado local: Aniversario de Sao Paulo", "fase": "inicio"} in res[
        "dias_pulados"
    ]
    assert "Confira" in res["aviso"]
    with pytest.raises(ToolError):
        service.calculate_deadline("cpc_5", "2027-13-01", "SP")


def test_datajud_lookup_case(tmp_path):
    service, rec, _ = make_service(tmp_path)
    res = service.datajud_lookup_case(limpar_digitos(NUMERO_1), movimentos=2)
    assert res["encontrado"] and res["numero"] == NUMERO_1
    assert res["tribunal"] == "TJSP" and res["total_movimentos"] == 3
    assert [m["nome"] for m in res["ultimos_movimentos"]] == ["Peticao", "Despacho"]
    assert res["processo_local"]["id"] == "proc-1"
    assert "NAO DEVE APARECER" not in json.dumps(res)
    assert len(rec.requests) == 1
    with pytest.raises(ToolError, match="Numero CNJ invalido"):
        service.datajud_lookup_case("0000001-00.2026.8.26.0100")


def test_datajud_sem_resultado_e_erro_http(tmp_path):
    service, _, _ = make_service(tmp_path, datajud_handler=lambda r: httpx.Response(200, json={"hits": {"hits": []}}))
    assert service.datajud_lookup_case(NUMERO_1)["encontrado"] is False
    service, _, _ = make_service(tmp_path, datajud_handler=lambda r: httpx.Response(429))
    with pytest.raises(ToolError, match="HTTP 429"):
        service.datajud_lookup_case(NUMERO_1)


def test_case_movements_datajud_e_local(tmp_path):
    service, rec, _ = make_service(tmp_path)
    res = service.case_movements("proc-1", limite=1)
    assert res["fonte"] == "datajud" and res["total"] == 3
    assert [m["nome"] for m in res["movimentos"]] == ["Peticao"]

    local = service.case_movements("proc-2")
    assert local["fonte"] == "local"
    assert local["movimentos"][0]["nome"] == "Notificacao de autuacao"
    assert len(rec.requests) == 1

    sem_chave, rec2, _ = make_service(tmp_path, datajud_key=None)
    assert sem_chave.case_movements("proc-1")["fonte"] == "local"
    assert rec2.requests == []
    with pytest.raises(ToolError, match="DataJud"):
        sem_chave.case_movements("proc-1", fonte="datajud")
    with pytest.raises(ToolError, match="CNJ valido"):
        service.case_movements("proc-2", fonte="datajud")
    with pytest.raises(ToolError, match="nao encontrado"):
        service.case_movements("inexistente")


def test_clients_with_pending_items(tmp_path):
    service, _, _ = make_service(tmp_path)
    res = service.clients_with_pending_items(dias=7)
    assert res["total_clientes"] == 2
    maria, joao = res["clientes"]
    assert maria["cliente"] == {"id": "cli-1", "nome": "Maria S. O.", "uf": "SP", "municipio": "Sao Paulo"}
    assert (maria["vencidos"], maria["hoje"], maria["urgentes"], maria["proximos"]) == (1, 1, 0, 0)
    assert maria["proximo_vencimento"] == "2026-03-12"
    assert maria["processos"] == [NUMERO_1]
    assert joao["urgentes"] == 2 and joao["cliente"]["nome"] == "Joao P."
    _sem_dados_sensiveis(res)
    assert service.clients_with_pending_items(dias=30)["clientes"][0]["proximos"] == 1


def test_record_movement_atualiza_processo_e_cria_prazo(tmp_path):
    service, _, _ = make_service(tmp_path)
    res = service.record_movement(
        "proc-1", "Intimacao para manifestacao", data="2026-03-06", regra_prazo="cpc_15", titulo_prazo="Manifestar"
    )
    assert res["anterior"]["ultimo_andamento"] == "Juntada de peticao"
    assert res["registrado"]["data_ultima_movimentacao"] == "2026-03-06"
    calculo = res["prazo_criado"]["calculo"]
    assert calculo["data_vencimento"] == "2026-03-27"

    db = JsonStore(service.store.path).load()
    proc = next(p for p in db["processos"] if p["id"] == "proc-1")
    assert proc["ultimoAndamento"] == "Intimacao para manifestacao"
    novo = next(p for p in db["prazos"] if p["id"] == res["prazo_criado"]["id"])
    assert novo["dataVencimento"] == "2026-03-27" and novo["processoId"] == "proc-1"
    assert novo["titulo"] == "Manifestar" and novo["concluido"] is False
    assert novo["municipio"] == "Sao Paulo"
    # O prazo novo aparece nas listagens
    assert res["prazo_criado"]["id"] in [p["id"] for p in service.list_deadlines()["prazos"]]
    # Os demais dados continuam no arquivo
    assert db["clientes"][0]["documento"] == "123.456.789-09"


def test_record_movement_validacoes(tmp_path):
    service, _, _ = make_service(tmp_path)
    antes = service.store.path.read_text(encoding="utf-8")
    with pytest.raises(ToolError, match="nao encontrado"):
        service.record_movement("proc-x", "algo")
    with pytest.raises(ToolError, match="obrigatoria"):
        service.record_movement("proc-1", "   ")
    with pytest.raises(ToolError, match="Regra"):
        service.record_movement("proc-1", "algo", regra_prazo="cpc_99")
    assert service.store.path.read_text(encoding="utf-8") == antes

    somente_leitura, _, _ = make_service(tmp_path, read_only=True)
    with pytest.raises(ToolError, match="somente leitura"):
        somente_leitura.record_movement("proc-1", "algo")


def test_generate_agenda_local(tmp_path):
    service, _, _ = make_service(tmp_path)
    agenda = service.generate_agenda(dias=7)
    assert [i["id"] for i in agenda["vencidos"]] == ["prz-vencido"]
    assert [i["id"] for i in agenda["vencendo_hoje"]] == ["prz-hoje"]
    assert [i["id"] for i in agenda["urgentes"]] == ["prz-urgente", "prz-semana"]
    assert agenda["proximos"] == []
    assert agenda["total_criticos"] == 4
    assert "Vencidos: 1" in agenda["texto"] and "Maria S. O." in agenda["texto"]
    assert "123.456.789-09" not in agenda["texto"]
    assert [i["id"] for i in service.generate_agenda(dias=20)["proximos"]] == ["prz-futuro"]
    with pytest.raises(ToolError):
        service.generate_agenda(dias=0)


def test_generate_agenda_backend(tmp_path):
    def backend(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {BACKEND_TOKEN}"
        assert request.url.path == "/agenda"
        assert request.url.params["hoje"] == "2026-03-12" and request.url.params["dias"] == "7"
        return httpx.Response(
            200,
            json={
                "hoje": "2026-03-12",
                "dias": 7,
                "vencidos": [
                    {"id": "prz-vencido", "due_date": "2026-03-10", "dias_restantes": -2, "status": "vencido"}
                ],
                "vencendo_hoje": [],
                "urgentes": [
                    {"id": "so-no-backend", "due_date": "2026-03-13", "dias_restantes": 1, "status": "urgente"}
                ],
                "proximos": [],
                "total_criticos": 2,
            },
        )

    service, _, rec = make_service(tmp_path, backend_handler=backend)
    agenda = service.generate_agenda(fonte="backend")
    assert len(rec.requests) == 1
    assert agenda["vencidos"][0]["cliente"]["nome"] == "Maria S. O."
    assert agenda["urgentes"][0]["id"] == "so-no-backend" and agenda["urgentes"][0]["cliente"] is None
    assert agenda["total_criticos"] == 2

    sem_backend, _, _ = make_service(tmp_path)
    with pytest.raises(ToolError, match="Backend nao configurado"):
        sem_backend.generate_agenda(fonte="backend")

    falho, _, _ = make_service(tmp_path, backend_handler=lambda r: httpx.Response(401))
    with pytest.raises(ToolError, match="HTTP 401") as exc:
        falho.generate_agenda(fonte="backend")
    assert BACKEND_TOKEN not in str(exc.value)


def test_backend_real_em_memoria(tmp_path):
    """Integracao com o backend do repositorio (app/) via ASGI em memoria, sem rede."""
    pytest.importorskip("nexjus_backend")
    from fastapi.testclient import TestClient

    from nexjus_backend.config import Settings as BackendSettings
    from nexjus_backend.main import create_app
    from nexjus_backend.models import Base

    app = create_app(BackendSettings(_env_file=None, database_url="sqlite://", api_token=BACKEND_TOKEN, smtp_host=None))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as tc:
        tc.headers.update({"Authorization": f"Bearer {BACKEND_TOKEN}"})
        push = tc.post(
            "/sync/push",
            json={
                "device_id": "maquina-1",
                "changes": [
                    {
                        "entity": "prazos",
                        "id": "prz-hoje",
                        "updated_at": "2026-03-01T10:00:00+00:00",
                        "payload": "opaco",
                        "due_date": "2026-03-12",
                        "done": False,
                    }
                ],
            },
        )
        assert push.status_code == 200, push.text

        def ponte(request: httpx.Request) -> httpx.Response:
            resp = tc.get(request.url.path, params=dict(request.url.params), headers=dict(request.headers))
            return httpx.Response(resp.status_code, content=resp.content, headers={"content-type": "application/json"})

        service, _, _ = make_service(tmp_path, backend_handler=ponte)
        agenda = service.generate_agenda(fonte="backend")
    assert [i["id"] for i in agenda["vencendo_hoje"]] == ["prz-hoje"]
    assert agenda["vencendo_hoje"][0]["processo"]["numero"] == NUMERO_1
