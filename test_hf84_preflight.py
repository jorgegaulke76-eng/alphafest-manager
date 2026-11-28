"""HF84: verificacao de release sem segredos, banco, rede ou escrita."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.hf84_preflight_seguranca import verificar

VERSION = "20.4.9-I8.13.5-HF53.3-HF8-HF65.24.61-HF83"


class GateHF84(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("VERSAO", VERSION + "\n")
        self.write("VERSAO.txt", VERSION + "\n")
        self.write("RELEASE_INFO.json", json.dumps({
            "version": VERSION, "created_at": "2026-11-28T17:14:18Z",
            "source_commit": "a" * 40,
        }))
        self.write("config.py", '_VERSION_FILE = _BASE_DIR / "VERSAO.txt"\nAPP_VERSION = _read_app_version()\n')
        self.write("scripts/sincronizar_release_rodape.py", "def sincronizar_release(): pass")
        self.write(".github/workflows/sincronizar-rodape-manager.yml", "sincronizar_release_rodape.py")
        self.write(".gitignore", "\n".join((
            ".env", ".streamlit/secrets.toml", "backups/",
            "clientes_db.json", "historico_orcamentos.json", "usuarios_config.json"
        )))
        self.write("HF84_FUNDACAO_SEGURA.md", "Roteiro de recuperacao")

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    def test_hf83_sincronizada_e_valida(self):
        r = verificar(self.root)
        self.assertTrue(r["ok"], r["erros"])
        self.assertEqual(r["versao"], VERSION)
        self.assertEqual(r["erros"], [])

    def test_hf84_valida_apos_sincronizacao(self):
        version = VERSION[:-4] + "HF84"
        for path in ("VERSAO", "VERSAO.txt"):
            self.write(path, version + "\n")
        meta = json.loads((self.root / "RELEASE_INFO.json").read_text())
        meta["version"] = version
        self.write("RELEASE_INFO.json", json.dumps(meta))
        self.assertTrue(verificar(self.root, hf_minima=84)["ok"])

    def test_divergencia_de_rodape_bloqueia(self):
        self.write("VERSAO.txt", VERSION[:-4] + "HF82\n")
        r = verificar(self.root)
        self.assertFalse(r["ok"])
        self.assertFalse(r["checks"]["versao_identica"]["ok"])

    def test_metadados_sem_sha_bloqueiam(self):
        self.write("RELEASE_INFO.json", json.dumps({
            "version": VERSION, "created_at": "2026-11-28",
            "source_commit": "invalido",
        }))
        r = verificar(self.root)
        self.assertFalse(r["checks"]["sha_da_release"]["ok"])
        self.assertFalse(r["checks"]["data_da_release"]["ok"])

    def test_minimo_nao_permite_regressao(self):
        self.assertFalse(verificar(self.root, hf_minima=84)["ok"])

    def test_protecao_de_segredos_obrigatoria(self):
        self.write(".gitignore", ".env\nbackups/\n")
        r = verificar(self.root)
        self.assertFalse(r["checks"]["ignore_essencial"]["ok"])

    def test_preflight_nao_altera_arquivos(self):
        files = [self.root / x for x in ("VERSAO", "VERSAO.txt", "RELEASE_INFO.json")]
        before = [x.read_bytes() for x in files]
        verificar(self.root)
        self.assertEqual(before, [x.read_bytes() for x in files])


if __name__ == "__main__":
    unittest.main()
