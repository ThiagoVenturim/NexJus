"""Cliente da API publica do DataJud (CNJ), porte de extension/src/services/datajud.ts.

A chave da API vem somente da configuracao (variavel de ambiente ou .env) e nunca aparece em
mensagens de erro, logs ou respostas. O transporte HTTP pode ser injetado para testes offline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DATAJUD_BASE_URL = "https://api-publica.datajud.cnj.jus.br"

# Segmento J.TR do numero unico CNJ -> alias do endpoint do DataJud (mesmo mapa da extensao).
MAPA_ENDPOINTS_DATAJUD: dict[str, str] = {
    "4.01": "api_publica_trf1",
    "4.02": "api_publica_trf2",
    "4.03": "api_publica_trf3",
    "4.04": "api_publica_trf4",
    "4.05": "api_publica_trf5",
    "4.06": "api_publica_trf6",
    "5.01": "api_publica_trt1",
    "5.02": "api_publica_trt2",
    "5.03": "api_publica_trt3",
    "5.04": "api_publica_trt4",
    "5.15": "api_publica_trt15",
    "8.01": "api_publica_tjac",
    "8.02": "api_publica_tjal",
    "8.03": "api_publica_tjap",
    "8.04": "api_publica_tjam",
    "8.05": "api_publica_tjba",
    "8.06": "api_publica_tjce",
    "8.07": "api_publica_tjdft",
    "8.08": "api_publica_tjes",
    "8.09": "api_publica_tjgo",
    "8.10": "api_publica_tjma",
    "8.11": "api_publica_tjmt",
    "8.12": "api_publica_tjms",
    "8.13": "api_publica_tjmg",
    "8.14": "api_publica_tjpa",
    "8.15": "api_publica_tjpb",
    "8.16": "api_publica_tjpr",
    "8.17": "api_publica_tjpe",
    "8.18": "api_publica_tjpi",
    "8.19": "api_publica_tjrj",
    "8.20": "api_publica_tjrn",
    "8.21": "api_publica_tjrs",
    "8.22": "api_publica_tjro",
    "8.23": "api_publica_tjrr",
    "8.24": "api_publica_tjsc",
    "8.25": "api_publica_tjse",
    "8.26": "api_publica_tjsp",
    "8.27": "api_publica_tjto",
}


class DataJudError(RuntimeError):
    """Falha na consulta. A mensagem nunca contem a chave da API."""


def limpar_digitos(numero: str) -> str:
    return re.sub(r"\D", "", numero or "")


def digito_verificador_cnj(nnnnnnn: str, aaaa: str, jtr: str, oooo: str) -> str:
    base = int(f"{nnnnnnn}{aaaa}{jtr}{oooo}00")
    return str(98 - (base % 97)).zfill(2)


def validar_numero_cnj(numero: str) -> bool:
    """Numeracao unica de 20 digitos (Resolucao CNJ 65/2008) com digito verificador mod 97."""
    d = limpar_digitos(numero)
    if len(d) != 20:
        return False
    nnnnnnn, dd, aaaa, jtr, oooo = d[0:7], d[7:9], d[9:13], d[13:16], d[16:20]
    return int(f"{nnnnnnn}{aaaa}{jtr}{oooo}{dd}") % 97 == 1


def formatar_numero_cnj(numero: str) -> str:
    d = limpar_digitos(numero)
    if len(d) != 20:
        return numero
    return f"{d[0:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:20]}"


def endpoint_por_numero(numero: str) -> str:
    d = limpar_digitos(numero)
    if len(d) != 20:
        raise ValueError("Numero de processo CNJ deve conter 20 digitos.")
    chave = f"{d[13]}.{d[14:16]}"
    alias = MAPA_ENDPOINTS_DATAJUD.get(chave)
    if not alias:
        raise ValueError(f"Tribunal nao mapeado para o segmento CNJ {chave}.")
    return f"{DATAJUD_BASE_URL}/{alias}/_search"


def normalizar_resposta(payload: Any) -> dict | None:
    """Extrai a capa e os movimentos do primeiro hit. Campos de partes nao sao copiados."""
    if not isinstance(payload, dict):
        return None
    outer = payload.get("hits")
    hits = outer.get("hits") if isinstance(outer, dict) else None
    if not isinstance(hits, list) or not hits or not isinstance(hits[0], dict):
        return None
    source = hits[0].get("_source") or {}
    if not isinstance(source, dict) or not source.get("numeroProcesso"):
        return None

    movimentos = []
    for m in source.get("movimentos") or []:
        if not isinstance(m, dict):
            continue
        movimentos.append(
            {
                "codigo": m.get("codigo") or 0,
                "nome": m.get("nome") or "Movimentacao",
                "data_hora": m.get("dataHora") or "",
            }
        )
    movimentos.sort(key=lambda item: item["data_hora"], reverse=True)

    classe = source.get("classe")
    orgao = source.get("orgaoJulgador")
    return {
        "numero_processo": source["numeroProcesso"],
        "tribunal": source.get("tribunal") or "",
        "classe": (classe.get("nome") or "") if isinstance(classe, dict) else "",
        "orgao_julgador": (orgao.get("nome") or "") if isinstance(orgao, dict) else "",
        "data_ajuizamento": source.get("dataAjuizamento") or "",
        "data_ultima_atualizacao": source.get("dataHoraUltimaAtualizacao") or "",
        "movimentos": movimentos,
    }


class DataJudClient:
    """Consulta por numero CNJ com cache em memoria por processo."""

    def __init__(
        self,
        api_key: str | None,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._timeout = timeout
        self._transport = transport
        self._cache: dict[str, dict | None] = {}

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def clear_cache(self) -> None:
        self._cache.clear()

    def consultar(self, numero: str) -> dict | None:
        digitos = limpar_digitos(numero)
        if len(digitos) != 20:
            raise ValueError("Numero de processo CNJ deve conter 20 digitos.")
        if not validar_numero_cnj(digitos):
            raise ValueError("Numero de processo CNJ com digito verificador invalido.")
        if not self._api_key:
            raise DataJudError("Chave da API publica do DataJud nao configurada (NEXJUS_DATAJUD_API_KEY).")
        if digitos in self._cache:
            return self._cache[digitos]

        endpoint = endpoint_por_numero(digitos)
        body = {"size": 1, "query": {"match": {"numeroProcesso": digitos}}}
        headers = {"Content-Type": "application/json", "Authorization": f"ApiKey {self._api_key}"}
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(endpoint, json=body, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("Falha de rede ao consultar o DataJud (%s)", type(exc).__name__)
            raise DataJudError(f"Falha de rede ao consultar o DataJud ({type(exc).__name__}).") from None

        if response.status_code != 200:
            logger.warning("DataJud respondeu HTTP %s", response.status_code)
            raise DataJudError(f"Erro ao consultar DataJud (HTTP {response.status_code}).")
        try:
            data = response.json()
        except ValueError:
            raise DataJudError("Resposta do DataJud nao e JSON valido.") from None

        normalizado = normalizar_resposta(data)
        if normalizado is not None:
            self._cache[digitos] = normalizado
        return normalizado
