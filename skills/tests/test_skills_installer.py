"""Instalacao e remocao das skills numa pasta temporaria (nunca no ~/.claude real)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import nexjus_skills
from nexjus_skills.catalog import load_all
from nexjus_skills.cli import main
from nexjus_skills.installer import MANIFESTO, default_target, install, uninstall

SKILL = Path("skills/deadline-checker/SKILL.md")
AGENTE = Path("agents/assistente-prazos.md")


def _arquivos(destino: Path) -> set[str]:
    return {p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file()}


def test_install_cria_layout_do_claude_code(tmp_path):
    relatorio = install(tmp_path)
    esperados = {f"skills/{i.nome}/SKILL.md" for i in load_all() if i.tipo == "skill"}
    esperados |= {f"agents/{i.nome}.md" for i in load_all() if i.tipo == "agente"}
    assert _arquivos(tmp_path) == esperados | {MANIFESTO}
    assert relatorio.contagem() == {"criado": len(esperados)}
    manifesto = json.loads((tmp_path / MANIFESTO).read_text(encoding="utf-8"))
    assert manifesto["versao"] == nexjus_skills.__version__
    assert set(manifesto["arquivos"]) == esperados
    assert b"\r\n" not in (tmp_path / SKILL).read_bytes()


def test_install_e_idempotente_e_atualiza_so_o_que_nao_foi_editado(tmp_path):
    install(tmp_path)
    assert install(tmp_path).contagem() == {"igual": len(load_all())}

    # Arquivo instalado e nao editado (hash do manifesto) com conteudo antigo: e atualizado.
    antigo = "versao antiga\n"
    (tmp_path / SKILL).write_text(antigo, encoding="utf-8")
    manifesto = json.loads((tmp_path / MANIFESTO).read_text(encoding="utf-8"))
    import hashlib

    manifesto["arquivos"][SKILL.as_posix()] = hashlib.sha256(antigo.encode()).hexdigest()
    (tmp_path / MANIFESTO).write_text(json.dumps(manifesto), encoding="utf-8")
    relatorio = install(tmp_path)
    assert ("atualizado", SKILL.as_posix()) in relatorio.acoes
    assert (tmp_path / SKILL).read_text(encoding="utf-8") != antigo


def test_install_preserva_edicao_local_sem_force(tmp_path):
    install(tmp_path)
    (tmp_path / AGENTE).write_text("minha versao\n", encoding="utf-8")
    relatorio = install(tmp_path)
    assert relatorio.conflitos == [AGENTE.as_posix()]
    assert (tmp_path / AGENTE).read_text(encoding="utf-8") == "minha versao\n"

    relatorio = install(tmp_path, force=True)
    assert ("sobrescrito", AGENTE.as_posix()) in relatorio.acoes
    assert (tmp_path / AGENTE).read_text(encoding="utf-8") != "minha versao\n"


def test_install_preserva_arquivo_do_usuario_com_mesmo_nome(tmp_path):
    (tmp_path / SKILL).parent.mkdir(parents=True)
    (tmp_path / SKILL).write_text("skill do usuario\n", encoding="utf-8")
    relatorio = install(tmp_path)
    assert relatorio.conflitos == [SKILL.as_posix()]
    assert SKILL.as_posix() not in json.loads((tmp_path / MANIFESTO).read_text(encoding="utf-8"))["arquivos"]
    # uninstall nao remove o que nao e do pacote
    uninstall(tmp_path)
    assert (tmp_path / SKILL).read_text(encoding="utf-8") == "skill do usuario\n"


def test_dry_run_e_only(tmp_path):
    relatorio = install(tmp_path / "dest", dry_run=True)
    assert relatorio.contagem() == {"criado": len(load_all())}
    assert not (tmp_path / "dest").exists()

    install(tmp_path, nomes=["daily-triage"])
    assert _arquivos(tmp_path) == {"skills/daily-triage/SKILL.md", MANIFESTO}
    with pytest.raises(ValueError, match="desconhecido"):
        install(tmp_path, nomes=["nao-existe"])


def test_uninstall_remove_so_o_instalado_e_nao_editado(tmp_path):
    outro = tmp_path / "skills" / "do-usuario" / "SKILL.md"
    outro.parent.mkdir(parents=True)
    outro.write_text("x\n", encoding="utf-8")
    install(tmp_path)
    (tmp_path / AGENTE).write_text("editado\n", encoding="utf-8")

    relatorio = uninstall(tmp_path)
    assert relatorio.conflitos == [AGENTE.as_posix()]
    assert _arquivos(tmp_path) == {"skills/do-usuario/SKILL.md", AGENTE.as_posix(), MANIFESTO}

    uninstall(tmp_path, force=True)
    assert _arquivos(tmp_path) == {"skills/do-usuario/SKILL.md"}


def test_default_target(tmp_path):
    assert default_target() == Path.home() / ".claude"
    assert default_target(tmp_path) == tmp_path.resolve() / ".claude"


def test_cli(tmp_path, capsys):
    assert main(["validate"]) == 0
    assert main(["list"]) == 0
    assert "deadline-checker" in capsys.readouterr().out

    assert main(["install", "--project", str(tmp_path), "--dry-run"]) == 0
    assert not (tmp_path / ".claude").exists()
    assert main(["install", "--project", str(tmp_path)]) == 0
    assert (tmp_path / ".claude" / SKILL).is_file()

    (tmp_path / ".claude" / AGENTE).write_text("editado\n", encoding="utf-8")
    assert main(["install", "--target", str(tmp_path / ".claude")]) == 1
    assert "--force" in capsys.readouterr().err
    assert main(["install", "--only", "nao-existe", "--target", str(tmp_path)]) == 2
    assert main(["uninstall", "--project", str(tmp_path), "--force"]) == 0
    assert not (tmp_path / ".claude" / AGENTE).exists()


def test_script_de_instalacao_roda_sem_pip(tmp_path):
    """O modulo roda direto do codigo-fonte, como fazem install.sh e install.ps1."""
    raiz = Path(nexjus_skills.__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(raiz)}
    resultado = subprocess.run(
        [sys.executable, "-m", "nexjus_skills", "install", "--target", str(tmp_path)],
        capture_output=True, text=True, env=env, check=False, cwd=tmp_path,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert (tmp_path / SKILL).is_file()
    pasta_skills = raiz.parent
    assert (pasta_skills / "install.sh").is_file()
    assert (pasta_skills / "install.ps1").is_file()
