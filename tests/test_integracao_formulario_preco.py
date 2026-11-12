"""Valida integração do seletor nos formulários sem importar app.py nem acessar Supabase."""
import ast
from pathlib import Path
import unittest
from catalogo_modalidade_preco_service import aplicar_modalidade, modalidade_atual

ROOT = Path(__file__).resolve().parents[1]
CODE = (ROOT / "app.py").read_text(encoding="utf-8")

class TestIntegracaoFormularioPreco(unittest.TestCase):
    def test_app_python_valido(self):
        ast.parse(CODE)

    def test_cadastro_e_edicao_exibem_seletor(self):
        self.assertIn('"Como mostrar o preço no site"', CODE)
        self.assertIn('key=f"cat_modalidade_preco_site_{sufixo}"', CODE)
        self.assertIn('"ModalidadePrecoSite": modalidade_preco_site', CODE)
        self.assertIn('"ExibirPrecoSite": modalidade_preco_site != "sob_orcamento"', CODE)

    def test_edicao_rapida_preserva_modalidade(self):
        self.assertIn('"💰 Preço no site"', CODE)
        self.assertIn('_cat_aplicar_modalidade(_registro_hf492, _modo_hf492)', CODE)

    def test_compatibilidade_sem_alterar_preco(self):
        produto = {"Nome":"PRODUTO TESTE","Preco":"35,00","ExibirPrecoSite":False}
        for modo in ("fixo","a_partir","sob_orcamento"):
            aplicar_modalidade(produto, modo)
            self.assertEqual(modalidade_atual(produto), modo)
            self.assertEqual(produto["Preco"], "35,00")

if __name__ == "__main__":
    unittest.main()
