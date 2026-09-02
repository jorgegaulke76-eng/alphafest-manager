import unittest
from datetime import date

from thu_comercial_service import (
    aplicar_registro_envio,
    montar_retornos_comerciais,
    aplicar_registro_cobranca,
    montar_cobrancas_assistidas,
)


class ThuComercialServiceTests(unittest.TestCase):
    def proposta(self, numero="P1", **extras):
        base = {
            "numero_proposta": numero,
            "cliente_nome": "Cliente Teste",
            "whatsapp": "11 99999-0000",
            "data_geracao": "28/08/2026",
            "data_entrega": "10/09/2026",
            "aprovado": False,
            "entregue": False,
        }
        base.update(extras)
        return base

    def test_registro_envio_preserva_primeiro_e_atualiza_ultimo(self):
        p = self.proposta()
        aplicar_registro_envio(p, now_text="01/09/2026 10:00", usuario="Jorge")
        aplicar_registro_envio(p, now_text="02/09/2026 11:00", usuario="Jorge")
        self.assertTrue(p["enviado"])
        self.assertEqual(p["enviado_em"], "01/09/2026 10:00")
        self.assertEqual(p["ultimo_envio_em"], "02/09/2026 11:00")
        self.assertEqual(p["envios_qtd"], 2)
        self.assertFalse(p["aprovado"])

    def test_so_entra_com_envio_explicitamente_registrado(self):
        hoje = date(2026, 9, 1)
        fila = montar_retornos_comerciais([self.proposta(enviado=False)], hoje)
        self.assertEqual(fila, [])

    def test_aprovada_ou_encerrada_nao_entra(self):
        hoje = date(2026, 9, 5)
        base = {"enviado": True, "ultimo_envio_em": "01/09/2026 10:00"}
        fila = montar_retornos_comerciais([
            self.proposta("AP", aprovado=True, **base),
            self.proposta("ENC", encerrado=True, **base),
        ], hoje)
        self.assertEqual(fila, [])

    def test_retorno_antigo_fica_prioritario(self):
        hoje = date(2026, 9, 5)
        fila = montar_retornos_comerciais([
            self.proposta("NOVO", enviado=True, ultimo_envio_em="05/09/2026 09:00", data_entrega="20/09/2026"),
            self.proposta("ANTIGO", enviado=True, ultimo_envio_em="01/09/2026 09:00", data_entrega="20/09/2026"),
        ], hoje)
        self.assertEqual(fila[0]["numero_proposta"], "ANTIGO")
        self.assertEqual(fila[0]["nivel"], "alta")

    def test_prazo_vencido_supera_retorno_normal(self):
        hoje = date(2026, 9, 5)
        fila = montar_retornos_comerciais([
            self.proposta("NORMAL", enviado=True, ultimo_envio_em="01/09/2026 09:00", data_entrega="20/09/2026"),
            self.proposta("VENCIDO", enviado=True, ultimo_envio_em="05/09/2026 09:00", data_entrega="04/09/2026"),
        ], hoje)
        self.assertEqual(fila[0]["numero_proposta"], "VENCIDO")
        self.assertEqual(fila[0]["nivel"], "urgente")

    def test_whatsapp_e_mensagem_sao_preparados_sem_envio_automatico(self):
        hoje = date(2026, 9, 2)
        fila = montar_retornos_comerciais([
            self.proposta("PX", enviado=True, ultimo_envio_em="01/09/2026 09:00")
        ], hoje)
        self.assertEqual(fila[0]["whatsapp_chave"], "11999990000")
        self.assertIn("orçamento PX", fila[0]["mensagem_sugerida"])


    def test_registro_cobranca_nao_marca_pago_e_preserva_primeira_data(self):
        p = self.proposta(aprovado=True, pago=False)
        aplicar_registro_cobranca(p, now_text="01/09/2026 10:00", usuario="Jorge")
        aplicar_registro_cobranca(p, now_text="03/09/2026 11:00", usuario="Jorge")
        self.assertTrue(p["cobranca_registrada"])
        self.assertEqual(p["primeira_cobranca_em"], "01/09/2026 10:00")
        self.assertEqual(p["ultima_cobranca_em"], "03/09/2026 11:00")
        self.assertEqual(p["cobrancas_qtd"], 2)
        self.assertFalse(p["pago"])

    def test_cobranca_so_entra_para_aprovado_nao_pago_nao_mensalista(self):
        hoje = date(2026, 9, 5)
        fila = montar_cobrancas_assistidas([
            self.proposta("OK", aprovado=True, pago=False),
            self.proposta("NAO_AP", aprovado=False, pago=False),
            self.proposta("PAGO", aprovado=True, pago=True),
            self.proposta("MENSAL", aprovado=True, pago=False, faturamento_mensal=True),
            self.proposta("ENC", aprovado=True, pago=False, encerrado=True),
        ], hoje)
        self.assertEqual([x["numero_proposta"] for x in fila], ["OK"])

    def test_entregue_nao_pago_permanece_na_fila_financeira_como_urgente(self):
        hoje = date(2026, 9, 5)
        fila = montar_cobrancas_assistidas([
            self.proposta("ENT", aprovado=True, pago=False, entregue=True, data_entrega="04/09/2026"),
        ], hoje)
        self.assertEqual(len(fila), 1)
        self.assertEqual(fila[0]["nivel"], "urgente")
        self.assertTrue(fila[0]["entregue"])

    def test_pronto_nao_pago_tem_prioridade_alta(self):
        hoje = date(2026, 9, 5)
        fila = montar_cobrancas_assistidas([
            self.proposta("PRONTO", aprovado=True, pago=False, pronto=True, data_entrega="10/09/2026"),
        ], hoje)
        self.assertEqual(fila[0]["nivel"], "alta")
        self.assertIn("pronto", fila[0]["motivo"].lower())

    def test_cobranca_registrada_hoje_vira_aguardar_sem_prazo_urgente(self):
        hoje = date(2026, 9, 5)
        fila = montar_cobrancas_assistidas([
            self.proposta(
                "AG", aprovado=True, pago=False, data_entrega="20/09/2026",
                cobranca_registrada=True, ultima_cobranca_em="05/09/2026 09:00", cobrancas_qtd=1,
            ),
        ], hoje)
        self.assertEqual(fila[0]["nivel"], "aguardar")
        self.assertEqual(fila[0]["dias_sem_cobranca"], 0)

    def test_pagamento_confirmado_remove_da_fila_de_cobranca(self):
        hoje = date(2026, 9, 5)
        p = self.proposta("PG", aprovado=True, pago=False)
        self.assertEqual(len(montar_cobrancas_assistidas([p], hoje)), 1)
        p["pago"] = True
        self.assertEqual(montar_cobrancas_assistidas([p], hoje), [])

    def test_cobranca_prepara_whatsapp_sem_alterar_status(self):
        hoje = date(2026, 9, 5)
        p = self.proposta("PIX", aprovado=True, pago=False)
        fila = montar_cobrancas_assistidas([p], hoje)
        self.assertEqual(fila[0]["whatsapp_chave"], "11999990000")
        self.assertIn("pagamento pendente", fila[0]["mensagem_sugerida"].lower())
        self.assertFalse(p["pago"])


if __name__ == "__main__":
    unittest.main()
