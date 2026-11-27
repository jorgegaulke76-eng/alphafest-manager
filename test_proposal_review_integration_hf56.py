"""HF56: executa os helpers e caminhos reais do app por AST, sem iniciar o Manager.

A conferência e o estado de aprovação são reais. Cadastro, persistência e
navegação usam doubles para provar a ordem dos efeitos e a retenção na falha.
"""
from __future__ import annotations

import ast
from contextlib import nullcontext
import copy
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import manager_workflow_hf53 as workflow
import proposal_review_ui_hf56 as review_ui
from catalogo_orcamento_service import ORCAMENTO_PRODUTO_LIVRE
from relacionamentos_service import localizar_cliente_orcamento


ROOT = Path(__file__).resolve().parent
TREE = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
FUNCTIONS = {node.name: node for node in TREE.body if isinstance(node, ast.FunctionDef)}
HELPERS = (
    "valor_float", "_hf55_rascunho_para_conferencia", "_hf56_rascunho_para_revisao",
    "_hf56_renderizar_revisao", "_hf56_validar_revisao", "atualizar_proposta",
    "_hf57_preservar_pendencias_apos_salvar",
)
TODAY = date(2026, 11, 25)


class State(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        self[name] = value


class Rerun(BaseException):
    pass


def save_body(anna):
    scope = FUNCTIONS["dialog_orcamento_anna"] if anna else TREE
    for node in ast.walk(scope):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Call):
            continue
        call = node.test
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "button":
            continue
        if anna:
            found = any(k.arg == "key" and isinstance(k.value, ast.Constant)
                        and k.value.value == "anna_modal_salvar_orcamento" for k in call.keywords)
        else:
            found = bool(call.args and isinstance(call.args[0], ast.Name)
                         and call.args[0].id == "rotulo_salvar")
        if found:
            return node.body
    raise AssertionError("Botão de salvar real não encontrado")


def review_body(anna):
    for node in ast.walk(TREE):
        for _, value in ast.iter_fields(node):
            if not isinstance(value, list):
                continue
            for index, statement in enumerate(value):
                if not isinstance(statement, ast.Assign) or not isinstance(statement.value, ast.Call):
                    continue
                call = statement.value
                if not isinstance(call.func, ast.Name) or call.func.id != "_hf56_renderizar_revisao":
                    continue
                is_anna = any(k.arg == "anna" and isinstance(k.value, ast.Constant)
                              and k.value.value is True for k in call.keywords)
                if is_anna == anna:
                    return value[index:index + 2]
    raise AssertionError("Renderização real da revisão não encontrada")


def install_function(env, name, body):
    function = ast.FunctionDef(
        name=name, args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[],
                                     kw_defaults=[], defaults=[]),
        body=copy.deepcopy(body), decorator_list=[],
    )
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), "app.py", "exec"), env)
    return env[name]


class ReviewIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.state = State(
            form_key=3, anna_modal_item_key=7, editar_numero="", temp_itens=[],
            anna_modal_itens=[], form_observacoes="Mensagem recebida do site:\nCanecas para Ana",
            anna_modal_observacoes="Mensagem recebida do site:\nCanecas para Pedro",
        )
        self.ui = SimpleNamespace(
            session_state=self.state, caption=Mock(), error=Mock(), warning=Mock(),
            info=Mock(), dataframe=Mock(), expander=lambda *a, **k: nullcontext(),
            checkbox=Mock(return_value=False),
            rerun=Mock(side_effect=Rerun), stop=Mock(side_effect=Rerun),
        )
        self.duplicate_guard = Mock(return_value=True)
        self.duplicate_render = Mock()
        self.duplicate_clear = Mock()
        self.history = []
        self.persist = Mock(return_value=True)
        self.guarantee = Mock(return_value=(True, {"id": "CLIENTE-TESTE"}, False, ""))
        self.anna_persist = Mock(return_value=(True, "PROP-ANNA-TESTE"))
        self.navigate = Mock(side_effect=Rerun)
        self.env = {
            "copy": copy, "st": self.ui, "_workflow_hf53": workflow, "_revisao_hf56": review_ui,
            "_rel_localizar_cliente_orcamento": localizar_cliente_orcamento,
            "hoje_local": lambda: TODAY, "agora_local": lambda: datetime(2026, 11, 25, 12),
            "_hf55_validar_conferencia": self.duplicate_guard,
            "_hf55_renderizar_conferencia": self.duplicate_render,
            "_duplicidades_hf55": SimpleNamespace(limpar_conferencia=self.duplicate_clear),
            "rerun_na_aba": self.navigate, "garantir_cliente_orcamento": self.guarantee,
            "carregar_historico": Mock(side_effect=lambda **kwargs: copy.deepcopy(self.history)),
            "salvar_historico_completo": self.persist, "_anna_salvar_proposta": self.anna_persist,
            "resumo_perfil_comercial": lambda cliente: {}, "I811_MODALIDADE_NORMAL": "Normal",
            "_status_resumo": lambda proposta: {}, "registrar_evento_proposta": Mock(),
            "registrar_atividade": Mock(), "obter_usuario_atual": lambda: "Teste",
            "_hf53_vincular_proposta_origem_anna": Mock(), "agendar_limpeza_formulario": Mock(),
            "carregar_projetos": Mock(return_value=[]), "salvar_projetos": Mock(),
            "carregar_atendimentos": Mock(return_value={"itens": []}), "salvar_atendimentos": Mock(),
        }
        module = ast.Module(body=[copy.deepcopy(FUNCTIONS[name]) for name in HELPERS], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "app.py", "exec"), self.env)

    def draft(self, anna=False, **changes):
        args = {
            "nome": "Cliente de teste", "documento": "", "whatsapp": "11999990000",
            "evento": "Festa", "itens": [{"produto": "Caneca", "quantidade": 2,
                "valor_unitario": 20.0, "especificacoes": "Nome Ana", "produto_catalogo_id": "CAT-1",
                "metadata": {"arte": "ana.pdf", "cor": "Azul"}}],
            "entrega": TODAY, "desconto": 2.0, "prazo": "10", "frete": "Entrega",
            "taxa_entrega": 8.0, "validade": "5", "subtotal": 40.0, "total": 46.0, "anna": anna,
        }
        args.update(changes)
        return self.env["_hf55_rascunho_para_conferencia"](**args)

    def prepare(self, anna, draft, editing=False):
        numero = "PROP-EXISTENTE" if editing else ""
        self.state.editar_numero = numero
        self.state.temp_itens = copy.deepcopy(draft["itens"])
        self.state.anna_modal_itens = copy.deepcopy(draft["itens"])
        self.history = [{"numero_proposta": numero, "itens": [{"produto": "Item antigo"}]}] if numero else []
        self.env.update(
            rascunho_hf55=draft, nome=draft["cliente_nome"], doc=draft["documento"], wa=draft["whatsapp"],
            evento=draft["evento"], itens=copy.deepcopy(draft["itens"]), numero_original=numero,
            proposta=copy.deepcopy(self.history[0]) if numero else {},
            entrega=TODAY, dt_entrega=TODAY, desconto=draft["desconto"], desc=draft["desconto"],
            prazo=draft["prazo_dias"], frete=draft["frete_tipo"], taxa_entrega=draft["taxa_entrega"],
            validade=draft["validade_dias"], subtotal=draft["subtotal"], total=draft["valor_total"],
            chave_modal="anna_modal_iniciado_" + (numero or "novo"),
        )
        self.state[self.env["chave_modal"]] = True

    def render(self, anna, draft, editing=False, accept=False):
        self.prepare(anna, draft, editing)
        self.ui.checkbox.return_value = accept
        install_function(self.env, "_render_real", review_body(anna))()

    def run_save(self, anna, draft, editing=False):
        self.prepare(anna, draft, editing)
        try:
            install_function(self.env, "_save_real", save_body(anna))()
        except Rerun:
            pass

    def review_state(self, anna):
        return self.state["_hf56_" + ("anna" if anna else "jorge") + "_revisao_final"]

    def test_integracao_renderiza_revisao_antes_de_conferencia_de_semelhantes(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                draft = self.draft(anna)
                self.render(anna, draft)
                self.assertTrue(self.review_state(anna)["resultado"]["pode_salvar"])
                self.duplicate_render.assert_called_with(
                    draft, **({"anna": True} if anna else {}), numero_original="")
        self.guarantee.assert_not_called()
        self.persist.assert_not_called()
        self.anna_persist.assert_not_called()

    def test_dados_invalidos_nao_chegam_ao_renderer_hf55(self):
        for anna in (False, True):
            for value in (-20.0, float("nan"), float("inf"), None, "abc"):
                with self.subTest(anna=anna, value=value):
                    draft = self.draft(anna)
                    draft["itens"][0]["valor_unitario"] = value
                    self.duplicate_render.reset_mock()
                    self.render(anna, draft)
                    self.assertFalse(self.review_state(anna)["resultado"]["pode_salvar"])
                    self.duplicate_render.assert_not_called()

    def test_guard_real_bloqueia_campos_invalidos_antes_de_qualquer_efeito(self):
        variants = (
            {"desconto": 90.0, "valor_total": 8.0}, {"data_entrega": ""},
            {"subtotal": float("nan")}, {"valor_total": 999.0}, {"itens": []},
        )
        for anna in (False, True):
            for editing in (False, True):
                for changes in variants:
                    with self.subTest(anna=anna, editing=editing, fields=list(changes)):
                        draft = self.draft(anna)
                        draft.update(changes)
                        self.run_save(anna, draft, editing)
                        self.guarantee.assert_not_called()
                        self.duplicate_guard.assert_not_called()
                        self.persist.assert_not_called()
                        self.anna_persist.assert_not_called()
                        self.env["carregar_historico"].assert_not_called()

    def test_valido_prossegue_para_guard_hf55_e_salvamento_sem_aceite_extra(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.run_save(anna, self.draft(anna))
                self.assertEqual(self.guarantee.call_args.args, ("Cliente de teste", "", "11999990000"))
                self.duplicate_guard.assert_called()
                self.assertNotIn("_hf56_" + ("anna" if anna else "jorge") + "_revisao_final", self.state)
        self.persist.assert_called_once()
        self.anna_persist.assert_called_once()
        self.ui.checkbox.assert_not_called()

    def test_hf55_continua_podendo_interromper_depois_da_validacao_comercial(self):
        self.duplicate_guard.return_value = False
        for anna in (False, True):
            self.run_save(anna, self.draft(anna))
            self.assertTrue(self.review_state(anna)["resultado"]["pode_salvar"])
        self.guarantee.assert_not_called()
        self.persist.assert_not_called()
        self.anna_persist.assert_not_called()

    def test_brinde_importado_exige_aceite_novo_sem_herdar_confirmacao_da_importacao(self):
        self.state["hf54_importacao_confirmada"] = True
        for anna in (False, True):
            draft = self.draft(anna, desconto=0.0, subtotal=0.0, total=8.0)
            draft["itens"][0]["valor_unitario"] = 0.0
            self.run_save(anna, draft)
            self.assertTrue(self.review_state(anna)["resultado"]["pode_salvar"])
            self.assertFalse(self.review_state(anna)["confirmada"])
        self.duplicate_guard.assert_not_called()
        self.guarantee.assert_not_called()

    def test_brinde_confirmado_preserva_zero_personalizacao_e_origem(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                draft = self.draft(anna, desconto=0.0, subtotal=0.0, total=8.0)
                draft["itens"][0]["valor_unitario"] = 0.0
                self.render(anna, draft, accept=True)
                self.run_save(anna, draft)
                saved = self.anna_persist.call_args.args[0] if anna else self.persist.call_args.args[0][0]
                self.assertEqual(saved["itens"], draft["itens"])
                self.assertEqual(saved["valor_total"], 8.0)
                self.assertEqual(saved["briefing_origem"], draft["briefing_origem"])
                self.assertNotIn("_item_em_preenchimento", saved)
                self.assertNotIn("_numero_em_edicao", saved)

    def test_modificacao_apos_aceite_exige_revisao_antes_de_cadastrar(self):
        for anna in (False, True):
            draft = self.draft(anna, prazo="")
            self.render(anna, draft, accept=True)
            draft["itens"][0]["especificacoes"] = "Nome Pedro"
            self.run_save(anna, draft)
            self.assertFalse(self.review_state(anna)["confirmada"])
        self.guarantee.assert_not_called()

    def test_aceite_nao_permite_ignorar_desconto_excedente_introduzido_depois(self):
        for anna in (False, True):
            draft = self.draft(anna, prazo="")
            self.render(anna, draft, accept=True)
            draft.update(desconto=50.0, valor_total=8.0)
            self.run_save(anna, draft)
            self.assertFalse(self.review_state(anna)["resultado"]["pode_salvar"])
        self.guarantee.assert_not_called()

    def test_edicao_historica_nao_exige_aceite_apenas_por_data_passada(self):
        for anna in (False, True):
            self.run_save(anna, self.draft(anna, entrega=date(2020, 1, 1)), editing=True)
        self.assertEqual(self.guarantee.call_count, 2)
        self.persist.assert_called_once()
        self.anna_persist.assert_called_once()

    def test_data_vazia_chega_como_bloqueio_sem_falha_de_strftime(self):
        for anna in (False, True):
            draft = self.draft(anna, entrega=None)
            self.assertEqual(draft["data_entrega"], "")
            self.render(anna, draft)
            codes = {x["codigo"] for x in self.review_state(anna)["resultado"]["bloqueios"]}
            self.assertIn("data_entrega_invalida", codes)
        self.duplicate_render.assert_not_called()

    def test_item_pendente_mudou_exige_novo_aceite_em_ambos(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                prefix, sequence = ("anna_modal_prod_", 7) if anna else ("produto_novo_", 3)
                self.state[f"{prefix}{sequence}_livre"] = "Caixa personalizada"
                draft = self.draft(anna)
                self.render(anna, draft, accept=True)
                self.assertTrue(self.review_state(anna)["confirmada"])
                self.state[f"{prefix}{sequence}_livre"] = "Sacola personalizada"
                self.run_save(anna, draft)
                self.assertFalse(self.review_state(anna)["confirmada"])
                self.assertIn("item_pendente", {x["codigo"] for x in self.review_state(anna)["resultado"]["avisos"]})
        self.guarantee.assert_not_called()

    def test_snapshot_pendente_nao_muta_proposta_e_distingue_numero_em_edicao(self):
        draft = self.draft()
        original = copy.deepcopy(draft)
        self.state["produto_novo_3_livre"] = "Novo produto"
        result = self.env["_hf56_rascunho_para_revisao"](draft, numero_original="P-1")
        self.assertEqual(draft, original)
        self.assertEqual(result["_numero_em_edicao"], "P-1")
        self.assertEqual(result["_item_em_preenchimento"]["produto_livre"], "Novo produto")
        result["itens"][0]["metadata"]["cor"] = "Verde"
        self.assertEqual(draft["itens"][0]["metadata"]["cor"], "Azul")

    def test_falha_jorge_preserva_rascunho_aceite_e_vinculos_sem_mensagem_de_sucesso(self):
        for editing in (False, True):
            with self.subTest(editing=editing):
                self.persist.return_value = False
                self.state.update(_atendimento_origem_id="AT-1", _projeto_origem_id="PRJ-1")
                draft = self.draft(prazo="")
                self.render(False, draft, editing=editing, accept=True)
                self.run_save(False, draft, editing)
                self.assertEqual(self.state.temp_itens, draft["itens"])
                self.assertEqual(self.state._atendimento_origem_id, "AT-1")
                self.assertEqual(self.state._projeto_origem_id, "PRJ-1")
                self.assertTrue(self.review_state(False)["confirmada"])
                self.assertIn("rascunho foi mantido", self.ui.error.call_args.args[0])
                self.assertNotIn("_ultima_proposta_salva", self.state)
                self.env["agendar_limpeza_formulario"].assert_not_called()
                self.env["salvar_projetos"].assert_not_called()
                self.env["salvar_atendimentos"].assert_not_called()
                self.duplicate_clear.assert_not_called()
                self.navigate.assert_not_called()

    def test_falha_anna_preserva_modal_itens_aceite_e_vinculos(self):
        self.anna_persist.return_value = (False, "Falha de gravação de teste")
        for editing in (False, True):
            draft = self.draft(True, prazo="")
            self.render(True, draft, editing=editing, accept=True)
            self.run_save(True, draft, editing)
            self.assertTrue(self.state[self.env["chave_modal"]])
            self.assertEqual(self.state.anna_modal_itens, draft["itens"])
            self.assertTrue(self.review_state(True)["confirmada"])
        self.duplicate_clear.assert_not_called()
        self.ui.rerun.assert_not_called()
        self.env["_hf53_vincular_proposta_origem_anna"].assert_not_called()
        self.env["registrar_atividade"].assert_not_called()

    def test_atualizar_proposta_retorna_confirmacao_real_e_busca_atual(self):
        self.history = [{"numero_proposta": "P-1", "itens": []}]
        for confirmed in (False, True):
            self.persist.return_value = confirmed
            self.assertIs(self.env["atualizar_proposta"]("P-1", {"numero_proposta": "P-1"}), confirmed)
            self.env["carregar_historico"].assert_called_with(force_refresh=True)

    def test_edicao_ausente_nao_inventa_registro_nem_afirma_gravacao(self):
        self.assertFalse(self.env["atualizar_proposta"]("P-AUSENTE", {"numero_proposta": "P-AUSENTE"}))
        self.persist.assert_not_called()

    def test_apos_sucesso_somente_revisao_do_formulario_salvo_e_limpa(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                other = "_hf56_" + ("jorge" if anna else "anna") + "_revisao_final"
                self.state[other] = {"prova": "outro formulário", "confirmada": True}
                self.run_save(anna, self.draft(anna))
                self.assertEqual(self.state[other], {"prova": "outro formulário", "confirmada": True})
                own = "_hf56_" + ("anna" if anna else "jorge") + "_revisao_final"
                self.assertNotIn(own, self.state)


class PendingItemContextTest(unittest.TestCase):
    def test_campos_padrao_e_geracoes_antigas_nao_indicam_item_pendente(self):
        state = {
            "form_key": 3, "produto_novo_3_catalogo": ORCAMENTO_PRODUTO_LIVRE,
            "produto_novo_3_livre": "  ", "qtd_3": 1, "valor_3": 0.0,
            "produto_novo_2_livre": "Item já incluído", "tema_2": "Antigo", "valor_2": 20,
            "anna_modal_item_key": 4, "anna_modal_prod_4_catalogo": ORCAMENTO_PRODUTO_LIVRE,
            "anna_modal_qtd_4": 1, "anna_modal_valor_4": 0.0,
            "anna_modal_prod_3_livre": "Item já incluído", "anna_modal_obs_3": "Antigo",
        }
        for anna in (False, True):
            self.assertIsNone(workflow.item_em_preenchimento(state, anna=anna))

    def test_produto_escolhido_ou_texto_livre_aparece_no_snapshot(self):
        for anna in (False, True):
            sequence_key = "anna_modal_item_key" if anna else "form_key"
            prefix = "anna_modal_prod_8" if anna else "produto_novo_8"
            for field in ("_catalogo", "_livre"):
                state = {sequence_key: 8, prefix + field: "Caneca"}
                result = workflow.item_em_preenchimento(state, anna=anna)
                self.assertEqual(result["perfil"], "anna" if anna else "jorge")
                self.assertEqual(result["sequencia"], 8)
                self.assertEqual(result["produto" + field], "Caneca")

    def test_detalhes_quantidade_e_preco_ativos_sao_detectados_isoladamente(self):
        for anna in (False, True):
            prefix = "anna_modal_" if anna else ""
            sequence_key = "anna_modal_item_key" if anna else "form_key"
            fields = {"tema": "Tema", "nome_item": "Ana", "cor": "Azul", "idade": "5",
                      "obs" if anna else "obs_item": "Detalhe", "qtd": 2, "valor": 0.5}
            for field, value in fields.items():
                with self.subTest(anna=anna, field=field):
                    state = {sequence_key: 9, f"{prefix}{field}_9": value}
                    self.assertIsNotNone(workflow.item_em_preenchimento(state, anna=anna))
                    self.assertIsNone(workflow.item_em_preenchimento(state, anna=not anna))

    def test_snapshot_nao_inclui_campos_de_item_ainda_nao_recebidos_do_navegador(self):
        state = {"form_key": 4, "produto_novo_4_livre": "Caixa"}
        result = workflow.item_em_preenchimento(state)
        self.assertEqual(result["detalhes"], {"tema": "", "nome_item": "", "cor": "", "idade": "", "obs_item": ""})
        self.assertEqual(result["quantidade"], 1)
        self.assertEqual(result["valor_unitario"], 0)


if __name__ == "__main__":
    unittest.main()
