"""Conferência final com Streamlit real e serviço puro; sem app.py, banco ou rede."""
from __future__ import annotations

import copy
from datetime import date
import logging
import math
import unittest

logging.disable(logging.CRITICAL)
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


PROPOSTA = {
    "cliente_nome": "Alice de Teste",
    "whatsapp": "11999990000",
    "documento": "12345678901",
    "evento": "Aniversário",
    "itens": [{
        "produto": "Caneca",
        "produto_catalogo_id": "CAT-01",
        "quantidade": 2,
        "valor_unitario": 20.0,
        "especificacoes": "Nome Ana | Tema Espaço",
        "metadata": {"arquivo": "arte-ana.pdf", "cores": ["azul", "prata"]},
    }],
    "subtotal": 40.0,
    "desconto": 0.0,
    "taxa_entrega": 0.0,
    "valor_total": 40.0,
    "frete_tipo": "Retirada",
    "data_entrega": "30/11/2026",
    "prazo_dias": "10",
    "validade_dias": "5",
    "observacoes": "Personalização confirmada pelo cliente",
    "briefing_origem": "Mensagem recebida do site:\n2 canecas, tema Espaço.",
    "_contexto_formulario": {"perfil": "jorge", "sequencia": 1},
}


BASE = '''
from contextlib import nullcontext
from copy import deepcopy
from datetime import date
from unittest.mock import patch
import streamlit as st
from proposal_review_ui_hf56 import (
    renderizar_revisao, validar_salvamento, limpar_revisao,
)
if "proposta" not in st.session_state:
    st.session_state["proposta"] = __PROPOSTA__
    st.session_state["proposta_anna"] = deepcopy(st.session_state["proposta"])
    st.session_state["hoje"] = date(2026, 11, 25)
    st.session_state["em_edicao"] = False
    st.session_state["item_pendente"] = False
    st.session_state["erro_servico"] = False
    st.session_state["gravacoes"] = []
    st.session_state["ultimo_resultado"] = None
    st.session_state["exibir_anna"] = False
    st.session_state["mudanca_no_salvar"] = None
    st.session_state["origem_site"] = {"fonte": "rascunho-importado", "revisado": True}

contexto = (patch("proposal_review_ui_hf56.conferir_orcamento",
                  side_effect=RuntimeError("fixture: segredo-interno-nao-exibir"))
            if st.session_state["erro_servico"] else nullcontext())
with contexto:
    if st.checkbox("Mostrar conferência", value=True, key="fixture_mostrar"):
        st.session_state["resultado_renderizado"] = renderizar_revisao(
            st, st.session_state["proposta"], prefixo="jorge",
            hoje=st.session_state["hoje"], em_edicao=st.session_state["em_edicao"],
            item_pendente=st.session_state["item_pendente"],
        )
    if st.session_state["exibir_anna"]:
        renderizar_revisao(
            st, st.session_state["proposta_anna"], prefixo="anna",
            hoje=st.session_state["hoje"],
        )
    if st.button("Salvar orçamento", key="fixture_salvar"):
        # Reproduz mudança tardia entre renderização e guard, sem executar app.py.
        if st.session_state["mudanca_no_salvar"] is not None:
            st.session_state["proposta"].update(st.session_state["mudanca_no_salvar"])
            st.session_state["mudanca_no_salvar"] = None
        permitido = validar_salvamento(
            st, st.session_state["proposta"], prefixo="jorge",
            hoje=st.session_state["hoje"], em_edicao=st.session_state["em_edicao"],
            item_pendente=st.session_state["item_pendente"],
        )
        st.session_state["ultimo_resultado"] = permitido
        if permitido:
            st.session_state["gravacoes"].append(deepcopy(st.session_state["proposta"]))
            limpar_revisao(st.session_state, "jorge")
'''


