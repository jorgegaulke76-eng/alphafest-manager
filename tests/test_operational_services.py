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


class ProposalStatusServiceTests(unittest.TestCase):
    def test_entregue_normaliza_pronto(self):
        from proposal_status_service import normalizar_status_desejados
        r = normalizar_status_desejados(True, True, False, True)
        self.assertTrue(r["pronto"])
        self.assertTrue(r["entregue"])

    def test_aplicar_status_preserva_regra_e_carimbos(self):
        from proposal_status_service import normalizar_status_desejados, aplicar_status_na_proposta

        proposta = {"numero_proposta": "P1", "aprovado": False, "pago": False, "pronto": False, "entregue": False}
        eventos = []
        desejados = normalizar_status_desejados(True, True, True, False)
        r = aplicar_status_na_proposta(
            proposta, desejados,
            now_text="01/09/2026 12:30", usuario="Jorge",
            registrar_evento=lambda p, descricao, usuario: eventos.append((descricao, usuario)),
        )
        self.assertEqual(r["anteriores"], {"aprovado": False, "pago": False, "pronto": False, "entregue": False})
        self.assertTrue(r["aprovou_agora"])
        self.assertEqual(proposta["aprovado_em"], "01/09/2026 12:30")
        self.assertEqual(proposta["pago_em"], "01/09/2026 12:30")
        self.assertEqual(proposta["pronto_em"], "01/09/2026 12:30")
        self.assertEqual(proposta["pronto_por"], "Jorge")
        self.assertTrue(proposta["pronto_em_confiavel"])
        self.assertEqual([x[0] for x in eventos], ["Orçamento aprovado", "Pagamento confirmado", "Pedido pronto"])

    def test_entrega_gera_conclusao_e_pronto(self):
        from proposal_status_service import normalizar_status_desejados, aplicar_status_na_proposta

        proposta = {"numero_proposta": "P2", "aprovado": True, "pago": True, "pronto": False, "entregue": False}
        eventos = []
        desejados = normalizar_status_desejados(True, True, False, True)
        r = aplicar_status_na_proposta(
            proposta, desejados,
            now_text="01/09/2026 12:31", usuario="Anna",
            registrar_evento=lambda p, descricao, usuario: eventos.append(descricao),
        )
        self.assertTrue(proposta["pronto"])
        self.assertTrue(proposta["entregue"])
        self.assertTrue(r["nova_conclusao"])
        self.assertIn("Pedido pronto", eventos)
        self.assertIn("Entrega concluída", eventos)
        self.assertIn("Entregue — operação finalizada e disponível no Histórico", eventos)

    def test_verificacao_persistencia_rejeita_estado_diferente(self):
        from proposal_status_service import normalizar_status_desejados, status_persistidos_correspondem
        desejados = normalizar_status_desejados(True, True, False, False)
        self.assertTrue(status_persistidos_correspondem({"aprovado": True, "pago": True}, desejados))
        self.assertFalse(status_persistidos_correspondem({"aprovado": True, "pago": False}, desejados))


class ProposalPersistenceServiceTests(unittest.TestCase):
    def test_prefere_mutacao_condicional_quando_disponivel(self):
        from proposal_persistence_service import atualizar_proposta_fresca

        chamadas = []
        cacheados = []
        invalidados = []

        def cloud(*args, **kwargs):
            chamadas.append((args, kwargs))
            registro = {"numero_proposta": "P1", "aprovado": True}
            return True, registro, [registro], "ok"

        ok, registro, motivo = atualizar_proposta_fresca(
            "P1", lambda p: p.update({"aprovado": True}),
            cloud_mutate=cloud,
            on_cloud_document=lambda doc: cacheados.append(doc),
            invalidate=lambda: invalidados.append(True),
        )
        self.assertTrue(ok)
        self.assertTrue(registro["aprovado"])
        self.assertEqual(motivo, "ok")
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(len(cacheados), 1)
        self.assertEqual(len(invalidados), 1)
        self.assertEqual(chamadas[0][1]["retries"], 4)

    def test_fallback_sempre_parte_de_leitura_fresca(self):
        from proposal_persistence_service import atualizar_proposta_fresca

        banco = [{"numero_proposta": "P2", "pago": False}]
        leituras = []
        gravacoes = []
        invalidados = []

        def load():
            leituras.append(True)
            return [dict(x) for x in banco]

        def save(hist):
            gravacoes.append(hist)
            banco[:] = [dict(x) for x in hist]
            return True

        ok, registro, motivo = atualizar_proposta_fresca(
            "P2", lambda p: p.update({"pago": True}),
            load_fresh=load, save_full=save,
            invalidate=lambda: invalidados.append(True),
        )
        self.assertTrue(ok)
        self.assertTrue(registro["pago"])
        self.assertEqual(motivo, "fallback")
        self.assertEqual(len(leituras), 1)
        self.assertEqual(len(gravacoes), 1)
        self.assertEqual(len(invalidados), 1)
        self.assertTrue(banco[0]["pago"])

    def test_fallback_nao_inventa_proposta_ausente(self):
        from proposal_persistence_service import atualizar_proposta_fresca
        ok, registro, motivo = atualizar_proposta_fresca(
            "INEXISTENTE", lambda p: p.update({"pago": True}),
            load_fresh=lambda: [], save_full=lambda h: True,
        )
        self.assertFalse(ok)
        self.assertIsNone(registro)
        self.assertIn("não encontrada", motivo.lower())


