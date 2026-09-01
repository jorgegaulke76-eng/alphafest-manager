import ast
import unittest
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class OrcamentoPublicacaoRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.functions = {
            node.name: node
            for node in cls.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_projecao_publica_do_item_e_allowlist(self):
        node = self.functions["_orcamento_item_publico_cliente"]
        module = ast.Module(body=[node], type_ignores=[])
        ast.fix_missing_locations(module)
        ns = {}
        exec(compile(module, str(APP_PATH), "exec"), ns)
        projetar = ns["_orcamento_item_publico_cliente"]
        item = {
            "produto": "CENTRO DE MESA",
            "especificacoes": "Tema: Sonic | Nome: Bento",
            "quantidade": 2,
            "valor_unitario": 12.5,
            "produto_catalogo_descricao": "DESCRICAO INTERNA NAO PODE SAIR",
            "produto_catalogo_material": "PAPEL INTERNO",
            "produto_catalogo_categoria": "PAPELARIA INTERNA",
            "imagem_principal": "data:image/png;base64,SEGREDO",
            "Imagens": ["foto-interna.png"],
            "VideoCatalogo": "https://interno/video.mp4",
        }
        self.assertEqual(
            projetar(item),
            {
                "produto": "CENTRO DE MESA",
                "especificacoes": "Tema: Sonic | Nome: Bento",
                "quantidade": 2,
                "valor_unitario": 12.5,
            },
        )

    def test_html_e_whatsapp_passam_pela_mesma_projecao_publica(self):
        for nome in ("formatar_msg_whatsapp", "gerar_html"):
            node = self.functions[nome]
            chamadas = [
                call
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "_orcamento_item_publico_cliente"
            ]
            self.assertTrue(chamadas, f"{nome} deve filtrar cada item pela projeção pública")


if __name__ == "__main__":
    unittest.main()
