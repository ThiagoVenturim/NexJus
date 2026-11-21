"""Cliente do backend opcional (app/, nexjus-backend) para a agenda sincronizada.

Usa `GET /agenda` com o token Bearer de NEXJUS_API_TOKEN. A agenda do backend traz apenas
identificadores e datas dos prazos, sem dados pessoais; o servidor MCP completa com os dados locais.
"""

from __future__ import annotations

import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)


class BackendError(RuntimeError):
    """Falha ao falar com o backend. A mensagem nunca contem o token."""


class BackendClient:
    def __init__(
        self,
        base_url: str | None,
        token: str | None,
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._token = token or ""
        self._timeout = timeout
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._token)

    def agenda(self, hoje: date, dias: int) -> dict:
        if not self.configured:
            raise BackendError("Backend nao configurado (NEXJUS_BACKEND_URL e NEXJUS_API_TOKEN).")
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout, transport=self._transport) as client:
                response = client.get(
                    "/agenda",
                    params={"hoje": hoje.isoformat(), "dias": dias},
                    headers={"Authorization": f"Bearer {self._token}"},
                )
        except httpx.HTTPError as exc:
            logger.warning("Falha de rede ao consultar o backend (%s)", type(exc).__name__)
            raise BackendError(f"Falha de rede ao consultar o backend ({type(exc).__name__}).") from None
        if response.status_code != 200:
            logger.warning("Backend respondeu HTTP %s", response.status_code)
            raise BackendError(f"Backend respondeu HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError:
            raise BackendError("Resposta do backend nao e JSON valido.") from None
        if not isinstance(data, dict):
            raise BackendError("Resposta do backend em formato inesperado.")
        return data
