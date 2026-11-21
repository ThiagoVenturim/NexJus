"""Alertas por e-mail com a agenda diaria.

LGPD: o e-mail leva apenas contagens, datas de vencimento e o identificador interno do prazo.
Nomes, documentos, numeros de processo e o payload sincronizado nunca entram na mensagem.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage

from .config import Settings
from .schemas import AgendaItem, AgendaResponse

logger = logging.getLogger(__name__)

Sender = Callable[[EmailMessage, Settings], None]


def _linhas(titulo: str, itens: list[AgendaItem]) -> list[str]:
    if not itens:
        return []
    linhas = [f"{titulo} ({len(itens)}):"]
    for item in itens:
        linhas.append(f"  - {item.due_date.isoformat()}  prazo {item.id}  ({item.dias_restantes:+d} dias)")
    return [*linhas, ""]


def render_digest(agenda: AgendaResponse) -> tuple[str, str]:
    """Devolve (assunto, corpo) em texto simples."""
    assunto = f"NexJus: {agenda.total_criticos} prazo(s) critico(s) em {agenda.hoje.isoformat()}"
    corpo = [
        f"Agenda de prazos de {agenda.hoje.isoformat()} (proximos {agenda.dias} dias).",
        "",
        *_linhas("Vencidos", agenda.vencidos),
        *_linhas("Vencendo hoje", agenda.vencendo_hoje),
        *_linhas("Urgentes (ate 3 dias)", agenda.urgentes),
        *_linhas("Proximos", agenda.proximos),
    ]
    if len(corpo) == 2:
        corpo.append("Nenhum prazo em aberto no periodo.")
        corpo.append("")
    corpo.append("Abra a extensao NexJus para ver os detalhes. Confira sempre o prazo no sistema oficial.")
    return assunto, "\n".join(corpo) + "\n"


def build_message(agenda: AgendaResponse, settings: Settings) -> EmailMessage:
    assunto, corpo = render_digest(agenda)
    message = EmailMessage()
    message["Subject"] = assunto
    message["From"] = settings.alert_from or ""
    message["To"] = ", ".join(settings.alert_recipients)
    message.set_content(corpo)
    return message


def smtp_sender(message: EmailMessage, settings: Settings) -> None:
    if not settings.smtp_host:
        raise RuntimeError("NEXJUS_SMTP_HOST nao configurado")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


def send_daily_alert(agenda: AgendaResponse, settings: Settings, sender: Sender = smtp_sender) -> bool:
    """Envia o resumo se houver SMTP configurado e algo em aberto. Retorna True se enviou."""
    if not settings.smtp_configured:
        logger.info("SMTP nao configurado; alerta diario nao enviado (%d criticos)", agenda.total_criticos)
        return False
    if agenda.total_criticos == 0 and not agenda.proximos:
        logger.info("Nenhum prazo em aberto; alerta diario nao enviado")
        return False
    sender(build_message(agenda, settings), settings)
    logger.info("Alerta diario enviado para %d destinatario(s)", len(settings.alert_recipients))
    return True
