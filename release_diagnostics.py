"""Diagnóstico de release do AlphaFest Manager.

HF23: separa integridade da versão atual de ruído histórico da suíte de testes.
O módulo é leve, não depende de Streamlit/Supabase e pode ser usado no Manager,
no build do ZIP e em CI/local.
"""
from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import re
from dataclasses import dataclass, asdict, field
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
    "site_integrity_service.py",
    "site_quote_import_service.py",
    "site_quote_import_ui.py",
    "proposal_duplicate_service_hf55.py",
    "proposal_duplicate_ui_hf55.py",
    "proposal_review_service_hf56.py",
    "proposal_review_ui_hf56.py",
    "proposal_draft_service_hf57.py",
    "proposal_draft_ui_hf57.py",
    "manager_workflow_hf53.py",
    "manager_operational_planning_hf53.py",
    "site_carrinho_orcamento_service.py",
    "site_vitrine_service.py",
    "site_dicas_multicanal_service.py",  # RC5: impediu erro Python 3.11 na geracao de Dicas
    "site_posts_service.py",
    "site_posts_ui.py",
    "site_metrics_dashboard_ui.py",
    "global_search_service.py",
    "update_safe_ui.py",
    "system_health_ui.py",
    "trash_ui.py",
    "alpha_connect_ui.py",
    "audit_ui.py",
    "catalogo_diagnostics_service.py",
    "catalogo_runtime_index_service.py",
    "clientes_runtime_index_service.py",
    "relacionamentos_runtime_service.py",
    "crm_runtime_index_service.py",
    "finance_runtime_index_service.py",
    "resultados_runtime_service.py",
    "project_runtime_index_service.py",
    "proposal_runtime_index_service.py",
    "document_runtime_service.py",
    "anna_fechamento_service.py",
    "anna_snapshot_runtime_service.py",
    "compras_runtime_index_service.py",
    "marketing_results_runtime_service.py",
    "reports_runtime_index_service.py",
    "historico_runtime_service.py",
    "thu_comercial_service.py",
    "central_operational_runtime.py",
    "central_entregas_engine.py",
    "prioridade_operacional_engine.py",
    "consumo_estoque_engine.py",
    "necessidades_compras_engine.py",
    "risco_producao_engine.py",
)

# HF65.24.53: reconhece também sufixos usados por asserts como endswith().
# Só se classificam restrições sobre a versão lida do projeto. Versões em
# comentários, fixtures e simulações de migração não tornam um teste histórico.
_VERSION_RX = re.compile(r"(?:20\.4\.9(?:-[A-Za-z0-9.]+)+|HF\d+(?:\.\d+)+)")
_VERSION_FILES = {"VERSAO", "VERSAO.txt", "RELEASE_INFO.json"}


@dataclass
class TestInventory:
    total_files: int
    portable_files: int
    current_release_files: int
    historical_version_files: int
    historical_examples: list[str]
    invalid_files: int = 0
    invalid_examples: list[str] = field(default_factory=list)

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
    candidates = list(root.glob("test_*.py"))
    if (root / "tests").is_dir():
        candidates.extend((root / "tests").rglob("test_*.py"))
    seen: set[Path] = set()
    result: list[Path] = []
    for path in sorted(candidates, key=lambda p: p.relative_to(root).as_posix()):
        resolved = path.resolve()
        if path.is_file() and resolved.is_relative_to(root) and resolved not in seen:
            seen.add(resolved)
            result.append(path)
    return result


def _scope_nodes(scope: ast.AST) -> Iterable[ast.AST]:
    """Percorre um escopo sem misturar variáveis de funções diferentes."""
    for child in ast.iter_child_nodes(scope):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield child
        yield from _scope_nodes(child)


