"""HF67 - testes de recomendacoes com dados artificiais."""
import copy
import unittest

from insights_organicos_hf67 import sugerir_acoes_organicas


def relatorio(total=10, atribuidos=9, contatos=30, convertidos=5, pedidos_canal=5,
              produto_pedidos=4, duplicados=0):
    return {
        "indicadores": {"pedidos_aprovados": total, "pedidos_atribuidos": atribuidos},
        "diagnostico": {"ids_atendimento_repetidos": duplicados, "numeros_repetidos": 0},
        "por_canal": [{"Canal de origem": "Instagram", "Atendimentos": contatos,
                       "Atendimentos convertidos": convertidos, "Pedidos aprovados": pedidos_canal}],
        "por_produto": [{"Produto": "Topo de bolo", "Pedidos aprovados": produto_pedidos}],
    }


class InsightsHF67Test(unittest.TestCase):
    def test_base_adequada_sugere_teste_nao_publica(self):
        base = relatorio()
        copia = copy.deepcopy(base)
        r = sugerir_acoes_organicas(base)
        self.assertEqual(base, copia)
        self.assertTrue(r["amostra_canais_suficiente"])
        self.assertTrue(any(a["tipo"] == "canal" for a in r["acoes"]))
        self.assertTrue(any(a["tipo"] == "produto" for a in r["acoes"]))
        self.assertIn("Nenhuma publicação", r["observacao"])

    def test_baixa_atribuicao_proibe_vencedor(self):
        r = sugerir_acoes_organicas(relatorio(atribuidos=2))
        self.assertFalse(r["amostra_canais_suficiente"])
        self.assertTrue(any(a["tipo"] == "dados" for a in r["acoes"]))
        self.assertFalse(any(a["tipo"] == "canal" for a in r["acoes"]))

    def test_amostra_insuficiente_nao_e_vencedor(self):
        for entradas, convertidos, pedidos in ((19, 10, 5), (30, 2, 5), (30, 5, 2)):
            with self.subTest(entradas=entradas, convertidos=convertidos, pedidos=pedidos):
                r = sugerir_acoes_organicas(relatorio(contatos=entradas, convertidos=convertidos,
                                                      pedidos_canal=pedidos))
                self.assertFalse(r["amostra_canais_suficiente"])

    def test_duplicados_pedem_revisao(self):
        r = sugerir_acoes_organicas(relatorio(duplicados=1))
        self.assertTrue(any("duplicados" in a["titulo"] for a in r["acoes"]))
        self.assertFalse(any(a["tipo"] == "canal" for a in r["acoes"]))

    def test_zero_e_ausencia_nao_fabricam_evidencia(self):
        for d in ({}, relatorio(total=0, atribuidos=0)):
            with self.subTest(d=d):
                r = sugerir_acoes_organicas(d)
                self.assertIsNone(r["cobertura_atribuicao"])
                self.assertFalse(r["amostra_canais_suficiente"])

    def test_produto_exige_tres_pedidos(self):
        r = sugerir_acoes_organicas(relatorio(produto_pedidos=2))
        self.assertFalse(any(a["tipo"] == "produto" for a in r["acoes"]))
        self.assertTrue(any(a["tipo"] == "produto_amostra" for a in r["acoes"]))


if __name__ == "__main__":
    unittest.main()