class MateriaisPedidoServiceTests(unittest.TestCase):
    def test_consumo_ativo_escolhe_mais_recente_e_ignora_estornado(self):
        from materiais_pedido_service import consumo_ativo_pedido
        consumos = [
            {"id": "C1", "numero_proposta": "P1", "confirmado_em": "2026-09-01T10:00:00", "estornado": False},
            {"id": "C2", "numero_proposta": "P1", "confirmado_em": "2026-09-01T11:00:00", "estornado": True},
            {"id": "C3", "numero_proposta": "P1", "confirmado_em": "2026-09-01T10:30:00", "estornado": False},
        ]
        self.assertEqual(consumo_ativo_pedido("P1", consumos)["id"], "C3")

    def test_fila_liberacao_so_aceita_aprovado_ativo_sem_consumo(self):
        from materiais_pedido_service import proposta_na_fila_liberacao
        p = {"numero_proposta": "P1"}
        self.assertTrue(proposta_na_fila_liberacao(p, numeros_consumo_ativos=[], aprovado=True, pronto=False, entregue=False))
        self.assertFalse(proposta_na_fila_liberacao(p, numeros_consumo_ativos=["P1"], aprovado=True, pronto=False, entregue=False))
        self.assertFalse(proposta_na_fila_liberacao(p, numeros_consumo_ativos=[], aprovado=False, pronto=False, entregue=False))
        self.assertFalse(proposta_na_fila_liberacao(p, numeros_consumo_ativos=[], aprovado=True, pronto=True, entregue=False))

    def test_confirmacao_ficha_padrao_preserva_regra_homologada(self):
        from materiais_pedido_service import preparar_confirmacao_consumo
        proposta = {
            "numero_proposta": "P1", "cliente_nome": "CLIENTE",
            "itens": [{"produto": "PAPEL DE ARROZ", "quantidade": 2}],
        }
        previa = {
            "produtos": [{"produto": "PAPEL DE ARROZ", "quantidade": 2, "ficha_id": "FT1"}],
            "necessidades": [{"material_id": "M1", "material_nome": "FOLHA", "unidade": "un", "necessario": 2}],
            "sem_ficha": [], "sem_catalogo": [], "materiais_estoque_pedido": [],
        }
        r = preparar_confirmacao_consumo(
            proposta=proposta, previa=previa, estoque={"materiais": []},
            modo_consumo="ficha_padrao", aprovado=True, ja_possui_consumo_ativo=False,
            usuario_nome="Jorge", agora_iso="2026-09-01T12:00:00", consumo_id="C1",
            normalizar_produto=lambda x: str(x or "").strip().casefold(),
        )
        self.assertTrue(r["ok"])
        c = r["consumo"]
        self.assertEqual(c["modo_consumo"], "ficha_padrao")
        self.assertEqual(c["modelo_materiais"], "reserva_consumo_real_v1")
        self.assertEqual(c["necessidades"][0]["necessario"], 2)
        self.assertEqual(c["confirmado_por"], "Jorge")
        self.assertEqual(c["reservas"], [])

    def test_confirmacao_manual_agrega_material_sem_alterar_ficha(self):
        from materiais_pedido_service import preparar_confirmacao_consumo
        proposta = {"numero_proposta": "P2", "itens": [{"produto": "ADESIVO", "quantidade": 1}]}
        estoque = {"materiais": [{"id": "M1", "nome": "PAPEL", "unidade": "folha", "ativo": True}]}
        r = preparar_confirmacao_consumo(
            proposta=proposta, previa={"sem_catalogo": [], "sem_ficha": ["ADESIVO"]}, estoque=estoque,
            modo_consumo="manual_pedido",
            necessidades_manuais=[{"material_id": "M1", "quantidade": 1}, {"material_id": "M1", "necessario": 2}],
            aprovado=True, ja_possui_consumo_ativo=False, usuario_nome="Anna",
            agora_iso="2026-09-01T12:01:00", consumo_id="C2",
            normalizar_produto=lambda x: str(x or "").strip().casefold(),
        )
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["consumo"]["necessidades"]), 1)
        self.assertEqual(r["consumo"]["necessidades"][0]["necessario"], 3)
        self.assertEqual(r["consumo"]["modo_consumo"], "manual_pedido")

    def test_sem_consumo_nao_inventa_material(self):
        from materiais_pedido_service import preparar_confirmacao_consumo
        r = preparar_confirmacao_consumo(
            proposta={"numero_proposta": "P3", "itens": [{"produto": "SERVIÇO", "quantidade": 1}]},
            previa={"sem_catalogo": [], "sem_ficha": ["SERVIÇO"]}, estoque={"materiais": []},
            modo_consumo="sem_consumo", aprovado=True, ja_possui_consumo_ativo=False,
            usuario_nome="Jorge", agora_iso="2026-09-01T12:02:00", consumo_id="C3",
            normalizar_produto=lambda x: str(x or "").strip().casefold(),
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r["consumo"]["necessidades"], [])
        self.assertEqual(r["consumo"]["modelo_materiais"], "sem_consumo_controlado_v1")

    def test_ficha_sem_material_exige_decisao_do_pedido(self):
        from materiais_pedido_service import preparar_confirmacao_consumo
        r = preparar_confirmacao_consumo(
            proposta={"numero_proposta": "P4", "itens": []},
            previa={"sem_catalogo": [], "sem_ficha": ["PRODUTO"], "necessidades": []},
            estoque={"materiais": []}, modo_consumo="ficha_padrao", aprovado=True,
            ja_possui_consumo_ativo=False, usuario_nome="Jorge",
            agora_iso="2026-09-01T12:03:00", consumo_id="C4",
            normalizar_produto=lambda x: str(x or "").strip().casefold(),
        )
        self.assertFalse(r["ok"])
        self.assertIn("sem Ficha Técnica", r["mensagem"])

    def test_inicio_producao_bloqueia_falta_e_consome_so_reservado(self):
        from materiais_pedido_service import decidir_inicio_consumo
        falta = decidir_inicio_consumo(
            {"modo_consumo": "ficha_padrao"},
            {"necessidades": [{"material_nome": "PAPEL", "pendente": 1, "reservado": 0}]},
        )
        self.assertFalse(falta["ok"])
        pronto = decidir_inicio_consumo(
            {"modo_consumo": "ficha_padrao"},
            {"necessidades": [{"material_nome": "PAPEL", "pendente": 0, "reservado": 2, "material_id": "M1"}]},
        )
        self.assertTrue(pronto["ok"])
        self.assertEqual(pronto["necessidades"][0]["reservado"], 2)

    def test_inicio_sem_consumo_e_legado_sao_idempotentes(self):
        from materiais_pedido_service import decidir_inicio_consumo
        sem = decidir_inicio_consumo({"modo_consumo": "sem_consumo"}, {"necessidades": []})
        self.assertTrue(sem["ok"])
        self.assertEqual(sem["necessidades"], [])
        legado = decidir_inicio_consumo(
            {"modo_consumo": "ficha_padrao"},
            {"necessidades": [{"material_nome": "PAPEL", "pendente": 0, "reservado": 0, "consumido": 2}]},
        )
        self.assertTrue(legado["ok"])
        self.assertEqual(legado["necessidades"], [])
