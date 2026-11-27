"""Regressão offline do pacote de atualização, sem executar o Manager."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zipfile import ZipFile

from build_update_package import run_critical_tests
from release_diagnostics import CRITICAL_PYTHON_FILES
from update_hygiene import REQUIRED_RUNTIME_FILES, build_clean_update_zip


class TestUpdatePackageHF52(unittest.TestCase):
    def test_real_zip_keeps_release_metadata_and_excludes_runtime_data(self):
        source = Path(__file__).resolve().parent
        version = "20.4.9-I8.13.5-HF53.3-HF8-HF65.24.52"
        release = {
            "version": version,
            "created_at": "2026-11-25T10:00:00-03:00",
            "timezone": "America/Sao_Paulo",
            "description": "Metadados de teste da atualização do site.",
        }
        excluded = (
            "catalogo_db.json",
            "historico_orcamentos.json",
            "clientes_db.json",
            "producao_db.json",
            "empresa_config.json",
            "usuarios_config.json",
            "integracoes_db.json",
            "site_home_content_db.json",
            "configuracao_personalizada.json",
            "release_info.json",
            "dados/catalogo_db.json",
            ".env",
            "secrets.toml",
            ".streamlit/secrets.toml",
            ".git/RELEASE_INFO.json",
            "tests/RELEASE_INFO.json",
        )

        with tempfile.TemporaryDirectory(prefix="alphafest_update_hf52_") as temp:
            root = Path(temp) / "alphafest-manager-main"
            root.mkdir()
            # Somente os fontes/assets exigidos pelo diagnóstico são copiados.
            # O builder compila fontes; não importa nem executa app.py.
            required = REQUIRED_RUNTIME_FILES | set(CRITICAL_PYTHON_FILES)
            for relative in sorted(required):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, target)

            for name in ("VERSAO", "VERSAO.txt"):
                (root / name).write_text(version + "\n", encoding="utf-8")
            release_bytes = json.dumps(release, ensure_ascii=False).encode("utf-8")
            (root / "RELEASE_INFO.json").write_bytes(release_bytes)

            for relative in excluded:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("DADO_DE_TESTE_QUE_NAO_DEVE_SER_EMPACOTADO", encoding="utf-8")
            # Um manifesto antigo deve ser substituído, nunca reaproveitado.
            (root / "UPDATE_MANIFEST.json").write_text(
                '{"version":"antiga","marcador":"manifesto_obsoleto"}', encoding="utf-8"
            )

            output = Path(temp) / "atualizacao.zip"
            result = build_clean_update_zip(root, output)
            self.assertTrue(result["audit"]["ok"])
            with ZipFile(output) as archive:
                initial_manifest = json.loads(archive.read(root.name + "/UPDATE_MANIFEST.json"))
                self.assertEqual(initial_manifest["validation"]["tests"]["execution_status"], "NAO_EXECUTADO")
                self.assertEqual(initial_manifest["validation"]["tests"]["approved_files"], 0)

            # O helper aceita evidência real de uma suíte explícita pequena, sem
            # disparar novamente o gate oficial nem depender da versão atual.
            (root / "test_gate_fixture.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
            execution = run_critical_tests(root, test_files=("test_gate_fixture.py",))
            self.assertEqual(execution["status"], "APROVADO")
            result = build_clean_update_zip(root, output, test_execution=execution)
            self.assertTrue(result["audit"]["ok"])

            prefix = root.name + "/"
            with ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertEqual(names.count(prefix + "RELEASE_INFO.json"), 1)
                self.assertEqual(archive.read(prefix + "RELEASE_INFO.json"), release_bytes)
                for relative in excluded:
                    with self.subTest(excluded=relative):
                        self.assertNotIn(prefix + relative, names)

                self.assertEqual(names.count(prefix + "UPDATE_MANIFEST.json"), 1)
                manifest = json.loads(archive.read(prefix + "UPDATE_MANIFEST.json"))
                self.assertEqual(manifest["version"], version)
                self.assertNotIn("marcador", manifest)
                self.assertEqual(manifest["validation"]["tests"]["found_files"], 1)
                self.assertEqual(manifest["validation"]["tests"]["executed_files"], 1)
                self.assertEqual(manifest["validation"]["tests"]["approved_files"], 1)
                self.assertEqual(manifest["validation"]["tests"]["execution_status"], "APROVADO")
                self.assertEqual(manifest["validation"]["tests"]["execution"]["source_fingerprint"], execution["source_fingerprint"])
                entries = {item["path"]: item for item in manifest["files"]}
                self.assertNotIn("UPDATE_MANIFEST.json", entries)
                self.assertEqual(manifest["file_count"], len(names) - 1)
                self.assertEqual(
                    entries["RELEASE_INFO.json"]["sha256"],
                    hashlib.sha256(release_bytes).hexdigest(),
                )
                self.assertEqual(entries["RELEASE_INFO.json"]["size"], len(release_bytes))
                for relative in excluded:
                    with self.subTest(manifest_excluded=relative):
                        self.assertNotIn(relative, entries)

            approved_bytes = output.read_bytes()
            failed_execution = dict(execution, status="REPROVADO")
            with self.assertRaisesRegex(RuntimeError, "Diagnóstico do pacote reprovado"):
                build_clean_update_zip(root, output, test_execution=failed_execution)
            self.assertEqual(output.read_bytes(), approved_bytes)


if __name__ == "__main__":
    unittest.main()
