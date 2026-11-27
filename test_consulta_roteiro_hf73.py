"""HF73: consulta sem mutacao, dados reais ou conexao externa."""
import copy
import unittest
from consulta_roteiro_hf73 import consultar_categoria_hf73


class ConsultaRoteiroHF73(unittest.TestCase):
    def setUp(self):
        self.quadro = {
            "cadastro": [{"Proposta": "P1", "Situacao": "Sem atendimento vinculado",
                          "cliente": "Nome Secreto"}],
            "comercial": [
                {"Proposta": "P2", "Prioridade": "urgente", "whatsapp": "11999999999"},
                {"Proposta": "P3", "Prioridade": "alta"},
                {"Proposta": "P4", "Prioridade": "normal"},
            ],
        }
        self.sem_envio = [{"numero_proposta": "P5", "cliente_nome": "Nome Secreto"},
                          {"numero_proposta": "P5"}]

    def test_categorias_independentes(self):
        esperado = {"cadastro": "P1", "urgente": "P2", "alta": "P3",
                    "normal": "P4", "envio": "P5"}
        for categoria, numero in esperado.items():
            with self.subTest(categoria=categoria):
                r = consultar_categoria_hf73(categoria, self.quadro, self.sem_envio)
                self.assertEqual(r["total"], 1)
                self.assertEqual(r["registros"][0]["Proposta"], numero)

    def test_pesquisa_parcial_e_limitacao(self):
        q = {"comercial": [{"Proposta": f"ORC-{i:02}", "Prioridade": "alta"}
                           for i in range(12)]}
        r = consultar_categoria_hf73("alta", q, [], busca="ORC-0", limite=3)
        self.assertEqual(r["total"], 10)
        self.assertEqual(r["exibidos"], 3)
        self.assertEqual(len(r["registros"]), 3)

    def test_sem_dados_pessoais_e_sem_mutacao(self):
        antes = copy.deepcopy((self.quadro, self.sem_envio))
        for categoria, _ in __import__("consulta_roteiro_hf73").CATEGORIAS:
            r = consultar_categoria_hf73(categoria, self.quadro, self.sem_envio)
            for registro in r["registros"]:
                self.assertNotIn("whatsapp", registro)
                self.assertNotIn("cliente", registro)
        self.assertEqual((self.quadro, self.sem_envio), antes)

    def test_vazio_e_invalido(self):
        self.assertEqual(consultar_categoria_hf73("x", None, None)["total"], 0)
        self.assertEqual(consultar_categoria_hf73("urgente", {}, [])["registros"], [])
        self.assertEqual(consultar_categoria_hf73("envio", {}, [None, {}])["total"], 0)


if __name__ == "__main__":
    unittest.main()
