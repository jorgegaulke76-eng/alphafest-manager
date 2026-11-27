"""Testes HF71 com exemplos artificiais, sem clientes e sem rede."""
import copy
from datetime import date
import unittest

from resumo_diario_hf71 import resumo_diario_hf71
from prioridades_comerciais_hf70 import quadro_prioridades_hf70


class ResumoHF71(unittest.TestCase):
    def test_separa_cadastro_envio_e_retorno_sem_duplicar(self):
        pendencias = [{"Proposta": "A", "Situacao": "Sem atendimento vinculado"}]
        retornos = [
            {"numero_proposta": "A", "nivel": "urgente"},
            {"numero_proposta": "B", "nivel": "alta"},
            {"numero_proposta": "C", "nivel": "normal"},
            {"numero_proposta": "D", "nivel": "aguardar"},
        ]
        nao_enviados = [{"numero_proposta": "C"}, {"numero_proposta": "C"}]
        originais = copy.deepcopy((pendencias, retornos, nao_enviados))
        quadro = quadro_prioridades_hf70(pendencias, retornos, nao_enviados)
        r = resumo_diario_hf71(quadro, nao_enviados, retornos, date(2026, 11, 27))
        self.assertEqual((r["conferencias"], r["sem_registro_envio"],
                          r["retornos_elegiveis"], r["altos"], r["aguardar"]),
                         (1, 1, 1, 1, 1))
        self.assertNotIn("Proposta A", r["texto"])
        self.assertEqual((pendencias, retornos, nao_enviados), originais)

    def test_texto_sem_dados_de_clientes_e_sem_contato_automatico(self):
        quadro = {"cadastro_total": 0, "comercial": [
            {"Proposta": "777", "Prioridade": "urgente",
             "cliente_nome": "Cliente Secreto", "whatsapp": "11999999999"}]}
        r = resumo_diario_hf71(quadro, [], [], date(2026, 11, 27))
        self.assertEqual(r["urgentes"], 1)
        for segredo in ("777", "Cliente Secreto", "11999999999"):
            self.assertNotIn(segredo, r["texto"])

    def test_vazio(self):
        r = resumo_diario_hf71(None, None, None, date(2026, 11, 27))
        self.assertEqual(r["retornos_elegiveis"], 0)
        self.assertEqual(r["sem_registro_envio"], 0)
        self.assertEqual(r["conferencias"], 0)


if __name__ == "__main__":
    unittest.main()
