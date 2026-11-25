"""HF57: recuperação real entre arquivo, workflow e helpers do Manager.

Não inicia app.py nem acessa produção. Extrai seus helpers e ramos por AST,
usa os serviços reais e torna gravações/navegação observáveis. A interface do
arquivo é exercitada separadamente em test_proposal_draft_ui_hf57.py.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import manager_workflow_hf53 as workflow
import proposal_draft_service_hf57 as drafts
import proposal_duplicate_ui_hf55 as duplicates
import proposal_review_ui_hf56 as reviews
from relacionamentos_service import localizar_cliente_comercial, localizar_cliente_orcamento
from test_site_quote_import_integration_hf54 import FREE, UI, Rerun, Stop


ROOT = Path(__file__).resolve().parent
TREE = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
FUNCTIONS = {n.name: n for n in TREE.body if isinstance(n, ast.FunctionDef)}
TODAY = date(2026, 11, 25)
NOW = datetime(2026, 11, 25, 15, 30, tzinfo=timezone.utc)
HELPERS = (
    "_hf54_pode_importar_site", "_hf54_identificacao_importada",
    "_hf54_cliente_do_formulario", "_hf57_capturar_rascunho",
    "_hf57_abrir_rascunho", "_hf57_mostrar_referencias",
    "_hf57_preservar_pendencias_apos_salvar", "agendar_limpeza_formulario",
    "_hf53_processar_abertura_pendente", "_orcamento_campos_cliente",
    "_orcamento_autopreencher_cliente_por_nome",
    "aplicar_limpeza_formulario_pendente", "aplicar_proposta_pendente_no_formulario",
    "_hf55_rascunho_para_conferencia", "_hf56_rascunho_para_revisao",
    "_hf56_validar_revisao",
)


def profile_keys(anna=False):
    return (
        "anna" if anna else "jorge", "anna_modal_" if anna else "form_",
        "anna_modal_itens" if anna else "temp_itens",
        "anna_modal_numero_original" if anna else "editar_numero",
        "anna_orc_cliente_novo" if anna else "jorge_orc_cliente",
        "_anna_hf53" if anna else "",
    )


def source_state(anna=False):
    profile, prefix, items_key, number_key, _, origin = profile_keys(anna)
    fields = {
        "cliente": "Maria", "documento": "", "whatsapp": "11900000002",
        "evento": "Festa de Ana", "observacoes": "Mensagem recebida do site:\nNome Ana\nNome Bia",
        "desconto": 2.0, "entrega": TODAY, "prazo": "10", "frete": "Entrega",
        "taxa_entrega": 8.0, "validade": "5",
    }
    state = {prefix + key: value for key, value in fields.items()}
    state.update({
        items_key: [
            {"produto": "Caneca", "quantidade": 1.5, "valor_unitario": 20.5,
             "especificacoes": "Nome Ana; cor azul", "produto_catalogo_id": "CAT-1",
             "metadata": {"arte": "ana.pdf", "camadas": [0, False, None, {"cor": "azul"}]}},
            {"produto": "Caneca", "quantidade": 1, "valor_unitario": 21,
             "especificacoes": "Nome Bia", "preco_especial_aplicado": True},
        ],
        number_key: "AF-ORIGEM", origin + "_atendimento_origem_id": "AT-ORIGEM",
        origin + "_projeto_origem_id": "PR-ORIGEM",
        "anna_modal_item_key" if anna else "form_key": 3,
        f"_hf55_{profile}_conferencia_duplicidades": {"confirmada": True},
        f"_hf56_{profile}_revisao_final": {"confirmada": True},
        "pago": True, "aprovado": True, "timeline": ["Não importar"],
    })
    return state


def portable_payload(state=None, *, anna=False):
    document = drafts.capturar_rascunho(
        source_state(anna) if state is None else state, anna=anna,
        agora=NOW, versao_manager="HF65.24.57",
    )
    return drafts.preparar_retomada(drafts.importar_rascunho(drafts.exportar_rascunho(document)))


class DraftIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.ui = UI()
        self.ui.error = self.ui.warning
        self.state = self.ui.session_state
        self.anna = False
        self.view = self.create = True
        self.clients = [{"id": "old", "nome": "Maria", "documento": "", "whatsapp": "11900000001"}]
        self.forbidden = Mock(side_effect=AssertionError("Recuperar não pode gravar ou vincular dados."))
        self.legacy = Mock(side_effect=lambda n="", d="", w="": localizar_cliente_comercial(
            self.clients, nome=n, documento=d, whatsapp=w))
        self.reference_renderer = Mock()

        def navigate(page, message=None):
            self.ui.navigation.append((page, message))
            raise Rerun()

        self.env = {
            "st": self.ui, "copy": SimpleNamespace(deepcopy=deepcopy), "datetime": datetime,
            "_workflow_hf53": workflow, "_rascunho_hf57": drafts,
            "_duplicidades_hf55": duplicates, "_revisao_hf56": reviews,
            "APP_VERSION": "HF65.24.57", "agora_local": lambda: NOW, "hoje_local": lambda: TODAY,
            "usuario_pode_ver_aba": lambda page: self.view and page == "novo_orcamento",
            "usuario_pode_acao": lambda page, action: self.create and (page, action) == ("novo_orcamento", "criar"),
            "obter_usuario_atual": lambda: {"nome": "Anna" if self.anna else "Jorge"},
            "usuario_em_operacao_protegida": lambda _: self.anna,
            "obter_perfil_configurado": lambda _: {"abas": ["novo_orcamento", "central"] if self.view else []},
            "rerun_na_aba": navigate, "valor_float": lambda value: float(value or 0),
            "_hf53_registrar_abertura_origem": self.forbidden,
            "_hf57_renderizar_referencias": self.reference_renderer,
            "ORCAMENTO_CLIENTE_LIVRE": FREE,
            "carregar_clientes": lambda: deepcopy(self.clients),
            "localizar_cliente_comercial": self.legacy,
            "_rel_localizar_cliente_orcamento": localizar_cliente_orcamento,
            "_orcamento_opcoes_cliente": lambda clients=None: ([FREE, "Maria"], {"Maria": self.clients[0]}),
            "_orcamento_cliente_ref": lambda client: client["id"],
            "_orcamento_resumo_cliente_selecionado": lambda _: "",
            "_orcamento_cliente_por_nome_digitado_unico": Mock(return_value=self.clients[0]),
            "garantir_cliente_orcamento": self.forbidden, "salvar_historico_completo": self.forbidden,
            "_anna_salvar_proposta": self.forbidden, "salvar_atendimentos": self.forbidden,
            "salvar_projetos": self.forbidden, "_hf55_validar_conferencia": self.forbidden,
        }
        exec(compile(ast.Module(body=[FUNCTIONS[name] for name in HELPERS], type_ignores=[]),
                     "actual_hf57_app_helpers", "exec"), self.env)

    def call(self, name, *args, **kwargs):
        return self.env[name](*args, **kwargs)

    def apply(self, data):
        self.assertTrue(self.call("_hf57_abrir_rascunho", data))
        with self.assertRaises(Rerun):
            self.call("_hf53_processar_abertura_pendente")

    def seed_current(self):
        profile, prefix, items_key, number_key, selector, origin = profile_keys(self.anna)
        self.state.update({prefix + "cliente": "Trabalho atual", items_key: [{"produto": "Balão"}],
                           number_key: "AF-ATUAL", selector + "_seletor": "Maria",
                           selector + "_token": "old", origin + "_atendimento_origem_id": "AT-ATUAL",
                           f"_hf57_origem_rascunho_{profile}": {"numero_proposta": "ANTERIOR"},
                           f"_hf57_pendencias_rascunho_{profile}": {"item_nao_adicionado": [{"info": "atual"}]},
                           "_hf57_teste_revisao_arquivo": {"arquivo": "mantido"}})
        for target in ("jorge", "anna"):
            self.state[f"_hf55_{target}_conferencia_duplicidades"] = {"confirmada": True}
            self.state[f"_hf55_{target}_sequencia_duplicidades"] = 7
            self.state[f"_hf56_{target}_revisao_final"] = {"confirmada": True}
            self.state[f"_hf56_{target}_sequencia_revisao_final"] = 8

    def test_capture_uses_current_profile_and_no_side_effects(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.state.update(source_state(anna))
                before = deepcopy(self.state)
                document = self.call("_hf57_capturar_rascunho", anna=anna)
                self.assertEqual(document["origem"]["perfil"], "anna" if anna else "jorge")
                self.assertEqual(document["formulario"]["itens"], before[profile_keys(anna)[2]])
                self.assertEqual(self.state, before)
                self.assertEqual(self.ui.navigation, [])
                self.forbidden.assert_not_called()

    def test_cross_profile_restore_preserves_all_fields_as_new(self):
        for source_anna in (False, True):
            for destination_anna in (False, True):
                with self.subTest(source=source_anna, destination=destination_anna):
                    self.setUp(); self.anna = destination_anna
                    payload = portable_payload(anna=source_anna)
                    before = deepcopy(payload)
                    self.apply(payload)
                    profile, prefix, items_key, number_key, selector, origin = profile_keys(self.anna)
                    for field in workflow.QUOTE_FIELDS:
                        self.assertEqual(self.state[prefix + field], payload[field])
                    self.assertEqual(self.state[items_key], payload["itens"])
                    self.assertFalse(self.state[number_key])
                    self.assertEqual(self.state[selector + "_seletor"], FREE)
                    self.assertEqual(self.state[origin + "_atendimento_origem_id"], "")
                    self.assertEqual(self.state[origin + "_projeto_origem_id"], "")
                    self.assertEqual(self.state[f"_hf57_origem_rascunho_{profile}"]["numero_proposta"], "AF-ORIGEM")
                    self.assertEqual(payload, before)
                    self.assertEqual(self.ui.navigation[-1][0], "central" if self.anna else "novo_orcamento")
                    for key in ("pago", "aprovado", "timeline", "numero_proposta", "relacionamento_id"):
                        self.assertNotIn(key, self.state)
                    self.forbidden.assert_not_called()

    def test_enqueue_is_copy_and_cannot_overwrite_an_existing_intention(self):
        payload = portable_payload()
        self.assertTrue(self.call("_hf57_abrir_rascunho", payload))
        pending = deepcopy(self.state)
        payload["itens"][0]["metadata"]["arte"] = "depois.pdf"
        self.assertEqual(self.state, pending)
        self.assertFalse(self.call("_hf57_abrir_rascunho", payload))
        self.assertEqual(self.state, pending)
        self.assertEqual(self.ui.navigation, [])
        self.forbidden.assert_not_called()

    def test_invalid_callback_payload_cannot_start_a_restore(self):
        for value in (None, [], {}, {"_hf57_retomada": "sim"}):
            with self.subTest(value=value):
                self.assertFalse(self.call("_hf57_abrir_rascunho", value))
                self.assertNotIn(workflow.PENDING_KEY, self.state)
        self.forbidden.assert_not_called()

    def test_creation_and_view_permissions_required_before_queue(self):
        for view, create in ((False, False), (False, True), (True, False)):
            with self.subTest(view=view, create=create):
                self.setUp(); self.seed_current(); self.view, self.create = view, create
                before = deepcopy(self.state)
                self.assertFalse(self.call("_hf57_abrir_rascunho", portable_payload()))
                self.assertEqual(self.state, before)
                self.forbidden.assert_not_called()

    def test_revoked_permission_after_review_preserves_current_and_file(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.seed_current()
                before = deepcopy(self.state)
                self.call("_hf57_abrir_rascunho", portable_payload())
                self.create = False
                self.call("_hf53_processar_abertura_pendente")
                self.assertEqual(self.state, before)
                self.assertEqual(self.ui.navigation, [])
                self.forbidden.assert_not_called()

    def test_existing_draft_is_unchanged_until_explicit_handoff_choice(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.seed_current()
                before = deepcopy(self.state)
                self.call("_hf57_abrir_rascunho", portable_payload())
                with self.assertRaises(Stop): self.call("_hf53_processar_abertura_pendente")
                for key, value in before.items(): self.assertEqual(self.state[key], value)
                self.assertIn(workflow.PENDING_KEY, self.state)
                self.forbidden.assert_not_called()

    def test_cancel_or_continue_preserves_current_references_and_approvals(self):
        for anna in (False, True):
            for choice in ("cancelar", "continuar"):
                with self.subTest(anna=anna, choice=choice):
                    self.setUp(); self.anna = anna; self.seed_current()
                    before = deepcopy(self.state)
                    self.call("_hf57_abrir_rascunho", portable_payload())
                    self.ui.selected_button = "hf53_abertura_" + choice
                    with self.assertRaises(Rerun): self.call("_hf53_processar_abertura_pendente")
                    for key, value in before.items(): self.assertEqual(self.state[key], value)
                    self.assertNotIn(workflow.PENDING_KEY, self.state)
                    self.forbidden.assert_not_called()

    def test_replace_clears_only_target_approvals_and_keeps_monotonic_counters(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.seed_current()
                self.ui.selected_button = "hf53_abertura_substituir"
                self.apply(portable_payload())
                profile, prefix, _, number_key, _, _ = profile_keys(anna)
                other = "jorge" if anna else "anna"
                self.assertEqual(self.state[prefix + "cliente"], "Maria")
                self.assertFalse(self.state[number_key])
                self.assertNotIn(f"_hf55_{profile}_conferencia_duplicidades", self.state)
                self.assertNotIn(f"_hf56_{profile}_revisao_final", self.state)
                self.assertTrue(self.state[f"_hf55_{other}_conferencia_duplicidades"]["confirmada"])
                self.assertTrue(self.state[f"_hf56_{other}_revisao_final"]["confirmada"])
                self.assertEqual(self.state[f"_hf55_{profile}_sequencia_duplicidades"], 7)
                self.assertEqual(self.state[f"_hf56_{profile}_sequencia_revisao_final"], 8)
                self.forbidden.assert_not_called()

    def test_injected_operational_links_never_reach_workflow_as_active(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                payload = portable_payload()
                payload.update(atendimento_id="AT-INJETADO", projeto_id="PR-INJETADO",
                               numero_proposta="EDITAR", editar_numero="EDITAR")
                self.call("_hf57_abrir_rascunho", payload)
                for key in ("atendimento_id", "projeto_id", "numero_proposta", "editar_numero"):
                    self.assertNotIn(key, self.state[workflow.PENDING_KEY]["dados"])
                # O próprio workflow também neutraliza vínculos se chamado diretamente.
                state = {}
                workflow.solicitar_abertura(state, "novo_orcamento", payload, anna=anna)
                workflow.resolver_abertura(state, "substituir", hoje=TODAY)
                _, _, _, number_key, _, origin = profile_keys(anna)
                self.assertFalse(state[number_key])
                self.assertEqual(state[origin + "_atendimento_origem_id"], "")
                self.assertEqual(state[origin + "_projeto_origem_id"], "")
                self.forbidden.assert_not_called()

    def test_incomplete_file_and_empty_date_remain_incomplete(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                payload = portable_payload({"form_entrega": None, "temp_itens": []})
                self.apply(payload)
                _, prefix, items_key, _, _, _ = profile_keys(anna)
                self.assertEqual(self.state[prefix + "cliente"], "")
                self.assertIsNone(self.state[prefix + "entrega"])
                self.assertEqual(self.state[items_key], [])
                self.forbidden.assert_not_called()

    def test_received_pending_item_is_informational_and_survives_reexport(self):
        source = source_state()
        source.update(produto_novo_3_livre="Faixa pendente", tema_3="Floresta", qtd_3=2)
        payload = portable_payload(source)
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.apply(payload)
                profile, _, items_key, _, _, _ = profile_keys(anna)
                self.assertEqual(len(self.state[items_key]), 2)
                self.assertNotIn(f"_hf53_edicao_{profile}", self.state)
                self.assertIsNone(workflow.item_em_preenchimento(self.state, anna=anna))
                document = self.call("_hf57_capturar_rascunho", anna=anna)
                self.assertEqual(document["pendencias"], payload["_hf57_pendencias"])
                for key in ("numero_proposta", "atendimento_id", "projeto_id"):
                    self.assertEqual(document["origem"][key], payload["_hf57_origem"][key])
                second = drafts.importar_rascunho(drafts.exportar_rascunho(document))
                self.assertEqual(second["pendencias"], document["pendencias"])
                self.forbidden.assert_not_called()

    def test_pending_information_alone_is_protected_from_another_handoff(self):
        source = {"form_entrega": None, "form_prazo": "10", "form_validade": "5",
                  "temp_itens": [], "form_key": 1,
                  "produto_novo_1_livre": "Ainda não adicionado"}
        payload = portable_payload(source)
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.apply(payload)
                profile = profile_keys(anna)[0]
                self.assertTrue(workflow.possui_rascunho(self.state, "novo_orcamento", anna=anna, hoje=TODAY))
                pending = deepcopy(self.state[f"_hf57_pendencias_rascunho_{profile}"])
                workflow.solicitar_abertura(self.state, "novo_orcamento", {"cliente": "Outro"}, anna=anna)
                with self.assertRaisesRegex(ValueError, "rascunho"):
                    workflow.resolver_abertura(self.state, "abrir", hoje=TODAY)
                self.assertEqual(self.state[f"_hf57_pendencias_rascunho_{profile}"], pending)
                workflow.resolver_abertura(self.state, "cancelar", hoje=TODAY)
                self.state.pop(f"_hf57_pendencias_rascunho_{profile}")
                self.assertFalse(workflow.possui_rascunho(self.state, "novo_orcamento", anna=anna, hoje=TODAY))

    def test_preserved_contact_is_not_replaced_by_homonym_or_name_autofill(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.apply(portable_payload())
                _, prefix, _, _, selector, _ = profile_keys(anna)
                self.call("_orcamento_campos_cliente", selector, nome_key=prefix + "cliente",
                          documento_key=prefix + "documento", whatsapp_key=prefix + "whatsapp")
                self.call("_orcamento_autopreencher_cliente_por_nome", prefixo=selector,
                          nome_key=prefix + "cliente", documento_key=prefix + "documento",
                          whatsapp_key=prefix + "whatsapp", reconhecido_id_key="recognition", mensagem_key="message")
                self.assertEqual(self.state[prefix + "cliente"], "Maria")
                self.assertEqual(self.state[prefix + "whatsapp"], "11900000002")
                self.assertIsNone(self.call("_hf54_cliente_do_formulario", "Maria", "", "11900000002", anna=anna))
                self.legacy.assert_not_called()
                self.env["_orcamento_cliente_por_nome_digitado_unico"].assert_not_called()
                self.state[selector + "_seletor"] = "Maria"
                self.call("_orcamento_campos_cliente", selector, nome_key=prefix + "cliente",
                          documento_key=prefix + "documento", whatsapp_key=prefix + "whatsapp")
                self.assertEqual(self.state[prefix + "whatsapp"], "11900000001")

    def test_manual_recovery_dismissal_only_removes_pending_information(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.seed_current()
                profile = profile_keys(anna)[0]
                self.state["anna_modal_item_key" if anna else "form_key"] = 9
                before = deepcopy(self.state)
                self.call("_hf57_mostrar_referencias", anna=anna)
                self.assertEqual(self.state, before)
                self.assertEqual(self.reference_renderer.call_args.kwargs["contexto"], 9)
                callback = self.reference_renderer.call_args.kwargs["dispensar_pendencias"]
                self.assertIs(callback(), True)
                before.pop(f"_hf57_pendencias_rascunho_{profile}")
                self.assertEqual(self.state, before)
                self.assertEqual(self.ui.navigation, [])
                self.forbidden.assert_not_called()

    def test_next_regular_quote_clears_recovery_scope(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.apply(portable_payload())
                profile = profile_keys(anna)[0]
                workflow.solicitar_abertura(self.state, "novo_orcamento", {"cliente": "Manual"}, anna=anna)
                workflow.resolver_abertura(self.state, "substituir", hoje=TODAY)
                self.assertNotIn(f"_hf57_origem_rascunho_{profile}", self.state)
                self.assertNotIn(f"_hf57_pendencias_rascunho_{profile}", self.state)
                self.assertFalse(self.state[f"_hf54_cliente_importado_{profile}"])

    def test_jorge_reset_and_existing_quote_clear_recovery_references(self):
        self.seed_current(); self.state.update(_limpar_formulario_pendente=True, form_key=2)
        self.call("aplicar_limpeza_formulario_pendente")
        self.assertNotIn("_hf57_origem_rascunho_jorge", self.state)
        self.assertNotIn("_hf57_pendencias_rascunho_jorge", self.state)
        self.seed_current()
        self.state["_proposta_pendente_formulario"] = {
            "prop": {"numero_proposta": "P1", "cliente_nome": "Outro cliente"}, "duplicar": False}
        self.call("aplicar_proposta_pendente_no_formulario")
        self.assertNotIn("_hf57_origem_rascunho_jorge", self.state)
        self.assertNotIn("_hf57_pendencias_rascunho_jorge", self.state)
        self.assertEqual(self.state["editar_numero"], "P1")

    def test_anna_initialization_preserves_restore_then_clears_other_quote(self):
        self.anna = True; self.apply(portable_payload())
        initializer = next(n for n in FUNCTIONS["dialog_orcamento_anna"].body
                           if isinstance(n, ast.If) and "_hf53_anna_contexto_formulario" in ast.unparse(n.test))
        code = compile(ast.Module(body=[initializer], type_ignores=[]), "actual_anna_init", "exec")
        self.env.update(proposta={}, numero_original="", chave_modal="anna_modal_iniciado_novo",
                        cliente_prefixo_hf6="anna_orc_cliente_novo")
        before = deepcopy(self.state); exec(code, self.env)
        self.assertEqual(self.state, before)
        self.env.update(proposta={"numero_proposta": "P2", "cliente_nome": "Outro", "itens": []},
                        numero_original="P2", chave_modal="anna_modal_iniciado_P2", cliente_prefixo_hf6="anna_orc_cliente_P2")
        exec(code, self.env)
        self.assertNotIn("_hf57_origem_rascunho_anna", self.state)
        self.assertNotIn("_hf57_pendencias_rascunho_anna", self.state)
        self.assertEqual(self.state["anna_modal_cliente"], "Outro")

    def test_restored_invalid_item_still_blocks_actual_save_before_any_write(self):
        from test_proposal_review_integration_hf56 import install_function, save_body
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                source = source_state(); source["temp_itens"][0]["quantidade"] = 0
                self.apply(portable_payload(source))
                _, prefix, items_key, _, _, _ = profile_keys(anna)
                items = self.state[items_key]
                subtotal = sum(i["quantidade"] * i["valor_unitario"] for i in items)
                proposal = self.call("_hf55_rascunho_para_conferencia", nome=self.state[prefix + "cliente"],
                    documento="", whatsapp=self.state[prefix + "whatsapp"], evento="Festa", itens=items,
                    entrega=TODAY, desconto=2, prazo="10", frete="Entrega", taxa_entrega=8, validade="5",
                    subtotal=subtotal, total=subtotal - 2 + 8, anna=anna)
                self.env.update(nome="Maria", rascunho_hf55=proposal, numero_original="")
                save = install_function(self.env, "actual_save_hf57", save_body(anna))
                with self.assertRaises(Rerun): save()
                self.forbidden.assert_not_called()
                self.assertEqual(self.state[items_key], items)
                profile = profile_keys(anna)[0]
                self.assertTrue(self.state[f"_hf56_{profile}_revisao_final"]["resultado"]["bloqueios"])

    def test_recovery_metadata_does_not_enter_commercial_payload_or_total(self):
        self.apply(portable_payload())
        proposal = self.call("_hf55_rascunho_para_conferencia", nome="Maria", documento="", whatsapp="11900000002",
                            evento="Festa", itens=self.state["temp_itens"], entrega=TODAY, desconto=2,
                            prazo="10", frete="Entrega", taxa_entrega=8, validade="5", subtotal=51.75, total=57.75)
        self.assertEqual(proposal["valor_total"], 57.75)
        self.assertEqual(proposal["atendimento_id"], "")
        self.assertEqual(proposal["projeto_id"], "")
        self.assertFalse(any(key.startswith("_hf57") for key in proposal))
        self.assertEqual(proposal["briefing_origem"], self.state["form_observacoes"])
        self.forbidden.assert_not_called()

    def finish_saved_quote(self, anna):
        """Executa o trecho real posterior à confirmação de gravação."""
        from test_proposal_review_integration_hf56 import install_function, save_body
        body = save_body(anna)
        if anna:
            body = next(n.body for n in body if isinstance(n, ast.If)
                        and isinstance(n.test, ast.Name) and n.test.id == "ok_salvar")
            marker = 'st.session_state[\'anna_modal_itens\'] = []'
        else:
            marker = 'st.session_state[\'_ultima_proposta_salva\'] = dict(dados)'
        start = next(index for index, n in enumerate(body) if ast.unparse(n) == marker)
        self.env.update(dados={"numero_proposta": "NOVA", "itens": deepcopy(self.state[profile_keys(anna)[2]])},
                        nome="Maria", cliente_novo_i811=False, retorno_salvar="NOVA",
                        chave_modal="anna_modal_iniciado_novo")
        finish = install_function(self.env, "actual_finish_hf57", body[start:])
        with self.assertRaises(Rerun): finish()

    def test_success_preserves_only_manual_recovery_then_continue_keeps_it(self):
        source = source_state()
        source.update(produto_novo_3_livre="Faixa pendente", tema_3="Floresta")
        payload = portable_payload(source)
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.apply(payload)
                profile, prefix, items_key, number_key, _, origin = profile_keys(anna)
                before = deepcopy(self.state)
                self.finish_saved_quote(anna)
                self.assertEqual(self.state[items_key], [])
                self.assertEqual(len(self.env["dados"]["itens"]), 2)
                self.assertFalse(self.state[number_key])
                self.assertNotIn("_limpar_formulario_pendente", self.state)
                for key in (f"_hf57_origem_rascunho_{profile}", f"_hf57_pendencias_rascunho_{profile}", prefix + "cliente"):
                    self.assertEqual(self.state[key], before[key])
                self.assertEqual(self.state[origin + "_atendimento_origem_id"], "")
                self.assertEqual(self.state[origin + "_projeto_origem_id"], "")
                self.assertTrue(workflow.possui_rascunho(self.state, "novo_orcamento", anna=anna, hoje=TODAY))
                self.call("_hf57_abrir_rascunho", portable_payload())
                self.ui.selected_button = "hf53_abertura_continuar"
                with self.assertRaises(Rerun): self.call("_hf53_processar_abertura_pendente")
                if anna:
                    initializer = next(n for n in FUNCTIONS["dialog_orcamento_anna"].body
                        if isinstance(n, ast.If) and "_hf53_anna_contexto_formulario" in ast.unparse(n.test))
                    self.env.update(proposta={}, numero_original="", cliente_prefixo_hf6="anna_orc_cliente_novo")
                    exec(compile(ast.Module(body=[initializer], type_ignores=[]), "actual_anna_reopen", "exec"), self.env)
                document = self.call("_hf57_capturar_rascunho", anna=anna)
                self.assertEqual(document["formulario"]["itens"], [])
                self.assertEqual(document["pendencias"], payload["_hf57_pendencias"])
                self.forbidden.assert_not_called()

    def test_success_without_manual_pending_information_keeps_regular_reset(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna; self.apply(portable_payload())
                self.finish_saved_quote(anna)
                if anna:
                    self.assertFalse(self.state["anna_modal_iniciado_novo"])
                    self.assertEqual(self.state["anna_modal_itens"], [])
                else:
                    self.assertTrue(self.state["_limpar_formulario_pendente"])
                    self.call("aplicar_limpeza_formulario_pendente")
                    self.assertEqual(self.state["temp_itens"], [])
                    self.assertEqual(self.state["form_cliente"], "")
                    self.assertNotIn("_hf57_origem_rascunho_jorge", self.state)
                self.forbidden.assert_not_called()


class DraftPlacementTest(unittest.TestCase):
    def test_export_renders_before_save_so_failed_saving_cannot_hide_download(self):
        found = set()
        for node in ast.walk(TREE):
            for _, statements in ast.iter_fields(node):
                if not isinstance(statements, list):
                    continue
                for index, statement in enumerate(statements):
                    if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                            and isinstance(statement.value.func, ast.Name)
                            and statement.value.func.id == "_hf57_renderizar_exportacao"):
                        continue
                    prefix = next(k.value.value for k in statement.value.keywords if k.arg == "prefixo")
                    # No ramo com itens, o botão salvar segue o exportador; nos
                    # ramos sem itens não existe qualquer gravação para testar.
                    following = statements[index + 1:index + 3]
                    if not any(isinstance(n, ast.If) and "st.button" in ast.unparse(n.test) for n in following):
                        continue
                    found.add(prefix)
                    calls = {n.func.id for later in statements[index + 1:] for n in ast.walk(later)
                             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
                    self.assertIn("_hf56_validar_revisao", calls)
        self.assertEqual(found, {"hf57_exportar_jorge", "hf57_exportar_anna"})

    def test_both_profiles_have_export_without_items_and_single_restore_entry(self):
        calls = [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        exports = [next(k.value.value for k in n.keywords if k.arg == "prefixo") for n in calls
                   if n.func.id == "_hf57_renderizar_exportacao"]
        restores = [next(k.value.value for k in n.keywords if k.arg == "prefixo") for n in calls
                    if n.func.id == "_hf57_renderizar_retomada"]
        self.assertCountEqual(exports, ["hf57_exportar_jorge"] * 2 + ["hf57_exportar_anna"] * 2)
        self.assertCountEqual(restores, ["hf57_retomar_jorge", "hf57_retomar_anna"])
        self.assertFalse(any(n.func.id == "_hf57_renderizar_retomada" for n in ast.walk(FUNCTIONS["dialog_orcamento_anna"])
                             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)))


if __name__ == "__main__":
    unittest.main()
