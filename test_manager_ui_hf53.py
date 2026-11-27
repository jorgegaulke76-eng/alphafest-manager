"""Smoke Streamlit dos helpers reais extraídos por AST, sem executar app.py.

Executar com o runtime de QA no PYTHONPATH. Sem Streamlit instalado os testes
são explicitamente ignorados; os testes puros continuam usando só stdlib.
"""
import ast
from pathlib import Path
import unittest

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


APP_SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)


def funcoes_reais(*nomes):
    por_nome = {n.name: n for n in APP_TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return "\n\n".join(ast.get_source_segment(APP_SOURCE, por_nome[nome]) for nome in nomes) + "\n\n"


BASE = '''
import copy
from datetime import date, datetime
import streamlit as st
import manager_workflow_hf53 as _workflow_hf53
from catalogo_orcamento_service import (
    resolver_produto_orcamento as _catalogo_resolver_orcamento,
    produto_catalogo_da_meta as _catalogo_produto_da_meta,
    snapshot_item_catalogo as _catalogo_snapshot_item,
    ORCAMENTO_PRODUTO_LIVRE as _catalogo_orcamento_livre,
)
def valor_float(v):
    return float(v or 0)
def hoje_local():
    return date(2026,11,25)
def agora_local():
    return datetime(2026,11,25,12,0,0)
def obter_usuario_atual():
    return {"nome":"Jorge"}
def usuario_em_operacao_protegida(usuario):
    return False
def obter_perfil_configurado(usuario):
    return {"abas":["projeto","novo_orcamento","central"]}
def carregar_catalogo():
    return []
def rerun_na_aba(chave, mensagem=None):
    st.session_state["destino"] = chave
    st.rerun()
def _hf53_registrar_abertura_origem(resultado):
    st.session_state["registros"] = st.session_state.get("registros", []) + [copy.deepcopy(resultado)]
def carregar_projetos():
    return copy.deepcopy(st.session_state.get("projetos", []))
def salvar_projetos(projetos):
    st.session_state["projetos"] = copy.deepcopy(projetos)
def registrar_evento_projeto(projeto, texto):
    projeto.setdefault("timeline", []).append(texto)
def _i811_preco_catalogo_float(produto):
    return float(produto.get("Preco", 0))
'''

HELPERS = funcoes_reais(
    "_hf53_rerun_item", "_hf53_iniciar_edicao_item", "_hf53_renderizar_edicao_item",
    "_hf53_solicitar_abertura", "_hf53_processar_abertura_pendente",
)


def clicar(app, rotulo):
    return next(b for b in app.button if b.label == rotulo).click().run()


@unittest.skipIf(AppTest is None, "Requer Streamlit no runtime de QA")
class ManagerUISmokeTest(unittest.TestCase):
    def sem_excecao(self, app):
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def editor(self, anna=False):
        corpo = '''
if "iniciado" not in st.session_state:
    st.session_state["iniciado"] = True
    item = {"produto":"Caneca", "quantidade":2, "valor_unitario":18.5,
            "especificacoes":"Tema: Espaço | Nome: Lia | Cor: azul",
            "produto_catalogo_id":"CAT-01", "preco_especial_aplicado":True,
            "valor_base_oficial":21.0, "abatimento_fixo_cliente":2.5,
            "perfil_comercial_cliente_id":"CLI-01", "projeto_id":"PRJ-01"}
    st.session_state["temp_itens"] = [copy.deepcopy(item)]
    st.session_state["anna_modal_itens"] = [copy.deepcopy(item)]
    st.session_state["form_cliente"] = "Cliente original"
    st.session_state["form_whatsapp"] = "000"
def formulario():
    anna = ANNA
    itens_key = "anna_modal_itens" if anna else "temp_itens"
    chave = "_hf53_edicao_anna" if anna else "_hf53_edicao_jorge"
    if st.session_state.get(chave):
        _hf53_renderizar_edicao_item(itens_key, anna=anna)
    elif st.button("Editar item real"):
        _hf53_iniciar_edicao_item(itens_key, 0, anna=anna)
    st.write(st.session_state[itens_key])
'''.replace("ANNA", repr(anna))
        if anna:
            # AppTest reproduz eventos como reruns completos, sem fragment_id de
            # navegador. Mantemos os widgets reais e registramos o escopo pedido.
            corpo += '''
_st_real = st
class _StreamlitHarness:
    def __getattr__(self, nome):
        return getattr(_st_real, nome)
    def rerun(self, *, scope="app"):
        _st_real.session_state["escopo_solicitado"] = scope
        _st_real.rerun()
st = _StreamlitHarness()
'''
        corpo += "\nformulario()\n"
        app = AppTest.from_string(BASE + HELPERS + corpo).run()
        return app

    def test_jorge_edita_personalizacao_preservando_preco_e_sem_duplicar(self):
        app = self.editor()
        clicar(app, "Editar item real")
        self.sem_excecao(app)
        app.text_area[0].set_value("Tema: Espaço | Nome: Ana | Cor: prata")
        clicar(app, "💾 Aplicar alteração do item")
        self.sem_excecao(app)
        itens = app.session_state["temp_itens"]
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["especificacoes"], "Tema: Espaço | Nome: Ana | Cor: prata")
        self.assertEqual(itens[0]["valor_unitario"], 18.5)
        self.assertEqual(itens[0]["perfil_comercial_cliente_id"], "CLI-01")
        self.assertTrue(itens[0]["preco_especial_aplicado"])
        self.assertEqual(app.session_state["form_cliente"], "Cliente original")

    def test_anna_cancelamento_no_editor_preserva_item_e_solicita_rerun_fragmento(self):
        app = self.editor(anna=True)
        antes = dict(app.session_state["anna_modal_itens"][0])
        clicar(app, "Editar item real")
        self.sem_excecao(app)
        app.text_area[0].set_value("Alteração a descartar")
        clicar(app, "Cancelar edição do item")
        self.sem_excecao(app)
        self.assertEqual(app.session_state["anna_modal_itens"], [antes])
        self.assertEqual(app.session_state["temp_itens"], [antes])
        self.assertEqual(app.session_state["escopo_solicitado"], "fragment")

    def handoff(self, *, existente=True, projeto=False):
        corpo = '''
if "iniciado" not in st.session_state:
    st.session_state["iniciado"] = True
    st.session_state["destino"] = "origem"
    st.session_state["temp_itens"] = [{"produto":"Anterior", "quantidade":2, "valor_unitario":3}] if EXISTENTE else []
    st.session_state["form_cliente"] = "Anterior" if EXISTENTE else ""
    st.session_state["form_documento"] = "DOC" if EXISTENTE else ""
    st.session_state["form_entrega"] = hoje_local()
    st.session_state["form_key"] = 0
_hf53_processar_abertura_pendente()
if st.session_state["destino"] == "origem":
    if st.button("Atalho real"):
        _hf53_solicitar_abertura(DESTINO, {"cliente":"Novo cliente", "whatsapp":"000", "atendimento_id":"AT-01",
                                             "necessidade":"Bubble azul", "itens":[{"produto":"Novo", "quantidade":1, "valor_unitario":7}]})
elif st.session_state["destino"] == "projeto":
    renderizar_assistente_projeto_personalizado()
else:
    st.text_input("Cliente recebido", key="form_cliente")
    st.text_input("WhatsApp recebido", key="form_whatsapp")
    st.write(st.session_state["temp_itens"])
'''.replace("EXISTENTE", repr(existente)).replace("DESTINO", repr("projeto" if projeto else "novo_orcamento"))
        return AppTest.from_string(BASE + HELPERS + funcoes_reais("renderizar_assistente_projeto_personalizado") + corpo).run()

    def test_atalho_confirma_rascunho_abre_destino_e_nao_repete_em_rerun(self):
        app = self.handoff()
        clicar(app, "Atalho real")
        self.sem_excecao(app)
        self.assertEqual(app.session_state["form_cliente"], "Anterior")
        self.assertEqual(len(app.warning), 1)
        self.assertNotIn("registros", app.session_state)
        clicar(app, "Substituir pelos novos dados")
        self.sem_excecao(app)
        self.assertEqual(app.text_input[0].value, "Novo cliente")
        self.assertEqual(app.session_state["form_documento"], "")
        self.assertEqual(app.session_state["temp_itens"], [{"produto":"Novo", "quantidade":1, "valor_unitario":7}])
        self.assertEqual(len(app.session_state["registros"]), 1)
        app.run()
        self.sem_excecao(app)
        self.assertEqual(len(app.session_state["registros"]), 1)
        self.assertEqual(len(app.session_state["temp_itens"]), 1)

    def test_atalho_cancelar_ou_continuar_preserva_rascunho(self):
        app = self.handoff()
        clicar(app, "Atalho real")
        clicar(app, "Cancelar abertura")
        self.sem_excecao(app)
        self.assertEqual(app.session_state["destino"], "origem")
        clicar(app, "Atalho real")
        clicar(app, "Continuar rascunho atual")
        self.sem_excecao(app)
        self.assertEqual(app.text_input[0].value, "Anterior")
        self.assertEqual(app.session_state["temp_itens"][0]["produto"], "Anterior")
        self.assertNotIn("registros", app.session_state)

    def test_atalho_sem_rascunho_abre_orcamento_diretamente(self):
        app = self.handoff(existente=False)
        clicar(app, "Atalho real")
        self.sem_excecao(app)
        self.assertEqual(app.session_state["destino"], "novo_orcamento")
        self.assertEqual(app.text_input[0].value, "Novo cliente")
        self.assertEqual(len(app.warning), 0)

    def test_projeto_abre_briefing_e_prepara_orcamento_uma_vez(self):
        app = self.handoff(existente=False, projeto=True)
        clicar(app, "Atalho real")
        self.sem_excecao(app)
        self.assertEqual(app.session_state["hf53_projeto_cliente"], "Novo cliente")
        self.assertEqual(app.session_state["hf53_projeto_necessidade"], "Bubble azul")
        clicar(app, "➡️ Salvar e preparar orçamento")
        self.sem_excecao(app)
        self.assertEqual(app.session_state["destino"], "novo_orcamento")
        self.assertEqual(app.text_input[0].value, "Novo cliente")
        self.assertEqual(len(app.session_state["temp_itens"]), 1)
        self.assertEqual(len(app.session_state["projetos"]), 1)
        self.assertIn("Bubble azul", app.session_state["temp_itens"][0]["especificacoes"])
        self.assertEqual(app.session_state["_atendimento_origem_id"], "AT-01")
        app.run()
        self.assertEqual(len(app.session_state["projetos"]), 1)
        self.assertEqual(len(app.session_state["temp_itens"]), 1)


if __name__ == "__main__":
    unittest.main()
