"""Regressões do handoff real de importação, sem iniciar o Manager ou a rede.

Os helpers são extraídos de app.py por AST. O fluxo, os localizadores de
clientes e a leitura confirmada são os módulos reais, com serviços externos
substituídos. Assim um erro de alias, identidade ou ordem de abertura falha.
"""
from __future__ import annotations

import ast
from contextlib import nullcontext
from copy import deepcopy
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cloud_db
import manager_workflow_hf53 as workflow
from relacionamentos_service import localizar_cliente_comercial, localizar_cliente_orcamento


SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = {n.name: n for n in TREE.body if isinstance(n, ast.FunctionDef)}
FREE = "✍️ Cliente novo / digitar manualmente"
TODAY = date(2026, 11, 25)
HELPERS = (
    "_hf54_pode_importar_site", "_hf54_carregar_catalogo_importacao",
    "_hf54_abrir_rascunho_importado", "_hf54_identificacao_importada",
    "_hf54_cliente_do_formulario", "_hf54_mostrar_origem_orcamento",
    "_hf53_processar_abertura_pendente", "_hf53_registrar_abertura_origem",
    "_orcamento_campos_cliente", "_orcamento_autopreencher_cliente_por_nome",
    "aplicar_limpeza_formulario_pendente", "aplicar_proposta_pendente_no_formulario",
)


class State(dict):
    __setattr__ = dict.__setitem__

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


class Rerun(Exception):
    pass


class Stop(Exception):
    pass


class UI:
    def __init__(self):
        self.session_state = State()
        self.messages = []
        self.texts = []
        self.infos = []
        self.selected_button = ""
        self.navigation = []

    def warning(self, text):
        self.messages.append(text)

    caption = warning
    write = warning

    def info(self, text):
        self.infos.append(text)

    def text(self, text):
        self.texts.append(text)

    def selectbox(self, label, options, *, index, key, **kwargs):
        self.session_state.setdefault(key, options[index])
        return self.session_state[key]

    def container(self, **kwargs):
        return nullcontext()

    def expander(self, *args, **kwargs):
        return nullcontext()

    def columns(self, sizes):
        return [self] * (sizes if isinstance(sizes, int) else len(sizes))

    def button(self, label, *, key, **kwargs):
        return key == self.selected_button

    def rerun(self, *args, **kwargs):
        raise Rerun()

    def stop(self):
        raise Stop()


def received():
    return {
        "cliente": "Maria", "whatsapp": "11900000002", "evento": "Festa",
        "observacoes": "Mensagem recebida do site:\n1. Caneca\nQuantidade: 2\nPersonalização/observações: Nome Ana",
        "itens": [
            {"produto": "Caneca", "quantidade": 2, "valor_unitario": 20.0, "especificacoes": "Nome Ana"},
            {"produto": "Caneca", "quantidade": 1, "valor_unitario": 21.0, "especificacoes": "Nome Bia"},
        ],
    }


class ImportIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.ui = UI()
        self.state = self.ui.session_state
        self.clients = [{"id": "old", "nome": "Maria", "documento": "", "whatsapp": "11900000001"}]
        self.view = True
        self.create = True
        self.anna = False
        self.legacy = Mock(side_effect=lambda n="", d="", w="": localizar_cliente_comercial(self.clients, nome=n, documento=d, whatsapp=w))
        self.forbidden = Mock(side_effect=AssertionError("A abertura não pode gravar dados ou usar fallback."))
        self.cloud = SimpleNamespace(load_document_confirmed=Mock(return_value=[]), load_document=self.forbidden)

        def navigate(page, message=None):
            self.ui.navigation.append((page, message))
            raise Rerun()

        self.env = {
            "st": self.ui, "copy": SimpleNamespace(deepcopy=deepcopy),
            "datetime": __import__("datetime").datetime,
            "_cloud_db": self.cloud, "_workflow_hf53": workflow,
            "ORCAMENTO_CLIENTE_LIVRE": FREE,
            "usuario_pode_ver_aba": lambda page: self.view and page == "novo_orcamento",
            "usuario_pode_acao": lambda page, action: self.create and (page, action) == ("novo_orcamento", "criar"),
            "obter_usuario_atual": lambda: {"nome": "Anna" if self.anna else "Jorge"},
            "usuario_em_operacao_protegida": lambda _: self.anna,
            "obter_perfil_configurado": lambda _: {"abas": ["novo_orcamento", "central"] if self.view else []},
            "hoje_local": lambda: TODAY, "valor_float": lambda value: float(value or 0),
            "rerun_na_aba": navigate,
            "carregar_clientes": lambda: deepcopy(self.clients),
            "localizar_cliente_comercial": self.legacy,
            "_rel_localizar_cliente_orcamento": localizar_cliente_orcamento,
            "_orcamento_opcoes_cliente": lambda clients=None: ([FREE, "Maria"], {"Maria": self.clients[0]}),
            "_orcamento_cliente_ref": lambda client: client["id"],
            "_orcamento_resumo_cliente_selecionado": lambda _: "",
            "_orcamento_cliente_por_nome_digitado_unico": Mock(return_value=self.clients[0]),
            "load_document": self.forbidden, "carregar_catalogo": self.forbidden,
            "carregar_atendimentos": self.forbidden, "carregar_projetos": self.forbidden,
            "salvar_atendimentos": self.forbidden, "salvar_projetos": self.forbidden,
            "salvar_historico_completo": self.forbidden,
        }
        nodes = [FUNCTIONS[name] for name in HELPERS]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "actual_app_helpers", "exec"), self.env)

    def call(self, name, *args, **kwargs):
        return self.env[name](*args, **kwargs)

    def marker(self, anna=None):
        return f"_hf54_cliente_importado_{'anna' if (self.anna if anna is None else anna) else 'jorge'}"

    def quote_keys(self):
        return ("anna_modal_", "anna_modal_itens", "anna_orc_cliente_novo") if self.anna else ("form_", "temp_itens", "jorge_orc_cliente")

    def test_permission_requires_view_and_creation(self):
        for view, create in ((True, True), (True, False), (False, True), (False, False)):
            with self.subTest(view=view, create=create):
                self.view, self.create = view, create
                self.assertIs(self.call("_hf54_pode_importar_site"), view and create)

    def test_enqueue_copies_data_does_not_rerun_or_save(self):
        data = received()
        self.assertTrue(self.call("_hf54_abrir_rascunho_importado", data))
        pending = self.state[workflow.PENDING_KEY]
        self.assertTrue(pending["dados"]["_hf54_importacao_site"])
        self.assertNotIn("_hf54_importacao_site", data)
        data["itens"][0]["especificacoes"] = "Alterado depois"
        self.assertEqual(pending["dados"]["itens"][0]["especificacoes"], "Nome Ana")
        self.assertEqual(self.ui.navigation, [])
        self.forbidden.assert_not_called()

    def test_pending_import_cannot_be_overwritten_by_second_click(self):
        self.call("_hf54_abrir_rascunho_importado", received())
        before = deepcopy(self.state)
        second = received(); second["cliente"] = "Outro trabalho"
        self.assertFalse(self.call("_hf54_abrir_rascunho_importado", second))
        self.assertEqual(self.state, before)
        self.assertTrue(self.ui.messages)

    def test_denied_creation_preserves_existing_draft(self):
        self.create = False
        self.state.update(form_cliente="Trabalho anterior", temp_itens=[{"produto": "Balão"}])
        before = deepcopy(self.state)
        self.assertFalse(self.call("_hf54_abrir_rascunho_importado", received()))
        self.assertEqual(self.state, before)
        self.forbidden.assert_not_called()

    def test_permission_revoked_after_enqueue_keeps_existing_work(self):
        self.state.update(form_cliente="Trabalho anterior", temp_itens=[{"produto": "Balão"}],
                          hf54_importar_jorge_texto="Mensagem preservada")
        before = deepcopy(self.state)
        self.call("_hf54_abrir_rascunho_importado", received())
        self.create = False
        self.call("_hf53_processar_abertura_pendente")
        self.assertEqual(self.state, before)
        self.assertNotIn(workflow.PENDING_KEY, self.state)
        self.assertEqual(self.ui.navigation, [])
        self.forbidden.assert_not_called()

    def test_empty_handoff_opens_once_in_correct_context(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                data = received()
                self.call("_hf54_abrir_rascunho_importado", data)
                with self.assertRaises(Rerun):
                    self.call("_hf53_processar_abertura_pendente")
                prefix, items_key, selector = self.quote_keys()
                self.assertEqual(self.state[items_key], data["itens"])
                self.assertEqual(self.state[prefix + "observacoes"], data["observacoes"])
                self.assertEqual(self.state[prefix + "whatsapp"], data["whatsapp"])
                self.assertEqual(self.state[selector + "_seletor"], FREE)
                self.assertTrue(self.state[self.marker()])
                self.assertEqual(self.ui.navigation[-1][0], "central" if anna else "novo_orcamento")
                self.assertEqual(self.state.get("_hf53_anna_abrir_formulario"), "novo_orcamento" if anna else None)
                self.assertNotIn(workflow.PENDING_KEY, self.state)
                before = deepcopy(self.state)
                self.call("_hf53_processar_abertura_pendente")
                self.assertEqual(self.state, before)
                self.assertEqual(len(self.ui.navigation), 1)
                self.forbidden.assert_not_called()

    def test_cancel_and_continue_preserve_current_work_and_identity(self):
        for anna in (False, True):
            for choice in ("cancelar", "continuar"):
                with self.subTest(anna=anna, choice=choice):
                    self.setUp(); self.anna = anna
                    prefix, items_key, selector = self.quote_keys()
                    self.state.update({prefix + "cliente": "Trabalho em andamento", items_key: [{"produto": "Balão"}],
                                       selector + "_seletor": "Maria", selector + "_token": "old", self.marker(): False})
                    before = deepcopy(self.state)
                    self.call("_hf54_abrir_rascunho_importado", received())
                    self.ui.selected_button = "hf53_abertura_" + choice
                    with self.assertRaises(Rerun):
                        self.call("_hf53_processar_abertura_pendente")
                    for key, value in before.items():
                        self.assertEqual(self.state[key], value)
                    self.assertNotIn(workflow.PENDING_KEY, self.state)
                    self.assertFalse(self.state[self.marker()])
                    self.forbidden.assert_not_called()

    def test_replace_discards_old_bindings_only_after_explicit_choice(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                prefix, items_key, selector = self.quote_keys()
                origin = "_anna_hf53" if anna else ""
                recognition = "_i811hf2_anna_cliente_reconhecido" if anna else "_i8111_cliente_reconhecido"
                self.state.update({prefix + "cliente": "Anterior", items_key: [{"produto": "Balão"}],
                                   selector + "_token": "old", selector + "_whatsapp_autofill": {"nome": "Anterior"},
                                   recognition + "_id": "old", recognition + "_msg": "encontrado",
                                   origin + "_atendimento_origem_id": "AT-antigo", origin + "_projeto_origem_id": "PR-antigo"})
                self.call("_hf54_abrir_rascunho_importado", received())
                with self.assertRaises(Stop):
                    self.call("_hf53_processar_abertura_pendente")
                self.assertEqual(self.state[prefix + "cliente"], "Anterior")
                self.ui.selected_button = "hf53_abertura_substituir"
                with self.assertRaises(Rerun):
                    self.call("_hf53_processar_abertura_pendente")
                self.assertEqual(self.state[items_key], received()["itens"])
                self.assertEqual(self.state[prefix + "cliente"], "Maria")
                self.assertEqual(self.state[selector + "_seletor"], FREE)
                for key in (selector + "_token", selector + "_whatsapp_autofill", recognition + "_id", recognition + "_msg"):
                    self.assertNotIn(key, self.state)
                self.assertEqual(self.state[origin + "_atendimento_origem_id"], "")
                self.assertEqual(self.state[origin + "_projeto_origem_id"], "")
                self.forbidden.assert_not_called()

    def test_next_regular_handoff_removes_import_scope(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                state = {self.marker(anna): True}
                workflow.solicitar_abertura(state, "novo_orcamento", {"cliente": "Manual"}, anna=anna)
                workflow.resolver_abertura(state, "substituir", hoje=TODAY)
                self.assertFalse(state[self.marker(anna)])

    def test_free_selector_preserves_reviewed_name_and_new_phone(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                self.call("_hf54_abrir_rascunho_importado", received())
                with self.assertRaises(Rerun): self.call("_hf53_processar_abertura_pendente")
                prefix, _, selector = self.quote_keys()
                self.call("_orcamento_campos_cliente", selector, nome_key=prefix + "cliente", documento_key=prefix + "documento", whatsapp_key=prefix + "whatsapp")
                self.assertEqual(self.state[prefix + "cliente"], "Maria")
                self.assertEqual(self.state[prefix + "whatsapp"], "11900000002")
                self.legacy.assert_not_called()

    def test_commercial_identity_rejects_homonym_with_new_phone(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.state[self.marker(anna)] = True
                self.assertIsNone(self.call("_hf54_cliente_do_formulario", "Maria", "", "11900000002", anna=anna))
                self.assertEqual(self.call("_hf54_cliente_do_formulario", "Maria", "", "11900000001", anna=anna)["id"], "old")
                self.state[self.marker(anna)] = False
                self.assertEqual(self.call("_hf54_cliente_do_formulario", "Maria", "", "11900000002", anna=anna)["id"], "old")

    def test_actual_form_price_and_badge_calls_respect_import_identity(self):
        targets = {"cliente_modal_i811", "cliente_previa_i8113", "cliente_item_i811", "cliente_itens_i811",
                   "cliente_reconhecido_i8111", "cliente_i811", "cliente_atual_i811"}
        assignments = [node for node in ast.walk(TREE) if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id in targets for t in node.targets)]
        self.assertEqual(len(assignments), len(targets))
        self.state.update({"_hf54_cliente_importado_anna": True, "_hf54_cliente_importado_jorge": True,
                           "form_cliente": "Maria", "form_documento": "", "form_whatsapp": "11900000002"})
        self.env.update(nome="Maria", doc="", wa="11900000002")
        for node in assignments:
            with self.subTest(target=ast.unparse(node.targets[0])):
                result = eval(compile(ast.Expression(node.value), "actual_form_identity", "eval"), self.env)
                self.assertIsNone(result)
        self.legacy.assert_not_called()

    def test_explicit_customer_selection_remains_available(self):
        self.state.update(form_cliente="Maria", form_documento="", form_whatsapp="11900000002",
                          _hf54_cliente_importado_jorge=True, jorge_orc_cliente_seletor="Maria")
        self.call("_orcamento_campos_cliente", "jorge_orc_cliente", nome_key="form_cliente", documento_key="form_documento", whatsapp_key="form_whatsapp")
        self.assertEqual(self.state["form_whatsapp"], "11900000001")
        self.assertEqual(self.call("_hf54_cliente_do_formulario", "Maria", "", self.state["form_whatsapp"])["id"], "old")

    def test_name_autofill_guard_is_scoped_to_free_imported_customer(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                prefix, _, selector = self.quote_keys()
                self.state.update({prefix + "cliente": "Mari", prefix + "documento": "", prefix + "whatsapp": "11900000002",
                                   selector + "_seletor": FREE, self.marker(): True})
                kwargs = dict(prefixo=selector, nome_key=prefix + "cliente", documento_key=prefix + "documento",
                              whatsapp_key=prefix + "whatsapp", reconhecido_id_key="recognition", mensagem_key="message")
                before = deepcopy(self.state)
                self.call("_orcamento_autopreencher_cliente_por_nome", **kwargs)
                self.assertEqual(self.state, before)
                self.env["_orcamento_cliente_por_nome_digitado_unico"].assert_not_called()
                self.state[self.marker()] = False
                self.call("_orcamento_autopreencher_cliente_por_nome", **kwargs)
                self.assertEqual(self.state[prefix + "whatsapp"], "11900000001")

    def test_long_original_is_kept_through_handoff_render_and_persistence(self):
        text = "Mensagem recebida do site:\n" + ("Nota completa <b>texto literal</b>\n" * 600) + "ÚLTIMO ITEM"
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.setUp(); self.anna = anna
                data = received(); data["observacoes"] = text
                self.call("_hf54_abrir_rascunho_importado", data)
                with self.assertRaises(Rerun): self.call("_hf53_processar_abertura_pendente")
                prefix, _, _ = self.quote_keys()
                self.call("_hf54_mostrar_origem_orcamento", self.state[prefix + "observacoes"])
                self.assertEqual(self.ui.texts, [text])
                self.assertEqual(self.ui.infos, [])
                self.state["form_observacoes"] = text
                self.state["anna_modal_observacoes"] = text
                values = [value for node in ast.walk(TREE) if isinstance(node, ast.Dict)
                          for key, value in zip(node.keys, node.values)
                          if isinstance(key, ast.Constant) and key.value == "briefing_origem"]
                self.assertEqual(len(values), 2)
                for value in values:
                    self.assertEqual(eval(compile(ast.Expression(value), "actual_origin_persistence", "eval"), self.env), text)

    def test_reset_and_existing_proposal_loading_clear_import_identity(self):
        self.state.update(_hf54_cliente_importado_jorge=True, _limpar_formulario_pendente=True, form_key=1)
        self.call("aplicar_limpeza_formulario_pendente")
        self.assertNotIn("_hf54_cliente_importado_jorge", self.state)
        self.state.update(_hf54_cliente_importado_jorge=True,
                          _proposta_pendente_formulario={"prop": {"numero_proposta": "P1", "cliente_nome": "Anterior"}, "duplicar": False})
        self.call("aplicar_proposta_pendente_no_formulario")
        self.assertNotIn("_hf54_cliente_importado_jorge", self.state)
        self.assertEqual(self.state["form_cliente"], "Anterior")

    def test_anna_initialization_preserves_import_handoff_but_clears_other_proposal(self):
        self.anna = True
        self.call("_hf54_abrir_rascunho_importado", received())
        with self.assertRaises(Rerun): self.call("_hf53_processar_abertura_pendente")
        initializer = next(n for n in FUNCTIONS["dialog_orcamento_anna"].body
                           if isinstance(n, ast.If) and "_hf53_anna_contexto_formulario" in ast.unparse(n.test))
        self.env.update(proposta={}, numero_original="", chave_modal="anna_modal_iniciado_novo",
                        cliente_prefixo_hf6="anna_orc_cliente_novo")
        code = compile(ast.Module(body=[initializer], type_ignores=[]), "actual_anna_initialization", "exec")
        before = deepcopy(self.state)
        exec(code, self.env)
        self.assertEqual(self.state, before)
        self.assertTrue(self.state["_hf54_cliente_importado_anna"])
        self.env.update(proposta={"numero_proposta": "P2", "cliente_nome": "Outro cliente", "itens": []},
                        numero_original="P2", chave_modal="anna_modal_iniciado_P2", cliente_prefixo_hf6="anna_orc_cliente_P2")
        exec(code, self.env)
        self.assertNotIn("_hf54_cliente_importado_anna", self.state)
        self.assertEqual(self.state["anna_modal_cliente"], "Outro cliente")

    def test_catalog_read_rejects_invalid_payload_without_fallback(self):
        for value in ({"itens": []}, None, "[]", ["produto inválido"]):
            with self.subTest(value=value):
                self.cloud.load_document_confirmed.return_value = value
                with self.assertRaisesRegex(ValueError, "inválido"):
                    self.call("_hf54_carregar_catalogo_importacao")
        self.forbidden.assert_not_called()

    def test_catalog_error_preserves_message_and_hides_internal_details(self):
        self.state["hf54_importar_jorge_texto"] = "Mensagem preservada"
        before = deepcopy(self.state)
        self.cloud.load_document_confirmed.side_effect = RuntimeError("token-interno-sensivel")
        with self.assertRaises(ValueError) as caught:
            self.call("_hf54_carregar_catalogo_importacao")
        self.assertNotIn("token-interno-sensivel", str(caught.exception))
        self.assertIn("catálogo online", str(caught.exception))
        self.assertEqual(self.state, before)
        self.forbidden.assert_not_called()

    def test_actual_confirmed_catalog_reader_uses_only_get(self):
        self.env["_cloud_db"] = cloud_db
        session = Mock()
        response = session.get.return_value
        response.json.return_value = [{"value": [{"Nome": "Caneca", "Preco": "20,00"}]}]
        with patch.object(cloud_db, "online_configured", return_value=True), \
                patch.object(cloud_db, "_config", return_value=("https://example.invalid", "dummy")), \
                patch.object(cloud_db, "_SESSION", session), \
                patch.object(cloud_db, "_read_local", self.forbidden), \
                patch.object(cloud_db, "_write_local", self.forbidden), \
                patch.object(cloud_db, "save_document", self.forbidden):
            result = self.call("_hf54_carregar_catalogo_importacao")
            self.assertEqual(result, [{"Nome": "Caneca", "Preco": "20,00"}])
            self.assertEqual(session.get.call_args.kwargs["params"]["key"], "eq.catalogo_db")
            self.assertEqual([call[0] for call in session.method_calls], ["get"])
            self.forbidden.assert_not_called()


if __name__ == "__main__":
    unittest.main()
