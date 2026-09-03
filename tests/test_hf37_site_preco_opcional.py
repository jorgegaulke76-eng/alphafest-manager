import unittest
from pathlib import Path

from site_manager_service import avaliar_produto_site
from site_vitrine_service import gerar_html_vitrine

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class HF37PrecoOpcionalSiteTests(unittest.TestCase):
    def _empresa(self):
        return {"nome": "AlphaFest", "whatsapp_catalogo": "11999998888"}

    def test_produto_antigo_sem_campo_oculta_preco_por_padrao(self):
        leitura = avaliar_produto_site({
            "Nome": "Copo", "Descricao": "Personalizado", "Imagens": ["https://x/copo.jpg"],
            "Preco": "22,00", "PublicarSite": True,
        })
        self.assertFalse(leitura["exibir_preco_site"])
        pagina = gerar_html_vitrine([{
            "Nome": "Copo", "Descricao": "Personalizado", "Imagens": ["https://x/copo.jpg"],
            "Preco": "22,00", "PublicarSite": True,
        }], self._empresa())
        self.assertNotIn("R$ 22,00", pagina)
        self.assertIn("Pedir orçamento", pagina)
        self.assertIn("card-footer no-price", pagina)

    def test_preco_so_aparece_quando_campo_esta_ativo(self):
        pagina = gerar_html_vitrine([{
            "Nome": "Bandeirola", "Descricao": "Personalizada", "Imagens": ["https://x/b.jpg"],
            "Preco": "22,00", "PublicarSite": True, "ExibirPrecoSite": True,
        }], self._empresa())
        self.assertIn("R$ 22,00", pagina)
        self.assertNotIn("card-footer no-price", pagina)

    def test_flag_ativa_sem_preco_nao_inventa_valor(self):
        pagina = gerar_html_vitrine([{
            "Nome": "Projeto especial", "Descricao": "Sob medida", "Imagens": ["https://x/p.jpg"],
            "PublicarSite": True, "ExibirPrecoSite": True,
        }], self._empresa())
        self.assertNotIn("Sob consulta", pagina)
        self.assertIn("Pedir orçamento", pagina)

    def test_catalogo_tem_controle_individual_e_persiste_na_fonte_unica(self):
        self.assertIn('"Exibir preço no site"', APP)
        self.assertIn('item_edicao.get("ExibirPrecoSite", False)', APP)
        self.assertIn('"ExibirPrecoSite": bool(exibir_preco_site)', APP)
        self.assertIn('"preço oculto no site"', APP)

    def test_hf37_continua_sem_publicacao_automatica(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('"🌐 Site completo — prévia HF40"', trecho)
        self.assertNotIn('publish_catalog_html(', trecho)


if __name__ == "__main__":
    unittest.main()
