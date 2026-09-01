import unittest

from fluxo_operacional_service import reconciliar_lista_fluxo
from status_diagnostics_service import diagnosticar_sincronizacao_status


class FluxoOperacionalServiceTests(unittest.TestCase):
    def proposta(self, numero, **extras):
        p = {
            "numero_proposta": numero,
            "cliente_nome": "Cliente",
            "itens": [{"produto": "TOPO DE BOLO", "quantidade": 1}],
        }
        p.update(extras)
        return p

    def test_nao_aprovado_fica_pedido_recebido(self):
        tarefas, alterado = reconciliar_lista_fluxo([], [self.proposta("P1")], now_text="01/09/2026 12:00")
        self.assertTrue(alterado)
        self.assertEqual(tarefas[0]["status"], "Pedido recebido")

    def test_aprovado_inicia_operacao(self):
        tarefas, _ = reconciliar_lista_fluxo([], [self.proposta("P2", aprovado=True)], now_text="01/09/2026 12:00")
        self.assertEqual(tarefas[0]["status"], "Arte pendente")

    def test_etapa_manual_e_preservada(self):
        base = [{
            "id": "P3::0", "numero_proposta": "P3", "indice_item": 0,
            "produto": "TOPO DE BOLO", "status": "Em produção",
            "prioridade": "Urgente", "ativa": True, "timeline": [],
        }]
        tarefas, _ = reconciliar_lista_fluxo(base, [self.proposta("P3", aprovado=True)], now_text="01/09/2026 12:00")
        self.assertEqual(tarefas[0]["status"], "Em produção")
        self.assertEqual(tarefas[0]["prioridade"], "Urgente")

    def test_remover_e_repor_aprovacao_preserva_etapa(self):
        base = [{
            "id": "P4::0", "numero_proposta": "P4", "indice_item": 0,
            "produto": "TOPO DE BOLO", "status": "Em produção",
            "prioridade": "Normal", "ativa": True, "timeline": [],
        }]
        bloqueadas, _ = reconciliar_lista_fluxo(base, [self.proposta("P4")], now_text="01/09/2026 12:00")
        self.assertEqual(bloqueadas[0]["status"], "Pedido recebido")
        restauradas, _ = reconciliar_lista_fluxo(bloqueadas, [self.proposta("P4", aprovado=True)], now_text="01/09/2026 12:01")
        self.assertEqual(restauradas[0]["status"], "Em produção")

    def test_entregue_nao_fica_ativo_no_fluxo(self):
        tarefas, _ = reconciliar_lista_fluxo([], [self.proposta("P5", aprovado=True, pronto=True, entregue=True)], now_text="01/09/2026 12:00")
        self.assertFalse(any(t.get("ativa", True) for t in tarefas))


class StatusDiagnosticsTests(unittest.TestCase):
    def test_pago_sem_aprovado_e_detectado(self):
        r = diagnosticar_sincronizacao_status([{"numero_proposta": "P1", "pago": True}])
        self.assertTrue(any(x["Problema"] == "Pago sem aprovação" for x in r["contradicoes"]))

    def test_registro_coerente_nao_cria_contradicao(self):
        r = diagnosticar_sincronizacao_status([{
            "numero_proposta": "P2", "aprovado": True, "pago": True, "pronto": True, "entregue": True,
        }])
        self.assertEqual(r["contradicoes"], [])


class ThuOperationalConsistencyTests(unittest.TestCase):
    def test_thu_usa_mesmas_contagens_operacionais_da_central(self):
        # O módulo de tela importa Streamlit, mas o cálculo do briefing é puro.
        import sys, types
        sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))
        from datetime import date
        from painel_indicadores import calcular_indicadores_unificados
        from alpha_core import calcular_alpha_core
        from thu_executivo import calcular_briefing

        hoje = date(2026, 9, 1)
        historico = [
            {
                "numero_proposta": "P-ATIVA-PRONTA",
                "aprovado": True,
                "pronto": True,
                "entregue": False,
                "data_entrega": "01/09/2026",
            },
            {
                "numero_proposta": "P-ENCERRADA-PRONTA",
                "aprovado": True,
                "pronto": True,
                "entregue": False,
                "encerrado": True,
                "data_entrega": "01/09/2026",
            },
            {
                "numero_proposta": "P-AGUARDA",
                "aprovado": False,
                "data_entrega": "02/09/2026",
            },
        ]
        indicadores = calcular_indicadores_unificados(historico, [], [], hoje)
        core = calcular_alpha_core(historico, [], hoje).to_dict()
        thu = calcular_briefing(historico, indicadores, hoje)

        self.assertEqual(thu["prontos_aguardando_entrega"], indicadores["prontos_operacionais"])
        self.assertEqual(thu["prontos_aguardando_entrega"], core["prontos_aguardando_entrega"])
        self.assertEqual(thu["entregas_hoje"], indicadores["entregas_hoje_abertas"])
        self.assertEqual(thu["atrasados"], indicadores["atrasados_operacionais"])
        self.assertEqual(thu["prontos_aguardando_entrega"], 1)
        self.assertEqual(thu["entregas_hoje"], 1)


