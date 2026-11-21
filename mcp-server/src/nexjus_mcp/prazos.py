"""Motor de prazos CPC e CTB, porte fiel de extension/src/domain/prazos.ts.

Regras (as mesmas da extensao):
- exclui o dia do comeco e inclui o do vencimento (CPC art. 224);
- o dia 1 da contagem e o primeiro dia util seguinte a publicacao ou notificacao;
- CPC conta apenas dias uteis forenses (art. 219) e suspende de 20/12 a 20/01 (art. 220);
- CTB (defesa previa, JARI, CETRAN) conta 30 dias corridos e prorroga o termo final que cair em dia nao util.

Cada calculo devolve uma trilha de auditoria com os dias pulados e o motivo, para que o advogado
possa conferir o resultado dia a dia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

RegraPrazo = Literal["cpc_5", "cpc_15", "cpc_custom", "ctb_defesa_previa", "ctb_jari", "ctb_cetran"]
TipoContagem = Literal["uteis", "corridos"]
StatusPrazo = Literal["concluido", "vencido", "hoje", "urgente", "no_prazo"]

REGRAS: tuple[str, ...] = ("cpc_5", "cpc_15", "cpc_custom", "ctb_defesa_previa", "ctb_jari", "ctb_cetran")
UFS: tuple[str, ...] = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)  # fmt: skip
DIAS_URGENTE = 3
MAX_DIAS_PRAZO = 3650

FERIADOS_NACIONAIS_FIXOS: dict[str, str] = {
    "01-01": "Confraternizacao Universal",
    "04-21": "Tiradentes",
    "05-01": "Dia do Trabalhador",
    "09-07": "Independencia do Brasil",
    "10-12": "Nossa Senhora Aparecida",
    "11-02": "Finados",
    "11-15": "Proclamacao da Republica",
    "11-20": "Dia Nacional de Zumbi e da Consciencia Negra",
    "12-25": "Natal",
}

FERIADOS_ESTADUAIS_POR_UF: dict[str, dict[str, str]] = {
    "AC": {
        "01-23": "Dia do Evangelico",
        "06-15": "Aniversario do Acre",
        "09-05": "Dia da Amazonia",
        "11-17": "Tratado de Petropolis",
    },
    "AL": {"06-24": "Sao Joao", "06-29": "Sao Pedro", "09-16": "Emancipacao Politica de Alagoas"},
    "AP": {"03-19": "Dia de Sao Jose", "09-13": "Criacao do Territorio Federal"},
    "AM": {"09-05": "Elevacao do Amazonas a Categoria de Provincia", "12-08": "Nossa Senhora da Conceicao"},
    "BA": {"07-02": "Independencia da Bahia"},
    "CE": {"03-19": "Sao Jose", "03-25": "Data Magna do Ceara"},
    "DF": {"11-30": "Dia do Evangelico"},
    "ES": {"05-23": "Colonizacao do Solo Espirito-Santense"},
    "GO": {"10-24": "Pedra Fundamental de Goiania"},
    "MA": {"07-28": "Adesao do Maranhao a Independencia"},
    "MT": {"11-20": "Consciencia Negra"},
    "MS": {"10-11": "Criacao do Estado de Mato Grosso do Sul"},
    "MG": {"04-21": "Data Magna de Minas Gerais"},
    "PA": {"08-15": "Adesao do Grao-Para a Independencia"},
    "PB": {"08-05": "Fundacao do Estado da Paraiba"},
    "PR": {"12-19": "Emancipacao Politica do Parana"},
    "PE": {"03-06": "Data Magna de Pernambuco", "06-24": "Sao Joao"},
    "PI": {"10-19": "Dia do Piaui"},
    "RJ": {"04-23": "Dia de Sao Jorge"},
    "RN": {"10-03": "Martires de Cunhau e Uruacu"},
    "RS": {"09-20": "Revolucao Farroupilha"},
    "RO": {"01-04": "Instalacao do Estado de Rondonia", "06-18": "Dia do Evangelico"},
    "RR": {"10-05": "Criacao do Estado de Roraima"},
    "SC": {"08-11": "Criacao da Capitania de Santa Catarina"},
    "SP": {"07-09": "Revolucao Constitucionalista de 1932"},
    "SE": {"07-08": "Emancipacao Politica de Sergipe"},
    "TO": {"10-05": "Criacao do Estado do Tocantins"},
}


@dataclass(frozen=True)
class FeriadoLocal:
    data: str  # YYYY-MM-DD ou MM-DD
    nome: str
    uf: str
    municipio: str | None = None


def parse_iso_date(value: str) -> date:
    """Aceita somente YYYY-MM-DD e recusa datas inexistentes."""
    text = (value or "").strip()
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValueError(f"Data invalida (esperado YYYY-MM-DD): {value}")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Data inexistente no calendario: {value}") from exc


def validar_uf(uf: str) -> str:
    sigla = (uf or "").strip().upper()
    if sigla not in UFS:
        raise ValueError(f"UF invalida: {uf}")
    return sigla


def calcular_pascoa(year: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def feriados_moveis(year: int) -> dict[str, str]:
    pascoa = calcular_pascoa(year)
    return {
        (pascoa - timedelta(days=48)).isoformat(): "Segunda-feira de Carnaval",
        (pascoa - timedelta(days=47)).isoformat(): "Terca-feira de Carnaval",
        (pascoa - timedelta(days=2)).isoformat(): "Sexta-feira da Paixao",
        (pascoa + timedelta(days=60)).isoformat(): "Corpus Christi",
    }


def is_recesso_forense_cpc(value: date) -> bool:
    return (value.month == 12 and value.day >= 20) or (value.month == 1 and value.day <= 20)


def is_fim_de_semana(value: date) -> bool:
    return value.weekday() >= 5


def _normalizar_municipio(value: str | None) -> str:
    return (value or "").strip().lower()


def nome_feriado(
    value: date, uf: str, municipio: str | None = None, feriados_locais: list[FeriadoLocal] | None = None
) -> str | None:
    """Nome do feriado que cai em `value`, ou None. Mesma ordem de verificacao da extensao."""
    iso = value.isoformat()
    mmdd = iso[5:]
    if mmdd in FERIADOS_NACIONAIS_FIXOS:
        return f"feriado nacional: {FERIADOS_NACIONAIS_FIXOS[mmdd]}"
    moveis = feriados_moveis(value.year)
    if iso in moveis:
        return f"feriado movel: {moveis[iso]}"
    estaduais = FERIADOS_ESTADUAIS_POR_UF.get(uf, {})
    if mmdd in estaduais:
        return f"feriado estadual ({uf}): {estaduais[mmdd]}"
    alvo = _normalizar_municipio(municipio)
    for fl in feriados_locais or []:
        if fl.uf != uf:
            continue
        fl_muni = _normalizar_municipio(fl.municipio)
        if fl_muni and fl_muni != alvo:
            continue
        if fl.data in (iso, mmdd):
            return f"feriado local: {fl.nome}"
    return None


def is_feriado(
    value: date, uf: str, municipio: str | None = None, feriados_locais: list[FeriadoLocal] | None = None
) -> bool:
    return nome_feriado(value, uf, municipio, feriados_locais) is not None


def motivo_nao_util(
    value: date,
    uf: str,
    municipio: str | None,
    feriados_locais: list[FeriadoLocal],
    considera_recesso_cpc: bool,
) -> str | None:
    """Motivo pelo qual o dia nao e util forense, ou None se for dia util."""
    if is_fim_de_semana(value):
        return "sabado" if value.weekday() == 5 else "domingo"
    if considera_recesso_cpc and is_recesso_forense_cpc(value):
        return "recesso forense (CPC art. 220)"
    return nome_feriado(value, uf, municipio, feriados_locais)


def parametros_padrao(regra: str) -> tuple[int, TipoContagem, bool]:
    """(dias, contagem, considera recesso CPC) de cada regra."""
    tabela: dict[str, tuple[int, TipoContagem, bool]] = {
        "cpc_5": (5, "uteis", True),
        "cpc_15": (15, "uteis", True),
        "cpc_custom": (10, "uteis", True),
        "ctb_defesa_previa": (30, "corridos", False),
        "ctb_jari": (30, "corridos", False),
        "ctb_cetran": (30, "corridos", False),
    }
    if regra not in tabela:
        raise ValueError(f"Regra de prazo desconhecida: {regra}. Use uma de: {', '.join(REGRAS)}")
    return tabela[regra]


FUNDAMENTO: dict[str, str] = {
    "cpc_5": "CPC arts. 219, 220 e 224: 5 dias uteis",
    "cpc_15": "CPC arts. 219, 220 e 224: 15 dias uteis",
    "cpc_custom": "CPC arts. 219, 220 e 224: prazo em dias uteis informado",
    "ctb_defesa_previa": "CTB: defesa previa, 30 dias corridos com prorrogacao para dia util",
    "ctb_jari": "CTB: recurso a JARI, 30 dias corridos com prorrogacao para dia util",
    "ctb_cetran": "CTB: recurso ao CETRAN, 30 dias corridos com prorrogacao para dia util",
}


@dataclass
class ResultadoPrazo:
    regra: str
    dias_prazo: int
    contagem: TipoContagem
    considera_recesso_cpc: bool
    data_publicacao_ou_notificacao: str
    data_inicio_contagem: str
    data_vencimento: str
    uf: str
    municipio: str | None
    fundamento: str
    dias_pulados: list[dict[str, str]] = field(default_factory=list)
    prorrogado: bool = False

    def to_dict(self) -> dict:
        return {
            "regra": self.regra,
            "dias_prazo": self.dias_prazo,
            "contagem": self.contagem,
            "considera_recesso_cpc": self.considera_recesso_cpc,
            "data_publicacao_ou_notificacao": self.data_publicacao_ou_notificacao,
            "data_inicio_contagem": self.data_inicio_contagem,
            "data_vencimento": self.data_vencimento,
            "uf": self.uf,
            "municipio": self.municipio,
            "fundamento": self.fundamento,
            "prorrogado": self.prorrogado,
            "dias_pulados": self.dias_pulados,
            "aviso": "Confira o prazo no sistema oficial do tribunal ou do orgao autuador.",
        }


def calcular_prazo(
    *,
    regra: str,
    data_publicacao_ou_notificacao: str,
    uf: str,
    dias_prazo: int | None = None,
    contagem: TipoContagem | None = None,
    municipio: str | None = None,
    feriados_locais: list[FeriadoLocal] | None = None,
) -> ResultadoPrazo:
    padrao_dias, padrao_contagem, considera_recesso = parametros_padrao(regra)
    dias = padrao_dias if dias_prazo is None else dias_prazo
    if isinstance(dias, bool) or not isinstance(dias, int) or dias <= 0:
        raise ValueError("A quantidade de dias do prazo deve ser um inteiro positivo.")
    if dias > MAX_DIAS_PRAZO:
        raise ValueError(f"A quantidade de dias do prazo deve ser no maximo {MAX_DIAS_PRAZO}.")
    tipo = contagem or padrao_contagem
    if tipo not in ("uteis", "corridos"):
        raise ValueError("Contagem deve ser 'uteis' ou 'corridos'.")
    sigla = validar_uf(uf)
    locais = feriados_locais or []
    base = parse_iso_date(data_publicacao_ou_notificacao)
    pulados: list[dict[str, str]] = []

    def nao_util(value: date) -> str | None:
        return motivo_nao_util(value, sigla, municipio, locais, considera_recesso)

    cursor = base + timedelta(days=1)
    while (motivo := nao_util(cursor)) is not None:
        pulados.append({"data": cursor.isoformat(), "motivo": motivo, "fase": "inicio"})
        cursor += timedelta(days=1)
    inicio = cursor.isoformat()
    prorrogado = False

    if tipo == "uteis":
        restantes = dias - 1
        while restantes > 0:
            cursor += timedelta(days=1)
            motivo = nao_util(cursor)
            if motivo is None:
                restantes -= 1
            else:
                pulados.append({"data": cursor.isoformat(), "motivo": motivo, "fase": "contagem"})
    else:
        cursor += timedelta(days=dias - 1)
        while (motivo := nao_util(cursor)) is not None:
            pulados.append({"data": cursor.isoformat(), "motivo": motivo, "fase": "prorrogacao"})
            prorrogado = True
            cursor += timedelta(days=1)

    return ResultadoPrazo(
        regra=regra,
        dias_prazo=dias,
        contagem=tipo,
        considera_recesso_cpc=considera_recesso,
        data_publicacao_ou_notificacao=base.isoformat(),
        data_inicio_contagem=inicio,
        data_vencimento=cursor.isoformat(),
        uf=sigla,
        municipio=municipio,
        fundamento=FUNDAMENTO[regra],
        dias_pulados=pulados,
        prorrogado=prorrogado,
    )


def classificar_status(data_vencimento: date, hoje: date, concluido: bool = False) -> tuple[StatusPrazo, int]:
    """Mesma regra de classificarStatusPrazo (extensao) e de nexjus_backend.agenda.classificar."""
    dias = (data_vencimento - hoje).days
    if concluido:
        return "concluido", dias
    if dias < 0:
        return "vencido", dias
    if dias == 0:
        return "hoje", 0
    if dias <= DIAS_URGENTE:
        return "urgente", dias
    return "no_prazo", dias
