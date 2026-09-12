"""Diagnóstico de release do AlphaFest Manager.

HF23: separa integridade da versão atual de ruído histórico da suíte de testes.
O módulo é leve, não depende de Streamlit/Supabase e pode ser usado no Manager,
no build do ZIP e em CI/local.
"""
from __future__ import annotations

import json
import py_compile
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from update_hygiene import runtime_integrity_check

# Módulos que sustentam boot, persistência, atualização e fluxos homologados.
CRITICAL_PYTHON_FILES = (
    "app.py",
    "config.py",
    "cloud_db.py",
    "update_hygiene.py",
    "build_update_package.py",
    "backup_schedule_service.py",
    "marketing_template_engine.py",
    "marketing_anna_renderer_hf11.py",
    "site_metrics_service.py",
    "global_search_service.py",
    "update_safe_ui.py",
    "system_health_ui.py",
    "trash_ui.py",
    "alpha_connect_ui.py",
    "audit_ui.py",
    "catalogo_diagnostics_service.py",
    "catalogo_runtime_index_service.py",
    "clientes_runtime_index_service.py",
    "crm_runtime_index_service.py",
    "finance_runtime_index_service.py",
    "project_runtime_index_service.py",
    "proposal_runtime_index_service.py",
    "document_runtime_service.py",
    "compras_runtime_index_service.py",
    "marketing_results_runtime_service.py",
    "thu_comercial_service.py",
    "central_operational_runtime.py",
    "central_entregas_engine.py",
    "prioridade_operacional_engine.py",
    "consumo_estoque_engine.py",
    "necessidades_compras_engine.py",
    "risco_producao_engine.py",
)

# Versões do Manager aparecem em muitos formatos. O regex é propositalmente
# restrito ao prefixo do produto para não classificar datas/números como release.
_VERSION_RX = re.compile(r"20\.4\.9(?:-[A-Za-z0-9.]+)+")
_VERSION_ASSERT_HINT_RX = re.compile(
    r"(?:VERSAO(?:\.txt)?|APP_VERSION|vers[aã]o|version)", re.IGNORECASE
)


@dataclass
class TestInventory:
    total_files: int
    portable_files: int
    current_release_files: int
    historical_version_files: int
    historical_examples: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReleaseDiagnostics:
    ok: bool
    version: str
    problems: list[str]
    warnings: list[str]
    checks: dict[str, object]
    test_inventory: TestInventory

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _read_current_version(root: Path) -> str:
    p = root / "VERSAO.txt"
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _iter_test_files(root: Path) -> Iterable[Path]:
    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return []
    return sorted(p for p in tests_dir.rglob("test_*.py") if p.is_file())


def scan_test_inventory(root: str | Path) -> TestInventory:
    """Classifica testes sem executá-los.

    * portable: não depende de versão exata;
    * current_release: referencia explicitamente a versão corrente;
    * historical_version: contém referência/assertiva de versão, mas somente para
      releases anteriores. Esses testes podem continuar úteis como arquivo de
      regressão, porém não devem reprovar a release atual só por número antigo.
    """
    root = Path(root).resolve()
    current = _read_current_version(root)
    portable = current_release = historical = 0
    examples: list[str] = []
    files = list(_iter_test_files(root))

    for path in files:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            portable += 1
            continue
        versions = set(_VERSION_RX.findall(source))
        has_version_assert_hint = bool(_VERSION_ASSERT_HINT_RX.search(source))
        if current and current in versions:
            current_release += 1
        elif versions and has_version_assert_hint:
            historical += 1
            if len(examples) < 8:
                examples.append(path.relative_to(root).as_posix())
        else:
            portable += 1

    return TestInventory(
        total_files=len(files),
        portable_files=portable,
        current_release_files=current_release,
        historical_version_files=historical,
        historical_examples=examples,
    )


def _compile_critical_files(root: Path) -> tuple[list[str], list[str]]:
    ok_files: list[str] = []
    errors: list[str] = []
    for rel in CRITICAL_PYTHON_FILES:
        path = root / rel
        if not path.is_file():
            errors.append(f"Arquivo Python crítico ausente: {rel}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            ok_files.append(rel)
        except Exception as exc:
            errors.append(f"Falha de sintaxe/compilação em {rel}: {exc}")
    return ok_files, errors


def run_release_diagnostics(root: str | Path) -> ReleaseDiagnostics:
    root = Path(root).resolve()
    problems: list[str] = []
    warnings: list[str] = []

    runtime = runtime_integrity_check(root)
    if not runtime.ok:
        problems.extend(runtime.problems)
    warnings.extend(runtime.warnings)

    compiled, compile_errors = _compile_critical_files(root)
    problems.extend(compile_errors)

    inventory = scan_test_inventory(root)
    if inventory.historical_version_files:
        warnings.append(
            f"{inventory.historical_version_files} arquivo(s) de teste dependem de versão histórica; "
            "eles são classificados como legado e não reprovam a release atual apenas pelo número antigo."
        )

    checks = {
        "runtime_integrity": "OK" if runtime.ok else "REPROVADO",
        "critical_python_compile": {
            "status": "OK" if not compile_errors else "REPROVADO",
            "files_checked": len(CRITICAL_PYTHON_FILES),
            "files_ok": len(compiled),
        },
        "tests": inventory.to_dict(),
    }

    return ReleaseDiagnostics(
        ok=not problems,
        version=runtime.version or _read_current_version(root),
        problems=problems,
        warnings=warnings,
        checks=checks,
        test_inventory=inventory,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Diagnóstico da release atual do AlphaFest Manager")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    result = run_release_diagnostics(args.root)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
