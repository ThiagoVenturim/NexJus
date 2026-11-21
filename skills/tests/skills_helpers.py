"""Dados ficticios e servidor MCP do NexJus montado em memoria para os testes das skills (sem rede)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx

from nexjus_mcp.backend import BackendClient
from nexjus_mcp.config import Settings
from nexjus_mcp.datajud import DataJudClient, digito_verificador_cnj
from nexjus_mcp.service import NexJusService
from nexjus_mcp.store import JsonStore

HOJE = date(2026, 3, 12)
_DV = digito_verificador_cnj("0000001", "2026", "826", "0100")
NUMERO = f"0000001-{_DV}.2026.8.26.0100"
CPF_FICTICIO = "123.456.789-09"
EMAIL_FICTICIO = "maria@example.com"


def sample_db() -> dict:
    prazo = {
        "regra": "cpc_15",
        "dataPublicacaoOuNotificacao": "2026-02-20",
        "diasPrazo": 15,
        "contagem": "uteis",
        "uf": "SP",
        "dataInicioContagem": "2026-02-23",
        "concluido": False,
        "criadoEm": "2026-02-20T00:00:00Z",
    }
    return {
        "clientes": [
            {
                "id": "cli-1",
                "nome": "Maria da Silva Oliveira",
                "documento": CPF_FICTICIO,
                "telefone": "(11) 98765-4321",
                "email": EMAIL_FICTICIO,
                "uf": "SP",
                "municipio": "Sao Paulo",
                "criadoEm": "2026-01-01T00:00:00Z",
            }
        ],
        "veiculos": [],
        "processos": [
            {
                "id": "proc-1",
                "clienteId": "cli-1",
                "numero": NUMERO,
                "tipo": "judicial",
                "orgaoOuTribunal": "TJSP",
                "fase": "conhecimento",
                "uf": "SP",
                "municipio": "Sao Paulo",
                "ultimoAndamento": f"Intimacao enviada a {EMAIL_FICTICIO}",
                "dataUltimaMovimentacao": "2026-03-01",
                "criadoEm": "2026-01-01T00:00:00Z",
            }
        ],
        "prazos": [
            {**prazo, "id": "p1", "processoId": "proc-1", "titulo": f"Replica, CPF {CPF_FICTICIO}",
             "dataVencimento": "2026-03-12"},
            {**prazo, "id": "p2", "processoId": "proc-1", "titulo": "Recurso", "dataVencimento": "2026-03-14"},
        ],
        "feriadosLocais": [],
    }


def _datajud(request: httpx.Request) -> httpx.Response:
    numero = json.loads(request.content)["query"]["match"]["numeroProcesso"]
    fonte = {
        "numeroProcesso": numero,
        "tribunal": "TJSP",
        "dataAjuizamento": "2026-01-10T00:00:00.000Z",
        "dataHoraUltimaAtualizacao": "2026-03-05T10:00:00.000Z",
        "classe": {"codigo": 7, "nome": "Procedimento Comum Civel"},
        "orgaoJulgador": {"codigo": 1, "nome": "1a Vara Civel"},
        "movimentos": [{"codigo": 11, "nome": "Despacho", "dataHora": "2026-03-05T10:00:00.000Z"}],
    }
    return httpx.Response(200, json={"hits": {"hits": [{"_source": fonte}]}})


def make_service(tmp_path: Path, **overrides) -> NexJusService:
    data_file = tmp_path / "dados.json"
    data_file.write_text(json.dumps(sample_db()), encoding="utf-8")
    settings = Settings(_env_file=None, data_file=str(data_file), **overrides)
    return NexJusService(
        settings,
        store=JsonStore(data_file),
        datajud=DataJudClient("chave-ficticia", transport=httpx.MockTransport(_datajud)),
        backend=BackendClient(None, None),
        relogio=lambda: HOJE,
    )
