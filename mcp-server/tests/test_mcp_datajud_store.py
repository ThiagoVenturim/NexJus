"""DataJud (transporte simulado), privacidade e arquivo local."""

from __future__ import annotations

import json
import logging

import httpx
import pytest
from mcp_helpers import DATAJUD_KEY, NUMERO_1, Recorder, datajud_ok, datajud_payload

from nexjus_mcp import privacy
from nexjus_mcp.config import Settings
from nexjus_mcp.datajud import (
    DataJudClient,
    DataJudError,
    endpoint_por_numero,
    limpar_digitos,
    normalizar_resposta,
    validar_numero_cnj,
)
from nexjus_mcp.store import JsonStore, StoreError, importar_csv_dir, parse_csv

# ----- DataJud -------------------------------------------------------------------------------


def test_validacao_cnj_e_endpoint():
    assert validar_numero_cnj(NUMERO_1)
    digitos = limpar_digitos(NUMERO_1)
    errado = digitos[:7] + ("00" if digitos[7:9] != "00" else "01") + digitos[9:]
    assert not validar_numero_cnj(errado)
    assert not validar_numero_cnj("123")
    assert endpoint_por_numero(NUMERO_1) == "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search"
    with pytest.raises(ValueError, match="nao mapeado"):
        endpoint_por_numero("0000001-00.2026.9.99.0100")


def test_normalizacao_ordena_movimentos_e_descarta_partes():
    dados = normalizar_resposta(datajud_payload("00000011220268260100"))
    assert dados is not None
    assert [m["nome"] for m in dados["movimentos"]] == ["Peticao", "Despacho", "Distribuicao"]
    assert dados["classe"] == "Procedimento Comum Civel"
    assert "NAO DEVE APARECER" not in json.dumps(dados)
    assert normalizar_resposta({"hits": {"hits": []}}) is None
    assert normalizar_resposta({"hits": []}) is None
    assert normalizar_resposta(None) is None


def test_consulta_envia_chave_no_header_e_usa_cache():
    rec = Recorder(datajud_ok)
    client = DataJudClient(DATAJUD_KEY, transport=rec.transport)
    primeiro = client.consultar(NUMERO_1)
    segundo = client.consultar(NUMERO_1)
    assert primeiro == segundo
    assert len(rec.requests) == 1
    req = rec.requests[0]
    assert req.headers["Authorization"] == f"ApiKey {DATAJUD_KEY}"
    assert str(req.url).endswith("/api_publica_tjsp/_search")
    assert json.loads(req.content)["query"]["match"]["numeroProcesso"] == limpar_digitos(NUMERO_1)


def test_erros_do_datajud_nao_vazam_a_chave(caplog):
    caplog.set_level(logging.DEBUG)

    def falha(_req):
        return httpx.Response(401, text=f"chave {DATAJUD_KEY} recusada")

    client = DataJudClient(DATAJUD_KEY, transport=httpx.MockTransport(falha))
    with pytest.raises(DataJudError) as exc:
        client.consultar(NUMERO_1)
    assert "HTTP 401" in str(exc.value)
    assert DATAJUD_KEY not in str(exc.value)
    assert DATAJUD_KEY not in caplog.text

    def rede(_req):
        raise httpx.ConnectError(f"falhou com {DATAJUD_KEY}")

    client = DataJudClient(DATAJUD_KEY, transport=httpx.MockTransport(rede))
    with pytest.raises(DataJudError) as exc:
        client.consultar(NUMERO_1)
    assert DATAJUD_KEY not in str(exc.value)
    assert DATAJUD_KEY not in caplog.text


def test_consulta_sem_chave_ou_numero_invalido():
    with pytest.raises(DataJudError, match="NEXJUS_DATAJUD_API_KEY"):
        DataJudClient(None).consultar(NUMERO_1)
    with pytest.raises(ValueError, match="verificador"):
        DataJudClient(DATAJUD_KEY).consultar("0000001-00.2026.8.26.0100")


