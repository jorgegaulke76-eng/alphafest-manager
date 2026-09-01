import unittest

from catalogo_orcamento_service import (
    ORCAMENTO_PRODUTO_LIVRE,
    aliases_catalogo_atomicos,
    mapa_identidade_produtos,
    normalizar_identidade_produto,
    opcoes_produto_orcamento,
    produto_catalogo_da_meta,
    resolver_produto_orcamento,
    resumo_dados_catalogo,
    snapshot_item_catalogo,
)


class CatalogoOrcamentoServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalogo = [
            {
                "CatalogoId": "CAT-1",
                "Nome": "PAPEL DE ARROZ",
                "Aliases": ["PAPEL ARROZ, ARROZ PERSONALIZADO"],
                "Categoria": "Papelaria",
                "Subcategoria": "Bolos",
                "Material": "Papel comestível",
                "Variacoes": ["A4", "A3"],
                "DescricaoCurta": "Impressão comestível",
                "Ativo": True,
            },
            {
                "CatalogoId": "CAT-2",
                "Nome": "TOPO DE BOLO",
                "Aliases": ["TOPO SIMPLES"],
                "Categoria": "Papelaria",
                "Ativo": True,
            },
            {
                "CatalogoId": "CAT-3",
                "Nome": "PRODUTO INATIVO",
                "Aliases": ["ANTIGO"],
                "Ativo": False,
            },
        ]

    def test_normalizacao_preserva_regra_historica(self):
        self.assertEqual(normalizar_identidade_produto("  PAPÉL--de Arroz  "), "papel de arroz")

    def test_alias_legado_agrupado_e_expandido_sem_perder_original(self):
        aliases = aliases_catalogo_atomicos(self.catalogo[0])
        self.assertIn("PAPEL ARROZ, ARROZ PERSONALIZADO", aliases)
        self.assertIn("PAPEL ARROZ", aliases)
        self.assertIn("ARROZ PERSONALIZADO", aliases)

    def test_nome_oficial_tem_prioridade_no_mapa(self):
        catalogo = [
            {"Nome": "ABC", "Aliases": []},
            {"Nome": "OUTRO", "Aliases": ["ABC"]},
        ]
        self.assertEqual(mapa_identidade_produtos(catalogo)["abc"], "ABC")

    def test_opcoes_exibem_somente_ativos_e_alias_aponta_para_oficial(self):
        opcoes, mapa = opcoes_produto_orcamento(self.catalogo)
        self.assertEqual(opcoes[0], ORCAMENTO_PRODUTO_LIVRE)
        self.assertIn("PAPEL DE ARROZ", opcoes)
        self.assertNotIn("PRODUTO INATIVO", opcoes)
        rotulo = next(x for x in opcoes if x.startswith("PAPEL ARROZ  →"))
        self.assertEqual(mapa[rotulo], "PAPEL DE ARROZ")

    def test_escolha_explicita_catalogo_vence_texto_livre(self):
        nome, meta = resolver_produto_orcamento("TOPO DE BOLO", "OUTRO TEXTO", self.catalogo)
        self.assertEqual(nome, "TOPO DE BOLO")
        self.assertEqual(meta["origem"], "catalogo")
        self.assertEqual(meta["catalogo_id"], "CAT-2")
        self.assertEqual(meta["digitado"], "OUTRO TEXTO")

    def test_alias_digitado_normaliza_para_nome_oficial(self):
        nome, meta = resolver_produto_orcamento(ORCAMENTO_PRODUTO_LIVRE, "papel arroz", self.catalogo)
        self.assertEqual(nome, "PAPEL DE ARROZ")
        self.assertEqual(meta["origem"], "catalogo_alias")
        self.assertEqual(meta["catalogo_id"], "CAT-1")

    def test_produto_novo_permanece_livre(self):
        nome, meta = resolver_produto_orcamento(ORCAMENTO_PRODUTO_LIVRE, "Produto totalmente novo", self.catalogo)
        self.assertEqual(nome, "Produto totalmente novo")
        self.assertEqual(meta["origem"], "livre")
        self.assertEqual(meta["catalogo_id"], "")
        self.assertEqual(meta["produto_oficial"], "")

    def test_meta_resolve_por_id_sem_adivinhacao(self):
        produto = produto_catalogo_da_meta({"origem": "catalogo", "catalogo_id": "CAT-2", "produto_oficial": "qualquer"}, self.catalogo)
        self.assertEqual(produto["Nome"], "TOPO DE BOLO")
        self.assertIsNone(produto_catalogo_da_meta({"origem": "livre", "produto_oficial": "TOPO DE BOLO"}, self.catalogo))

    def test_snapshot_nao_injeta_campos_de_personalizacao(self):
        meta = {"origem": "catalogo_alias", "digitado": "papel arroz", "catalogo_id": "CAT-1"}
        snap = snapshot_item_catalogo(meta, self.catalogo[0])
        self.assertEqual(snap["produto_catalogo_descricao"], "Impressão comestível")
        self.assertEqual(snap["produto_catalogo_material"], "Papel comestível")
        self.assertNotIn("tema", snap)
        self.assertNotIn("nome", snap)
        self.assertNotIn("cor", snap)
        self.assertNotIn("detalhes", snap)

    def test_resumo_catalogo_e_apenas_informativo(self):
        texto = resumo_dados_catalogo(self.catalogo[0])
        self.assertIn("Papelaria / Bolos", texto)
        self.assertIn("Material: Papel comestível", texto)
        self.assertIn("Opções: A4 • A3", texto)


if __name__ == "__main__":
    unittest.main()
