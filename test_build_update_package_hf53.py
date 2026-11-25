"""Gate reproduzível com suítes pequenas; nunca chama o gate padrão recursivamente."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import build_update_package as builder


class TestCriticalGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="alphafest_gate_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "VERSAO.txt").write_text("20.4.9-HF65.24.53", encoding="utf-8")

    def write(self, name, source):
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        return name

    def test_unittest_and_plain_functions_are_both_executed(self):
        name = self.write("test_both.py", "import unittest\n"
                          "def test_function():\n    assert 2 + 2 == 4\n"
                          "class TestCase(unittest.TestCase):\n"
                          "    def test_method(self):\n        self.assertEqual('ok'.upper(), 'OK')\n")
        report = builder.run_critical_tests(self.root, test_files=(name, name))
        self.assertEqual(report["status"], "APROVADO")
        self.assertEqual(report["selected_files"], 1)
        self.assertEqual(report["executed_files"], 1)
        self.assertEqual(report["approved_files"], 1)
        self.assertEqual(report["tests_run"], 2)
        self.assertEqual(report["tests_passed"], 2)

    def test_failure_skip_empty_and_missing_files_cannot_pass(self):
        cases = {
            "test_fail.py": "def test_failure():\n    assert False, 'known failure'\n",
            "test_skip.py": "import unittest\n@unittest.skip('dependency missing')\ndef test_skip(): pass\n",
            "test_empty.py": "VALUE = 1\n",
            "test_missing.py": None,
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                if source is not None:
                    self.write(name, source)
                report = builder.run_critical_tests(self.root, test_files=(name,))
                self.assertEqual(report["status"], "REPROVADO")
                self.assertEqual(report["approved_files"], 0)

    def test_network_attempt_is_blocked_before_connection(self):
        name = self.write("test_network.py", "import socket\n"
                          "def test_network():\n    socket.create_connection(('127.0.0.1', 9))\n")
        report = builder.run_critical_tests(self.root, test_files=(name,))
        self.assertEqual(report["status"], "REPROVADO")
        self.assertIn("acesso à rede bloqueado", report["results"][0]["detail"])

    def test_manager_cannot_be_imported_by_gate(self):
        self.write("app.py", "raise RuntimeError('Manager must never run')\n")
        name = self.write("test_import.py", "import app\ndef test_ok(): pass\n")
        report = builder.run_critical_tests(self.root, test_files=(name,))
        self.assertEqual(report["status"], "REPROVADO")
        self.assertIn("não pode importar/executar", report["results"][0]["detail"])

    def test_historical_version_pin_is_reported_without_imposing_old_release(self):
        good = self.write("test_good.py", "def test_ok(): assert True\n")
        old = self.write("test_old.py", "from pathlib import Path\ndef test_version():\n"
                         "    value = Path('VERSAO.txt').read_text()\n"
                         "    assert value.endswith('HF65.24.50')\n")
        report = builder.run_critical_tests(self.root, test_files=(old, good))
        self.assertEqual(report["status"], "APROVADO")
        self.assertEqual(report["historical_files"], [old])
        self.assertEqual(report["executed_files"], 1)
        self.assertEqual(report["tests_passed"], 1)
        self.assertEqual(builder.run_critical_tests(self.root, test_files=(old,))["status"], "REPROVADO")

    def test_source_changed_during_tests_invalidates_evidence(self):
        name = self.write("test_mutation.py", "from pathlib import Path\ndef test_mutation():\n"
                          "    Path('changed.py').write_text('CHANGED = True\\n')\n")
        report = builder.run_critical_tests(self.root, test_files=(name,))
        self.assertEqual(report["tests_passed"], 1)
        self.assertFalse(report["source_unchanged"])
        self.assertEqual(report["status"], "REPROVADO")

    def test_failed_gate_never_calls_packager_or_overwrites_existing_output(self):
        name = self.write("test_failure.py", "def test_failure(): assert False\n")
        output = self.root / "update.zip"

        def diagnostic(root, **kwargs):
            report = kwargs.get("test_execution", {})
            return SimpleNamespace(ok=report.get("status", "APROVADO") == "APROVADO",
                                   problems=["critical gate failed"])

        with patch.object(builder, "CRITICAL_TEST_FILES", (name,)), \
                patch.object(builder, "run_release_diagnostics", side_effect=diagnostic), \
                patch.object(builder, "build_clean_update_zip") as package:
            with self.assertRaisesRegex(RuntimeError, "Gate crítico reprovado"):
                builder.build_validated_update(self.root, output)
            self.assertFalse(output.exists())
            output.write_bytes(b"previous artifact")
            with self.assertRaisesRegex(RuntimeError, "Gate crítico reprovado"):
                builder.build_validated_update(self.root, output)
            self.assertEqual(output.read_bytes(), b"previous artifact")
            package.assert_not_called()


if __name__ == "__main__":
    unittest.main()
