"""Motor de prazos: mesmos casos de extension/tests/prazos.test.ts, mais a trilha de auditoria."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from nexjus_mcp.prazos import (
    FeriadoLocal,
    calcular_pascoa,
    calcular_prazo,
    classificar_status,
    is_feriado,
    is_recesso_forense_cpc,
    parse_iso_date,
)


def test_pascoa_e_feriados_moveis_2026():
    assert calcular_pascoa(2026) == date(2026, 4, 5)
    for iso in ("2026-02-16", "2026-02-17", "2026-04-03", "2026-06-04"):
        assert is_feriado(parse_iso_date(iso), "SP")


def test_feriados_estaduais_e_locais():
    assert is_feriado(date(2026, 7, 9), "SP")
    assert not is_feriado(date(2026, 7, 9), "RJ")
    assert is_feriado(date(2026, 4, 23), "RJ")
    locais = [FeriadoLocal(data="01-25", nome="Aniversario de Sao Paulo", uf="SP", municipio="Sao Paulo")]
    assert is_feriado(date(2026, 1, 25), "SP", "Sao Paulo", locais)
    assert not is_feriado(date(2026, 1, 25), "SP", "Campinas", locais)


def test_cpc_5_e_15_dias_uteis():
    r5 = calcular_prazo(regra="cpc_5", data_publicacao_ou_notificacao="2026-03-06", uf="SP")
    assert (r5.data_inicio_contagem, r5.data_vencimento) == ("2026-03-09", "2026-03-13")
    r15 = calcular_prazo(regra="cpc_15", data_publicacao_ou_notificacao="2026-03-06", uf="SP")
    assert (r15.data_inicio_contagem, r15.data_vencimento) == ("2026-03-09", "2026-03-27")
    assert r15.contagem == "uteis"
    assert r15.considera_recesso_cpc is True


def test_recesso_forense_suspende_cpc():
    assert not is_recesso_forense_cpc(date(2026, 12, 19))
    assert is_recesso_forense_cpc(date(2026, 12, 20))
    assert is_recesso_forense_cpc(date(2027, 1, 20))
    assert not is_recesso_forense_cpc(date(2027, 1, 21))
    r = calcular_prazo(regra="cpc_5", data_publicacao_ou_notificacao="2026-12-18", uf="SP")
    assert r.data_inicio_contagem == "2027-01-21"
    assert r.data_vencimento == "2027-01-27"
    motivos = {d["data"]: d["motivo"] for d in r.dias_pulados}
    assert motivos["2026-12-19"] == "sabado"
    assert motivos["2026-12-21"] == "recesso forense (CPC art. 220)"
    assert motivos["2027-01-23"] == "sabado"
    assert all(d["fase"] in ("inicio", "contagem") for d in r.dias_pulados)


def test_ctb_30_dias_corridos_com_prorrogacao():
    defesa = calcular_prazo(regra="ctb_defesa_previa", data_publicacao_ou_notificacao="2026-03-02", uf="SP")
    assert (defesa.contagem, defesa.dias_prazo) == ("corridos", 30)
    assert (defesa.data_inicio_contagem, defesa.data_vencimento) == ("2026-03-03", "2026-04-01")
    assert defesa.prorrogado is False

    jari = calcular_prazo(regra="ctb_jari", data_publicacao_ou_notificacao="2026-03-04", uf="SP")
    assert (jari.data_inicio_contagem, jari.data_vencimento) == ("2026-03-05", "2026-04-06")
    assert jari.prorrogado is True
    assert [d["data"] for d in jari.dias_pulados] == ["2026-04-03", "2026-04-04", "2026-04-05"]
    assert jari.dias_pulados[0]["motivo"] == "feriado movel: Sexta-feira da Paixao"
    assert {d["fase"] for d in jari.dias_pulados} == {"prorrogacao"}


def test_ctb_nao_aplica_recesso_cpc():
    r = calcular_prazo(regra="ctb_cetran", data_publicacao_ou_notificacao="2026-12-21", uf="SP")
    assert r.data_inicio_contagem == "2026-12-22"
    assert r.considera_recesso_cpc is False


def test_feriado_local_entra_na_contagem():
    locais = [FeriadoLocal(data="2026-03-10", nome="Feriado municipal", uf="SP", municipio="Sao Paulo")]
    sem = calcular_prazo(regra="cpc_5", data_publicacao_ou_notificacao="2026-03-06", uf="SP")
    com = calcular_prazo(
        regra="cpc_5", data_publicacao_ou_notificacao="2026-03-06", uf="SP", municipio="Sao Paulo", feriados_locais=locais
    )
    assert sem.data_vencimento == "2026-03-13"
    assert com.data_vencimento == "2026-03-16"
    assert {"data": "2026-03-10", "motivo": "feriado local: Feriado municipal", "fase": "contagem"} in com.dias_pulados


def test_auditoria_e_consistente_com_o_resultado():
    """Para cada prazo em dias uteis, dias do intervalo = dias uteis contados + dias pulados na contagem."""
    for dia in range(1, 29):
        r = calcular_prazo(regra="cpc_15", data_publicacao_ou_notificacao=f"2026-02-{dia:02d}", uf="SP")
        inicio = parse_iso_date(r.data_inicio_contagem)
        fim = parse_iso_date(r.data_vencimento)
        pulados_contagem = [d for d in r.dias_pulados if d["fase"] == "contagem"]
        assert (fim - inicio).days + 1 == r.dias_prazo + len(pulados_contagem)
        assert parse_iso_date(r.data_publicacao_ou_notificacao) + timedelta(days=1) <= inicio


@pytest.mark.parametrize(
    "kwargs, mensagem",
    [
        ({"regra": "cpc_99", "data_publicacao_ou_notificacao": "2026-03-06", "uf": "SP"}, "Regra"),
        ({"regra": "cpc_5", "data_publicacao_ou_notificacao": "2026-02-30", "uf": "SP"}, "inexistente"),
        ({"regra": "cpc_5", "data_publicacao_ou_notificacao": "06/03/2026", "uf": "SP"}, "YYYY-MM-DD"),
        ({"regra": "cpc_5", "data_publicacao_ou_notificacao": "2026-03-06", "uf": "XX"}, "UF"),
        ({"regra": "cpc_custom", "data_publicacao_ou_notificacao": "2026-03-06", "uf": "SP", "dias_prazo": 0}, "inteiro"),
    ],
)
def test_entradas_invalidas(kwargs, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        calcular_prazo(**kwargs)


def test_classificacao_igual_a_extensao():
    hoje = date(2026, 3, 12)
    assert classificar_status(date(2026, 3, 10), hoje)[0] == "vencido"
    assert classificar_status(date(2026, 3, 12), hoje) == ("hoje", 0)
    assert classificar_status(date(2026, 3, 14), hoje)[0] == "urgente"
    assert classificar_status(date(2026, 3, 15), hoje)[0] == "urgente"
    assert classificar_status(date(2026, 3, 16), hoje)[0] == "no_prazo"
    assert classificar_status(date(2026, 3, 10), hoje, concluido=True)[0] == "concluido"


def test_classificacao_igual_ao_backend():
    agenda = pytest.importorskip("nexjus_backend.agenda")
    hoje = date(2026, 3, 12)
    for delta in range(-10, 15):
        venc = hoje + timedelta(days=delta)
        assert classificar_status(venc, hoje) == agenda.classificar(venc, hoje)
