"""Testes da sincronização do rodapé do AlphaFest Manager."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from scripts.sincronizar_release_rodape import sincronizar_release

ORIGINAL = "20.4.9-I8.13.5-HF53.3-HF8-HF65.24.61-HF80"


class SincronizacaoRodape(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "VERSAO").write_text(ORIGINAL + "\n", encoding="utf-8")
        (self.root / "VERSAO.txt").write_text(ORIGINAL + "\n", encoding="utf-8")
        (self.root / "RELEASE_INFO.json").write_text(json.dumps({
            "version": ORIGINAL,
            "created_at": "2026-11-28T15:00:04Z",
            "timezone": "America/Sao_Paulo",
            "description": "HF80",
        }), encoding="utf-8")

    def sync(self, message):
        return sincronizar_release(self.root, message, "a"*40, "2026-11-29T13:01:02Z")

    def test_atualiza_todos_os_arquivos_para_hf81(self):
        self.assertTrue(self.sync("HF81: melhoria no site (#62)"))
        esperado = ORIGINAL[:-4] + "HF81"
        self.assertEqual((self.root/"VERSAO").read_text().strip(), esperado)
        self.assertEqual((self.root/"VERSAO.txt").read_text().strip(), esperado)
        info = json.loads((self.root/"RELEASE_INFO.json").read_text())
        self.assertEqual(info["version"], esperado)
        self.assertEqual(info["created_at"], "2026-11-29T13:01:02Z")
        self.assertEqual(info["source_commit"], "a"*40)

    def test_nao_muda_pins_historicos_nem_rebaixa(self):
        for msg in ("fix HF65.24.87 legado", "HF79: regressao", "chore: ajuste normal"):
            self.assertFalse(self.sync(msg))
        self.assertEqual((self.root/"VERSAO").read_text().strip(), ORIGINAL)

    def test_rejeita_metadados_divergentes(self):
        (self.root/"VERSAO").write_text("HF67\n")
        with self.assertRaisesRegex(ValueError, "divergentes"):
            self.sync("HF81")

if __name__ == "__main__":
    unittest.main()
