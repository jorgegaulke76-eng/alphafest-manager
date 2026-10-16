"""Teste de interface Streamlit sobre o cadastro isolado, sem banco online.

Usa streamlit.testing.v1.AppTest e um catálogo fictício salvo em tempfile.
"""
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "demo_cadastro_preco_isolado.py"

class TestInterfaceCadastroIsolado(unittest.TestCase):
    def test_cadastro_edicao_e_leitura_pelo_formulario(self):
        app = AppTest.from_file(str(SCRIPT), default_timeout=20).run()
        self.assertFalse(app.exception, str(app.exception))
        self.assertIn("Cadastrar produto", [t.label for t in app.tabs])

        app.text_input[0].set_value("Produto fictício UI")
        app.text_input[1].set_value("38,00")
        app.button[0].click().run()
        self.assertFalse(app.exception, str(app.exception))
        self.assertTrue(any("Produto fictício salvo" in x.message for x in app.success))

        # O teste deve verificar o arquivo temporário, não somente o rótulo visível.
        arquivo = Path(app.session_state["catalogo_teste_pasta"]) / "catalogo_ficticio.json"
        import json
        itens = json.loads(arquivo.read_text(encoding="utf-8"))
        self.assertEqual(itens[0]["Preco"], "38,00")
        self.assertEqual(itens[0]["ModalidadePrecoSite"], "sob_orcamento")

if __name__ == "__main__":
    unittest.main()
