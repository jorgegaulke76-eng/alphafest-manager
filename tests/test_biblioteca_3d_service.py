import unittest

from biblioteca_3d_service import (
    arquivo_3d_valido,
    imagem_valida,
    criar_registro,
    filtrar_modelos,
    tamanho_legivel,
    selecionar_modelos,
    modelo_para_produto_catalogo,
)


class Biblioteca3DServiceTests(unittest.TestCase):
    def test_formatos_3d_comuns_sao_aceitos(self):
        for nome in ("zebra.3mf", "peca.STL", "kit.zip", "modelo.step", "placa.gcode"):
            self.assertTrue(arquivo_3d_valido(nome), nome)
        self.assertFalse(arquivo_3d_valido("foto.png"))

    def test_imagem_unica_usa_formatos_comuns(self):
        self.assertTrue(imagem_valida("capa.webp"))
        self.assertFalse(imagem_valida("modelo.3mf"))

    def test_criar_registro_exige_nome_imagem_e_arquivo(self):
        with self.assertRaises(ValueError):
            criar_registro(nome="", descricao="", tempo_impressao="", imagem_path="img", arquivo_path="arq", arquivo_nome="x.3mf")
        with self.assertRaises(ValueError):
            criar_registro(nome="Zebra", descricao="", tempo_impressao="", imagem_path="", arquivo_path="arq", arquivo_nome="x.3mf")
        with self.assertRaises(ValueError):
            criar_registro(nome="Zebra", descricao="", tempo_impressao="", imagem_path="img", arquivo_path="", arquivo_nome="x.3mf")

    def test_registro_preserva_dados_essenciais(self):
        item = criar_registro(
            nome=" Zebra tricotada ", descricao=" Modelo fofo ", tempo_impressao="3h 20min",
            imagem_path="imagens/a.webp", arquivo_path="arquivos/a.3mf", arquivo_nome="cute-zebra.3mf",
            arquivo_tamanho=2_500_000, criado_em="2026-09-02T15:00:00", registro_id="abc",
        )
        self.assertEqual(item["id"], "abc")
        self.assertEqual(item["nome"], "Zebra tricotada")
        self.assertEqual(item["tempo_impressao"], "3h 20min")
        self.assertEqual(item["arquivo_nome"], "cute-zebra.3mf")

    def test_busca_considera_nome_descricao_e_arquivo(self):
        dados = [
            {"nome": "Zebra", "descricao": "Tricotada", "tempo_impressao": "2h", "arquivo_nome": "zebra.3mf"},
            {"nome": "Dragao", "descricao": "Articulado", "tempo_impressao": "7h", "arquivo_nome": "dragon.3mf"},
        ]
        self.assertEqual([x["nome"] for x in filtrar_modelos(dados, "tricotada")], ["Zebra"])
        self.assertEqual([x["nome"] for x in filtrar_modelos(dados, "dragon")], ["Dragao"])

    def test_tamanho_legivel(self):
        self.assertEqual(tamanho_legivel(0), "0 B")
        self.assertIn("MB", tamanho_legivel(3_000_000))

    def test_hf23_selecao_de_modelos_respeita_ids(self):
        dados = [
            {"id": "b", "nome": "Zebra"},
            {"id": "a", "nome": "Dragao"},
        ]
        self.assertEqual([x["id"] for x in selecionar_modelos(dados, ["b"])], ["b"])

    def test_hf23_catalogo_publico_nao_expoe_arquivo_privado(self):
        modelo = {
            "id": "abc",
            "nome": "Zebra",
            "descricao": "Modelo tricotado",
            "tempo_impressao": "13 horas",
            "imagem_path": "modelos/abc/imagem/zebra.webp",
            "arquivo_path": "modelos/abc/arquivo/zebra.3mf",
            "arquivo_nome": "zebra.3mf",
            "arquivo_tamanho": 123456,
        }
        produto = modelo_para_produto_catalogo(modelo, "data:image/webp;base64,AAA")
        self.assertEqual(produto["Nome"], "Zebra")
        self.assertIn("13 horas", produto["Material"])
        self.assertEqual(produto["Imagens"], ["data:image/webp;base64,AAA"])
        self.assertNotIn("arquivo_path", produto)
        self.assertNotIn("arquivo_nome", produto)
        self.assertNotIn("arquivo_tamanho", produto)


if __name__ == "__main__":
    unittest.main()
