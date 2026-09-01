import unittest
from datetime import date

from thu_comercial_service import aplicar_registro_envio, montar_retornos_comerciais


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


if __name__ == "__main__":
    unittest.main()
