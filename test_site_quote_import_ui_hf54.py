"""Fluxos reais de revisão por Streamlit AppTest, sem app.py, banco ou rede."""
from __future__ import annotations

import copy
import logging
import unittest

logging.disable(logging.CRITICAL)
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


CATALOGO = [
    {"Nome": "Caneca", "CatalogoId": "CAT-01", "Preco": 18.5, "Ativo": True},
    {"Nome": "Topo de bolo", "CatalogoId": "CAT-02", "Preco": 25, "Ativo": True},
]

BASE = '''
from copy import deepcopy
import streamlit as st
from site_quote_import_ui import renderizar_importacao
if "catalogo" not in st.session_state:
    st.session_state["catalogo"] = CATALOGO
    st.session_state["aberturas"] = []
    st.session_state["modo"] = "ok"
    st.session_state["offline"] = False
    st.session_state["temp_itens"] = [{"produto":"Rascunho existente", "quantidade":9, "valor_unitario":42}]
def carregar():
    if st.session_state["offline"]:
        raise RuntimeError("fixture offline")
    return deepcopy(st.session_state["catalogo"])
def abrir(dados):
    if st.session_state["modo"] == "erro":
        raise ValueError("fixture recusa")
    if st.session_state["modo"] == "recusado":
        return False
    st.session_state["aberturas"].append(deepcopy(dados))
    return True
if st.button("Alterar catálogo", key="fixture_catalogo"):
    st.session_state["catalogo"][0]["Preco"] = 21.0
if st.button("Alternar conexão", key="fixture_conexao"):
    st.session_state["offline"] = not st.session_state["offline"]
renderizar_importacao(st, carregar, abrir, prefixo="teste")
'''


def mensagem(nome="Caneca", quantidade="2", nota="Nome: Ana\nTema: Espaço"):
    return ("Olá! Gostaria de solicitar um orçamento na AlphaFest para os seguintes produtos:\n\n"
            f"1. {nome}\nQuantidade: {quantidade}\nPersonalização/observações: {nota}\n\n"
            "Podem confirmar valores, disponibilidade, prazo e opções de retirada/entrega? Obrigado!")


