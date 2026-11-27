"""HF68: casos sinteticos, sem banco, sem credenciais e sem modificacao."""
import copy
import unittest
from conferencia_vinculos_hf68 import fila_conferencia_vinculos


class ConferenciaHF68(unittest.TestCase):
    def test_diagnostico_sem_mutacao_e_sem_vinculo_por_telefone(self):
        a = [{"id": "A1", "telefone": "(11) 99999-1111"},
             {"id": "A2", "telefone": "(11) 99999-1111"}]
        p = [{"numero_proposta": "P1", "whatsapp": "5511999991111"},
             {"numero_proposta": "P2", "atendimento_id": "A1"},
             {"numero_proposta": "P3", "atendimento_id": "A404"},
             {"numero_proposta": "P4", "atendimento_id": "A2"}]
        antes = copy.deepcopy((a, p))
        r = fila_conferencia_vinculos(a, p)
        self.assertEqual((a, p), antes)
        self.assertEqual(r["total"], 2)
        self.assertEqual(r["registros"][1]["Pistas de atendimento (nao verificadas)"], "A1, A2")
        self.assertEqual(p[0].get("atendimento_id"), None)

    def test_ids_e_numeros_duplicados_nao_sao_aceitos_como_vinculo(self):
        a = [{"id": "X"}, {"id": "X"}]
        p = [{"numero_proposta": "D", "atendimento_id": "X"},
             {"numero_proposta": "D", "atendimento_id": "X"},
             {"numero_proposta": "E", "atendimento_id": "X"},
             {"atendimento_id": "X"}]
        r = fila_conferencia_vinculos(a, p)
        self.assertEqual(r["total"], 4)
        self.assertEqual(r["por_situacao"]["Numero de proposta repetido"], 2)
        self.assertEqual(r["por_situacao"]["ID de atendimento repetido"], 1)
        self.assertEqual(r["por_situacao"]["Proposta sem numero"], 1)

    def test_ausencia_e_formatos_invalidos(self):
        self.assertEqual(fila_conferencia_vinculos(None, None)["total"], 0)
        self.assertEqual(fila_conferencia_vinculos([None, {}], [None, {}, {"numero_proposta": "1"}])["total"], 2)

    def test_atendimento_valido_nao_aparece_como_pendencia(self):
        r = fila_conferencia_vinculos([{"id": "OK"}], [{"numero_proposta": "10", "atendimento_id": "OK"}])
        self.assertEqual(r["total"], 0)


if __name__ == "__main__":
    unittest.main()
