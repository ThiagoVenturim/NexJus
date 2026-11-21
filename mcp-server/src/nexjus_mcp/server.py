"""Servidor MCP local do NexJus (transporte stdio).

Expoe os prazos e processos do arquivo local, o motor de prazos CPC/CTB e o DataJud como
ferramentas e recursos MCP. Logs vao para stderr (stdout e o canal do protocolo) e nunca
incluem segredos nem dados de clientes.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .prazos import FUNDAMENTO, REGRAS, parametros_padrao
from .service import NexJusService
from .store import StoreError

logger = logging.getLogger(__name__)

INSTRUCOES = (
    "Ferramentas do NexJus para acompanhar prazos processuais (CPC e CTB) e processos. "
    "Os dados vem de um arquivo local do advogado; nomes de clientes podem vir abreviados (LGPD) e "
    "documentos, telefones e e-mails nunca sao enviados. Todo prazo deve ser conferido no sistema oficial."
)

Status = Literal["concluido", "vencido", "hoje", "urgente", "no_prazo"]
Regra = Literal["cpc_5", "cpc_15", "cpc_custom", "ctb_defesa_previa", "ctb_jari", "ctb_cetran"]
DataISO = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Data no formato YYYY-MM-DD")]

_LEITURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_REDE = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
_ESCRITA = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)


def _executar(func: Callable[..., dict], *args: Any, **kwargs: Any) -> dict:
    """Converte erros esperados em ToolError com mensagem segura para o cliente."""
    try:
        return func(*args, **kwargs)
    except (ValueError, StoreError, RuntimeError) as exc:
        raise ToolError(str(exc)) from None


def build_server(service: NexJusService) -> MCPServer:
    server = MCPServer(name="nexjus", instructions=INSTRUCOES, version=__version__)

    @server.tool(annotations=_LEITURA)
    def calculate_deadline(
        regra: Regra,
        data_publicacao_ou_notificacao: DataISO,
        uf: Annotated[str, Field(min_length=2, max_length=2, description="Sigla da UF, por exemplo SP")],
        dias_prazo: Annotated[int | None, Field(ge=1, le=3650)] = None,
        contagem: Literal["uteis", "corridos"] | None = None,
        municipio: str | None = None,
    ) -> dict:
        """Calcula o vencimento de um prazo CPC (dias uteis, recesso de 20/12 a 20/01) ou CTB (30 dias
        corridos com prorrogacao), com a trilha dos dias pulados e o motivo de cada um."""
        return _executar(
            service.calculate_deadline, regra, data_publicacao_ou_notificacao, uf, dias_prazo, contagem, municipio
        )

    @server.tool(annotations=_LEITURA)
    def list_deadlines(
        status: list[Status] | None = None,
        processo: Annotated[str | None, Field(description="Id local ou numero do processo")] = None,
        cliente_id: str | None = None,
        incluir_concluidos: bool = False,
        hoje: DataISO | None = None,
        limite: Annotated[int, Field(ge=1, le=500)] = 100,
    ) -> dict:
        """Lista os prazos cadastrados com status (vencido, hoje, urgente ate 3 dias, no_prazo, concluido)."""
        return _executar(
            service.list_deadlines,
            status=list(status) if status else None,
            processo=processo,
            cliente_id=cliente_id,
            incluir_concluidos=incluir_concluidos,
            hoje=hoje,
            limite=limite,
        )

    @server.tool(annotations=_LEITURA)
    def deadlines_this_week(hoje: DataISO | None = None) -> dict:
        """Prazos pendentes que vencem de hoje ate domingo desta semana, mais os ja vencidos."""
        return _executar(service.deadlines_this_week, hoje=hoje)

    @server.tool(annotations=_REDE)
    def datajud_lookup_case(
        numero: Annotated[str, Field(description="Numero CNJ com 20 digitos, com ou sem pontuacao")],
        movimentos: Annotated[int, Field(ge=1, le=100)] = 5,
    ) -> dict:
        """Consulta a capa do processo na API publica do DataJud (CNJ) e os ultimos movimentos."""
        return _executar(service.datajud_lookup_case, numero, movimentos)

    @server.tool(annotations=_REDE)
    def case_movements(
        processo: Annotated[str, Field(description="Id local ou numero CNJ do processo")],
        limite: Annotated[int, Field(ge=1, le=500)] = 20,
        fonte: Literal["auto", "datajud", "local"] = "auto",
    ) -> dict:
        """Movimentos do processo, do mais recente ao mais antigo (DataJud ou registro local)."""
        return _executar(service.case_movements, processo, limite, fonte)

    @server.tool(annotations=_LEITURA)
    def clients_with_pending_items(
        hoje: DataISO | None = None,
        dias: Annotated[int, Field(ge=0, le=365)] = 7,
    ) -> dict:
        """Clientes com prazos vencidos ou que vencem nos proximos dias, ordenados por urgencia."""
        return _executar(service.clients_with_pending_items, hoje=hoje, dias=dias)

    @server.tool(annotations=_ESCRITA)
    def record_movement(
        processo: Annotated[str, Field(description="Id local ou numero do processo")],
        descricao: Annotated[str, Field(min_length=1, max_length=2000)],
        data: DataISO | None = None,
        regra_prazo: Regra | None = None,
        titulo_prazo: Annotated[str | None, Field(max_length=200)] = None,
        dias_prazo: Annotated[int | None, Field(ge=1, le=3650)] = None,
    ) -> dict:
        """Registra um andamento no processo local. Com regra_prazo, cria o prazo decorrente contado a
        partir da data do andamento (publicacao ou notificacao)."""
        return _executar(service.record_movement, processo, descricao, data, regra_prazo, titulo_prazo, dias_prazo)

    @server.tool(annotations=_LEITURA)
    def generate_agenda(
        hoje: DataISO | None = None,
        dias: Annotated[int, Field(ge=1, le=60)] = 7,
        fonte: Literal["local", "backend"] = "local",
    ) -> dict:
        """Agenda de prazos (vencidos, hoje, urgentes e proximos) em JSON e em texto pronto para leitura.
        Com fonte=backend usa a agenda sincronizada do backend opcional do NexJus."""
        return _executar(service.generate_agenda, hoje=hoje, dias=dias, fonte=fonte)

    @server.resource("nexjus://agenda", name="agenda", mime_type="text/plain")
    def agenda_resource() -> str:
        """Agenda de prazos de hoje para os proximos 7 dias."""
        try:
            return service.generate_agenda()["texto"]
        except (ValueError, StoreError, RuntimeError) as exc:
            raise ResourceError(str(exc)) from None

    @server.resource("nexjus://prazos/pendentes", name="prazos-pendentes", mime_type="application/json")
    def prazos_pendentes_resource() -> str:
        """Prazos pendentes (nao concluidos) com status calculado para hoje."""
        try:
            return json.dumps(service.list_deadlines(limite=500), ensure_ascii=False)
        except (ValueError, StoreError, RuntimeError) as exc:
            raise ResourceError(str(exc)) from None

    @server.resource("nexjus://regras", name="regras-de-prazo", mime_type="application/json")
    def regras_resource() -> str:
        """Regras de prazo suportadas, com dias, tipo de contagem e fundamento legal."""
        regras = []
        for regra in REGRAS:
            dias, contagem, recesso = parametros_padrao(regra)
            regras.append(
                {
                    "regra": regra,
                    "dias_padrao": dias,
                    "contagem": contagem,
                    "considera_recesso_cpc": recesso,
                    "fundamento": FUNDAMENTO[regra],
                }
            )
        return json.dumps(regras, ensure_ascii=False)

    return server