@unittest.skipIf(AppTest is None, "Requer Streamlit para testar a interface real")
class ImportacaoSiteUITest(unittest.TestCase):
    def app(self, extra=""):
        script = BASE.replace("CATALOGO", repr(CATALOGO)) + extra
        app = AppTest.from_string(script, default_timeout=20).run()
        self.sem_excecao(app)
        return app

    def sem_excecao(self, app):
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def botao(self, app, label):
        return next(b for b in app.button if b.label == label)

    def clicar(self, app, label):
        resultado = self.botao(app, label).click().run()
        self.sem_excecao(resultado)
        return resultado

    def analisar(self, app, texto, prefixo="teste"):
        app.text_area(key=f"{prefixo}_mensagem").input(texto).run()
        app.button(key=f"{prefixo}_analisar").click().run()
        self.sem_excecao(app)
        return app

    def widgets(self, app, prefixo="teste"):
        return f"{prefixo}_{app.session_state[f'_{prefixo}_revisao']['geracao']}"

    def conferir(self, app):
        app.checkbox(key=self.widgets(app) + "_conferido").check().run()
        self.sem_excecao(app)

    def test_abre_revisado_com_cliente_e_origem_sem_salvar_nem_reaplicar(self):
        app = self.analisar(self.app(), mensagem())
        w = self.widgets(app)
        app.number_input(key=w + "_qtd_0").set_value(3.0).run()
        app.number_input(key=w + "_preco_0").set_value(17.5).run()
        app.text_area(key=w + "_detalhes_0").input("Nome: Bia\nCor: azul\nDetalhe completo").run()
        app.text_input(key=w + "_cliente").input("Cliente confirmado").run()
        app.text_input(key=w + "_whatsapp").input("11999990000").run()
        app.text_input(key=w + "_evento").input("Aniversário").run()
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        chamadas = app.session_state["aberturas"]
        self.assertEqual(len(chamadas), 1)
        dados = chamadas[0]
        self.assertEqual(dados["cliente"], "Cliente confirmado")
        self.assertEqual(dados["whatsapp"], "11999990000")
        self.assertEqual(dados["evento"], "Aniversário")
        self.assertEqual(dados["itens"][0]["quantidade"], 3)
        self.assertEqual(dados["itens"][0]["valor_unitario"], 17.5)
        self.assertEqual(dados["itens"][0]["especificacoes"], "Nome: Bia\nCor: azul\nDetalhe completo")
        self.assertEqual(dados["itens"][0]["produto_catalogo_id"], "CAT-01")
        self.assertIn(mensagem(), dados["observacoes"])
        app.run()
        self.assertEqual(len(app.session_state["aberturas"]), 1)
        self.assertEqual(app.session_state["temp_itens"][0]["produto"], "Rascunho existente")

    def test_texto_alterado_exige_nova_analise_e_reseta_preco_e_conferencia(self):
        app = self.analisar(self.app(), mensagem())
        w = self.widgets(app)
        app.number_input(key=w + "_preco_0").set_value(13.0).run()
        self.conferir(app)
        app.text_area(key="teste_mensagem").input(mensagem("Topo de bolo")).run()
        self.assertTrue(any("mensagem mudou" in e.value for e in app.warning))
        self.assertFalse(any(b.label == "Abrir rascunho no orçamento" for b in app.button))
        self.clicar(app, "Analisar mensagem")
        novo = self.widgets(app)
        self.assertNotEqual(novo, w)
        self.assertEqual(app.number_input(key=novo + "_preco_0").value, 25.0)
        self.assertFalse(app.checkbox(key=novo + "_conferido").value)
        self.assertEqual(app.session_state["aberturas"], [])

    def test_mudar_catalogo_entre_analise_e_abertura_bloqueia(self):
        app = self.analisar(self.app(), mensagem())
        self.clicar(app, "Alterar catálogo")
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        self.assertEqual(app.session_state["aberturas"], [])
        self.assertTrue(any("Catálogo mudou" in e.value for e in app.warning))
        app.run()
        self.assertTrue(self.botao(app, "Abrir rascunho no orçamento").disabled)
        self.clicar(app, "Analisar mensagem")
        w = self.widgets(app)
        self.assertEqual(app.number_input(key=w + "_preco_0").value, 21.0)
        self.assertFalse(app.checkbox(key=w + "_conferido").value)

    def test_reverter_texto_preserva_revisao_mas_exige_nova_conferencia(self):
        original = mensagem()
        app = self.analisar(self.app(), original)
        w = self.widgets(app)
        app.number_input(key=w + "_preco_0").set_value(12.25).run()
        app.text_area(key=w + "_detalhes_0").input("Detalhe revisado completo").run()
        self.conferir(app)
        app.text_area(key="teste_mensagem").input(original + "\nTexto temporário").run()
        app.text_area(key="teste_mensagem").input(original).run()
        self.sem_excecao(app)
        self.assertEqual(app.number_input(key=w + "_preco_0").value, 12.25)
        self.assertEqual(app.text_area(key=w + "_detalhes_0").value, "Detalhe revisado completo")
        self.assertFalse(app.checkbox(key=w + "_conferido").value)

    def test_analise_recusada_por_conexao_nao_apaga_revisao_anterior(self):
        app = self.analisar(self.app(), mensagem())
        w = self.widgets(app)
        app.number_input(key=w + "_preco_0").set_value(11.5).run()
        self.clicar(app, "Alternar conexão")
        self.clicar(app, "Analisar mensagem")
        self.assertTrue(any("revisão anterior foi preservada" in e.value for e in app.error))
        self.clicar(app, "Alternar conexão")
        self.assertEqual(app.number_input(key=w + "_preco_0").value, 11.5)
        self.assertEqual(app.session_state["aberturas"], [])

    def test_produto_livre_sem_preco_exige_escolha_explicita(self):
        app = self.analisar(self.app(), mensagem("Produto fora do catálogo"))
        w = self.widgets(app)
        self.assertEqual(app.number_input(key=w + "_preco_0").value, 0)
        self.conferir(app)
        self.assertTrue(self.botao(app, "Abrir rascunho no orçamento").disabled)
        app.checkbox(key=w + "_sem_preco").check().run()
        self.assertFalse(app.checkbox(key=w + "_conferido").value)
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        item = app.session_state["aberturas"][0]["itens"][0]
        self.assertEqual(item["produto"], "Produto fora do catálogo")
        self.assertEqual(item["valor_unitario"], 0)

    def test_quantidade_ilegivel_fica_vazia_e_exige_correcao(self):
        app = self.analisar(self.app(), mensagem(quantidade="duas caixas"))
        w = self.widgets(app)
        self.assertIsNone(app.number_input(key=w + "_qtd_0").value)
        self.conferir(app)
        self.assertTrue(self.botao(app, "Abrir rascunho no orçamento").disabled)
        app.number_input(key=w + "_qtd_0").set_value(4.0).run()
        self.assertFalse(app.checkbox(key=w + "_conferido").value)
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        self.assertEqual(app.session_state["aberturas"][0]["itens"][0]["quantidade"], 4)

    def test_falha_ou_recusa_callback_preserva_revisao(self):
        for modo in ("erro", "recusado"):
            with self.subTest(modo=modo):
                app = self.analisar(self.app(), mensagem())
                w = self.widgets(app)
                app.number_input(key=w + "_preco_0").set_value(14.0).run()
                app.session_state["modo"] = modo
                self.conferir(app)
                self.clicar(app, "Abrir rascunho no orçamento")
                self.assertEqual(app.session_state["aberturas"], [])
                self.assertFalse(app.session_state["_teste_revisao"]["encaminhada"])
                self.assertEqual(app.number_input(key=w + "_preco_0").value, 14.0)

    def test_retoma_tentativa_encaminhada_preservando_edicoes_sem_reenvio(self):
        app = self.analisar(self.app(), mensagem())
        w = self.widgets(app)
        app.number_input(key=w + "_preco_0").set_value(14.75).run()
        app.text_area(key=w + "_detalhes_0").input("Ajuste revisado").run()
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        self.clicar(app, "Revisar importação novamente")
        novo = self.widgets(app)
        self.assertEqual(app.number_input(key=novo + "_preco_0").value, 14.75)
        self.assertEqual(app.text_area(key=novo + "_detalhes_0").value, "Ajuste revisado")
        self.assertFalse(app.checkbox(key=novo + "_conferido").value)
        self.assertEqual(len(app.session_state["aberturas"]), 1)

    def test_sair_e_voltar_preserva_texto_e_revisao_encaminhada(self):
        script = BASE.replace("CATALOGO", repr(CATALOGO)).replace(
            'renderizar_importacao(st, carregar, abrir, prefixo="teste")',
            'if st.checkbox("Mostrar importador", value=True, key="fixture_mostrar"):\n    renderizar_importacao(st, carregar, abrir, prefixo="teste")',
        )
        app = AppTest.from_string(script, default_timeout=20).run()
        self.analisar(app, mensagem())
        w = self.widgets(app)
        app.number_input(key=w + "_preco_0").set_value(12.75).run()
        app.text_input(key=w + "_cliente").input("Cliente do rascunho importado").run()
        app.text_input(key=w + "_whatsapp").input("11987650000").run()
        app.text_input(key=w + "_evento").input("Festa de teste").run()
        app.text_area(key=w + "_detalhes_0").input("Personalização revisada antes de sair").run()
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        app.checkbox(key="fixture_mostrar").uncheck().run()
        app.run()
        self.assertNotIn("teste_mensagem", app.session_state)
        app.checkbox(key="fixture_mostrar").check().run()
        self.sem_excecao(app)
        self.assertEqual(app.text_area(key="teste_mensagem").value, mensagem())
        self.clicar(app, "Revisar importação novamente")
        novo = self.widgets(app)
        self.assertEqual(app.number_input(key=novo + "_preco_0").value, 12.75)
        self.assertEqual(app.text_input(key=novo + "_cliente").value, "Cliente do rascunho importado")
        self.assertEqual(app.text_input(key=novo + "_whatsapp").value, "11987650000")
        self.assertEqual(app.text_input(key=novo + "_evento").value, "Festa de teste")
        self.assertEqual(app.text_area(key=novo + "_detalhes_0").value, "Personalização revisada antes de sair")
        self.assertEqual(len(app.session_state["aberturas"]), 1)

    def test_fechar_revisao_preserva_mensagem_e_rascunho_do_manager(self):
        app = self.analisar(self.app(), mensagem())
        existente = copy.deepcopy(app.session_state["temp_itens"])
        self.clicar(app, "Fechar revisão")
        self.assertEqual(app.text_area(key="teste_mensagem").value, mensagem())
        self.assertEqual(app.session_state["temp_itens"], existente)
        self.assertNotIn("_teste_revisao", app.session_state)
        self.assertEqual(app.session_state["aberturas"], [])

    def test_conexao_falha_na_abertura_preserva_precos_e_permite_tentar(self):
        app = self.analisar(self.app(), mensagem())
        w = self.widgets(app)
        app.number_input(key=w + "_preco_0").set_value(16.0).run()
        self.clicar(app, "Alternar conexão")
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        self.assertEqual(app.session_state["aberturas"], [])
        self.assertTrue(any("Catálogo online" in e.value for e in app.error))
        self.assertEqual(app.number_input(key=w + "_preco_0").value, 16.0)
        self.clicar(app, "Alternar conexão")
        self.clicar(app, "Abrir rascunho no orçamento")
        self.assertEqual(len(app.session_state["aberturas"]), 1)

    def test_revisoes_com_prefixos_distintos_nao_misturam_itens(self):
        app = self.app('\nrenderizar_importacao(st, carregar, abrir, prefixo="outro")\n')
        self.analisar(app, mensagem(), "teste")
        self.analisar(app, mensagem("Topo de bolo", "7", "Outro trabalho"), "outro")
        a, b = self.widgets(app, "teste"), self.widgets(app, "outro")
        self.assertEqual(app.number_input(key=a + "_qtd_0").value, 2)
        self.assertEqual(app.number_input(key=b + "_qtd_0").value, 7)
        app.number_input(key=a + "_preco_0").set_value(12.0).run()
        self.assertEqual(app.number_input(key=b + "_preco_0").value, 25)

    def test_mensagem_longa_preserva_25_linhas_e_personalizacoes(self):
        nota = "Linha inicial\nDetalhes completos: " + "x" * 450
        texto = "Olá! Gostaria de solicitar um orçamento na AlphaFest para os seguintes produtos:\n\n" + "\n\n".join(
            f"{i}. Caneca\nQuantidade: {i}\nPersonalização/observações: {nota} {i}" for i in range(1, 26)
        ) + "\n\nPodem confirmar valores, disponibilidade, prazo e opções de retirada/entrega? Obrigado!"
        app = self.analisar(self.app(), texto)
        self.assertGreater(len(texto), 6000)
        w = self.widgets(app)
        self.assertEqual(app.text_area(key=w + "_detalhes_24").value, nota + " 25")
        self.conferir(app)
        self.clicar(app, "Abrir rascunho no orçamento")
        dados = app.session_state["aberturas"][0]
        self.assertEqual(len(dados["itens"]), 25)
        self.assertEqual(dados["itens"][24]["especificacoes"], nota + " 25")
        self.assertIn(texto, dados["observacoes"])


if __name__ == "__main__":
    unittest.main()
