"""Conferencia de minutas: dados pessoais, pendencias, fontes e aviso."""

from __future__ import annotations

from nexjus_skills.cli import main
from nexjus_skills.guardrails import AVISO_MINUTA, conferir_texto, dados_pessoais

MINUTA_OK = f"""Ao Senhor Presidente da JARI
Processo n. 0000001-45.2026.8.26.0100

Do direito: falta de notificacao no prazo (CTB art. 281, par. unico, II; STJ, Sumula 312).

## Fontes
- CTB art. 281, texto fornecido pelo advogado.
- STJ, Sumula 312, fornecida pelo advogado.

{AVISO_MINUTA}
"""


def test_minuta_completa_passa():
    assert conferir_texto(MINUTA_OK) == []


def test_aviso_com_quebra_de_linha_e_aceito():
    texto = MINUTA_OK.replace("para revisao do advogado", "para revisao\ndo advogado")
    assert conferir_texto(texto) == []


def test_dados_pessoais_sao_apontados_e_cnj_nao():
    texto = "Cliente CPF 123.456.789-09, e-mail maria@example.com, tel (11) 98765-4321, CNPJ 12.345.678/0001-90."
    tipos = {a.detalhe.split()[0] for a in dados_pessoais(texto)}
    assert tipos == {"cpf", "e-mail", "telefone", "cnpj"}
    assert dados_pessoais("Processo 0000001-45.2026.8.26.0100 e 00000014520268260100") == []
    # o achado nunca repete o dado
    assert all("123.456" not in str(a) for a in dados_pessoais(texto))


def test_pendencias_citacao_sem_fonte_e_aviso_ausente():
    texto = "Conforme REsp 1.234.567, o auto e nulo.\nData: [CONFERIR: data da notificacao]\n"
    achados = conferir_texto(texto)
    tipos = [a.tipo for a in achados]
    assert tipos == ["pendencia", "citacao sem fonte", "aviso ausente"]
    assert achados[0].linha == 2
    assert "data da notificacao" in achados[0].detalhe
    assert [a.tipo for a in conferir_texto(texto, minuta=False)] == ["pendencia", "citacao sem fonte"]


def test_cli_check(tmp_path, capsys):
    ok = tmp_path / "ok.md"
    ok.write_text(MINUTA_OK, encoding="utf-8")
    ruim = tmp_path / "ruim.md"
    ruim.write_text("CPF 123.456.789-09\n", encoding="utf-8")
    assert main(["check", str(ok)]) == 0
    assert "nada a apontar" in capsys.readouterr().out
    assert main(["check", str(ruim)]) == 1
    saida = capsys.readouterr().out
    assert "dado pessoal" in saida and "123.456" not in saida
    assert main(["check", "--not-draft", str(tmp_path / "nao-existe.md")]) == 2
