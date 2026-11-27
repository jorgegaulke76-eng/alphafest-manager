"""Testes HF66 com registros ficticios. Nao acessam banco nem rede."""
import copy
import unittest

from analytics_vendas_produtos_hf66 import consolidar_vendas_e_produtos


class VendasProdutosHF66(unittest.TestCase):
    def test_distingue_aprovacao_pagamento_e_atribuicao(self):
        atendimentos = [
            {"id": "AT1", "canal_origem": "Instagram"},
            {"id": "AT2", "canal_origem": "Instagram"},
            {"id": "AT3", "canal_origem": "Google"},
        ]
        propostas = [
            {"numero_proposta": "P1", "atendimento_id": "AT1", "aprovado": True,
             "pago": False, "valor_total": "R$ 120,00",
             "itens": [{"produto": "Topo", "quantidade": 2, "valor_unitario": "50,00"}]},
            {"numero_proposta": "P2", "atendimento_id": "AT1", "aprovado": True,
             "valor_total": 30, "itens": [{"produto": "Topo", "quantidade": 1, "valor_unitario": 30}]},
            {"numero_proposta": "P3", "atendimento_id": "AT2", "enviado": True,
             "valor_total": 500, "itens": [{"produto": "Balões", "quantidade": 3, "valor_unitario": 30}]},
            {"numero_proposta": "P4", "aprovado": True, "valor_total": 60,
             "itens": [{"produto": "Balões", "quantidade": 2, "valor_unitario": 30}]},
            {"numero_proposta": "P5", "aprovado": True, "atendimento_id": "INVALIDO", "valor_total": 40,
             "itens": [{"produto": "Camiseta", "quantidade": 1, "valor_unitario": 40}]},
        ]
        antes = copy.deepcopy((atendimentos, propostas))
        d = consolidar_vendas_e_produtos(atendimentos, propostas)
        self.assertEqual((atendimentos, propostas), antes)
        self.assertEqual(d["indicadores"]["pedidos_aprovados"], 4)
        self.assertEqual(d["indicadores"]["valor_aprovado"], 250)
        self.assertEqual(d["indicadores"]["pedidos_atribuidos"], 2)
        insta = next(x for x in d["por_canal"] if x["Canal de origem"] == "Instagram")
        self.assertEqual(insta["Atendimentos"], 2)
        self.assertEqual(insta["Atendimentos convertidos"], 1)
        self.assertEqual(insta["Pedidos aprovados"], 2)
        self.assertEqual(insta["Conversão (%)"], 50.0)
        self.assertEqual(insta["Valor aprovado (R$)"], 150.0)
        topo = next(x for x in d["por_produto"] if x["Produto"] == "Topo")
        self.assertEqual(topo["Pedidos aprovados"], 2)
        self.assertEqual(topo["Quantidade"], 3)
        self.assertEqual(topo["Bruto dos itens (R$)"], 130.0)
        self.assertEqual(d["diagnostico"]["aprovadas_sem_atendimento"], 1)
        self.assertEqual(d["diagnostico"]["aprovadas_vinculo_invalido"], 1)

    def test_proposta_cancelada_nao_e_venda(self):
        p = [{"numero_proposta": "1", "aprovado": True, "cancelado_cliente": True}]
        self.assertEqual(consolidar_vendas_e_produtos([], p)["indicadores"]["pedidos_aprovados"], 0)

    def test_deduplica_numero_de_proposta(self):
        p = [{"numero_proposta": "1", "aprovado": True, "total": 12},
             {"numero_proposta": "1", "aprovado": True, "total": 12}]
        r = consolidar_vendas_e_produtos([], p)
        self.assertEqual(r["indicadores"]["pedidos_aprovados"], 1)
        self.assertEqual(r["diagnostico"]["numeros_repetidos"], 1)

    def test_valores_invalidos_nao_fabricam_receita(self):
        p = [{"numero_proposta": "A", "aprovado": True, "valor_total": "não informado"},
             {"numero_proposta": "B", "aprovado": True, "valor_total": -2},
             {"numero_proposta": "C", "aprovado": True, "valor_total": "R$ 1.234,50"}]
        r = consolidar_vendas_e_produtos([], p)
        self.assertEqual(r["indicadores"]["valor_aprovado"], 1234.5)
        self.assertEqual(r["diagnostico"]["pedidos_sem_total_confiavel"], 2)

    def test_ausencia_de_dados_nao_gera_venda(self):
        r = consolidar_vendas_e_produtos(None, None)
        self.assertEqual(r["indicadores"]["pedidos_aprovados"], 0)
        self.assertEqual(r["por_canal"], [])
        self.assertEqual(r["por_produto"], [])

    def test_produto_com_preco_ausente_preserva_contagem(self):
        r = consolidar_vendas_e_produtos([], [
            {"numero_proposta": "1", "aprovado": True, "itens": [
                {"produto": "Impressão 3D", "quantidade": 1}
            ]}
        ])
        self.assertEqual(r["por_produto"][0]["Pedidos aprovados"], 1)
        self.assertEqual(r["diagnostico"]["itens_sem_valor_unitario"], 1)


if __name__ == "__main__":
    unittest.main()
