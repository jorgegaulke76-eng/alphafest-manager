import unittest
from datetime import date

from thu_comercial_service import (
    aplicar_registro_envio,
    montar_retornos_comerciais,
    aplicar_registro_cobranca,
    montar_cobrancas_assistidas,
    montar_agenda_executiva,
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


    def test_agenda_executiva_deduplica_pedido_com_operacao_e_cobranca(self):
        cobrancas = [{
            "numero_proposta": "DUP",
            "cliente_nome": "Cliente DUP",
            "nivel": "urgente",
            "prioridade": 1160,
            "motivo": "Pagamento pendente",
            "acao": "Cobrar agora",
            "whatsapp": "11 99999-0000",
            "mensagem_sugerida": "Cobrança pronta",
        }]
        operacao = [{
            "numero_proposta": "DUP",
            "cliente_nome": "Cliente DUP",
            "prioridade_rank": 0,
            "prioridade_chave": "atrasado_producao",
            "area": "Produção",
            "motivo_prioridade": "Prazo vencido e produção não concluída",
            "proxima_acao": "Resolver produção",
        }]
        agenda = montar_agenda_executiva([], cobrancas, operacao)
        self.assertEqual(len(agenda), 1)
        self.assertEqual(agenda[0]["numero_proposta"], "DUP")
        self.assertEqual(agenda[0]["dominio"], "Produção")
        self.assertEqual(agenda[0]["sinais_qtd"], 2)
        self.assertIn("💳 Financeiro", agenda[0]["dominios_secundarios"])

    def test_agenda_executiva_exclui_acompanhamento_passivo(self):
        agenda = montar_agenda_executiva(
            [{"numero_proposta": "RET", "nivel": "aguardar", "prioridade": 300}],
            [{"numero_proposta": "COB", "nivel": "aguardar", "prioridade": 320}],
            [{
                "numero_proposta": "OK",
                "prioridade_rank": 5,
                "prioridade_chave": "dentro_prazo",
                "area": "Produção",
            }],
        )
        self.assertEqual(agenda, [])

    def test_agenda_executiva_prioriza_janela_agora_antes_de_hoje(self):
        agenda = montar_agenda_executiva(
            [{
                "numero_proposta": "AGORA",
                "cliente_nome": "Agora",
                "nivel": "urgente",
                "prioridade": 1000,
                "motivo": "Prazo vencido",
                "acao": "Retomar agora",
            }],
            [],
            [{
                "numero_proposta": "HOJE",
                "cliente_nome": "Hoje",
                "prioridade_rank": 2,
                "prioridade_chave": "proximo_prazo",
                "area": "Produção",
                "motivo_prioridade": "Próximo do prazo",
                "proxima_acao": "Revisar produção",
            }],
        )
        self.assertEqual([x["numero_proposta"] for x in agenda], ["AGORA", "HOJE"])
        self.assertEqual(agenda[0]["janela"], "agora")
        self.assertEqual(agenda[1]["janela"], "hoje")

    def test_agenda_executiva_mantem_atalho_whatsapp_da_acao_principal(self):
        agenda = montar_agenda_executiva(
            [],
            [{
                "numero_proposta": "PIX",
                "cliente_nome": "Cliente PIX",
                "nivel": "urgente",
                "prioridade": 1250,
                "motivo": "Entregue e não pago",
                "acao": "Cobrar",
                "whatsapp": "11 99999-0000",
                "whatsapp_chave": "11999990000",
                "mensagem_sugerida": "Mensagem financeira",
            }],
            [],
        )
        self.assertEqual(agenda[0]["origem"], "cobranca")
        self.assertEqual(agenda[0]["whatsapp_chave"], "11999990000")
        self.assertEqual(agenda[0]["mensagem_sugerida"], "Mensagem financeira")

    def test_agenda_executiva_operacional_nao_inventa_whatsapp(self):
        agenda = montar_agenda_executiva([], [], [{
            "numero_proposta": "OP",
            "cliente_nome": "Operação",
            "prioridade_rank": 1,
            "prioridade_chave": "vence_hoje",
            "area": "Produção",
            "motivo_prioridade": "Entrega hoje",
            "proxima_acao": "Finalizar produção",
        }])
        self.assertEqual(agenda[0]["origem"], "operacao")
        self.assertEqual(agenda[0]["whatsapp"], "")
        self.assertEqual(agenda[0]["mensagem_sugerida"], "")

    def test_agenda_executiva_limite_e_aplicado_depois_da_ordenacao(self):
        retornos = []
        for i in range(5):
            retornos.append({
                "numero_proposta": f"P{i}",
                "cliente_nome": f"Cliente {i}",
                "nivel": "normal",
                "prioridade": 700 + i,
                "motivo": "Retorno",
                "acao": "Acompanhar",
            })
        agenda = montar_agenda_executiva(retornos, [], [], limite=2)
        self.assertEqual(len(agenda), 2)
        self.assertEqual([x["numero_proposta"] for x in agenda], ["P4", "P3"])

    def test_agenda_executiva_incorpora_sem_avanco_como_sinal_assistido(self):
        continuidade = [{
            "numero_proposta": "CONT",
            "cliente_nome": "Cliente Continuidade",
            "nivel": "alta",
            "prioridade": 1020,
            "motivo": "mesmo estágio há 4 dia(s)",
            "acao": "Conferir se a produção avançou",
        }]
        agenda = montar_agenda_executiva([], [], [], continuidade)
        self.assertEqual(len(agenda), 1)
        self.assertEqual(agenda[0]["dominio"], "Sem avanço")
        self.assertEqual(agenda[0]["origem"], "continuidade")
        self.assertEqual(agenda[0]["janela"], "hoje")
        self.assertEqual(agenda[0]["whatsapp"], "")
        self.assertEqual(agenda[0]["mensagem_sugerida"], "")

    def test_agenda_executiva_deduplica_operacao_e_sem_avanco_sem_trocar_causa_principal(self):
        operacao = [{
            "numero_proposta": "MESMO",
            "cliente_nome": "Cliente Mesmo",
            "prioridade_rank": 0,
            "prioridade_chave": "atrasado_producao",
            "area": "Produção",
            "motivo_prioridade": "Prazo vencido e produção não concluída",
            "proxima_acao": "Resolver produção",
        }]
        continuidade = [{
            "numero_proposta": "MESMO",
            "cliente_nome": "Cliente Mesmo",
            "nivel": "urgente",
            "prioridade": 1300,
            "motivo": "prazo vencido · sem mudança de status desde a abertura",
            "acao": "Conferir avanço",
        }]
        agenda = montar_agenda_executiva([], [], operacao, continuidade)
        self.assertEqual(len(agenda), 1)
        self.assertEqual(agenda[0]["dominio"], "Produção")
        self.assertEqual(agenda[0]["sinais_qtd"], 2)
        self.assertIn("⏳ Sem avanço", agenda[0]["dominios_secundarios"])

    def test_agenda_executiva_sem_avanco_normal_vai_para_acompanhar(self):
        continuidade = [{
            "numero_proposta": "FUT",
            "cliente_nome": "Cliente Futuro",
            "nivel": "normal",
            "prioridade": 810,
            "motivo": "mesmo estágio há 2 dia(s)",
            "acao": "Conferir próximo marco",
        }]
        agenda = montar_agenda_executiva([], [], [], continuidade)
        self.assertEqual(agenda[0]["janela"], "acompanhar")

    def test_agenda_executiva_nao_muta_as_filas_de_origem(self):
        import copy
        retornos = [{
            "numero_proposta": "R1",
            "cliente_nome": "Cliente",
            "nivel": "alta",
            "prioridade": 900,
            "motivo": "Retorno",
            "acao": "Retomar",
        }]
        antes = copy.deepcopy(retornos)
        montar_agenda_executiva(retornos, [], [])
        self.assertEqual(retornos, antes)


if __name__ == "__main__":
    unittest.main()