@unittest.skipIf(AppTest is None, "Requer Streamlit para testar a interface real")
class ConferenciaFinalUITest(unittest.TestCase):
    def app(self, proposta=None):
        payload = PROPOSTA if proposta is None else proposta
        app = AppTest.from_string(BASE.replace("__PROPOSTA__", repr(payload)),
                                  default_timeout=20).run()
        self.sem_excecao(app)
        return app

    def sem_excecao(self, app):
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def com_aviso(self, **campos):
        proposta = copy.deepcopy(PROPOSTA)
        proposta["prazo_dias"] = ""
        proposta.update(campos)
        return proposta

    def chave(self, app, prefixo="jorge"):
        revisao = app.session_state[f"_{prefixo}_revisao_final"]
        return f"{prefixo}_revisao_final_{revisao['geracao']}_confirmar"

    def conferir(self, app, prefixo="jorge"):
        app.checkbox(key=self.chave(app, prefixo)).check().run()
        self.sem_excecao(app)
        self.assertTrue(app.session_state[f"_{prefixo}_revisao_final"]["confirmada"])
        return app

    def salvar(self, app):
        app.button(key="fixture_salvar").click().run()
        self.sem_excecao(app)
        # O chamador faz seu rerun após o guard. Separar os ciclos também deixa
        # o AppTest observar a nova geração sem reter nós da árvore anterior.
        app.run()
        self.sem_excecao(app)
        return app

    def avisos(self, app):
        return app.session_state["resultado_renderizado"]["avisos"]

    def test_sem_pendencias_salva_sem_checkbox_extra_e_nao_altera_rascunho(self):
        app = self.app()
        self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])
        self.assertEqual(len(app.error), 0)
        self.assertEqual(len(app.warning), 0)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual(app.expander[0].label, "Conferência final do orçamento")
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(app.session_state["gravacoes"], [PROPOSTA])
        self.assertEqual(app.session_state["proposta"], PROPOSTA)
        self.assertEqual(app.session_state["origem_site"], {"fonte": "rascunho-importado", "revisado": True})

    def test_brinde_com_valor_zero_exige_aceite_e_salva_sem_reescrever(self):
        proposta = copy.deepcopy(PROPOSTA)
        proposta["itens"][0]["valor_unitario"] = 0.0
        proposta.update(subtotal=0.0, valor_total=0.0)
        app = self.app(proposta)
        self.assertEqual(len(app.error), 0)
        self.assertIn("preco_zero", [a["codigo"] for a in self.avisos(app)])
        self.assertEqual(app.checkbox(key=self.chave(app)).label,
                         "Revisei os pontos de atenção e quero salvar este orçamento")
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.conferir(app)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(app.session_state["gravacoes"], [proposta])

    def test_bloqueios_ficam_fora_do_expander_e_nao_tem_aceite(self):
        proposta = self.com_aviso(cliente_nome="", data_entrega="31/02/2026")
        app = self.app(proposta)
        self.assertGreaterEqual(len(app.error), 2)
        self.assertEqual(len(app.expander[0].error), 0)
        self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual(app.session_state["proposta"], proposta)

    def test_erro_novo_nunca_e_liberado_por_aceite_antigo(self):
        app = self.conferir(self.app(self.com_aviso()))
        proposta = copy.deepcopy(app.session_state["proposta"])
        proposta["itens"][0]["quantidade"] = 0
        proposta.update(subtotal=0.0, valor_total=0.0)
        app.session_state["proposta"] = proposta
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])
        self.assertTrue(any("quantidade" in erro.value for erro in app.error))

    def test_desconto_maior_que_subtotal_recusa_sem_truncar_total(self):
        proposta = copy.deepcopy(PROPOSTA)
        proposta.update(desconto=50.0, valor_total=0.0)
        app = self.app(proposta)
        self.assertTrue(any("desconto é maior" in erro.value for erro in app.error))
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["proposta"], proposta)
        resumo = app.dataframe[1].value
        self.assertEqual(resumo.loc[resumo["Condição"] == "Total", "Valor"].iloc[0], "R$ -10,00")

    def test_numeros_invalidos_nao_derrubam_interface_nem_viram_subtotal_parcial(self):
        for valor in (float("nan"), float("inf"), -float("inf"), "preço indefinido"):
            with self.subTest(valor=valor):
                app = self.app()
                proposta = copy.deepcopy(PROPOSTA)
                proposta["itens"][0]["valor_unitario"] = valor
                proposta["itens"].append(copy.deepcopy(PROPOSTA["itens"][0]))
                app.session_state["proposta"] = proposta
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["gravacoes"], [])
                self.assertGreater(len(app.error), 0)
                self.assertIsNone(app.session_state["resultado_renderizado"]["resumo"]["subtotal"])
                self.assertEqual(app.dataframe[0].value.iloc[0]["Valor unitário"], "Revisar")
                self.assertEqual(app.dataframe[1].value.iloc[0]["Valor"], "Revisar")
                mantido = app.session_state["proposta"]["itens"][0]["valor_unitario"]
                if isinstance(valor, float) and math.isnan(valor):
                    self.assertTrue(math.isnan(mantido))
                else:
                    self.assertEqual(mantido, valor)

    def test_payload_invalido_e_lista_corrompida_bloqueiam_sem_excecao(self):
        for proposta in (None, "rascunho inválido", {**PROPOSTA, "itens": [None]}):
            with self.subTest(proposta=proposta):
                app = self.app()
                app.session_state["proposta"] = proposta
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["gravacoes"], [])
                self.assertGreater(len(app.error), 0)
                self.assertEqual(app.session_state["proposta"], proposta)

    def test_data_passada_exige_confirmacao_so_para_novo_orcamento(self):
        proposta = copy.deepcopy(PROPOSTA)
        proposta["data_entrega"] = "24/11/2026"
        novo = self.app(proposta)
        self.assertIn("entrega_passada", [a["codigo"] for a in self.avisos(novo)])
        self.salvar(novo)
        self.assertIs(novo.session_state["ultimo_resultado"], False)
        self.conferir(novo)
        self.salvar(novo)
        self.assertEqual(novo.session_state["gravacoes"], [proposta])
        historico = self.app(proposta)
        historico.session_state["em_edicao"] = True
        historico.run()
        self.sem_excecao(historico)
        self.assertNotIn("entrega_passada", [a["codigo"] for a in self.avisos(historico)])
        self.assertEqual([c.key for c in historico.checkbox], ["fixture_mostrar"])
        self.salvar(historico)
        self.assertEqual(historico.session_state["gravacoes"], [proposta])

    def test_whatsapp_vazio_informa_e_nao_exige_mais_clique(self):
        proposta = copy.deepcopy(PROPOSTA)
        proposta["whatsapp"] = ""
        app = self.app(proposta)
        self.assertTrue(any("WhatsApp não informado" in info.value for info in app.info))
        self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])
        self.assertEqual(len(app.warning), 0)
        self.salvar(app)
        self.assertEqual(app.session_state["gravacoes"], [proposta])

    def test_item_pendente_pede_confirmacao_sem_adicionar_item(self):
        app = self.app()
        app.session_state["item_pendente"] = True
        app.run()
        self.sem_excecao(app)
        self.assertIn("item_pendente", [a["codigo"] for a in self.avisos(app)])
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.conferir(app)
        self.salvar(app)
        self.assertEqual(app.session_state["gravacoes"], [PROPOSTA])

    def test_preco_quantidade_e_personalizacao_invalida_aceite(self):
        for campo, valor in (("valor_unitario", 18.5), ("quantidade", 3),
                             ("especificacoes", "Nome Bia | Tema Espaço"),
                             ("metadata", {"arquivo": "arte-bia.pdf", "cores": ["azul"]})):
            with self.subTest(campo=campo):
                app = self.conferir(self.app(self.com_aviso()))
                anterior = self.chave(app)
                proposta = copy.deepcopy(app.session_state["proposta"])
                proposta["itens"][0][campo] = valor
                item = proposta["itens"][0]
                proposta["subtotal"] = proposta["valor_total"] = item["quantidade"] * item["valor_unitario"]
                app.session_state["proposta"] = proposta
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["gravacoes"], [])
                self.assertNotEqual(self.chave(app), anterior)
                self.assertFalse(app.checkbox(key=self.chave(app)).value)
                self.assertEqual(app.session_state["proposta"], proposta)
                self.conferir(app)
                self.salvar(app)
                self.assertEqual(app.session_state["gravacoes"], [proposta])

    def test_condicoes_cliente_origem_e_contexto_invalida_aceite(self):
        mudancas = (
            {"cliente_nome": "Bia de Teste"}, {"evento": "Formatura"},
            {"desconto": 2.0, "valor_total": 38.0},
            {"frete_tipo": "Entrega", "taxa_entrega": 5.0, "valor_total": 45.0},
            {"data_entrega": "01/12/2026"}, {"validade_dias": "7"},
            {"observacoes": "Retirada combinada às 17h"},
            {"briefing_origem": "Mensagem manual alterada no site"},
            {"_contexto_formulario": {"perfil": "jorge", "sequencia": 2}},
        )
        for mudanca in mudancas:
            with self.subTest(campos=tuple(mudanca)):
                app = self.conferir(self.app(self.com_aviso()))
                anterior = self.chave(app)
                proposta = copy.deepcopy(app.session_state["proposta"])
                proposta.update(mudanca)
                app.session_state["proposta"] = proposta
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertNotEqual(self.chave(app), anterior)
                self.assertFalse(app.checkbox(key=self.chave(app)).value)
                self.assertEqual(app.session_state["proposta"], proposta)

    def test_contexto_da_conferencia_invalida_aceite(self):
        for campo, valor in (("hoje", date(2026, 11, 26)), ("em_edicao", True),
                             ("item_pendente", True)):
            with self.subTest(campo=campo):
                app = self.conferir(self.app(self.com_aviso()))
                anterior = self.chave(app)
                app.session_state[campo] = valor
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertNotEqual(self.chave(app), anterior)
                self.assertFalse(app.checkbox(key=self.chave(app)).value)

    def test_snapshot_de_item_pendente_e_numero_editado_invalida_aceite(self):
        for alterar_item in (True, False):
            with self.subTest(alterar_item=alterar_item):
                proposta = copy.deepcopy(PROPOSTA)
                proposta["_item_em_preenchimento"] = {
                    "perfil": "jorge", "geracao": 3,
                    "produto": "Copo", "quantidade": 1, "especificacoes": "Nome Ana",
                }
                proposta["_numero_em_edicao"] = "PROP-01"
                app = self.app(proposta)
                app.session_state["item_pendente"] = True
                app.run()
                self.conferir(app)
                anterior = self.chave(app)
                alterada = copy.deepcopy(app.session_state["proposta"])
                if alterar_item:
                    alterada["_item_em_preenchimento"]["especificacoes"] = "Nome Bia"
                else:
                    alterada["_numero_em_edicao"] = "PROP-02"
                app.session_state["proposta"] = alterada
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertNotEqual(self.chave(app), anterior)
                self.assertFalse(app.checkbox(key=self.chave(app)).value)
                self.assertEqual(app.session_state["proposta"], alterada)

    def test_reordenar_chaves_preserva_aceite_mas_desmarcar_recusa(self):
        app = self.conferir(self.app(self.com_aviso()))
        anterior = self.chave(app)
        proposta = dict(reversed(list(app.session_state["proposta"].items())))
        proposta["itens"] = [dict(reversed(list(proposta["itens"][0].items())))]
        app.session_state["proposta"] = proposta
        app.run()
        self.sem_excecao(app)
        self.assertEqual(self.chave(app), anterior)
        self.assertTrue(app.checkbox(key=anterior).value)
        app.checkbox(key=anterior).uncheck().run()
        self.sem_excecao(app)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertFalse(app.checkbox(key=self.chave(app)).value)

    def test_guard_recalcula_mudanca_depois_de_renderizar_sem_mudar_widget_criado(self):
        app = self.conferir(self.app(self.com_aviso()))
        anterior = self.chave(app)
        app.session_state["mudanca_no_salvar"] = {"observacoes": "Nova condição após renderizar"}
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertNotEqual(self.chave(app), anterior)
        self.assertFalse(app.checkbox(key=self.chave(app)).value)

    def test_ocultar_interface_preserva_aceite_se_dados_nao_mudam(self):
        app = self.conferir(self.app(self.com_aviso()))
        anterior = self.chave(app)
        app.checkbox(key="fixture_mostrar").uncheck().run()
        app.run()
        self.sem_excecao(app)
        self.assertTrue(app.session_state["_jorge_revisao_final"]["confirmada"])
        app.checkbox(key="fixture_mostrar").check().run()
        self.sem_excecao(app)
        self.assertEqual(self.chave(app), anterior)
        self.assertTrue(app.checkbox(key=anterior).value)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)

    def test_guard_com_interface_oculta_detecta_mudanca(self):
        app = self.conferir(self.app(self.com_aviso()))
        app.checkbox(key="fixture_mostrar").uncheck().run()
        app.session_state["proposta"]["evento"] = "Casamento"
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        app.checkbox(key="fixture_mostrar").check().run()
        self.sem_excecao(app)
        self.assertFalse(app.checkbox(key=self.chave(app)).value)

    def test_prefixos_jorge_anna_tem_aceites_e_limpeza_independentes(self):
        app = self.app(self.com_aviso())
        app.session_state["exibir_anna"] = True
        app.run()
        self.sem_excecao(app)
        self.conferir(app, "anna")
        chave_anna = self.chave(app, "anna")
        self.assertFalse(app.checkbox(key=self.chave(app, "jorge")).value)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.conferir(app, "jorge")
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(self.chave(app, "anna"), chave_anna)
        self.assertTrue(app.checkbox(key=chave_anna).value)
        self.assertFalse(app.checkbox(key=self.chave(app, "jorge")).value)

    def test_limpeza_apos_sucesso_exige_nova_confirmacao(self):
        app = self.conferir(self.app(self.com_aviso()))
        anterior = self.chave(app)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertNotEqual(self.chave(app), anterior)
        self.assertFalse(app.checkbox(key=self.chave(app)).value)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(len(app.session_state["gravacoes"]), 1)

    def test_resumo_mostra_valores_e_personalizacoes_sem_agrupar_linhas(self):
        proposta = copy.deepcopy(PROPOSTA)
        proposta["itens"].append({**copy.deepcopy(proposta["itens"][0]),
                                  "especificacoes": "Nome Bia | Tema Espaço",
                                  "quantidade": 1.5, "valor_unitario": 10.25})
        proposta.update(subtotal=55.375, desconto=5.375, frete_tipo="Entrega",
                        taxa_entrega=7.5, valor_total=57.5)
        app = self.app(proposta)
        self.assertEqual(len(app.metric), 0)
        self.assertEqual(len(app.expander[0].dataframe), 2)
        linhas = app.dataframe[0].value
        self.assertEqual(list(linhas["Personalização"]), ["Nome Ana | Tema Espaço", "Nome Bia | Tema Espaço"])
        self.assertEqual(list(linhas["Quantidade"]), ["2", "1,5"])
        self.assertEqual(list(linhas["Valor unitário"]), ["R$ 20,00", "R$ 10,25"])
        valores = app.dataframe[1].value
        self.assertEqual(valores.iloc[-1]["Valor"], "R$ 57,50")
        self.assertEqual(app.session_state["proposta"], proposta)
        self.salvar(app)
        self.assertEqual(app.session_state["gravacoes"], [proposta])

    def test_erro_inesperado_preserva_rascunho_e_recuperacao_exige_novo_aceite(self):
        proposta = self.com_aviso()
        app = self.conferir(self.app(proposta))
        app.session_state["erro_servico"] = True
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual(app.session_state["proposta"], proposta)
        self.assertTrue(any("rascunho foi preservado" in erro.value.lower() for erro in app.error))
        self.assertFalse(any("segredo-interno" in erro.value for erro in app.error))
        self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])
        app.session_state["erro_servico"] = False
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertFalse(app.checkbox(key=self.chave(app)).value)
        self.conferir(app)
        self.salvar(app)
        self.assertEqual(app.session_state["gravacoes"], [proposta])


if __name__ == "__main__":
    unittest.main()
