"""Integração real da conferência com leitura, permissões e salvamento.

Extrai os helpers e os corpos de Salvar do app.py por AST, sem iniciar o
Manager. Persistência e navegação são substituídas por sentinelas para provar
que nenhuma escrita ocorre antes da decisão de conferência.
"""
from __future__ import annotations

import ast
import copy
from datetime import date, datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cloud_db
from relacionamentos_service import localizar_cliente_orcamento


SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = {n.name: n for n in TREE.body if isinstance(n, ast.FunctionDef)}
HELPERS = (
    "_hf55_carregar_historico_conferencia", "_hf55_rascunho_para_conferencia",
    "_hf55_consultar_proposta", "_hf55_renderizar_conferencia", "_hf55_validar_conferencia",
)
TODAY = date(2026, 11, 25)


class State(dict):
    __setattr__ = dict.__setitem__

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


class Rerun(BaseException):
    pass


class ReachedWrite(BaseException):
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
    raise AssertionError("Botão real de salvar não encontrado")


class DuplicateIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.history_file = Path(self.temporary.name) / "historico_orcamentos.json"
        self.state = State(
            form_key=4, anna_modal_item_key=7, editar_numero="", temp_itens=[],
            form_observacoes="Mensagem recebida do site:\n1. Caneca\nQuantidade: 1",
            anna_modal_observacoes="Mensagem recebida do site:\n1. Camiseta\nQuantidade: 2",
            _atendimento_origem_id="AT-J", _projeto_origem_id="PRJ-J",
            _anna_hf53_atendimento_origem_id="AT-A", _anna_hf53_projeto_origem_id="PRJ-A",
        )
        self.ui = SimpleNamespace(
            session_state=self.state, caption=Mock(), warning=Mock(), error=Mock(),
            rerun=Mock(side_effect=Rerun), stop=Mock(side_effect=Rerun),
        )
        self.db = SimpleNamespace(
            online_configured=Mock(return_value=True),
            load_document_confirmed=Mock(return_value=[]),
        )
        self.duplicate = SimpleNamespace(
            renderizar_conferencia=Mock(), validar_salvamento=Mock(return_value=True),
            limpar_conferencia=Mock(),
        )
        self.permission = Mock(return_value=True)
        self.navigate = Mock(side_effect=Rerun)
        self.env = {
            "st": self.ui, "copy": copy, "json": json, "Path": Path,
            "_cloud_db": self.db, "ARQUIVO_HISTORICO": str(self.history_file),
            "_duplicidades_hf55": self.duplicate, "usuario_pode_ver_aba": self.permission,
            "_rel_localizar_cliente_orcamento": localizar_cliente_orcamento,
            "hoje_local": lambda: TODAY, "valor_float": lambda value: float(value or 0),
            "rerun_na_aba": self.navigate,
            # Esta suíte verifica a conferência HF55; a validação comercial
            # anterior tem testes próprios com o serviço real na HF56.
            "_hf56_validar_revisao": Mock(return_value=True),
        }
        module = ast.Module(body=[copy.deepcopy(FUNCTIONS[name]) for name in HELPERS], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "app.py", "exec"), self.env)

    def read(self):
        return self.env["_hf55_carregar_historico_conferencia"]()

    def draft(self, anna=False, **changes):
        args = dict(
            nome=" Maria ", documento="123.456.789-09", whatsapp="(11) 99999-7777",
            evento=" Festa ", itens=[{
                "produto": "Caneca", "quantidade": 2, "valor_unitario": 19.5,
                "especificacoes": "Nome Ana", "produto_catalogo_id": "CAT-1",
                "preco_especial_aplicado": True, "metadados": {"origem": "site"},
            }], entrega=TODAY, desconto=3.0, prazo="10", frete="Entrega",
            taxa_entrega=8.0, validade="5", subtotal=39.0, total=44.0, anna=anna,
        )
        args.update(changes)
        return self.env["_hf55_rascunho_para_conferencia"](**args)

    def test_online_confirma_chave_correta_sem_contingencia_nem_mutacao(self):
        history = [{"numero_proposta": "P-1", "itens": [{"produto": "Caneca"}]}]
        self.db.load_document_confirmed.return_value = history
        self.history_file.write_text("JSON local inválido", encoding="utf-8")
        result = self.read()
        self.db.load_document_confirmed.assert_called_once_with("historico_orcamentos", [])
        result[0]["itens"].clear()
        self.assertEqual(len(history[0]["itens"]), 1)
        self.assertEqual(self.history_file.read_text(encoding="utf-8"), "JSON local inválido")

    def test_falha_online_nunca_considera_historico_local_vazio_como_confirmacao(self):
        self.history_file.write_text("[]", encoding="utf-8")
        self.db.load_document_confirmed.side_effect = RuntimeError("segredo interno")
        with self.assertRaises(ValueError) as raised:
            self.read()
        self.assertNotIn("segredo interno", str(raised.exception))
        self.assertIn("preservado", str(raised.exception))

    def test_shapes_invalidos_do_historico_sao_recusados(self):
        for invalid in (None, {}, "[]", [None], ["proposta"], [{}, 1]):
            with self.subTest(invalid=invalid):
                self.db.load_document_confirmed.return_value = invalid
                with self.assertRaises(ValueError):
                    self.read()

    def test_leitura_fresca_em_cada_chamada_nao_usa_cache(self):
        self.db.load_document_confirmed.side_effect = [[], [{"numero_proposta": "NOVA"}]]
        self.assertEqual(self.read(), [])
        self.assertEqual(self.read()[0]["numero_proposta"], "NOVA")
        self.assertEqual(self.db.load_document_confirmed.call_count, 2)

    def test_offline_explicito_le_arquivo_existente_sem_criar_outros(self):
        self.db.online_configured.return_value = False
        data = [{"numero_proposta": "LOCAL", "cliente_nome": "Maria"}]
        original = json.dumps(data)
        self.history_file.write_text(original, encoding="utf-8")
        self.assertEqual(self.read(), data)
        self.assertEqual(self.history_file.read_text(encoding="utf-8"), original)
        self.db.load_document_confirmed.assert_not_called()
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [self.history_file])

    def test_offline_ausencia_confirmada_nao_cria_arquivo(self):
        self.db.online_configured.return_value = False
        self.assertEqual(self.read(), [])
        self.assertFalse(self.history_file.exists())

    def test_offline_corrompido_ou_servico_indisponivel_nao_finge_sucesso(self):
        self.db.online_configured.return_value = False
        self.history_file.write_text("{ incompleto", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.read()
        self.env["_cloud_db"] = None
        self.history_file.write_text("[]", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.read()

    def test_adapter_http_real_so_get_e_ausencia_confirmada(self):
        self.env["_cloud_db"] = cloud_db
        response = Mock()
        response.json.return_value = []
        with patch.object(cloud_db, "_config", return_value=("https://banco.test", "chave-ficticia")), \
             patch.object(cloud_db, "_SESSION") as session, \
             patch.object(cloud_db, "_read_local", side_effect=AssertionError("fallback proibido")), \
             patch.object(cloud_db, "_write_local", side_effect=AssertionError("escrita proibida")):
            session.get.return_value = response
            self.assertEqual(self.read(), [])
            self.assertEqual(session.get.call_args.kwargs["params"]["key"], "eq.historico_orcamentos")
            session.post.assert_not_called()
            session.put.assert_not_called()
            response.json.return_value = [{"value": [{"numero_proposta": "ONLINE"}]}]
            self.assertEqual(self.read()[0]["numero_proposta"], "ONLINE")
            session.get.side_effect = OSError("conexão indisponível")
            with self.assertRaises(ValueError):
                self.read()

    def test_sem_permissao_nao_expoe_nem_le_historico(self):
        self.permission.return_value = False
        with self.assertRaises(PermissionError):
            self.read()
        self.env["_hf55_renderizar_conferencia"](self.draft())
        self.assertTrue(self.env["_hf55_validar_conferencia"](self.draft()))
        self.db.online_configured.assert_not_called()
        self.duplicate.renderizar_conferencia.assert_not_called()
        self.duplicate.validar_salvamento.assert_not_called()
        self.assertIn("acesso ao Histórico", self.ui.caption.call_args.args[0])

    def test_rascunho_tem_campos_reais_metadados_e_copia_profunda(self):
        items = [{"produto": "Caneca", "quantidade": 2, "valor_unitario": 19.5,
                  "especificacoes": "Nome Ana", "metadados": {"origem": "site"}}]
        result = self.draft(itens=items)
        self.assertEqual(result["cliente_nome"], "Maria")
        self.assertEqual(result["data_entrega"], "25/11/2026")
        self.assertEqual(result["itens"], items)
        self.assertEqual(result["briefing_origem"], self.state.form_observacoes)
        self.assertEqual(result["atendimento_id"], "AT-J")
        self.assertEqual(result["projeto_id"], "PRJ-J")
        self.assertEqual(result["_contexto_formulario"], {"perfil": "jorge", "sequencia": 4})
        result["itens"][0]["metadados"]["origem"] = "alterado"
        self.assertEqual(items[0]["metadados"]["origem"], "site")
        self.db.online_configured.assert_not_called()

    def test_rascunho_anna_usa_origem_e_geracao_proprias(self):
        result = self.draft(anna=True)
        self.assertEqual(result["briefing_origem"], self.state.anna_modal_observacoes)
        self.assertEqual(result["atendimento_id"], "AT-A")
        self.assertEqual(result["projeto_id"], "PRJ-A")
        self.assertEqual(result["_contexto_formulario"], {"perfil": "anna", "sequencia": 7})
        self.state.anna_modal_item_key += 1
        self.assertNotEqual(result["_contexto_formulario"], self.draft(anna=True)["_contexto_formulario"])

    def test_cadastro_selecionado_renomeado_sem_contato_e_identificado_pelo_vinculo(self):
        from proposal_duplicate_service_hf55 import analisar_duplicidades
        selected = {"id": "REL-1", "nome": "Maria Atual", "documento": "", "whatsapp": ""}
        draft = self.draft(nome="Maria Atual", documento="", whatsapp="", cliente_selecionado=selected)
        self.assertEqual(draft["relacionamento_id"], "REL-1")
        old = copy.deepcopy(draft)
        old.update(cliente_nome="Maria Antiga", data_geracao="24/11/2026", numero_proposta="P-1")
        result = analisar_duplicidades(draft, [old], TODAY)
        self.assertEqual(result["candidatos"][0]["identidade"], "relacionamento")
        self.db.online_configured.assert_not_called()

    def test_dados_digitados_de_outro_cliente_nao_herdam_vinculo_do_seletor(self):
        selected = {"id": "REL-1", "nome": "Maria", "documento": "", "whatsapp": "11988887777"}
        for fields in ({"nome": "Maria", "whatsapp": "11911112222"},
                       {"nome": "Outra Pessoa", "whatsapp": ""}):
            with self.subTest(fields=fields):
                result = self.draft(documento="", cliente_selecionado=selected, **fields)
                self.assertEqual(result["relacionamento_id"], "")

    def test_aprovacao_abrange_preco_quantidade_condicoes_origem_e_contexto(self):
        from proposal_duplicate_service_hf55 import assinatura_proposta
        original = self.draft()
        fingerprint = assinatura_proposta(original)
        changes = {
            "documento": "outro", "whatsapp": "11911112222", "evento": "Outro",
            "data_entrega": "26/11/2026", "prazo_dias": "20", "validade_dias": "7",
            "desconto": 4.0, "valor_total": 45.0, "frete_tipo": "Retirada",
            "taxa_entrega": 9.0, "briefing_origem": "Nova origem", "projeto_id": "PRJ-NOVO",
            "_contexto_formulario": {"perfil": "jorge", "sequencia": 5},
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed[field] = value
                self.assertNotEqual(fingerprint, assinatura_proposta(changed))
        for field, value in (("valor_unitario", 20), ("quantidade", 3), ("especificacoes", "Nome Pedro")):
            changed = copy.deepcopy(original)
            changed["itens"][0][field] = value
            self.assertNotEqual(fingerprint, assinatura_proposta(changed))

    def test_retirada_ignora_taxa_oculta_do_widget(self):
        self.assertEqual(self.draft(frete="Retirada", taxa_entrega=88)["taxa_entrega"], 0.0)

    def test_edicao_de_existente_nao_exige_conferencia_de_criacao(self):
        for anna in (False, True):
            self.env["_hf55_renderizar_conferencia"](self.draft(anna=anna), anna=anna, numero_original="EXISTENTE")
            self.assertTrue(self.env["_hf55_validar_conferencia"](self.draft(anna=anna), anna=anna, numero_original="EXISTENTE"))
        self.duplicate.renderizar_conferencia.assert_not_called()
        self.duplicate.validar_salvamento.assert_not_called()
        self.db.online_configured.assert_not_called()

    def test_perfis_usam_renderer_e_guard_reais_com_leitor_atual(self):
        for anna in (False, True):
            draft = self.draft(anna=anna)
            self.env["_hf55_renderizar_conferencia"](draft, anna=anna)
            self.env["_hf55_validar_conferencia"](draft, anna=anna)
            expected_prefix = "hf55_anna" if anna else "hf55_jorge"
            for call in (self.duplicate.renderizar_conferencia.call_args, self.duplicate.validar_salvamento.call_args):
                self.assertIs(call.args[0], self.ui)
                self.assertIs(call.args[1], draft)
                self.assertEqual(call.kwargs["prefixo"], expected_prefix)
                self.assertIs(call.kwargs["carregar_historico"], self.env["_hf55_carregar_historico_conferencia"])
                self.assertEqual(call.kwargs["hoje"], TODAY)

    def test_navegacao_preserva_rascunho_e_somente_abre_consulta(self):
        before = copy.deepcopy(self.state)
        with self.assertRaises(Rerun):
            self.env["_hf55_consultar_proposta"]("PROP-ANTIGA")
        self.assertEqual(self.state.alerta_proposta_numero, "PROP-ANTIGA")
        self.assertEqual({k: v for k, v in self.state.items() if k != "alerta_proposta_numero"}, before)
        self.navigate.assert_called_once_with("historico")
        self.db.online_configured.assert_not_called()

    def test_navegacao_revalida_permissao(self):
        self.permission.return_value = False
        before = copy.deepcopy(self.state)
        self.env["_hf55_consultar_proposta"]("PROP-ANTIGA")
        self.assertEqual(self.state, before)
        self.navigate.assert_not_called()

    def run_save(self, anna, *, allow=False, editing=False, name="Maria"):
        self.duplicate.validar_salvamento.return_value = allow
        self.state.editar_numero = "EXISTENTE" if editing else ""
        guarantee = Mock(side_effect=ReachedWrite)
        self.env.update(
            rascunho_hf55=self.draft(anna=anna), nome=name, doc="123", wa="11999997777",
            numero_original="EXISTENTE" if editing else "", proposta={},
            agora_local=lambda: datetime(2026, 11, 25, 12, 0),
            garantir_cliente_orcamento=guarantee, carregar_historico=Mock(return_value=[]),
        )
        function = ast.FunctionDef(
            name="_salvar_real", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[],
                kw_defaults=[], defaults=[]), body=copy.deepcopy(save_body(anna)), decorator_list=[],
        )
        module = ast.Module(body=[function], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "app.py", "exec"), self.env)
        try:
            self.env["_salvar_real"]()
        except (Rerun, ReachedWrite) as outcome:
            return guarantee, type(outcome)
        return guarantee, None

    def test_salvar_jorge_interrompe_antes_de_cadastrar_ou_gravar(self):
        before = copy.deepcopy(self.state)
        guarantee, outcome = self.run_save(False)
        self.assertIs(outcome, Rerun)
        guarantee.assert_not_called()
        self.assertEqual(self.state, before)
        self.navigate.assert_called_once_with("novo_orcamento")

    def test_salvar_anna_interrompe_com_rerun_do_dialogo_antes_de_gravar(self):
        before = copy.deepcopy(self.state)
        guarantee, outcome = self.run_save(True)
        self.assertIs(outcome, Rerun)
        guarantee.assert_not_called()
        self.assertEqual(self.state, before)
        self.ui.rerun.assert_called_once_with(scope="fragment")

    def test_salvar_liberado_prossegue_para_fluxo_existente_em_ambos(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                guarantee, outcome = self.run_save(anna, allow=True)
                self.assertIs(outcome, ReachedWrite)
                guarantee.assert_called_once()
                self.assertEqual(guarantee.call_args.args, ("Maria", "123", "11999997777"))

    def test_salvar_edicao_preserva_fluxo_sem_guard_de_nova_proposta(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                self.duplicate.validar_salvamento.reset_mock()
                guarantee, outcome = self.run_save(anna, editing=True)
                self.assertIs(outcome, ReachedWrite)
                guarantee.assert_called_once()
                self.duplicate.validar_salvamento.assert_not_called()

    def test_nome_anna_vazio_nao_consulta_nem_cadastra(self):
        guarantee, outcome = self.run_save(True, name="  ")
        self.assertIsNone(outcome)
        guarantee.assert_not_called()
        self.duplicate.validar_salvamento.assert_not_called()
        self.ui.error.assert_called_once_with("Informe o nome do cliente.")


if __name__ == "__main__":
    unittest.main()
