"""HF70: testes conservadores com registros inteiramente artificiais."""
import copy
import unittest
from prioridades_comerciais_hf70 import quadro_prioridades_hf70


class PrioridadesHF70(unittest.TestCase):
    def test_nao_converte_problema_de_cadastro_em_lead(self):
        pendencias = [{"Proposta": "P1", "Situacao": "Sem atendimento vinculado"}]
        retorno = [{"numero_proposta": "P1", "nivel": "urgente"}]
        original = copy.deepcopy((pendencias, retorno))
        r = quadro_prioridades_hf70(pendencias, retorno, [])
        self.assertEqual(r["cadastro_total"], 1)
        self.assertEqual(r["comercial_total"], 0)
        self.assertEqual(r["retornos_bloqueados_por_conferencia"], 1)
        self.assertEqual((pendencias, retorno), original)

    def test_apenas_retorno_real_da_fila_oficial_entra_comercial(self):
        retornos = [{"numero_proposta": "A", "nivel": "alta"},
                    {"numero_proposta": "B", "nivel": "aguardar"},
                    {"numero_proposta": "C", "nivel": "normal"},
                    {"numero_proposta": "D", "nivel": "urgente"}]
        r = quadro_prioridades_hf70([], retornos, [{"numero_proposta": "C"}])
        self.assertEqual([x["Proposta"] for x in r["comercial"]], ["D", "A"])

    def test_nao_inventa_orcamento_sem_numero_ou_multiplica_duplicatas(self):
        r = quadro_prioridades_hf70(
            [{"Proposta": "77", "Situacao": "Numero de proposta repetido"}] * 2,
            [{"numero_proposta": "77", "nivel": "urgente"}] * 2, [])
        self.assertEqual(len(r["cadastro"]), 1)
        self.assertEqual(r["cadastro_total"], 2)
        self.assertEqual(r["comercial_total"], 0)

    def test_nulos_e_sinais_desconhecidos_nao_geram_prioridade(self):
        self.assertEqual(quadro_prioridades_hf70(None, None, None)["comercial_total"], 0)
        self.assertEqual(quadro_prioridades_hf70([None, {}], [None, {}, {"numero_proposta": "1", "nivel": "novo"}], [])["cadastro_total"], 0)


if __name__ == "__main__":
    unittest.main()
