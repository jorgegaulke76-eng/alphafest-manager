import io
import json
import unittest
import zipfile
from pathlib import Path

from site_completo_service import gerar_html_site_completo
from site_production_service import gerar_pacote_producao, preparar_html_producao, resumo_producao


class HF42SiteProducaoTests(unittest.TestCase):
    def _catalogo(self):
        return [{
            "Nome": "Bandeirola",
            "Categoria": "Brinde / Decorativo",
            "Descricao": "Personalizada.",
            "Imagens": ["https://example.com/b.jpg"],
            "PublicarSite": True,
            "Preco": "22,00",
            "ExibirPrecoSite": True,
        }]

    def _empresa(self):
        return {
            "nome": "AlphaFest",
            "subtitulo": "Personalizados & Balões",
            "slogan": "O poder de estar presente em cada presente...",
            "whatsapp_catalogo": "11972949533",
            "celular": "(11) 97294-9533",
            "email": "alphafesti@gmail.com",
            "endereco": "Itatiba - SP",
            "cidade": "Itatiba",
            "uf": "SP",
        }

    def test_html_publico_remove_notas_internas_do_manager(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=False)
        self.assertNotIn("PRÉVIA INTERNA", pagina)
        self.assertNotIn("site anterior", pagina)
        self.assertNotIn("configuração oficial da empresa no AlphaFest Manager", pagina)
        self.assertNotIn("Catálogo oficial do Manager", pagina)
        self.assertIn("Ideias selecionadas para você", pagina)

    def test_preparacao_producao_libera_indexacao_e_canonical(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=False)
        publico = preparar_html_producao(pagina)
        self.assertIn('name="robots" content="index,follow,max-image-preview:large"', publico)
        self.assertIn('rel="canonical" href="https://alphafest.com.br/"', publico)
        self.assertNotIn("SITE PARALELO HF40", publico)
        self.assertNotIn("noindex,nofollow,noarchive", publico)

    def test_pacote_final_tem_robots_sitemap_e_sem_staging(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=False)
        data = gerar_pacote_producao(pagina, total_produtos=1)
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            nomes = set(zf.namelist())
            self.assertEqual(nomes, {
                "index.html", "404.html", "robots.txt", "sitemap.xml", "_headers",
                "README-PRODUCAO.txt", "STATUS-PRODUCAO.json",
            })
            self.assertNotIn("CNAME", nomes)
            self.assertIn("Allow: /", zf.read("robots.txt").decode("utf-8"))
            self.assertIn("https://alphafest.com.br/", zf.read("sitemap.xml").decode("utf-8"))
            self.assertNotIn("X-Robots-Tag: noindex", zf.read("_headers").decode("utf-8"))
            self.assertNotIn("HOMOLOGAÇÃO", zf.read("index.html").decode("utf-8"))

    def test_status_producao_reflete_estado_homologado(self):
        r = resumo_producao(total_produtos=16)
        self.assertEqual(r["zona_cloudflare"], "Active")
        self.assertTrue(r["dns_cloudflare"])
        self.assertTrue(r["dominio_raiz_conectado"])
        self.assertEqual(r["www"], "301 → alphafest.com.br")
        self.assertEqual(r["produtos_snapshot"], 16)

    def test_ui_manager_expoe_download_final_hf42(self):
        app = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('"🚀 Produção oficial — HF44"', app)
        self.assertIn('alphafest-site-producao-hf44.zip', app)
        self.assertIn('versao_manager="20.4.9-I8.13.5-HF44"', app)
        self.assertIn('_site_gerar_pacote_producao(', app)

    def test_pacote_final_nao_altera_dns(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=False)
        data = gerar_pacote_producao(pagina)
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            readme = zf.read("README-PRODUCAO.txt").decode("utf-8")
            self.assertIn("NÃO altera DNS", readme)
            self.assertIn("não altera DNS, nameservers, MX, webmail ou Custom Domains".casefold(), readme.casefold())


if __name__ == "__main__":
    unittest.main()
