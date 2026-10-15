import unittest
from site_manager_service import avaliar_produto_site
from site_vitrine_service import gerar_html_vitrine

class TestModalidadesPreco(unittest.TestCase):
    def produto(self, modalidade=None):
        p = {"Nome": "Caneca personalizada", "Descricao": "Caneca de teste", "Preco": "38,00", "Imagens": ["https://example.com/caneca.jpg"], "PublicarSite": True, "Ativo": True}
        if modalidade is not None:
            p["ModalidadePrecoSite"] = modalidade
        return p

    def test_default_is_quote(self):
        item = avaliar_produto_site(self.produto())
        self.assertEqual(item["modalidade_preco_site"], "sob_orcamento")
        self.assertFalse(item["exibir_preco_site"])

    def test_fixed(self):
        item = avaliar_produto_site(self.produto("fixo"))
        self.assertTrue(item["exibir_preco_site"])

    def test_starting_at(self):
        item = avaliar_produto_site(self.produto("a_partir"))
        self.assertEqual(item["modalidade_preco_site"], "a_partir")

    def test_legacy_explicit_display_remains(self):
        p = self.produto()
        p["ExibirPrecoSite"] = True
        self.assertEqual(avaliar_produto_site(p)["modalidade_preco_site"], "fixo")

if __name__ == "__main__":
    unittest.main()
