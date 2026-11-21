"""Minimizacao de dados pessoais (LGPD) nas respostas do servidor MCP.

O cliente MCP (por exemplo um assistente de IA) recebe somente o necessario para o trabalho:
- documento (CPF/CNPJ), telefone, e-mail e RENAVAM nunca saem do servidor;
- no modo "minimo" (padrao) o nome do cliente vira primeiro nome + iniciais, a placa fica mascarada
  e CPF, CNPJ, e-mail e telefone em textos livres sao substituidos por marcadores;
- no modo "completo" o nome e a placa saem inteiros, mas os campos acima continuam fora.
"""

from __future__ import annotations

import re

_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TELEFONE = re.compile(r"(?<!\d)(?:\(?\d{2}\)?\s?)?9?\d{4}-?\d{4}(?!\d)")
_CNJ = re.compile(r"\b\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}\b")


def nome_cliente(nome: str | None, modo: str) -> str:
    texto = " ".join((nome or "").split())
    if not texto:
        return ""
    if modo == "completo":
        return texto
    partes = texto.split(" ")
    iniciais = [f"{p[0].upper()}." for p in partes[1:] if p and p.lower() not in ("da", "de", "do", "das", "dos", "e")]
    return " ".join([partes[0], *iniciais])


def placa(valor: str | None, modo: str) -> str:
    texto = (valor or "").strip().upper()
    if not texto or modo == "completo":
        return texto
    if len(texto) <= 3:
        return "*" * len(texto)
    return texto[:3] + "*" * (len(texto) - 4) + texto[-1]


def redigir_texto(texto: str | None, modo: str) -> str:
    """Troca CPF, CNPJ, e-mail e telefone por marcadores. Numeros de processo CNJ sao preservados."""
    valor = texto or ""
    if modo == "completo" or not valor:
        return valor
    protegidos: list[str] = []

    def _guardar(match: re.Match[str]) -> str:
        protegidos.append(match.group(0))
        return f"\x00{len(protegidos) - 1}\x00"

    valor = _CNJ.sub(_guardar, valor)
    valor = _EMAIL.sub("[e-mail]", valor)
    valor = _CNPJ.sub("[cnpj]", valor)
    valor = _CPF.sub("[cpf]", valor)
    valor = _TELEFONE.sub("[telefone]", valor)
    return re.sub(r"\x00(\d+)\x00", lambda m: protegidos[int(m.group(1))], valor)
