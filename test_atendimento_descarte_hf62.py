"""HF62 - testes isolados, sem Streamlit, Supabase ou dados reais."""
import unittest

from atendimento_descarte_hf62 import (
    MOTIVOS_RETIRADA, preparar_retirada, preparar_reativacao, propostas_ligadas,
)


class DescarteSeguroHF62(unittest.TestCase):
    def setUp(self):
        self.item = {
            "id": "AT-01", "status": "Aguardando cliente", "cliente": "Cliente ficticio",
            "numero_proposta": "P-01", "historico": [{"descricao": "Contato ficticio"}],
        }

    def test_consulta_sem_venda_eh_reversivel_e_nao_muta_origem(self):
        base = dict(self.item)
        resposta = preparar_retirada(base, MOTIVOS_RETIRADA[0], "27/11/2026 15:00", [{"numero_proposta": "P-01", "aprovado": False}])
        self.assertEqual(resposta["status"], "Arquivado")
        self.assertEqual(resposta["status_anterior_descarte"], "Aguardando cliente")
        self.assertEqual(resposta["motivo_arquivamento"], MOTIVOS_RETIRADA[0])
        self.assertEqual(base["status"], "Aguardando cliente")
        resta = preparar_reativacao(resposta, "27/11/2026 16:00")
        self.assertEqual(resta["status"], "Aguardando cliente")
        self.assertEqual(resta["reativado_em"], "27/11/2026 16:00")
        self.assertEqual(resta["historico"], self.item["historico"])

    def test_propostas_vinculadas_por_id_ou_numero_sem_falso_positivo(self):
        propostas = [{"atendimento_id": "AT-01", "numero_proposta": "P-02"},
                     {"numero_proposta": "P-01"}, {"atendimento_id": "OUTRA", "numero_proposta": "P-03"}]
        self.assertEqual(len(propostas_ligadas(self.item, propostas)), 2)

    def test_bloqueia_pedido_status(self):
        for status in ("Pedido aprovado", "Em produção", "Pronto", "Pós-venda"):
            with self.subTest(status=status), self.assertRaises(ValueError):
                preparar_retirada({**self.item, "status": status}, MOTIVOS_RETIRADA[0], "agora")

    def test_bloqueia_proposta_aprovada_mesmo_legado(self):
        for campo in ("aprovado", "Aprovado", "pago", "Pago", "pronto", "Pronto", "entregue", "Entregue", "confirmada"):
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                preparar_retirada(self.item, MOTIVOS_RETIRADA[0], "agora", [{campo: True}])

    def test_bloqueia_status_operacional_proposta(self):
        with self.assertRaises(ValueError):
            preparar_retirada(self.item, MOTIVOS_RETIRADA[0], "agora", [{"status": "Em produção"}])

    def test_bloqueia_reativacao_de_arquivo_legado(self):
        with self.assertRaises(ValueError):
            preparar_reativacao({"id": "AT-01", "status": "Arquivado"}, "agora")

    def test_bloqueia_motivo_invalido(self):
        with self.assertRaises(ValueError):
            preparar_retirada(self.item, "motivo desconhecido", "agora")


if __name__ == "__main__":
    unittest.main()
