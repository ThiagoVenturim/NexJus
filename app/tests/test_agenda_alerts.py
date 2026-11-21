from __future__ import annotations

from datetime import date

import pytest

from conftest import make_settings, ts
from nexjus_backend.agenda import classificar
from nexjus_backend.alerts import render_digest, send_daily_alert
from nexjus_backend.schemas import AgendaResponse

HOJE = date(2026, 11, 20)


def prazo(id, due, done=False, **extra):
    return {
        "entity": "prazos",
        "id": id,
        "updated_at": ts(5),
        "payload": "Cliente Fulano de Tal, processo 0000000-00.0000.0.00.0000",
        "due_date": due,
        "done": done,
        **extra,
    }


@pytest.mark.parametrize(
    ("due", "status", "dias"),
    [
        (date(2026, 11, 19), "vencido", -1),
        (date(2026, 11, 20), "hoje", 0),
        (date(2026, 11, 23), "urgente", 3),
        (date(2026, 11, 24), "no_prazo", 4),
    ],
)
def test_classificar_matches_extension_rule(due, status, dias):
    assert classificar(due, HOJE) == (status, dias)


@pytest.fixture
def seeded(client):
    changes = [
        prazo("vencido", "2026-11-18"),
        prazo("hoje", "2026-11-20"),
        prazo("urgente", "2026-11-22"),
        prazo("proximo", "2026-11-26"),
        prazo("longe", "2027-02-01"),
        prazo("feito", "2026-11-19", done=True),
        prazo("sem-data", None),
        prazo("apagado", "2026-11-20", deleted=True),
    ]
    assert client.post("/sync/push", json={"device_id": "m", "changes": changes}).status_code == 200
    return client


def test_agenda_endpoint(seeded):
    body = seeded.get("/agenda", params={"hoje": "2026-11-20", "dias": 7}).json()
    assert [i["id"] for i in body["vencidos"]] == ["vencido"]
    assert [i["id"] for i in body["vencendo_hoje"]] == ["hoje"]
    assert [i["id"] for i in body["urgentes"]] == ["urgente"]
    assert [i["id"] for i in body["proximos"]] == ["proximo"]
    assert body["total_criticos"] == 3
    assert "Fulano" not in str(body)


def _agenda(seeded) -> AgendaResponse:
    return AgendaResponse.model_validate(seeded.get("/agenda", params={"hoje": "2026-11-20"}).json())


def test_digest_has_no_personal_data(seeded):
    assunto, corpo = render_digest(_agenda(seeded))
    assert "3 prazo(s) critico(s)" in assunto
    assert "prazo vencido" in corpo and "2026-11-18" in corpo
    assert "Fulano" not in corpo and "0000000-00" not in corpo


def test_send_daily_alert_uses_sender_offline(seeded):
    settings = make_settings(
        smtp_host="smtp.exemplo.invalid",
        alert_from="nexjus@exemplo.invalid",
        alert_to="a@exemplo.invalid, b@exemplo.invalid",
    )
    sent = []
    assert send_daily_alert(_agenda(seeded), settings, sender=lambda msg, _s: sent.append(msg)) is True
    assert sent[0]["To"] == "a@exemplo.invalid, b@exemplo.invalid"
    assert "Fulano" not in sent[0].get_content()


def test_send_daily_alert_skips_without_smtp(seeded):
    sent = []
    assert send_daily_alert(_agenda(seeded), make_settings(), sender=lambda m, s: sent.append(m)) is False
    assert sent == []


def test_send_daily_alert_skips_empty_agenda():
    empty = AgendaResponse(hoje=HOJE, dias=7, vencidos=[], vencendo_hoje=[], urgentes=[], proximos=[], total_criticos=0)
    settings = make_settings(
        smtp_host="smtp.exemplo.invalid", alert_from="x@exemplo.invalid", alert_to="y@exemplo.invalid"
    )
    assert send_daily_alert(empty, settings, sender=lambda m, s: pytest.fail("nao deveria enviar")) is False
    assert "Nenhum prazo em aberto" in render_digest(empty)[1]