def _live_version_expression(node: ast.AST, names: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and (child.id in names or child.id == "APP_VERSION"):
            return True
        if isinstance(child, ast.Attribute) and child.attr == "APP_VERSION":
            return True
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value in _VERSION_FILES:
            return True
    return False


def test_version_constraints(path: Path) -> set[str]:
    """Extrai pins positivos da versão do projeto, sem executar o arquivo."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_names = {
        alias.asname or alias.name
        for node in tree.body if isinstance(node, ast.ImportFrom)
        for alias in node.names if alias.name == "APP_VERSION"
    }
    constraints: set[str] = set()
    scopes = [tree] + [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for scope in scopes:
        nodes = list(_scope_nodes(scope))
        names = set(module_names)
        # Propaga aliases locais: p = root/'VERSAO.txt'; v = p.read_text().
        while True:
            before = set(names)
            for node in nodes:
                if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                    if _live_version_expression(node.value, names):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        names.update(n.id for target in targets for n in ast.walk(target) if isinstance(n, ast.Name))
            if names == before:
                break
        for node in nodes:
            expression = None
            if isinstance(node, ast.Assert):
                # Rejeitar uma versão antiga não prende o teste àquela versão.
                if isinstance(node.test, ast.Compare) and all(isinstance(op, (ast.NotEq, ast.NotIn)) for op in node.test.ops):
                    continue
                expression = node.test
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"assertEqual", "assertIn", "assertTrue"}:
                    expression = node
            if expression is not None and _live_version_expression(expression, names):
                for child in ast.walk(expression):
                    if isinstance(child, ast.Constant) and isinstance(child.value, str):
                        constraints.update(_VERSION_RX.findall(child.value))
        if scope is tree:
            module_names.update(names)
    return constraints


def classify_test_file(path: Path, current_version: str) -> str:
    try:
        constraints = test_version_constraints(path)
    except (OSError, SyntaxError, UnicodeError):
        return "invalid"
    if not constraints:
        return "portable"
    if any(current_version == pin or current_version.endswith("-" + pin) for pin in constraints):
        return "current_release"
    return "historical_version"


def release_source_fingerprint(root: str | Path) -> str:
    """Assina fontes e versões usados pelo gate, sem ler bancos ou credenciais."""
    root = Path(root).resolve()
    paths = set(root.glob("*.py")) | set(_iter_test_files(root))
    paths.update(root / name for name in ("VERSAO", "VERSAO.txt", "RELEASE_INFO.json"))
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


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
    portable = current_release = historical = invalid = 0
    examples: list[str] = []
    invalid_examples: list[str] = []
    files = list(_iter_test_files(root))

    for path in files:
        classification = classify_test_file(path, current)
        if classification == "current_release":
            current_release += 1
        elif classification == "historical_version":
            historical += 1
            if len(examples) < 8:
                examples.append(path.relative_to(root).as_posix())
        elif classification == "invalid":
            invalid += 1
            if len(invalid_examples) < 8:
                invalid_examples.append(path.relative_to(root).as_posix())
        else:
            portable += 1

    return TestInventory(
        total_files=len(files),
        portable_files=portable,
        current_release_files=current_release,
        historical_version_files=historical,
        historical_examples=examples,
        invalid_files=invalid,
        invalid_examples=invalid_examples,
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


def run_release_diagnostics(root: str | Path, *, test_execution: dict | None = None) -> ReleaseDiagnostics:
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
    if inventory.invalid_files:
        problems.append("Teste(s) ilegível(is) ou com sintaxe inválida: " + ", ".join(inventory.invalid_examples))
    if inventory.historical_version_files:
        warnings.append(
            f"{inventory.historical_version_files} arquivo(s) de teste dependem de versão histórica; "
            "eles são classificados como legado e não reprovam a release atual apenas pelo número antigo."
        )

    execution = dict(test_execution or {})
    if test_execution is not None:
        if (execution.get("status") != "APROVADO"
                or int(execution.get("executed_files", 0)) < 1
                or execution.get("approved_files") != execution.get("executed_files")
                or int(execution.get("tests_run", 0)) < 1
                or execution.get("tests_passed") != execution.get("tests_run")
                or any(execution.get(key, 0) for key in ("failures", "errors", "skipped"))):
            problems.append("O conjunto crítico de testes não foi aprovado.")
        if execution.get("source_fingerprint") != release_source_fingerprint(root):
            problems.append("Os fontes ou metadados mudaram depois da execução dos testes críticos.")
    checks = {
        "runtime_integrity": "OK" if runtime.ok else "REPROVADO",
        "critical_python_compile": {
            "status": "OK" if not compile_errors else "REPROVADO",
            "files_checked": len(CRITICAL_PYTHON_FILES),
            "files_ok": len(compiled),
        },
        "tests": {
            "found_files": inventory.total_files,
            "executed_files": int(execution.get("executed_files", 0)),
            "approved_files": int(execution.get("approved_files", 0)),
            "executed_cases": int(execution.get("tests_run", 0)),
            "approved_cases": int(execution.get("tests_passed", 0)),
            "execution_status": execution.get("status", "NAO_EXECUTADO"),
            "inventory": inventory.to_dict(),
            "execution": execution,
        },
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
