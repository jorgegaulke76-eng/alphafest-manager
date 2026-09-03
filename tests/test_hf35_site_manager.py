import unittest
from pathlib import Path

from site_manager_service import avaliar_produto_site, resumir_catalogo_site, ordenar_produtos_site

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class HF35SiteManagerTests(unittest.TestCase):
    def test_site_service_preserva_produto_e_avalia_prontidao(self):
        produto = {
            "Nome": "Topo",
            "Descricao": "Personalizado",
            "Imagens": ["foto.jpg"],
            "Preco": "15,00",
            "PublicarSite": True,
            "Destaque": True,
        }
        antes = dict(produto)
        leitura = avaliar_produto_site(produto)
        self.assertEqual(produto, antes)
        self.assertTrue(leitura["pronto"])
        self.assertTrue(leitura["publicar_site"])
        self.assertTrue(leitura["destaque"])

    def test_preco_nao_bloqueia_personalizado_sob_consulta(self):
        leitura = avaliar_produto_site({
            "Nome": "Projeto sob medida",
            "DescricaoCurta": "Feito conforme a necessidade",
            "Imagens": ["foto.webp"],
            "PublicarSite": True,
        })
        self.assertTrue(leitura["pronto"])
        self.assertIn("Valor sob consulta", leitura["avisos"])

    def test_resumo_separa_marcados_e_candidatos(self):
        catalogo = [
            {"Nome": "A", "Descricao": "ok", "Imagens": ["a.jpg"], "PublicarSite": True},
            {"Nome": "B", "Descricao": "ok", "Imagens": ["b.jpg"], "PublicarSite": False},
            {"Nome": "C", "Descricao": "", "Imagens": [], "PublicarSite": True},
        ]
        resumo = resumir_catalogo_site(catalogo)
        self.assertEqual(resumo["marcados_site"], 2)
        self.assertEqual(resumo["prontos_marcados"], 1)
        self.assertEqual(resumo["revisar_marcados"], 1)
        self.assertEqual(resumo["prontos_nao_marcados"], 1)

    def test_ordem_prioriza_publicados_e_destaques(self):
        catalogo = [
            {"Nome": "B", "Descricao": "ok", "Imagens": ["b.jpg"]},
            {"Nome": "A", "Descricao": "ok", "Imagens": ["a.jpg"], "PublicarSite": True, "Destaque": True},
        ]
        ordenados = ordenar_produtos_site(catalogo)
        self.assertEqual(ordenados[0]["nome"], "A")
        self.assertEqual(ordenados[0]["indice_catalogo"], 1)

    def test_navegacao_e_permissoes_dos_dois_perfis(self):
        self.assertIn('("site", "🌐 Site AlphaFest")', APP)
        self.assertIn('"📢 Marketing": ["site", "crescimento", "calendario"]', APP)
        self.assertIn('{"catalogo", "site"}', APP)
        self.assertIn('"biblioteca_3d", "site"', APP)
        self.assertIn('not in {"historico", "catalogo", "fluxo", "site"}', APP)
        self.assertIn('k7.button("🌐 Site AlphaFest"', APP)

    def test_central_usa_catalogo_e_scan_existentes_sem_banco_paralelo(self):
        self.assertIn('if pagina_atual == "site":', APP)
        self.assertIn('catalogo_site_hf35 = carregar_catalogo()', APP)
        self.assertIn('marketing_site_hf35 = carregar_marketing()', APP)
        self.assertIn('marketing_site_hf35["acervo_site_ultimo_scan"] = novo_scan_hf35', APP)
        self.assertIn('thu_site_analisar_acervo(42)', APP)
        self.assertNotIn('site_db.json', APP)
        self.assertNotIn('salvar_site_db', APP)

    def test_hf35_nao_publica_site_automaticamente(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('Nada será publicado automaticamente', trecho)
        self.assertIn('A HF35 não substitui nem publica o site atual', trecho)
        self.assertNotIn('publish_catalog_html(', trecho)


if __name__ == "__main__":
    unittest.main()
