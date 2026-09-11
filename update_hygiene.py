"""Blindagem de atualização do AlphaFest Manager.

HF18: separa pacote de atualização (código + assets + migrações) dos dados da empresa.
O módulo é deliberadamente independente de Streamlit/Supabase para poder rodar no
build, em teste local e no diagnóstico do Manager.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

HF7_PREVIEW_SHA256 = "b3600ab50b327c6eb972f120654d554bec8a18967ce08f300392e2301a7d9601"
REQUIRED_RUNTIME_FILES = {
    "app.py",
    "requirements.txt",
    "VERSAO",
    "VERSAO.txt",
    "cloud_db.py",
    "backup_schedule_service.py",
    "release_diagnostics.py",
    "config.py",
    "marketing_template_engine.py",
    "marketing_anna_renderer_hf11.py",
    "assets/marketing/template_mestre_hf7_preview.png",
}

# Documentos persistentes nunca pertencem a um ZIP de atualização.
DATA_JSON_NAMES = {
    "historico_orcamentos.json", "catalogo_db.json", "clientes_db.json",
    "producao_db.json", "empresa_config.json", "projetos_db.json",
    "campanhas_db.json", "atendimentos_db.json", "segmentos_db.json",
    "backup_config.json", "auditoria_db.json", "lixeira_db.json",
    "system_meta.json", "componentes_db.json", "marketing_db.json",
    "catalogos_legados_db.json", "catalogos_gerados_db.json",
    "catalogo_modelos_db.json", "integracoes_db.json", "alpha_intelligence_db.json",
    "usuarios_config.json", "orientacoes_thu.json", "faturamento_mensal_db.json",
    "compras_db.json", "estoque_db.json", "fichas_tecnicas_db.json",
    "consumo_pedidos_db.json", "planejamento_compras_db.json",
    "agenda_anna_snapshots_db.json", "biblioteca_3d_db.json",
    "galeria_trabalhos_db.json", "feature_flags.json",
}

EXCLUDED_DIRS = {
    ".git", ".pytest_cache", ".devcontainer", "tests", "tests - Copia",
    "assets - Copia", "templates - Copia", "github-pages - Copia", "supabase - Copia",
}

_COPY_RX = re.compile(r"(?:^|\s)-?\s*Copia(?:\.|$|\s)", re.IGNORECASE)


@dataclass
class AuditResult:
    ok: bool
    version: str
    problems: list[str]
    warnings: list[str]
    stats: dict[str, int | str]

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_version(root: Path) -> tuple[str, list[str]]:
    problems: list[str] = []
    values: list[str] = []
    for name in ("VERSAO", "VERSAO.txt"):
        p = root / name
        if not p.is_file():
            problems.append(f"Arquivo obrigatório ausente: {name}")
            continue
        values.append(p.read_text(encoding="utf-8").strip())
    version = values[0] if values else ""
    if len(values) == 2 and values[0] != values[1]:
        problems.append(f"VERSAO e VERSAO.txt divergentes: {values[0]} != {values[1]}")
    if not version:
        problems.append("Versão vazia.")
    return version, problems


def runtime_integrity_check(root: str | Path) -> AuditResult:
    """Validação leve da instalação atual, sem rejeitar lixo histórico já existente."""
    root = Path(root).resolve()
    version, problems = read_version(root)
    warnings: list[str] = []
    for rel in sorted(REQUIRED_RUNTIME_FILES):
        if not (root / rel).is_file():
            problems.append(f"Runtime obrigatório ausente: {rel}")

    hf7 = root / "assets/marketing/template_mestre_hf7_preview.png"
    if hf7.is_file():
        current = sha256_file(hf7)
        if current != HF7_PREVIEW_SHA256:
            problems.append("Template Mestre HF7 não confere com o hash congelado.")

    copy_count = 0
    data_count = 0
    for p in root.iterdir() if root.is_dir() else []:
        if _COPY_RX.search(p.name):
            copy_count += 1
        if p.is_file() and p.name in DATA_JSON_NAMES:
            data_count += 1
    if copy_count:
        warnings.append(f"Instalação ainda contém {copy_count} item(ns) legado(s) 'Copia' na raiz; novos pacotes limpos não os reenviam.")
    if data_count:
        warnings.append(f"Há {data_count} arquivo(s) local(is) de dados na raiz; eles são preservados e nunca entram no pacote de atualização.")

    return AuditResult(
        ok=not problems,
        version=version,
        problems=problems,
        warnings=warnings,
        stats={"legacy_copy_root": copy_count, "local_data_root": data_count},
    )


def _has_copy_marker(rel: PurePosixPath) -> bool:
    return any(_COPY_RX.search(part) for part in rel.parts)


def exclusion_reason(rel: PurePosixPath) -> str | None:
    """Retorna o motivo de exclusão do pacote de atualização, ou None para incluir."""
    parts = rel.parts
    if not parts:
        return "vazio"
    if any(part in EXCLUDED_DIRS for part in parts):
        return "diretorio_nao_producao"
    if _has_copy_marker(rel):
        return "arquivo_copia"
    name = rel.name
    low = name.casefold()
    if name in DATA_JSON_NAMES or (len(parts) == 1 and low.endswith(".json")):
        return "dados_persistentes"
    if low.endswith((".pyc", ".pyo", ".tmp", ".log")) or "__pycache__" in parts:
        return "cache_temporario"
    if ".bak" in low or re.search(r"\.bak[_-]?hf\d+", low):
        return "backup_codigo"
    if low.startswith("atualiza") and len(parts) == 1 and not low.endswith((".md", ".txt")):
        return "pacote_antigo_embutido"
    if low.endswith((".zip", ".7z", ".rar")):
        return "arquivo_compactado_embutido"
    if low in {".env", "secrets.toml"}:
        return "segredo_local"
    # Histórico de release antigo não é necessário em produção; conserva só o release atual
    # por meio do builder, que o adiciona explicitamente quando informado.
    if len(parts) == 1 and low.startswith("update_info_") and low.endswith(".md"):
        return "historico_release"
    return None


def iter_update_files(root: Path, release_note: str | None = None) -> Iterable[Path]:
    release_note = str(release_note or "").strip()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = PurePosixPath(path.relative_to(root).as_posix())
        reason = exclusion_reason(rel)
        if reason:
            if release_note and rel.as_posix() == release_note:
                yield path
            continue
        yield path


def _manifest(root: Path, files: list[Path], version: str) -> dict:
    entries = []
    total = 0
    for p in files:
        rel = p.relative_to(root).as_posix()
        size = p.stat().st_size
        total += size
        entries.append({"path": rel, "size": size, "sha256": sha256_file(p)})
    validation = {}
    try:
        # Import tardio evita ciclo: release_diagnostics usa runtime_integrity_check.
        from release_diagnostics import run_release_diagnostics
        diag = run_release_diagnostics(root)
        validation = {
            "status": "OK" if diag.ok else "REPROVADO",
            "problems": list(diag.problems),
            "warnings": list(diag.warnings),
            "critical_python_compile": diag.checks.get("critical_python_compile", {}),
            "tests": diag.test_inventory.to_dict(),
        }
    except Exception as exc:
        validation = {"status": "INDISPONIVEL", "problems": [str(exc)]}

    return {
        "schema": 2,
        "product": "AlphaFest Manager",
        "version": version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "codigo_assets_migracoes_sem_dados",
        "hf7_preview_sha256": HF7_PREVIEW_SHA256,
        "validation": validation,
        "file_count": len(entries),
        "uncompressed_bytes": total,
        "files": entries,
    }


def build_clean_update_zip(root: str | Path, output: str | Path, *, release_note: str | None = None) -> dict:
    root = Path(root).resolve()
    output = Path(output).resolve()
    audit = runtime_integrity_check(root)
    if not audit.ok:
        raise RuntimeError("Preflight da base falhou: " + " | ".join(audit.problems))

    files = list(iter_update_files(root, release_note=release_note))
    rels = {p.relative_to(root).as_posix() for p in files}
    missing = sorted(REQUIRED_RUNTIME_FILES - rels)
    if missing:
        raise RuntimeError("Pacote limpo removeria arquivo obrigatório: " + ", ".join(missing))

    manifest = _manifest(root, files, audit.version)
    output.parent.mkdir(parents=True, exist_ok=True)
    wrapper = root.name
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(root).as_posix()
            zf.write(p, f"{wrapper}/{rel}")
        zf.writestr(f"{wrapper}/UPDATE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    package_audit = audit_update_zip(output)
    if not package_audit.ok:
        output.unlink(missing_ok=True)
        raise RuntimeError("Pacote gerado foi reprovado: " + " | ".join(package_audit.problems))
    return {
        "path": str(output),
        "version": audit.version,
        "file_count": manifest["file_count"],
        "uncompressed_bytes": manifest["uncompressed_bytes"],
        "zip_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "audit": package_audit.to_dict(),
    }


def audit_update_zip(zip_path: str | Path) -> AuditResult:
    zip_path = Path(zip_path)
    problems: list[str] = []
    warnings: list[str] = []
    version = ""
    forbidden = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            problems.append("ZIP vazio.")
            return AuditResult(False, "", problems, warnings, {"files": 0})
        top = PurePosixPath(names[0]).parts[0]
        rels: set[str] = set()
        for name in names:
            pp = PurePosixPath(name)
            if not pp.parts or pp.parts[0] != top:
                problems.append(f"Estrutura inconsistente no ZIP: {name}")
                continue
            rel = PurePosixPath(*pp.parts[1:])
            rels.add(rel.as_posix())
            if rel.name == "UPDATE_MANIFEST.json":
                continue
            # Um único release note atual é permitido; o builder não leva o histórico.
            if len(rel.parts) == 1 and rel.name.casefold().startswith("update_info_") and rel.name.casefold().endswith(".md"):
                continue
            reason = exclusion_reason(rel)
            if reason:
                forbidden += 1
                problems.append(f"Arquivo proibido ({reason}): {rel.as_posix()}")
        missing = sorted(REQUIRED_RUNTIME_FILES - rels)
        if missing:
            problems.append("Obrigatórios ausentes: " + ", ".join(missing))
        try:
            v1 = zf.read(f"{top}/VERSAO").decode("utf-8").strip()
            v2 = zf.read(f"{top}/VERSAO.txt").decode("utf-8").strip()
            version = v1
            if v1 != v2:
                problems.append("VERSAO e VERSAO.txt divergem dentro do ZIP.")
        except Exception as exc:
            problems.append(f"Não foi possível ler versão do ZIP: {exc}")
        try:
            hf7_bytes = zf.read(f"{top}/assets/marketing/template_mestre_hf7_preview.png")
            hf7_hash = hashlib.sha256(hf7_bytes).hexdigest()
            if hf7_hash != HF7_PREVIEW_SHA256:
                problems.append("HF7 dentro do ZIP não confere com o hash congelado.")
        except Exception as exc:
            problems.append(f"Não foi possível validar HF7 dentro do ZIP: {exc}")
        manifest_name = f"{top}/UPDATE_MANIFEST.json"
        if manifest_name not in names:
            problems.append("UPDATE_MANIFEST.json ausente.")
        else:
            try:
                manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
                if str(manifest.get("version") or "").strip() != version:
                    problems.append("Versão do UPDATE_MANIFEST diverge da versão do ZIP.")
                validation = manifest.get("validation") or {}
                if validation.get("status") != "OK":
                    problems.append(
                        "Diagnóstico gravado no UPDATE_MANIFEST não está aprovado: "
                        + str(validation.get("status") or "AUSENTE")
                    )
                expected_count = manifest.get("file_count")
                if isinstance(expected_count, int):
                    packaged_payload = len([n for n in names if n != manifest_name])
                    if expected_count != packaged_payload:
                        problems.append(
                            f"Contagem do UPDATE_MANIFEST diverge do ZIP: {expected_count} != {packaged_payload}."
                        )
            except Exception as exc:
                problems.append(f"UPDATE_MANIFEST inválido: {exc}")

    return AuditResult(
        ok=not problems,
        version=version,
        problems=problems,
        warnings=warnings,
        stats={"files": len(names), "forbidden_files": forbidden, "zip_bytes": zip_path.stat().st_size},
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gera/valida atualização limpa do AlphaFest Manager")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--release-note", default="")
    parser.add_argument("--audit-zip", default="")
    args = parser.parse_args()
    if args.audit_zip:
        print(json.dumps(audit_update_zip(args.audit_zip).to_dict(), ensure_ascii=False, indent=2))
    elif args.output:
        print(json.dumps(build_clean_update_zip(args.root, args.output, release_note=args.release_note or None), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(runtime_integrity_check(args.root).to_dict(), ensure_ascii=False, indent=2))
