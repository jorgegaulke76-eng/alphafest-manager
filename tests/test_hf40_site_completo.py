import io
import json
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote

from site_completo_service import gerar_html_site_completo
from site_staging_service import gerar_pacote_staging, preparar_html_staging, resumo_staging

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class HF40SiteCompletoTests(unittest.TestCase):
    def _catalogo(self):
        return [
            {
                "Nome": "Bandeirola tecido com borda",
                "Categoria": "Brinde / Decorativo",
                "Descricao": "Personalizada para festas e eventos.",
                "Imagens": ["https://example.com/bandeirola.jpg"],
                "PublicarSite": True,
                "Destaque": True,
                "Preco": "22,00",
                "ExibirPrecoSite": True,
            },
            {
                "Nome": "Adesivo DTF UV",
                "Categoria": "Adesivo DTF UV",
                "Descricao": "Personalização resistente.",
                "Imagens": ["https://example.com/dtf.jpg"],
                "PublicarSite": True,
                "Preco": "55,00",
                "ExibirPrecoSite": False,
            },
        ]

    def _empresa(self):
        return {
            "nome": "Alphafest",
            "subtitulo": "Personalizados & Balões",
            "slogan": "O poder de estar presente em cada presente...",
            "whatsapp_catalogo": "11972949533",
            "celular": "(11) 97294-9533",
            "email": "alphafesti@gmail.com",
            "endereco": "Avenida Manoel Verginio de Almeida, 442 - Alto Santa Cruz - Itatiba - SP",
            "cep": "13251-530",
            "cidade": "Itatiba",
            "uf": "SP",
        }

    def test_site_completo_mantem_vitrine_e_acrescenta_cinco_areas(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=True)
        self.assertIn("PRÉVIA INTERNA HF40", pagina)
        for alvo in ['href="#inicio"', 'href="#produtos"', 'href="#servicos"', 'href="#quem-somos"', 'href="#contato"']:
            self.assertIn(alvo, pagina)
        self.assertIn('id="servicos"', pagina)
        self.assertIn('id="quem-somos"', pagina)
        self.assertIn('id="contato"', pagina)
        self.assertIn("Gráfica rápida", pagina)
        self.assertIn("Impressão 3D", pagina)
        self.assertIn("Gravação a laser", pagina)
        self.assertIn("Bandeirola tecido com borda", pagina)
        self.assertIn("R$ 22,00", pagina)
        self.assertNotIn("R$ 55,00", pagina)

    def test_contato_vem_da_configuracao_oficial_e_whatsapp_funciona(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=False)
        texto = unquote(pagina)
        self.assertIn("(11) 97294-9533", pagina)
        self.assertIn("alphafesti@gmail.com", pagina)
        self.assertIn("Avenida Manoel Verginio de Almeida, 442", pagina)
        self.assertIn("CEP 13251-530", pagina)
        self.assertIn("https://wa.me/5511972949533", pagina)
        self.assertIn("novo site da AlphaFest", texto)
        self.assertIn("google.com/maps/search", pagina)

    def test_site_completo_nao_cria_segunda_fonte_de_produtos(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('_site_gerar_html_completo(', trecho)
        self.assertIn('catalogo_site_hf35', trecho)
        self.assertIn('empresa_vitrine_hf36 = carregar_config_empresa()', trecho)
        self.assertNotIn('save_document("site_', trecho)
        self.assertNotIn('catalogo_site_db', trecho)

    def test_staging_hf40_continua_sem_dns_e_reflete_workers_static_assets(self):
        pagina = gerar_html_site_completo(self._catalogo(), self._empresa(), modo_preview=False)
        dados = gerar_pacote_staging(pagina, total_produtos=2, versao_manager="20.4.9-I8.13.5-HF40")
        with zipfile.ZipFile(io.BytesIO(dados), "r") as zf:
            nomes = set(zf.namelist())
            self.assertNotIn("CNAME", nomes)
            self.assertIn("DEPLOY-CLOUDFLARE-WORKERS.txt", nomes)
            html_staging = zf.read("index.html").decode("utf-8")
            self.assertIn("SITE PARALELO HF40", html_staging)
            self.assertIn('name="robots" content="noindex,nofollow,noarchive"', html_staging)
            self.assertIn('id="quem-somos"', html_staging)
            status = json.loads(zf.read("STATUS-STAGING.json").decode("utf-8"))
            self.assertEqual(status["hospedagem_planejada"], "Cloudflare Workers · Static Assets")
            self.assertFalse(status["dns_alterado"])
            self.assertEqual(status["produtos_snapshot"], 2)
            deploy = zf.read("DEPLOY-CLOUDFLARE-WORKERS.txt").decode("utf-8")
            self.assertIn("*.workers.dev", deploy)
            self.assertIn("New deployment", deploy)

    def test_ui_manager_expoe_hf40_sem_publicar_dominio(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('"🌐 Site completo — prévia HF40"', trecho)
        self.assertIn('"🚧 Site paralelo / staging — HF40"', trecho)
        self.assertIn('alphafest-site-staging-hf40.zip', trecho)
        self.assertIn('"DNS alterado", "NÃO"', trecho)
        self.assertIn('Cloudflare Workers · Static Assets', trecho)
        self.assertNotIn('publish_catalog_html(', trecho)


if __name__ == "__main__":
    unittest.main()
