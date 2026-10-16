"""Testa expressões reais de campos de preço no formulário oficial via AST.

Não importa app.py: só extrai as três expressões de um dicionário do formulário.
Não executa o aplicativo, não salva dados reais e não acessa o Supabase.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app.py"


def campos_oficiais():
    arvore = ast.parse(SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(arvore):
        if not isinstance(node, ast.Dict):
            continue
        pares = {chave.value: valor for chave, valor in zip(node.keys, node.values)
                 if isinstance(chave, ast.Constant) and isinstance(chave.value, str)}
        if {"Preco", "ModalidadePrecoSite", "ExibirPrecoSite"}.issubset(pares):
            return {chave: pares[chave] for chave in
                    ("Preco", "ModalidadePrecoSite", "ExibirPrecoSite")}
    raise AssertionError("Dicionário de gravação do formulário oficial não encontrado")


class TestCamposGravacaoOficial(unittest.TestCase):
    def test_existe_mapeamento_de_gravacao(self):
        campos = campos_oficiais()
        self.assertEqual(set(campos), {"Preco", "ModalidadePrecoSite", "ExibirPrecoSite"})

    def test_expressoes_do_formulario_preservam_preco(self):
        campos = campos_oficiais()
        for modo in ("fixo", "a_partir", "sob_orcamento"):
            with self.subTest(modo=modo):
                contexto = {"modalidade_preco_site": modo, "preco_cat": "38,00"}
                valores = {chave: eval(compile(ast.Expression(expr), str(SOURCE), "eval"),
                                      {"__builtins__": {}}, contexto)
                           for chave, expr in campos.items()}
                self.assertEqual(valores["Preco"], "38,00")
                self.assertEqual(valores["ModalidadePrecoSite"], modo)
                self.assertEqual(valores["ExibirPrecoSite"], modo != "sob_orcamento")


if __name__ == "__main__":
    unittest.main()
