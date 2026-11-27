"""Contrato dos campos oficiais na HF60. Nao executa app.py nem acessa Supabase."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class IntegracaoCatalogoHF60(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texto = (ROOT / "app.py").read_text(encoding="utf-8")
        cls.arvore = ast.parse(cls.texto)

    def test_formulario_oficial_tem_seletor_e_salva_modalidade(self):
        self.assertIn('modalidade_preco_site = st.selectbox(', self.texto)
        self.assertIn('"ModalidadePrecoSite": modalidade_preco_site', self.texto)
        self.assertIn('exibir_preco_site = modalidade_preco_site != "sob_orcamento"', self.texto)

    def test_edicao_rapida_nao_descarta_modo_a_partir(self):
        self.assertIn('"💰 Preço no site": st.column_config.SelectboxColumn(', self.texto)
        self.assertIn('PRECO_MODALIDADES_HF60[preco_modalidade_atual_hf60(_prod_hf492)]', self.texto)
        self.assertIn('_novo_preco_hf492 != preco_modalidade_atual_hf60(_produto_hf492)', self.texto)
        self.assertIn('_registro_hf492["ModalidadePrecoSite"] = _preco_hf492', self.texto)
        self.assertIn('_registro_hf492["ExibirPrecoSite"] = _preco_hf492 != "sob_orcamento"', self.texto)

    def test_sem_checkbox_legado_conflitante(self):
        self.assertNotIn('key=f"cat_exibir_preco_site_{sufixo}"', self.texto)
        self.assertIn('key=f"cat_modalidade_preco_site_{sufixo}"', self.texto)

if __name__ == "__main__":
    unittest.main()
