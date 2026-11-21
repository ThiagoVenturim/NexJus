"""Arquivo local de dados do servidor MCP.

O formato e o mesmo `NexJusDatabase` da extensao (extension/src/types/models.ts): um JSON com
`clientes`, `veiculos`, `processos`, `prazos` e `feriadosLocais`. Tambem aceita o envelope sem
criptografia gravado pela extensao (`{"encrypted": false, "database": {...}}`).

O arquivo pode ser montado a partir dos CSV exportados pela extensao (`nexjus-mcp import-csv`).
A gravacao e atomica (arquivo temporario + rename) para nao corromper os dados.
"""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

COLECOES = ("clientes", "veiculos", "processos", "prazos", "feriadosLocais")
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class StoreError(RuntimeError):
    """Problema ao ler ou gravar o arquivo local. A mensagem nao inclui conteudo de registros."""


def banco_vazio() -> dict[str, list]:
    return {nome: [] for nome in COLECOES}


def _normalizar(raw: Any) -> dict[str, list]:
    if not isinstance(raw, dict):
        raise StoreError("Arquivo de dados invalido: esperado um objeto JSON.")
    if "encrypted" in raw:
        if raw.get("encrypted"):
            raise StoreError(
                "O arquivo esta criptografado pela extensao. Exporte os dados sem criptografia "
                "ou use os CSV exportados com 'nexjus-mcp import-csv'."
            )
        raw = raw.get("database") or {}
        if not isinstance(raw, dict):
            raise StoreError("Arquivo de dados invalido: campo 'database' nao e um objeto.")
    db = banco_vazio()
    for nome in COLECOES:
        itens = raw.get(nome) or []
        if not isinstance(itens, list):
            raise StoreError(f"Arquivo de dados invalido: '{nome}' deve ser uma lista.")
        db[nome] = [item for item in itens if isinstance(item, dict)]
    return db


class JsonStore:
    """Leitura e gravacao do arquivo JSON local, com trava para chamadas concorrentes."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def load(self) -> dict[str, list]:
        if not self.path.exists():
            return banco_vazio()
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StoreError(f"Nao foi possivel ler o arquivo de dados ({type(exc).__name__}).") from None
        if not text.strip():
            return banco_vazio()
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StoreError(f"Arquivo de dados com JSON invalido (linha {exc.lineno}).") from None
        return _normalizar(raw)

    def save(self, db: dict[str, list]) -> None:
        data = {nome: db.get(nome, []) for nome in COLECOES}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".nexjus-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp, self.path)
        except OSError as exc:
            Path(tmp).unlink(missing_ok=True)
            raise StoreError(f"Nao foi possivel gravar o arquivo de dados ({type(exc).__name__}).") from None

    def update(self, mutate) -> Any:
        """Le, aplica `mutate(db)` e grava. Devolve o retorno de `mutate`."""
        with self._lock:
            db = self.load()
            result = mutate(db)
            self.save(db)
            return result


def _desfazer_protecao_formula(value: str) -> str:
    if value.startswith("'") and value[1:].startswith(_FORMULA_PREFIXES):
        return value[1:]
    return value


def parse_csv(text: str) -> list[dict[str, str]]:
    """Le um CSV exportado pela extensao (RFC 4180, com protecao contra formulas)."""
    reader = csv.reader(io.StringIO(text.replace("\r\n", "\n").replace("\r", "\n")))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        return []
    headers = [h.strip() for h in rows[0]]
    out = []
    for row in rows[1:]:
        item = {}
        for idx, header in enumerate(headers):
            value = row[idx].strip() if idx < len(row) else ""
            item[header] = _desfazer_protecao_formula(value)
        out.append(item)
    return out


def _converter_prazo(row: dict[str, str]) -> dict:
    item: dict[str, Any] = dict(row)
    try:
        item["diasPrazo"] = int(row.get("diasPrazo") or 0) or 15
    except ValueError:
        item["diasPrazo"] = 15
    item["concluido"] = row.get("concluido") in ("true", "1")
    item["contagem"] = "corridos" if row.get("contagem") == "corridos" else "uteis"
    if not row.get("municipio"):
        item.pop("municipio", None)
    return item


def importar_csv_dir(directory: str | os.PathLike[str]) -> dict[str, list]:
    """Monta o banco a partir de clientes.csv, veiculos.csv, processos.csv e prazos.csv."""
    base = Path(directory)
    db = banco_vazio()
    for nome in ("clientes", "veiculos", "processos", "prazos"):
        arquivo = base / f"{nome}.csv"
        if not arquivo.exists():
            continue
        linhas = parse_csv(arquivo.read_text(encoding="utf-8-sig"))
        if nome == "prazos":
            linhas = [_converter_prazo(row) for row in linhas]
        if nome == "processos":
            for row in linhas:
                if not row.get("veiculoId"):
                    row.pop("veiculoId", None)
        prefixo = {"clientes": "cli", "veiculos": "vei", "processos": "proc", "prazos": "prz"}[nome]
        for row in linhas:
            if not row.get("id"):
                row["id"] = f"{prefixo}-{uuid.uuid4().hex[:12]}"
        db[nome] = linhas
    return db
