"""Testes locais de persistencia em arquivo temporario, sem Supabase.

Nao importa app.py nem conecta ao banco de producao.
"""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from catalogo_modalidade_preco_service import aplicar_modalidade, modalidade_atual
from site_manager_service import avaliar_produto_site
from site_vitrine_service import gerar_html_vitrine


class TestPersistenciaPrecoLocal(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="alphafest_homologacao_")
        self.addCleanup(self.temp.cleanup)
        self.arquivo = Path(self.temp.name) / "catalogo_db.json"
        self.produto = {
            "Nome": "Caneca ficticia - homologacao",
            "Descricao": "Caneca usada exclusivamente em testes.",
            "Preco": "38,00",
            "Imagens": ["https://example.com/teste.jpg"],
            "Ativo": True,
            "PublicarSite": True,
            "ExibirPrecoSite": False,
            "Estoque": 23,
        }
        self.original = copy.deepcopy(self.produto)

    def salvar(self, itens):
        self.arquivo.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")

    def recarregar(self):
        return json.loads(self.arquivo.read_text(encoding="utf-8"))

    def test_cadastro_e_reabertura_sob_orcamento(self):
        self.salvar([self.produto])
        reaberto = self.recarregar()[0]
        self.assertEqual(modalidade_atual(reaberto), "sob_orcamento")
        self.assertEqual(reaberto["Preco"], "38,00")
        self.assertIn("Consultar valores", gerar_html_vitrine([reaberto], {}))

    def test_edicao_salvar_reabrir_todos_os_modos(self):
        self.salvar([self.produto])
        for modo, esperado in (
            ("fixo", "R$ 38,00"),
            ("a_partir", "A partir de R$ 38,00"),
            ("sob_orcamento", "Consultar valores"),
        ):
            with self.subTest(modo=modo):
                itens = self.recarregar()
                aplicar_modalidade(itens[0], modo)
                self.salvar(itens)
                reaberto = self.recarregar()[0]
                self.assertEqual(modalidade_atual(reaberto), modo)
                self.assertEqual(reaberto["Preco"], self.original["Preco"])
                self.assertEqual(reaberto["Estoque"], self.original["Estoque"])
                self.assertIn(esperado, gerar_html_vitrine([reaberto], {}))
                self.assertEqual(avaliar_produto_site(reaberto)["modalidade_preco_site"], modo)

    def test_legado_continua_preservado(self):
        self.produto.pop("ExibirPrecoSite")
        self.salvar([self.produto])
        reaberto = self.recarregar()[0]
        self.assertEqual(modalidade_atual(reaberto), "sob_orcamento")
        self.assertNotIn("ModalidadePrecoSite", reaberto)
        self.assertEqual(reaberto["Preco"], "38,00")


if __name__ == "__main__":
    unittest.main()
