"""Testes isolados HF65, sem dados de clientes, rede ou banco."""
import unittest
from copy import deepcopy
from retorno_registrado_hf65 import (
    link_whatsapp_retorno, validar_retorno_realizado, aplicar_retorno_realizado,
)

BASE = {
    "numero_proposta": "TEST-01", "cliente_nome": "Cliente Exemplo",
    "enviado": True, "enviado_em": "25/11/2026 10:00",
    "ultimo_envio_em": "25/11/2026 10:00",
    "envios_qtd": 1, "total": 80.0,
    "itens": [{"produto": "Exemplo"}],
}

class RetornoHF65(unittest.TestCase):
    def test_link_apenas_numero_br_valido_sem_enviar(self):
        link = link_whatsapp_retorno("(11) 98765-4321", "Olá! Tudo bem?")
        self.assertTrue(link.startswith("https://wa.me/5511987654321?text="))
        self.assertIn("%21", link)
        self.assertEqual(link_whatsapp_retorno("123", "olá"), "")
        self.assertEqual(link_whatsapp_retorno("11987654321", ""), "")
        self.assertEqual(link_whatsapp_retorno("11987654321", "x" * 1301), "")
        self.assertEqual(link_whatsapp_retorno("5511987654321", "olá").split("?")[0],
                         "https://wa.me/5511987654321")

    def test_registro_conserva_campos_comerciais(self):
        p = deepcopy(BASE)
        aplicar_retorno_realizado(p, instante="27/11/2026 15:41", usuario="Jorge")
        self.assertEqual(p["enviado_em"], BASE["enviado_em"])
        self.assertEqual(p["ultimo_envio_em"], "27/11/2026 15:41")
        self.assertEqual(p["envios_qtd"], 2)
        self.assertEqual(p["itens"], BASE["itens"])
        self.assertEqual(p["total"], BASE["total"])
        self.assertFalse(p.get("aprovado", False))

    def test_bloqueia_sem_envio_inicial(self):
        self.assertFalse(validar_retorno_realizado({**BASE, "enviado": False})[0])

    def test_impede_repeticao_no_mesmo_minuto(self):
        self.assertFalse(validar_retorno_realizado(
            BASE, instante=BASE["ultimo_envio_em"])[0])

    def test_impede_pedido_em_operacao_e_encerrado(self):
        for campo in ("Aprovado", "Pago", "Pronto", "Entregue",
                      "cancelado_cliente", "encerrado"):
            with self.subTest(campo=campo):
                self.assertFalse(validar_retorno_realizado({**BASE, campo: True})[0])
        self.assertFalse(validar_retorno_realizado({**BASE, "status": "Em produção"})[0])
        self.assertFalse(validar_retorno_realizado({**BASE, "status_comercial": "nao_fechado_sem_retorno"})[0])

    def test_nao_gravar_horario_vazio(self):
        with self.assertRaises(ValueError):
            aplicar_retorno_realizado(deepcopy(BASE), instante="", usuario="Jorge")

if __name__ == "__main__":
    unittest.main()
