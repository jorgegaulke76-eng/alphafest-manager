import unittest
from site_manager_service import avaliar_produto_site
from site_vitrine_service import gerar_html_vitrine
from catalogo_modalidade_preco_service import aplicar_modalidade

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

    def test_vitrine_renders_three_modes(self):
        for modo, esperado in (("fixo", "R$ 38,00"), ("a_partir", "A partir de R$ 38,00"), ("sob_orcamento", "Consultar valores")):
            with self.subTest(modo=modo):
                html = gerar_html_vitrine([self.produto(modo)], {"whatsapp_catalogo": "11999999999"})
                self.assertIn(esperado, html)

    def test_price_value_is_preserved(self):
        produto = self.produto()
        self.assertTrue(aplicar_modalidade(produto, "a_partir"))
        self.assertEqual(produto["Preco"], "38,00")
        self.assertTrue(produto["ExibirPrecoSite"])
        aplicar_modalidade(produto, "sob_orcamento")
        self.assertEqual(produto["Preco"], "38,00")
        self.assertFalse(produto["ExibirPrecoSite"])

    def test_legacy_explicit_display_remains(self):
        p = self.produto()
        p["ExibirPrecoSite"] = True
        self.assertEqual(avaliar_produto_site(p)["modalidade_preco_site"], "fixo")

if __name__ == "__main__":
    unittest.main()
