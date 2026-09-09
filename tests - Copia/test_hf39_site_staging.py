import io
import json
import unittest
import zipfile
from pathlib import Path

from site_staging_service import gerar_pacote_staging, preparar_html_staging, resumo_staging

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class HF40SiteStagingRegressionTests(unittest.TestCase):
    def test_staging_injeta_noindex_e_aviso_sem_tocar_dominio(self):
        html = "<!doctype html><html><head><title>x</title></head><body>ok</body></html>"
        pagina = preparar_html_staging(html)
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', pagina)
        self.assertIn("SITE PARALELO HF40", pagina)
        self.assertIn("NÃO PUBLICADO EM ALPHAFEST.COM.BR", pagina)

    def test_pacote_nao_contem_cname_e_traz_rollback(self):
        dados = gerar_pacote_staging("<html><head></head><body>AlphaFest</body></html>", total_produtos=16)
        with zipfile.ZipFile(io.BytesIO(dados), "r") as zf:
            nomes = set(zf.namelist())
            self.assertNotIn("CNAME", nomes)
            self.assertIn("index.html", nomes)
            self.assertIn("robots.txt", nomes)
            self.assertIn("_headers", nomes)
            self.assertIn("CHECKLIST-VIRADA-DOMINIO.txt", nomes)
            self.assertIn("STATUS-STAGING.json", nomes)
            self.assertEqual(zf.read("robots.txt").decode("utf-8"), "User-agent: *\nDisallow: /\n")
            status = json.loads(zf.read("STATUS-STAGING.json").decode("utf-8"))
            self.assertFalse(status["dns_alterado"])
            self.assertFalse(status["publicado_dominio_final"])
            self.assertEqual(status["dominio_final"], "alphafest.com.br")
            checklist = zf.read("CHECKLIST-VIRADA-DOMINIO.txt").decode("utf-8")
            self.assertIn("rollback", checklist.lower())

    def test_resumo_staging_preserva_endereco(self):
        resumo = resumo_staging(total_produtos=16)
        self.assertEqual(resumo["dominio_final"], "alphafest.com.br")
        self.assertEqual(resumo["hospedagem_planejada"], "Cloudflare Workers · Static Assets")
        self.assertFalse(resumo["dns_alterado"])
        self.assertEqual(resumo["produtos_snapshot"], 16)

    def test_app_expoe_staging_sem_publicacao_dns(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('"🚧 Site paralelo / staging — HF40"', trecho)
        self.assertIn('"Cloudflare Workers · Static Assets"', trecho)
        self.assertIn('"DNS alterado", "NÃO"', trecho)
        self.assertIn('alphafest-site-staging-hf40.zip', trecho)
        self.assertIn('_site_gerar_pacote_staging(', trecho)
        self.assertIn('Nenhuma dessas etapas de DNS é executada automaticamente', trecho)
        self.assertNotIn('CNAME(', trecho)


if __name__ == "__main__":
    unittest.main()
