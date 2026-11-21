"""Conferencia automatica de textos gerados pelas skills (minutas, relatorios, resumos).

Nao avalia o merito juridico. Aponta o que o advogado precisa resolver antes de usar o texto:
dados pessoais que nao deveriam estar ali, marcadores [CONFERIR] pendentes, citacoes de
jurisprudencia sem secao de fontes e minutas sem o aviso de revisao.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

AVISO_MINUTA = (
    "Rascunho gerado com apoio de IA para revisao do advogado responsavel. "
    "Conferir prazos, fatos e citacoes nos sistemas oficiais antes de usar."
)
"""Aviso que toda minuta deve trazer no final, literalmente."""

MARCADOR_CONFERIR = "[CONFERIR"
"""Prefixo dos marcadores de pendencia, por exemplo `[CONFERIR: data da notificacao]`."""

SECAO_FONTES = re.compile(r"^#{1,6}\s*fontes\b", re.IGNORECASE | re.MULTILINE)

_CNJ = re.compile(r"\b\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}\b")
_PADROES_PESSOAIS: dict[str, re.Pattern[str]] = {
    "e-mail": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "cnpj": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b"),
    "cpf": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b"),
    "telefone": re.compile(r"\(\d{2}\)\s?9?\d{4}-?\d{4}\b|\b\d{2}\s9\d{4}-\d{4}\b"),
}
_CITACAO_JURISPRUDENCIA = re.compile(
    r"\b(REsp|AREsp|AgInt|AgRg|EREsp|RE|ARE|HC|RHC|MS|ADI|ADPF|Apela[cç][aã]o|S[uú]mula|Tema)\s*(n[.o]?\s*)?\d",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Achado:
    tipo: str
    detalhe: str
    linha: int

    def __str__(self) -> str:
        return f"linha {self.linha}: {self.tipo}: {self.detalhe}"


def _linha(texto: str, posicao: int) -> int:
    return texto.count("\n", 0, posicao) + 1


def dados_pessoais(texto: str) -> list[Achado]:
    """CPF, CNPJ, e-mail e telefone encontrados no texto. Numeros de processo CNJ sao ignorados."""
    sem_cnj = _CNJ.sub(lambda m: "#" * len(m.group(0)), texto)
    achados: list[Achado] = []
    ocupado: list[tuple[int, int]] = []
    for tipo, padrao in _PADROES_PESSOAIS.items():
        for m in padrao.finditer(sem_cnj):
            if any(a <= m.start() < b for a, b in ocupado):
                continue
            ocupado.append((m.start(), m.end()))
            achados.append(Achado("dado pessoal", f"{tipo} visivel no texto", _linha(texto, m.start())))
    return sorted(achados, key=lambda a: a.linha)


def conferir_texto(texto: str, *, minuta: bool = True) -> list[Achado]:
    """Lista o que impede o uso direto do texto. Lista vazia significa nada a apontar.

    Com `minuta=True` exige o AVISO_MINUTA. Citacoes de jurisprudencia exigem uma secao "Fontes".
    """
    achados = dados_pessoais(texto)
    inicio = 0
    while (pos := texto.find(MARCADOR_CONFERIR, inicio)) >= 0:
        fim = texto.find("]", pos)
        trecho = texto[pos : fim + 1 if fim >= 0 else pos + 60]
        achados.append(Achado("pendencia", trecho, _linha(texto, pos)))
        inicio = pos + len(MARCADOR_CONFERIR)
    citacao = _CITACAO_JURISPRUDENCIA.search(texto)
    if citacao and not SECAO_FONTES.search(texto):
        achados.append(
            Achado("citacao sem fonte", f"'{citacao.group(0)}' citado sem secao Fontes", _linha(texto, citacao.start()))
        )
    if minuta and " ".join(AVISO_MINUTA.split()) not in " ".join(texto.split()):
        achados.append(Achado("aviso ausente", "a minuta nao traz o aviso de revisao do advogado", 0))
    return achados
