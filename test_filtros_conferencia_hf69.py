"""Testes HF69 com dados ficticios e sem acesso a banco ou rede."""
import copy
import unittest
from filtros_conferencia_hf69 import filtrar_fila_vinculos


class FiltrosHF69(unittest.TestCase):
    def setUp(self):
        self.itens = [
            {"Proposta": "1001", "Situacao": "Sem atendimento vinculado"},
            {"Proposta": "1002", "Situacao": "Atendimento nao encontrado"},
            {"Proposta": "ABC-1001", "Situacao": "Atendimento nao encontrado"},
        ]

    def test_busca_parcial_pelo_numero(self):
        self.assertEqual(len(filtrar_fila_vinculos(self.itens, "1001")), 2)
        self.assertEqual(filtrar_fila_vinculos(self.itens, "abc")[0]["Proposta"], "ABC-1001")

    def test_filtro_combinado(self):
        r = filtrar_fila_vinculos(self.itens, "1001", "Atendimento nao encontrado")
        self.assertEqual([x["Proposta"] for x in r], ["ABC-1001"])

    def test_sem_resultados_e_entradas_invalidas(self):
        self.assertEqual(filtrar_fila_vinculos(None), [])
        self.assertEqual(filtrar_fila_vinculos(self.itens, "nao existe"), [])
        self.assertEqual(filtrar_fila_vinculos([None, "texto", self.itens[0]]), [self.itens[0]])

    def test_nao_muda_origem_nem_devolve_referencia_mutavel(self):
        antes = copy.deepcopy(self.itens)
        encontrados = filtrar_fila_vinculos(self.itens)
        encontrados[0]["Proposta"] = "alterada"
        self.assertEqual(self.itens, antes)


if __name__ == "__main__":
    unittest.main()
