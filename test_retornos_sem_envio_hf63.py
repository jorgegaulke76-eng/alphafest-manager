"""HF63 - cenarios ficticios, sem Streamlit, rede ou banco."""
import unittest

from retornos_sem_envio_hf63 import listar_sem_registro_envio


class SemEnvioHF63(unittest.TestCase):
    def test_nao_concluir_que_foi_enviado_somente_pela_existencia(self):
        rows = [
            {"numero_proposta": "100", "cliente_nome": "Cliente Ficticio", "enviado": False, "data_geracao": "27/11/2026"},
            {"numero_proposta": "101", "enviado": True, "data_geracao": "26/11/2026"},
            {"numero_proposta": "102", "aprovado": True},
            {"numero_proposta": "103", "Pago": "sim"},
            {"numero_proposta": "104", "Pronto": True},
            {"numero_proposta": "105", "status_comercial": "nao_fechado_sem_retorno"},
            {"numero_proposta": "106", "cancelado_cliente": True},
            {"numero_proposta": "", "enviado": False},
        ]
        self.assertEqual([x["numero_proposta"] for x in listar_sem_registro_envio(rows)], ["100"])
        self.assertFalse(rows[0]["enviado"])

    def test_aceita_proposta_legada_sem_atendimento(self):
        rows = [{"numero_proposta": "P-LEGADO", "enviado": False}]
        self.assertEqual(listar_sem_registro_envio(rows)[0]["numero_proposta"], "P-LEGADO")

    def test_remover_duplicadas_e_priorizar_mais_recentes(self):
        rows = [
            {"numero_proposta": "A", "data_geracao": "01/11/2026"},
            {"numero_proposta": "B", "data_geracao": "26/11/2026"},
            {"numero_proposta": "A", "data_geracao": "27/11/2026"},
            {"numero_proposta": "C", "data_geracao": "2026-11-27"},
        ]
        self.assertEqual(
            [x["numero_proposta"] for x in listar_sem_registro_envio(rows)],
            ["C", "B", "A"],
        )

    def test_ignora_listas_invalidas(self):
        self.assertEqual(listar_sem_registro_envio([None, "erro", {}, []]), [])

    def test_exclui_status_operacional_mesmo_sem_aprovacao(self):
        rows = [{"numero_proposta": "A", "status": "Pedido aprovado"}, {"numero_proposta": "B", "status": "Em produção"}]
        self.assertEqual(listar_sem_registro_envio(rows), [])


if __name__ == "__main__":
    unittest.main()
