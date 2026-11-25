"""Inventário e evidência do diagnóstico sem executar o Manager."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import release_diagnostics as diagnostics


class TestReleaseDiagnostics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="alphafest_diagnostics_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version = "20.4.9-I8.13.5-HF53.3-HF8-HF65.24.53"
        (self.root / "VERSAO.txt").write_text(self.version, encoding="utf-8")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_root_and_nested_tests_are_found_without_symlink_duplicates(self):
        first = self.write("test_root.py", "def test_ok(): assert True\n")
        self.write("tests/nested/test_nested.py", "def test_ok(): assert True\n")
        (self.root / "tests" / "test_alias.py").symlink_to(first)
        self.write("unrelated/test_ignored.py", "raise RuntimeError('not in inventory')\n")
        inventory = diagnostics.scan_test_inventory(self.root)
        self.assertEqual(inventory.total_files, 2)
        self.assertEqual(inventory.portable_files, 2)

    def test_real_version_suffix_and_import_alias_pins_are_historical(self):
        self.write("test_suffix.py", "from pathlib import Path\ndef test_version():\n"
                   "    value = (Path(__file__).parent / 'VERSAO').read_text().strip()\n"
                   "    assert value.endswith('HF65.24.50')\n")
        self.write("tests/test_full.py", "from config import APP_VERSION as release_version\n"
                   "def test_version():\n    assert release_version == '20.4.9-HF65.24.50'\n")
        inventory = diagnostics.scan_test_inventory(self.root)
        self.assertEqual(inventory.historical_version_files, 2)
        self.assertEqual(inventory.portable_files, 0)

    def test_current_release_pin_classified_separately(self):
        self.write("test_current.py", "from config import APP_VERSION\n"
                   "def test_version():\n    assert APP_VERSION.endswith('HF65.24.53')\n")
        self.assertEqual(diagnostics.scan_test_inventory(self.root).current_release_files, 1)

    def test_fixture_versions_comments_and_negative_asserts_are_portable(self):
        self.write("test_fixture.py", '"""Regression for 20.4.9-HF65.24.50."""\n'
                   "def test_migration():\n    before = {'version': '20.4.9-HF65.24.50'}\n"
                   "    assert before['version'].endswith('HF65.24.50')\n")
        self.write("test_negative.py", "from config import APP_VERSION\n"
                   "def test_not_old():\n    assert APP_VERSION != '20.4.9-HF65.24.50'\n")
        self.assertEqual(diagnostics.scan_test_inventory(self.root).portable_files, 2)

    def test_invalid_source_is_not_counted_as_portable(self):
        self.write("test_broken.py", "def broken(:\n")
        inventory = diagnostics.scan_test_inventory(self.root)
        self.assertEqual(inventory.invalid_files, 1)
        self.assertEqual(inventory.portable_files, 0)

    def run_diagnostic(self, **kwargs):
        runtime = SimpleNamespace(ok=True, problems=[], warnings=[], version=self.version)
        with patch.object(diagnostics, "runtime_integrity_check", return_value=runtime), \
                patch.object(diagnostics, "_compile_critical_files", return_value=([], [])):
            return diagnostics.run_release_diagnostics(self.root, **kwargs)

    def test_inventory_does_not_claim_execution_or_execute_tests(self):
        self.write("test_never_import.py", "raise RuntimeError('must not be imported')\n")
        result = self.run_diagnostic()
        self.assertTrue(result.ok)
        counts = result.checks["tests"]
        self.assertEqual(counts["found_files"], 1)
        self.assertEqual(counts["executed_files"], 0)
        self.assertEqual(counts["approved_files"], 0)
        self.assertEqual(counts["execution_status"], "NAO_EXECUTADO")

    def test_execution_counts_and_stale_source_evidence(self):
        self.write("test_ok.py", "def test_ok(): assert True\n")
        execution = {"status": "APROVADO", "executed_files": 1, "approved_files": 1,
                     "tests_run": 3, "tests_passed": 3,
                     "source_fingerprint": diagnostics.release_source_fingerprint(self.root)}
        result = self.run_diagnostic(test_execution=execution)
        self.assertTrue(result.ok)
        self.assertEqual(result.checks["tests"]["executed_cases"], 3)
        self.assertEqual(result.checks["tests"]["approved_cases"], 3)
        self.write("module.py", "CHANGED = True\n")
        changed = self.run_diagnostic(test_execution=execution)
        self.assertFalse(changed.ok)
        self.assertTrue(any("mudaram" in problem for problem in changed.problems))

    def test_approval_label_without_executed_tests_is_rejected(self):
        report = {"status": "APROVADO", "source_fingerprint": diagnostics.release_source_fingerprint(self.root)}
        result = self.run_diagnostic(test_execution=report)
        self.assertFalse(result.ok)
        self.assertTrue(any("não foi aprovado" in problem for problem in result.problems))


if __name__ == "__main__":
    unittest.main()
