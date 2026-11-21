"""Dados ficticios e fabricas usados pelos testes do servidor MCP (nada de rede)."""

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

HOJE = date(2026, 3, 12)  # quinta-feira
DATAJUD_KEY = "chave-ficticia-de-teste"
BACKEND_TOKEN = "token-de-teste-0123456789"


def cnj(sequencial: str, ano: str = "2026", jtr: str = "826", origem: str = "0100") -> str:
    dv = digito_verificador_cnj(sequencial, ano, jtr, origem)
    return f"{sequencial}-{dv}.{ano}.{jtr[0]}.{jtr[1:]}.{origem}"


NUMERO_1 = cnj("0000001")
NUMERO_2 = cnj("0000002")


def sample_db() -> dict:
    return {
        "clientes": [
            {
                "id": "cli-1",
                "nome": "Maria da Silva Oliveira",
                "documento": "123.456.789-09",
                "telefone": "(11) 98765-4321",
                "email": "maria@example.com",
                "uf": "SP",
                "municipio": "Sao Paulo",
                "criadoEm": "2026-01-01T00:00:00Z",
            },
            {
                "id": "cli-2",
                "nome": "Joao Pereira",
                "documento": "987.654.321-00",
                "telefone": "",
                "email": "",
                "uf": "RJ",
                "municipio": "Rio de Janeiro",
                "criadoEm": "2026-01-01T00:00:00Z",
            },
        ],
        "veiculos": [
            {
                "id": "vei-1",
                "clienteId": "cli-2",
                "placa": "BRA2E19",
                "renavam": "12345678901",
                "uf": "RJ",
                "marcaModelo": "Modelo X",
                "criadoEm": "2026-01-01T00:00:00Z",
            }
        ],
        "processos": [
            {
                "id": "proc-1",
                "clienteId": "cli-1",
                "numero": NUMERO_1,
                "tipo": "judicial",
                "orgaoOuTribunal": "TJSP",
                "fase": "conhecimento",
                "uf": "SP",
                "municipio": "Sao Paulo",
                "ultimoAndamento": "Juntada de peticao",
                "dataUltimaMovimentacao": "2026-03-01",
                "criadoEm": "2026-01-01T00:00:00Z",
            },
            {
                "id": "proc-2",
                "clienteId": "cli-2",
                "veiculoId": "vei-1",
                "numero": "AIT E012345678",
                "tipo": "transito",
                "orgaoOuTribunal": "DETRAN-RJ",
                "fase": "defesa_previa",
                "uf": "RJ",
                "municipio": "Rio de Janeiro",
                "ultimoAndamento": "Notificacao de autuacao",
                "dataUltimaMovimentacao": "2026-03-02",
                "criadoEm": "2026-01-01T00:00:00Z",
            },
        ],
        "prazos": [
            _prazo("prz-vencido", "proc-1", "Replica", "2026-03-10"),
            _prazo("prz-hoje", "proc-1", "Contestacao de Maria, CPF 123.456.789-09", "2026-03-12"),
            _prazo("prz-urgente", "proc-2", "Defesa previa", "2026-03-14", regra="ctb_defesa_previa"),
            _prazo("prz-semana", "proc-2", "Juntar documentos", "2026-03-15"),
            _prazo("prz-futuro", "proc-1", "Recurso", "2026-03-25"),
            _prazo("prz-feito", "proc-1", "Manifestacao", "2026-03-11", concluido=True),
            _prazo("prz-invalido", "proc-1", "Data errada", "2026-02-30"),
        ],
        "feriadosLocais": [{"data": "01-25", "nome": "Aniversario de Sao Paulo", "uf": "SP", "municipio": "Sao Paulo"}],
    }


def _prazo(pid: str, processo: str, titulo: str, venc: str, *, regra: str = "cpc_15", concluido: bool = False) -> dict:
    return {
        "id": pid,
        "processoId": processo,
        "titulo": titulo,
        "regra": regra,
        "dataPublicacaoOuNotificacao": "2026-02-20",
        "diasPrazo": 15,
        "contagem": "uteis",
        "uf": "SP",
        "dataInicioContagem": "2026-02-23",
        "dataVencimento": venc,
        "concluido": concluido,
        "criadoEm": "2026-02-20T00:00:00Z",
    }


def write_db(path: Path, db: dict | None = None) -> Path:
    path.write_text(json.dumps(db if db is not None else sample_db()), encoding="utf-8")
    return path


def datajud_payload(numero_digitos: str) -> dict:
    return {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "numeroProcesso": numero_digitos,
                        "tribunal": "TJSP",
                        "dataAjuizamento": "2026-01-10T00:00:00.000Z",
                        "dataHoraUltimaAtualizacao": "2026-03-05T10:00:00.000Z",
                        "classe": {"codigo": 7, "nome": "Procedimento Comum Civel"},
                        "orgaoJulgador": {"codigo": 1, "nome": "1a Vara Civel"},
                        "movimentos": [
                            {"codigo": 26, "nome": "Distribuicao", "dataHora": "2026-01-10T09:00:00.000Z"},
                            {"codigo": 85, "nome": "Peticao", "dataHora": "2026-03-05T10:00:00.000Z"},
                            {"codigo": 11, "nome": "Despacho", "dataHora": "2026-02-01T12:00:00.000Z"},
                        ],
                        "partes": [{"nome": "NAO DEVE APARECER"}],
                    }
                }
            ]
        }
    }


class Recorder:
    """Transporte httpx falso que registra as requisicoes."""

    def __init__(self, handler) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def datajud_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    return httpx.Response(200, json=datajud_payload(body["query"]["match"]["numeroProcesso"]))


def make_service(
    tmp_path: Path,
    *,
    db: dict | None = None,
    datajud_handler=datajud_ok,
    datajud_key: str | None = DATAJUD_KEY,
    backend_handler=None,
    **settings_overrides,
) -> tuple[NexJusService, Recorder, Recorder | None]:
    data_file = write_db(tmp_path / "dados.json", db)
    values = {"data_file": str(data_file)}
    values.update(settings_overrides)
    settings = Settings(_env_file=None, **values)
    datajud_rec = Recorder(datajud_handler)
    datajud = DataJudClient(datajud_key, transport=datajud_rec.transport)
    backend_rec = Recorder(backend_handler) if backend_handler else None
    backend = BackendClient(
        "http://127.0.0.1:8000" if backend_rec else None,
        BACKEND_TOKEN if backend_rec else None,
        transport=backend_rec.transport if backend_rec else None,
    )
    service = NexJusService(
        settings, store=JsonStore(data_file), datajud=datajud, backend=backend, relogio=lambda: HOJE
    )
    return service, datajud_rec, backend_rec
