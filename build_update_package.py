"""Atalho oficial para gerar o ZIP de atualização limpo do AlphaFest Manager."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from update_hygiene import build_clean_update_zip
from release_diagnostics import classify_test_file, release_source_fingerprint, run_release_diagnostics


# Seleção deliberada de regressões funcionais aplicáveis. Acrescentar aqui os
# novos fluxos críticos de cada release; o inventário completo não é um gate.
# Nenhum destes testes importa o Manager nem precisa de banco ou rede.
CRITICAL_TEST_FILES = (
    "test_manager_workflow_hf53.py",
    "test_manager_operational_planning_hf53.py",
    "test_planejamento_diario_hf49.py",
    "test_planejamento_semanal_hf48.py",
    "test_central_producao_painel_hf41.py",
    "test_site_integrity_hf53.py",
    "test_site_cart_hf53.py",
    "test_site_search_hf53.py",
    "test_site_posts_hf53.py",
    "test_site_metrics_funnel_hf53.py",
    "test_release_diagnostics_hf53.py",
    "test_build_update_package_hf53.py",
    "test_site_vitrine_hf52.py",
    "test_site_release_cache_hf52.py",
    "test_update_package_hf52.py",
    "test_pwa_hf652414.py",
    "test_posts_hf652417.py",
    "test_posts_hf652418.py",
    "test_roteiro_producao_hf51.py",
    "test_hf652438_sob_encomenda.py",
)
_RESULT_MARKER = "ALPHAFEST_TEST_RESULT="

# Processo separado por arquivo: impede que mocks/estado de uma suíte afetem a
# próxima e usa o mesmo Python do comando de build. Funções test_* legadas também
# são executadas: unittest padrão sozinho as ignoraria silenciosamente.
_OFFLINE_TEST_RUNNER = r'''
import importlib.abc
import importlib.util
import inspect
import json
from pathlib import Path
import socket
import sys
import traceback
import unittest

def no_network(*args, **kwargs):
    raise RuntimeError("Testes críticos são offline: acesso à rede bloqueado.")

socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network
socket.getaddrinfo = no_network

class NoManagerImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "app" or fullname.startswith("app."):
            raise ImportError("O gate não pode importar/executar o Manager (app.py).")

class CountSuccess(unittest.TextTestResult):
    passed = 0
    def addSuccess(self, test):
        self.passed += 1
        super().addSuccess(test)

sys.meta_path.insert(0, NoManagerImport())
root, relative = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, str(root))
report = {"tests_run": 0, "tests_passed": 0, "failures": 0, "errors": 0, "skipped": 0}
try:
    spec = importlib.util.spec_from_file_location("_alphafest_critical_test", root / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    for name, value in sorted(vars(module).items()):
        if name.startswith("test_") and inspect.isfunction(value) and value.__module__ == module.__name__:
            suite.addTest(unittest.FunctionTestCase(value))
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=CountSuccess).run(suite)
    report.update(tests_run=result.testsRun, tests_passed=result.passed,
                  failures=len(result.failures) + len(result.unexpectedSuccesses),
                  errors=len(result.errors), skipped=len(result.skipped) + len(result.expectedFailures))
    ok = result.wasSuccessful() and not report["skipped"] and result.testsRun > 0
except Exception:
    traceback.print_exc()
    report["errors"] += 1
    ok = False
report["status"] = "APROVADO" if ok else "REPROVADO"
print("ALPHAFEST_TEST_RESULT=" + json.dumps(report), flush=True)
sys.exit(0 if ok else 1)
'''


def run_critical_tests(root: str | Path, *, test_files=None, timeout: float = 60) -> dict:
    """Executa a seleção explícita offline; não gera ZIP nem chama diagnósticos.

    test_files permite testar o runner com fixtures pequenas, sem executar o
    próprio gate recursivamente. A CLI oficial sempre usa CRITICAL_TEST_FILES.
    Um teste ausente, vazio, pulado ou com erro impede a aprovação.
    """
    root = Path(root).resolve()
    fingerprint = release_source_fingerprint(root)
    version = (root / "VERSAO.txt").read_text(encoding="utf-8").strip()
    selected = list(dict.fromkeys(CRITICAL_TEST_FILES if test_files is None else test_files))
    results = []
    historical = []
    for relative in selected:
        path = root / relative
        item = {"file": relative, "executed": False, "status": "REPROVADO",
                "tests_run": 0, "tests_passed": 0, "failures": 0, "errors": 0, "skipped": 0}
        if not path.resolve().is_relative_to(root) or not path.is_file():
            item.update(errors=1, detail="Arquivo crítico ausente ou fora da raiz.")
            results.append(item)
            continue
        classification = classify_test_file(path, version)
        if classification == "historical_version":
            historical.append(relative)
            continue
        if classification == "invalid":
            item.update(errors=1, detail="Arquivo crítico ilegível ou com sintaxe inválida.")
            results.append(item)
            continue
        try:
            proc = subprocess.run(
                [sys.executable, "-B", "-c", _OFFLINE_TEST_RUNNER, str(root), relative],
                cwd=root, text=True, capture_output=True, timeout=timeout,
            )
            item["executed"] = True
            if _RESULT_MARKER in proc.stdout:
                payload = proc.stdout.rsplit(_RESULT_MARKER, 1)[1].strip().splitlines()[0]
                item.update(json.loads(payload))
            else:
                item.update(errors=1, detail="Runner não retornou resultado de testes.")
            if proc.returncode != 0:
                item["status"] = "REPROVADO"
            if item["status"] != "APROVADO":
                item["detail"] = (proc.stderr or proc.stdout or item.get("detail", "Falha no runner."))[-6000:]
        except subprocess.TimeoutExpired:
            item.update(executed=True, errors=1, detail=f"Tempo limite de {timeout:g}s excedido.")
        except (OSError, ValueError, IndexError) as exc:
            item.update(errors=1, detail=str(exc))
        results.append(item)
    unchanged = fingerprint == release_source_fingerprint(root)
    approved = bool(results) and all(item["status"] == "APROVADO" for item in results) and unchanged
    return {
        "status": "APROVADO" if approved else "REPROVADO",
        "selected_files": len(selected),
        "executed_files": sum(bool(item["executed"]) for item in results),
        "approved_files": sum(item["status"] == "APROVADO" for item in results),
        **{key: sum(item[key] for item in results) for key in ("tests_run", "tests_passed", "failures", "errors", "skipped")},
        "historical_files": historical,
        "source_fingerprint": fingerprint,
        "source_unchanged": unchanged,
        "python_version": sys.version.split()[0],
        "results": results,
    }


def build_validated_update(root: str | Path, output: str | Path, *, release_note: str | None = None) -> dict:
    """O caminho oficial só promove o ZIP após o gate e a auditoria do pacote."""
    root, output = Path(root).resolve(), Path(output).resolve()
    diagnostics = run_release_diagnostics(root)
    if not diagnostics.ok:
        raise RuntimeError("Diagnóstico da release reprovado: " + " | ".join(diagnostics.problems))
    execution = run_critical_tests(root)
    diagnostics = run_release_diagnostics(root, test_execution=execution)
    if not diagnostics.ok:
        failed = [item["file"] for item in execution["results"] if item["status"] != "APROVADO"]
        details = " | ".join(item.get("detail", "") for item in execution["results"] if item["status"] != "APROVADO")
        raise RuntimeError("Gate crítico reprovado (" + ", ".join(failed) + "): "
                           + " | ".join(diagnostics.problems) + ("\n" + details if details else ""))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alphafest_build_", dir=output.parent) as temp:
        staged = Path(temp) / "update.zip"
        result = build_clean_update_zip(root, staged, release_note=release_note, test_execution=execution)
        if release_source_fingerprint(root) != execution["source_fingerprint"]:
            raise RuntimeError("Fontes alterados durante o empacotamento; ZIP não promovido.")
        os.replace(staged, output)
    result["path"] = str(output)
    result["release_diagnostics"] = diagnostics.to_dict()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--release-note", default="")
    args = parser.parse_args()
    try:
        result = build_validated_update(args.root, args.output, release_note=args.release_note or None)
    except RuntimeError as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
