"""HF84: preflight seguro e somente leitura do AlphaFest Manager.

Valida metadados usados pelo rodape, rotina de sincronizacao e protecoes
basicas do repositorio antes de uma release. Nao le valores de Secrets,
nao acessa banco, nao publica site e nao altera arquivos.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

VERSION_RE = re.compile(r"^20\.4\.9-[A-Za-z0-9.-]+-HF(?P<hf>\d{2,3})$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_IGNORE = (
    ".env", ".streamlit/secrets.toml", "backups/",
    "clientes_db.json", "historico_orcamentos.json",
    "usuarios_config.json",
)


def verificar(root: Path, *, hf_minima: int = 83) -> dict:
    root = Path(root)
    checks = {}
    errors = []
    def check(name: str, ok: bool, message: str) -> None:
        checks[name] = {"ok": bool(ok), "detail": message}
        if not ok:
            errors.append(message)

    def ler(path: str) -> str:
        try:
            return (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""

    principal = ler("VERSAO").strip()
    rodape = ler("VERSAO.txt").strip()
    try:
        release = json.loads(ler("RELEASE_INFO.json"))
        if not isinstance(release, dict):
            raise ValueError("release not object")
    except (ValueError, TypeError):
        release = {}

    match = VERSION_RE.fullmatch(rodape)
    check("versao_identica", bool(principal and rodape and principal == rodape == release.get("version")),
          "VERSAO, VERSAO.txt e RELEASE_INFO.json devem ser identicos")
    check("hf_minima", bool(match and int(match.group("hf")) >= hf_minima),
          f"Ultima versao do rodape deve ser HF{hf_minima} ou superior")
    check("sha_da_release", bool(SHA_RE.fullmatch(str(release.get("source_commit", "")))),
          "RELEASE_INFO.json precisa apontar para SHA completo")
    try:
        dt = datetime.fromisoformat(str(release.get("created_at", "")).replace("Z", "+00:00"))
        aware = dt.tzinfo is not None and dt.utcoffset() is not None
    except ValueError:
        aware = False
    check("data_da_release", aware, "Data da versao precisa conter fuso horario")
    config = ler("config.py")
    check("rodape_lido_do_arquivo", '"VERSAO.txt"' in config and "APP_VERSION = _read_app_version()" in config,
          "Config do Manager deve consultar VERSAO.txt")
    sync = ler("scripts/sincronizar_release_rodape.py")
    workflow = ler(".github/workflows/sincronizar-rodape-manager.yml")
    check("sync_existe", bool(sync and "sincronizar_release(" in sync and workflow and "sincronizar_release_rodape.py" in workflow),
          "Atualizacao automatica da versao deve permanecer configurada")
    ignore = ler(".gitignore")
    missing = [p for p in REQUIRED_IGNORE if p not in ignore.splitlines()]
    check("ignore_essencial", not missing, "Itens essenciais ausentes do .gitignore: " + ", ".join(missing))
    check("roteiro_recuperacao", bool(ler("HF84_FUNDACAO_SEGURA.md")),
          "Deve existir roteiro de recuperacao e release nao destrutivo")
    return {"ok": not errors, "versao": rodape, "checks": checks, "erros": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--min-hf", type=int, default=83)
    args = parser.parse_args()
    result = verificar(args.root, hf_minima=args.min_hf)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
