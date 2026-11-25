"""HF55: consultar o Histórico preserva os widgets reais do rascunho.

Executa os helpers extraídos do app.py com Streamlit AppTest. O banco e o
catálogo usam dados fictícios; a navegação, os seletores, a retenção de widgets
e a conferência são as implementações de produção.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import unittest

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


ROOT = Path(__file__).resolve().parent
HELPERS = {
    "localizar_cliente_comercial", "_orcamento_cliente_ref", "_orcamento_opcoes_cliente",
    "_orcamento_campos_cliente", "_orcamento_opcoes_produto_catalogo", "_orcamento_resolver_produto",
    "_orcamento_produto_digitado_unico", "_orcamento_campos_produto",
    "rerun_na_aba", "_hf55_consultar_proposta", "_hf55_carregar_historico_conferencia",
    "_hf55_rascunho_para_conferencia", "_hf55_renderizar_conferencia",
}


def app_source(*, anna, product_free):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    functions = {
        node.name: ast.get_source_segment(source, node)
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name in HELPERS
    }
    if set(functions) != HELPERS:
        raise AssertionError(f"Helpers do fluxo real não encontrados: {HELPERS - set(functions)}")
    setup = f'''
import sys
sys.path.insert(0, {str(ROOT)!r})
import copy
import json
from pathlib import Path
from datetime import date
from types import SimpleNamespace
import streamlit as st
import manager_workflow_hf53 as workflow
import proposal_duplicate_ui_hf55 as _duplicidades_hf55
from relacionamentos_service import (
    normalizar_texto_cliente, chave_cliente,
    localizar_cliente_comercial as _rel_localizar_cliente_comercial,
    localizar_cliente_orcamento as _rel_localizar_cliente_orcamento,
)
from catalogo_orcamento_service import (
    ORCAMENTO_PRODUTO_LIVRE, normalizar_identidade_produto,
    aliases_catalogo_atomicos as _aliases_catalogo_atomicos,
    opcoes_produto_orcamento as _catalogo_opcoes_orcamento,
    resolver_produto_orcamento as _catalogo_resolver_orcamento,
)
ORCAMENTO_CLIENTE_LIVRE = "✍️ Cliente novo / digitar manualmente"
ANNA = {anna!r}
PRODUCT_FREE = {product_free!r}
TODAY = date(2026, 11, 25)
FIELDS = 'anna_modal_' if ANNA else 'form_'
CUSTOMER = 'anna_orc_cliente_novo' if ANNA else 'jorge_orc_cliente'
PRODUCT = 'anna_modal_prod_7' if ANNA else 'produto_novo_7'
REVIEW = 'hf55_anna' if ANNA else 'hf55_jorge'
ITEMS = 'anna_modal_itens' if ANNA else 'temp_itens'
SEQUENCE = 'anna_modal_item_key' if ANNA else 'form_key'
NUMBER = 'anna_modal_numero_original' if ANNA else 'editar_numero'
PENDING = {{
    'tema': 'anna_modal_tema_7' if ANNA else 'tema_7',
    'nome': 'anna_modal_nome_item_7' if ANNA else 'nome_item_7',
    'cor': 'anna_modal_cor_7' if ANNA else 'cor_7',
    'idade': 'anna_modal_idade_7' if ANNA else 'idade_7',
    'obs': 'anna_modal_obs_7' if ANNA else 'obs_item_7',
    'qtd': 'anna_modal_qtd_7' if ANNA else 'qtd_7',
    'valor': 'anna_modal_valor_7' if ANNA else 'valor_7',
}}
ITEM = {{'produto': 'Caneca', 'produto_catalogo_id': 'CAT-1', 'quantidade': 2,
        'valor_unitario': 19.5, 'especificacoes': 'Nome: Ana'}}
HISTORY = [{{'numero_proposta': 'PROP-TESTE', 'data_geracao': '25/11/2026',
            'cliente_nome': 'Maria Silva', 'whatsapp': '11911112222', 'documento': '',
            'itens': [copy.deepcopy(ITEM)]}}]
_cloud_db = SimpleNamespace(online_configured=lambda: True,
                           load_document_confirmed=lambda key, default: copy.deepcopy(HISTORY))
def carregar_clientes():
    # Homônimo cadastrado: nunca deve substituir o telefone novo importado.
    return [{{'id': 'REL-1', 'nome': 'Maria Silva', 'documento': '', 'whatsapp': '11988887777'}}]
def carregar_catalogo():
    return [{{'Nome': 'Caneca', 'CatalogoId': 'CAT-1', 'Preco': 19.5, 'Ativo': True}}]
def _orcamento_resumo_cliente_selecionado(cliente): return ''
def usuario_pode_ver_aba(aba): return True
def indice_aba(aba): return 0
def hoje_local(): return TODAY
def valor_float(value): return float(value or 0)
'''
    main = '''
if not st.session_state.get('_hf55_navigation_seed'):
    seed = {
        FIELDS+'cliente': 'Maria Silva', FIELDS+'documento': '', FIELDS+'whatsapp': '11911112222',
        FIELDS+'evento': 'Festa da Ana', FIELDS+'observacoes': 'Mensagem recebida do site:\\nCaneca para Ana',
        FIELDS+'desconto': 2.5, FIELDS+'entrega': date(2026, 12, 4), FIELDS+'prazo': '12',
        FIELDS+'frete': 'Entrega', FIELDS+'taxa_entrega': 8.0, FIELDS+'validade': '7',
        CUSTOMER+'_seletor': ORCAMENTO_CLIENTE_LIVRE,
        PRODUCT+'_catalogo': ORCAMENTO_PRODUTO_LIVRE if PRODUCT_FREE else 'Caneca',
        PRODUCT+'_livre': 'Peça avulsa desenhada pelo cliente' if PRODUCT_FREE else 'Texto manual preservado',
        PENDING['tema']: 'Espaço', PENDING['nome']: 'Pedro', PENDING['cor']: 'Azul',
        PENDING['idade']: '7 anos', PENDING['obs']: 'Gravar no verso', PENDING['qtd']: 3, PENDING['valor']: 27.5,
        ITEMS: [copy.deepcopy(ITEM)], SEQUENCE: 7, NUMBER: '',
        '_hf54_cliente_importado_'+('anna' if ANNA else 'jorge'): True,
    }
    st.session_state.update(seed)
    st.session_state['_expected_draft'] = copy.deepcopy(seed)
    st.session_state['_hf55_navigation_seed'] = True
    st.session_state['_pagina_principal'] = 'novo_orcamento'

# Mesmo mecanismo que _hf53_processar_abertura_pendente executa em todo rerun.
for key in workflow.chaves_rascunho(st.session_state):
    st.session_state[key] = st.session_state[key]

def render_quote():
    _orcamento_campos_cliente(CUSTOMER, nome_key=FIELDS+'cliente',
                              documento_key=FIELDS+'documento', whatsapp_key=FIELDS+'whatsapp')
    nome = st.text_input('Nome', key=FIELDS+'cliente')
    doc = st.text_input('Documento', key=FIELDS+'documento')
    wa = st.text_input('WhatsApp', key=FIELDS+'whatsapp')
    evento = st.text_input('Evento', key=FIELDS+'evento')
    _orcamento_campos_produto(PRODUCT)
    for label in ('tema', 'nome', 'cor', 'idade', 'obs'):
        st.text_input('Item pendente: '+label, key=PENDING[label])
    st.number_input('Qtd pendente', min_value=1, key=PENDING['qtd'])
    st.number_input('Valor pendente', min_value=0.0, key=PENDING['valor'])
    desconto = st.number_input('Desconto', min_value=0.0, key=FIELDS+'desconto')
    entrega = st.date_input('Entrega', key=FIELDS+'entrega')
    prazo = st.text_input('Prazo', key=FIELDS+'prazo')
    frete = st.selectbox('Frete', ['Retirada', 'Entrega'], key=FIELDS+'frete')
    taxa = st.number_input('Taxa', min_value=0.0, key=FIELDS+'taxa_entrega')
    validade = st.text_input('Validade', key=FIELDS+'validade')
    proposta = _hf55_rascunho_para_conferencia(
        nome=nome, documento=doc, whatsapp=wa, evento=evento, itens=st.session_state[ITEMS],
        entrega=entrega, desconto=desconto, prazo=prazo, frete=frete, taxa_entrega=taxa,
        validade=validade, subtotal=39.0, total=44.5, anna=ANNA,
    )
    _hf55_renderizar_conferencia(proposta, anna=ANNA)

@st.dialog('Rascunho Anna')
def render_anna():
    render_quote()

if st.session_state['_pagina_principal'] == 'novo_orcamento':
    if ANNA:
        render_anna()
    else:
        render_quote()
else:
    st.write('Consulta somente leitura da proposta selecionada')
    if st.button('Voltar ao rascunho', key='hf55_navigation_back'):
        rerun_na_aba('novo_orcamento')
'''
    return setup + "\n\n" + "\n\n".join(functions.values()) + "\n\n" + main


@unittest.skipIf(AppTest is None, "Requer Streamlit para testar navegação e retenção de widgets")
class ProposalDuplicateNavigationHF55Tests(unittest.TestCase):
    def roundtrip(self, *, anna, product_free):
        app = AppTest.from_string(app_source(anna=anna, product_free=product_free), default_timeout=10).run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        expected = deepcopy(app.session_state['_expected_draft'])
        prefix = 'hf55_anna' if anna else 'hf55_jorge'
        fields = 'anna_modal_' if anna else 'form_'
        customer = 'anna_orc_cliente_novo' if anna else 'jorge_orc_cliente'
        product = 'anna_modal_prod_7' if anna else 'produto_novo_7'

        app.button(key=prefix+'_consultar_duplicidades').click().run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        review = app.session_state['_'+prefix+'_conferencia_duplicidades']
        self.assertEqual(len(review['resultado']['candidatos']), 1)
        app.button(key=f"{prefix}_duplicidades_{review['geracao']}_abrir").click().run()
        # AppTest 1.51 pode reter nós da tela anterior após st.rerun no mesmo
        # lote. Redesenha sem serializar esses widgets já removidos; nenhum
        # valor de sessão é restaurado pelo teste.
        app._run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertEqual(app.session_state['_pagina_principal'], 'historico')
        self.assertEqual(app.session_state['alerta_proposta_numero'], 'PROP-TESTE')
        self.assertIn(customer+'_seletor', app.session_state)
        for key, value in expected.items():
            self.assertEqual(app.session_state[key], value, f'Estado perdido durante a consulta: {key}')

        app.button(key='hf55_navigation_back').click().run()
        app._run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        for key, value in expected.items():
            self.assertEqual(app.session_state[key], value, f'Estado alterado ao voltar: {key}')
        self.assertEqual(app.text_input(key=fields+'whatsapp').value, '11911112222')
        self.assertEqual(app.selectbox(key=customer+'_seletor').value, expected[customer+'_seletor'])
        self.assertEqual(app.selectbox(key=product+'_catalogo').value, expected[product+'_catalogo'])
        self.assertEqual(app.text_input(key=product+'_livre').value, expected[product+'_livre'])
        self.assertEqual(len(app.session_state['anna_modal_itens' if anna else 'temp_itens']), 1)

    def test_jorge_consulta_preserva_cliente_importado_e_produto_selecionado(self):
        self.roundtrip(anna=False, product_free=False)

    def test_anna_consulta_preserva_cliente_importado_e_produto_selecionado(self):
        self.roundtrip(anna=True, product_free=False)

    def test_jorge_consulta_preserva_produto_livre_e_demais_campos_pendentes(self):
        self.roundtrip(anna=False, product_free=True)

    def test_anna_consulta_preserva_produto_livre_e_demais_campos_pendentes(self):
        self.roundtrip(anna=True, product_free=True)


if __name__ == '__main__':
    unittest.main()
