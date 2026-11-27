"""Testes do encerramento manual HF64, com registros exclusivamente ficticios."""
import unittest
from datetime import date
from copy import deepcopy
from encerramento_sem_retorno_hf64 import (
    elegibilidade_encerramento, aplicar_encerramento_sem_retorno,
)

HOJE = date(2026, 11, 27)
BASE = {
    "numero_proposta": "FICT-01", "cliente_nome": "Cliente Ficticio",
    "enviado": True, "ultimo_envio_em": "24/11/2026 10:00",
    "itens": [{"produto": "Item ficticio", "quantidade": 2, "valor_unitario": 10}],
    "total": 20.0, "atendimento_id": "AT-FICT-01",
}

class EncerramentoHF64Test(unittest.TestCase):
    def test_apos_tres_dias_pode_encerrar_por_confirmacao(self):
        proposta = deepcopy(BASE)
        ok, motivo = elegibilidade_encerramento(proposta, HOJE)
        self.assertTrue(ok, motivo)
        updated = aplicar_encerramento_sem_retorno(
            proposta, hoje=HOJE, agora_texto="27/11/2026 15:36", usuario="Jorge")
        self.assertTrue(updated["nao_fechado_sem_retorno"])
        self.assertEqual(updated["status_comercial"], "nao_fechado_sem_retorno")
        self.assertEqual(updated["itens"], BASE["itens"])
        self.assertEqual(updated["total"], BASE["total"])
        self.assertEqual(updated["atendimento_id"], BASE["atendimento_id"])

    def test_nunca_inferir_que_cliente_nao_respondeu(self):
        self.assertEqual(BASE.get("nao_fechado_sem_retorno"), None)
        self.assertTrue(elegibilidade_encerramento(BASE, HOJE)[0])

    def test_bloqueia_proposta_nao_enviada(self):
        self.assertFalse(elegibilidade_encerramento({**BASE, "enviado": False}, HOJE)[0])

    def test_bloqueia_proposta_recente_ou_data_invalida(self):
        for ultimo in ["26/11/2026 10:00", "27/11/2026", "", "2030-01-01"]:
            with self.subTest(ultimo=ultimo):
                self.assertFalse(elegibilidade_encerramento({**BASE, "ultimo_envio_em": ultimo}, HOJE)[0])

    def test_data_utc_convertida_ao_fuso_do_brasil(self):
        self.assertTrue(elegibilidade_encerramento(
            {**BASE, "ultimo_envio_em": "2026-11-25T01:00:00Z"}, HOJE)[0])

    def test_bloqueia_status_oficiais(self):
        for campo in ("Aprovado", "Pago", "Pronto", "Entregue", "cancelado_cliente", "encerrado"):
            with self.subTest(campo=campo):
                self.assertFalse(elegibilidade_encerramento({**BASE, campo: True}, HOJE)[0])
        self.assertFalse(elegibilidade_encerramento({**BASE, "status": "Em produção"}, HOJE)[0])

    def test_bloqueia_sem_identificador(self):
        self.assertFalse(elegibilidade_encerramento({**BASE, "numero_proposta": ""}, HOJE)[0])

    def test_requer_dados_validos(self):
        self.assertFalse(elegibilidade_encerramento(None, HOJE)[0])
        with self.assertRaises(ValueError):
            aplicar_encerramento_sem_retorno(
                {**BASE, "enviado": False}, hoje=HOJE,
                agora_texto="27/11/2026", usuario="Jorge")

if __name__ == "__main__":
    unittest.main()
