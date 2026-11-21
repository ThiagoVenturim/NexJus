"""Configuracao lida somente de variaveis de ambiente ou de um arquivo .env local.

Segredos (chave do DataJud, token do backend) ficam em SecretStr e nunca sao exibidos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Privacidade = Literal["minimo", "completo"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXJUS_", env_file=".env", extra="ignore", populate_by_name=True)

    data_file: str = Field(
        default="./nexjus-data.json",
        validation_alias="NEXJUS_MCP_DATA_FILE",
    )
    privacy: Privacidade = Field(
        default="minimo",
        validation_alias="NEXJUS_MCP_PRIVACY",
    )
    read_only: bool = Field(
        default=False,
        validation_alias="NEXJUS_MCP_READ_ONLY",
    )

    datajud_api_key: SecretStr | None = None
    datajud_timeout: float = Field(default=15.0, gt=0, le=120)

    backend_url: str | None = None
    api_token: SecretStr | None = None

    @field_validator("datajud_api_key", "api_token")
    @classmethod
    def _vazio_vira_none(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value().strip():
            return None
        return value

    @field_validator("backend_url")
    @classmethod
    def _url_backend(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        url = value.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise ValueError("NEXJUS_BACKEND_URL deve comecar com http:// ou https://")
        return url

    @property
    def backend_configured(self) -> bool:
        return bool(self.backend_url and self.api_token)