def test_settings_nao_exibem_segredos():
    s = Settings(_env_file=None, datajud_api_key=DATAJUD_KEY, api_token="token-de-teste-0123456789")
    assert DATAJUD_KEY not in repr(s)
    assert "token-de-teste" not in repr(s)
    assert Settings(_env_file=None, datajud_api_key="  ").datajud_api_key is None
    with pytest.raises(ValueError):
        Settings(_env_file=None, backend_url="ftp://host")


# ----- privacidade ---------------------------------------------------------------------------


def test_nome_e_placa_minimizados():
    assert privacy.nome_cliente("Maria da Silva Oliveira", "minimo") == "Maria S. O."
    assert privacy.nome_cliente("Maria da Silva Oliveira", "completo") == "Maria da Silva Oliveira"
    assert privacy.placa("BRA2E19", "minimo") == "BRA***9"
    assert privacy.placa("BRA2E19", "completo") == "BRA2E19"


def test_redacao_de_texto_livre_preserva_numero_cnj():
    texto = f"Cliente CPF 123.456.789-09, CNPJ 12.345.678/0001-90, maria@example.com, (11) 98765-4321, {NUMERO_1}"
    saida = privacy.redigir_texto(texto, "minimo")
    for dado in ("123.456.789-09", "12.345.678/0001-90", "maria@example.com", "98765-4321"):
        assert dado not in saida
    assert "[cpf]" in saida and "[cnpj]" in saida and "[e-mail]" in saida and "[telefone]" in saida
    assert NUMERO_1 in saida
    assert privacy.redigir_texto(texto, "completo") == texto


# ----- arquivo local -------------------------------------------------------------------------


def test_store_le_envelope_e_recusa_criptografado(tmp_path):
    arquivo = tmp_path / "db.json"
    arquivo.write_text(json.dumps({"encrypted": False, "database": {"clientes": [{"id": "c"}]}}), encoding="utf-8")
    db = JsonStore(arquivo).load()
    assert db["clientes"] == [{"id": "c"}]
    assert db["prazos"] == []

    arquivo.write_text(json.dumps({"encrypted": True, "payload": {"iv": "x"}}), encoding="utf-8")
    with pytest.raises(StoreError, match="criptografado"):
        JsonStore(arquivo).load()

    arquivo.write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(StoreError, match="JSON invalido"):
        JsonStore(arquivo).load()

    assert JsonStore(tmp_path / "inexistente.json").load()["processos"] == []


def test_store_grava_de_forma_atomica(tmp_path):
    store = JsonStore(tmp_path / "sub" / "db.json")
    store.update(lambda db: db["clientes"].append({"id": "c1", "nome": "Ana"}))
    assert JsonStore(store.path).load()["clientes"] == [{"id": "c1", "nome": "Ana"}]
    assert [p.name for p in store.path.parent.iterdir()] == ["db.json"]


def test_importa_csv_exportado_pela_extensao(tmp_path):
    (tmp_path / "clientes.csv").write_text(
        'id,nome,documento,telefone,email,uf,municipio,criadoEm\ncli-1,"Silva, Ana",1,2,3,SP,Sao Paulo,2026-01-01\n',
        encoding="utf-8",
    )
    (tmp_path / "prazos.csv").write_text(
        "id,processoId,titulo,regra,dataPublicacaoOuNotificacao,diasPrazo,contagem,uf,municipio,"
        "dataInicioContagem,dataVencimento,concluido,criadoEm\n"
        ",proc-1,'=Replica,cpc_15,2026-03-06,15,uteis,SP,,2026-03-09,2026-03-27,true,2026-03-06\n",
        encoding="utf-8",
    )
    db = importar_csv_dir(tmp_path)
    assert db["clientes"][0]["nome"] == "Silva, Ana"
    prazo = db["prazos"][0]
    assert prazo["id"].startswith("prz-")
    assert prazo["titulo"] == "=Replica"
    assert prazo["diasPrazo"] == 15 and prazo["concluido"] is True
    assert "municipio" not in prazo
    assert db["processos"] == []
    assert parse_csv("id\n") == []
