"""Configuracao lida somente de variaveis de ambiente ou de um arquivo .env local.

Segredos (token da API, senha do SMTP, senha embutida na URL do banco) usam SecretStr ou
sao mascarados antes de qualquer exibicao, para que nunca aparecam em logs.
"""

from __future__ import annotations

import re
from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXJUS_", env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = Field(
        default="sqlite:///./nexjus.db",
        repr=False,
        validation_alias=AliasChoices("NEXJUS_DATABASE_URL", "DATABASE_URL"),
    )
    api_token: SecretStr | None = None
    cors_origins: str = ""
    max_push_changes: int = Field(default=500, ge=1, le=5000)
    max_payload_bytes: int = Field(default=262_144, ge=1024)
    max_clock_skew_seconds: int = Field(default=300, ge=0)

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    alert_from: str | None = None
    alert_to: str | None = None

    agenda_hora: str = "07:30"
    agenda_dias: int = Field(default=7, ge=1, le=60)

    @field_validator("api_token")
    @classmethod
    def _token_minimo(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        if len(value.get_secret_value()) < 16:
            raise ValueError("NEXJUS_API_TOKEN precisa ter ao menos 16 caracteres")
        return value

    @field_validator("agenda_hora")
    @classmethod
    def _hora_valida(cls, value: str) -> str:
        if not _HORA.match(value):
            raise ValueError("NEXJUS_AGENDA_HORA deve estar no formato HH:MM")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def alert_recipients(self) -> list[str]:
        return [item.strip() for item in (self.alert_to or "").split(",") if item.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.alert_from and self.alert_recipients)

    def safe_database_url(self) -> str:
        """URL do banco com a senha mascarada, segura para logs."""
        return make_url(self.database_url).render_as_string(hide_password=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
