"""HF74: verifica organizacao sem importar Streamlit ou acessar dados."""
import ast
from pathlib import Path
import unittest


class InterfaceHF74(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fonte = Path("central_oportunidades.py").read_text(encoding="utf-8")
        cls.arvore = ast.parse(cls.fonte)

    def test_painel_e_abas_aparecem_na_ordem_correta(self):
        fonte = self.fonte
        painel = fonte.index('st.markdown("#### 📅 Painel comercial do dia")')
        detalhes = fonte.index('st.expander("📂 Detalhes de cadastro e retornos (HF70)"')
        abas = fonte.index('guia_hf74, consulta_hf74 = st.tabs(')
        self.assertLess(painel, detalhes)
        self.assertLess(detalhes, abas)
        self.assertIn('with guia_hf74:', fonte)
        self.assertIn('with consulta_hf74:', fonte)\n        self.assertIn('with cadastro_hf74:', fonte)\n        self.assertIn('with retornos_hf74:', fonte)\n        self.assertNotIn('with st.expander("📂 Conferências cadastrais", expanded=False):', fonte)

    def test_mantem_as_funcoes_e_controles_de_consulta(self):
        fonte = self.fonte
        for texto in (
            'quadro_prioridades_hf70(', 'resumo_diario_hf71(',
            'roteiro_diario_hf72(', 'consultar_categoria_hf73(',
            'hf71_resumo_diario_txt', 'hf72_roteiro_diario_txt',
            'hf73_categoria_roteiro', 'hf73_busca_proposta',
            'opp_retornos_resumo_txt',
        ):
            self.assertIn(texto, fonte)

    def test_nao_adiciona_escrita_automatica_nos_modulos_de_consulta(self):
        for modulo in ("resumo_diario_hf71.py", "roteiro_diario_hf72.py",
                       "consulta_roteiro_hf73.py"):
            ast.parse(Path(modulo).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