if __name__ == "__main__":
    unittest.main()


class AuditoriaOperacionalServiceTests(unittest.TestCase):
    def proposta(self, numero, **extras):
        p = {"numero_proposta": numero}
        p.update(extras)
        return p

    def test_sincronizacao_calcula_reparos_sem_streamlit(self):
        from auditoria_operacional_service import executar_auditoria_sincronizacao

        historico = [self.proposta("P1", aprovado=True)]
        tarefas_antes = []

        def montar_previsao(**kwargs):
            return [{"numero_proposta": "P1", "chave": "dentro"}]

        def montar_fila(historico, hoje, resumo_produtos=None):
            return []

        def reconciliar(_historico):
            return [{"numero_proposta": "P1", "ativa": True}]

        r = executar_auditoria_sincronizacao(
            historico=historico,
            tarefas_antes=tarefas_antes,
            consumos=[], estoque={}, planejamentos=[], hoje=None,
            momento="2026-09-01T12:00:00",
            montar_previsao=montar_previsao,
            montar_fila_entregas=montar_fila,
            reconciliar_fluxo=reconciliar,
            resumo_produtos=None,
        )
        self.assertEqual(r["problemas_antes"], 1)
        self.assertEqual(r["reparos_automaticos"], 1)
        self.assertTrue(r["ok"])

    def test_saneamento_so_audita_depois_de_gravacao_confirmada(self):
        from auditoria_operacional_service import aplicar_plano_saneamento
        from consistencia_operacional_engine import aplicar_correcoes_seguras_status

        plano = {
            "planos": [
                {"pedido": "OK", "correcoes": [{"campo": "aprovado"}]},
                {"pedido": "FALHA", "correcoes": [{"campo": "pronto"}]},
            ]
        }
        banco = {
            "OK": {"numero_proposta": "OK", "pago": True, "aprovado": False},
            "FALHA": {"numero_proposta": "FALHA", "entregue": True, "pronto": False},
        }
        auditoria = []

        def atualizar(numero, mutar):
            if numero == "FALHA":
                return False, banco[numero], "simulado"
            mutar(banco[numero])
            return True, banco[numero], ""

        def registrar(*args, **kwargs):
            auditoria.append((args, kwargs))

        r = aplicar_plano_saneamento(
            plano_inicial=plano,
            atualizar_proposta=atualizar,
            aplicar_correcoes=aplicar_correcoes_seguras_status,
            registrar_mudanca=registrar,
        )
        self.assertTrue(banco["OK"]["aprovado"])
        self.assertFalse(banco["FALHA"]["pronto"])
        self.assertEqual(r["alteracoes_confirmadas"], 1)
        self.assertEqual(len(r["falhas"]), 1)
        self.assertEqual(len(auditoria), 1)

    def test_linhas_de_ui_sao_puras(self):
        from auditoria_operacional_service import linhas_previa_saneamento, linhas_relatorio_sincronizacao

        prev = linhas_previa_saneamento({
            "planos": [{
                "pedido": "P1", "cliente": "Cliente",
                "correcoes": [{"campo": "pronto", "motivo": "Entregue exige Pronto"}],
            }]
        })
        self.assertEqual(prev[0]["Campo"], "status.pronto")
        rel = linhas_relatorio_sincronizacao({
            "fluxo_faltantes": ["P2"],
            "contradicoes": [{"pedido": "P3", "problema": "Pago sem Aprovado"}],
        })
        self.assertEqual(len(rel), 2)
        self.assertEqual(rel[1]["Detalhe"], "Pago sem Aprovado")
