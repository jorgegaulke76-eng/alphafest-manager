"""Conferência real por AppTest + serviço puro, sem Manager, banco ou rede."""
from __future__ import annotations

import copy
import logging
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
    }],
    "observacoes": "Personalização confirmada pelo cliente",
}


def registro(numero="PROP-TEST-01", **campos):
    resultado = copy.deepcopy(PROPOSTA)
    resultado.update({
        "numero_proposta": numero,
        "data_geracao": "25/11/2026",
        "aprovado": False,
        "pago": False,
        "pronto": False,
        "entregue": False,
    })
    resultado.update(campos)
    return resultado


def proposta_comercial():
    proposta = copy.deepcopy(PROPOSTA)
    proposta.update(subtotal=40.0, desconto=0.0, valor_total=40.0,
                    taxa_entrega=0.0, frete_tipo="Retirada", data_entrega="30/11/2026",
                    prazo_dias="10", validade_dias="5")
    return proposta


def dados_inassinaveis():
    return (
        ("metadata_nan", {"metadata": {"valor": float("nan"), "detalhe": "segredo-nao-exibir"}}),
        ("metadata_bytes", {"metadata": {"arquivo": b"segredo-nao-exibir"}}),
        ("prazo_nan", {"prazo_dias": float("nan")}),
    )


BASE = '''
from copy import deepcopy
from datetime import date
import streamlit as st
from proposal_duplicate_ui_hf55 import (
    renderizar_conferencia, validar_salvamento, limpar_conferencia,
)
if "proposta" not in st.session_state:
    st.session_state["proposta"] = __PROPOSTA__
    st.session_state["historico"] = __HISTORICO__
    st.session_state["hoje"] = date(2026, 11, 25)
    st.session_state["leituras"] = 0
    st.session_state["offline"] = False
    st.session_state["gravacoes"] = []
    st.session_state["navegacoes"] = []
    st.session_state["ultimo_resultado"] = None
    st.session_state["mudanca_no_salvar"] = None
    st.session_state["origem_site"] = {"fonte": "rascunho-importado", "revisado": True}

def carregar():
    st.session_state["leituras"] += 1
    if st.session_state["offline"]:
        raise RuntimeError("fixture: segredo-do-banco-nao-exibir")
    return deepcopy(st.session_state["historico"])

def abrir(numero):
    st.session_state["navegacoes"].append(numero)

if st.checkbox("Mostrar conferência", value=True, key="fixture_mostrar"):
    renderizar_conferencia(
        st, st.session_state["proposta"], prefixo="teste",
        carregar_historico=carregar, hoje=st.session_state["hoje"],
        abrir_proposta=abrir,
    )

if st.button("Salvar proposta", key="fixture_salvar"):
    if st.session_state["mudanca_no_salvar"] is not None:
        st.session_state["proposta"].update(st.session_state["mudanca_no_salvar"])
        st.session_state["mudanca_no_salvar"] = None
    permitido = validar_salvamento(
        st, st.session_state["proposta"], prefixo="teste",
        carregar_historico=carregar, hoje=st.session_state["hoje"],
    )
    st.session_state["ultimo_resultado"] = permitido
    if permitido:
        st.session_state["gravacoes"].append(deepcopy(st.session_state["proposta"]))
        limpar_conferencia(st.session_state, "teste")
'''


@unittest.skipIf(AppTest is None, "Requer Streamlit para testar a interface real")
class ConferenciaDuplicidadesUITest(unittest.TestCase):
    def app(self, historico=None, extra=""):
        script = (BASE.replace("__PROPOSTA__", repr(PROPOSTA))
                  .replace("__HISTORICO__", repr([registro()] if historico is None else historico)))
        app = AppTest.from_string(script + extra, default_timeout=20).run()
        self.sem_excecao(app)
        return app

    def sem_excecao(self, app):
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def clicar(self, app, key):
        app.button(key=key).click().run()
        self.sem_excecao(app)
        return app

    def chave_conferencia(self, app, prefixo="teste"):
        revisao = app.session_state[f"_{prefixo}_conferencia_duplicidades"]
        return f"{prefixo}_duplicidades_{revisao['geracao']}_confirmar"

    def conferir(self, app, prefixo="teste"):
        app.checkbox(key=self.chave_conferencia(app, prefixo)).check().run()
        self.sem_excecao(app)
        return app

    def analisar(self, app, prefixo="teste"):
        return self.clicar(app, f"{prefixo}_consultar_duplicidades")

    def salvar(self, app):
        self.clicar(app, "fixture_salvar")
        # O Manager faz seu rerun após o guard. Separar os ciclos evita que
        # AppTest 1.51 retenha nós antigos quando um bloco fica mais curto no
        # mesmo conjunto de mensagens de st.rerun(). O guard ainda executa
        # depois dos widgets reais, no ciclo que recebeu o clique de salvar.
        app.run()
        self.sem_excecao(app)
        return app

    def test_renderizar_nao_consulta_e_checkbox_nao_reconsulta(self):
        app = self.app()
        self.assertEqual(app.session_state["leituras"], 0)
        app.run()
        self.assertEqual(app.session_state["leituras"], 0)
        self.analisar(app)
        self.assertEqual(app.session_state["leituras"], 1)
        self.assertEqual(len(app.session_state["gravacoes"]), 0)
        self.conferir(app)
        self.assertEqual(app.session_state["leituras"], 1)
        self.assertTrue(app.session_state["_teste_conferencia_duplicidades"]["confirmada"])

    def test_primeiro_salvar_com_indicio_recusa_e_conferencia_libera_uma_nova(self):
        app = self.app()
        original = copy.deepcopy(app.session_state["proposta"])
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)
        self.assertTrue(any("semelhante" in e.value for e in app.warning))
        self.assertEqual(app.session_state["proposta"], original)
        self.conferir(app)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(app.session_state["gravacoes"], [original])
        self.assertEqual(app.session_state["leituras"], 2)
        self.assertEqual(app.session_state["origem_site"], {"fonte": "rascunho-importado", "revisado": True})

    def test_sem_candidatos_salva_depois_de_leitura_fresca(self):
        app = self.app(historico=[])
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(app.session_state["leituras"], 1)
        self.assertEqual(app.session_state["gravacoes"], [PROPOSTA])

    def test_resultado_sem_candidatos_na_consulta_nao_dispensa_nova_leitura(self):
        app = self.app(historico=[])
        self.analisar(app)
        self.assertTrue(any("Nenhuma proposta semelhante" in e.value for e in app.success))
        app.session_state["historico"] = [registro()]
        self.salvar(app)
        self.assertEqual(app.session_state["leituras"], 2)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])

    def test_reconsulta_igual_preserva_aceite_e_desmarcar_recusa_salvamento(self):
        app = self.conferir(self.analisar(self.app()))
        chave = self.chave_conferencia(app)
        self.analisar(app)
        self.assertEqual(self.chave_conferencia(app), chave)
        self.assertTrue(app.checkbox(key=chave).value)
        app.checkbox(key=chave).uncheck().run()
        self.sem_excecao(app)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)

    def test_mudar_payload_invalida_conferencia_mesmo_com_mesmos_candidatos(self):
        for campo, valor in (("evento", "Formatura"), ("observacoes", "Novo combinado")):
            with self.subTest(campo=campo):
                app = self.conferir(self.analisar(self.app()))
                anterior = self.chave_conferencia(app)
                novo = copy.deepcopy(app.session_state["proposta"])
                novo[campo] = valor
                app.session_state["proposta"] = novo
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["gravacoes"], [])
                self.assertNotEqual(self.chave_conferencia(app), anterior)
                self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)
                self.assertEqual(app.session_state["proposta"], novo)

    def test_mudar_preco_invalida_prova_sem_perder_personalizacao(self):
        app = self.conferir(self.analisar(self.app()))
        original = copy.deepcopy(app.session_state["proposta"])
        alterada = copy.deepcopy(original)
        alterada["itens"][0]["valor_unitario"] = 18.5
        app.session_state["proposta"] = alterada
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)
        self.assertEqual(app.session_state["proposta"]["itens"], alterada["itens"])
        self.conferir(app)
        self.salvar(app)
        self.assertEqual(app.session_state["gravacoes"], [alterada])

    def test_candidato_novo_no_salvar_invalida_checkbox_ja_renderizada(self):
        app = self.conferir(self.analisar(self.app()))
        anterior = self.chave_conferencia(app)
        app.session_state["historico"] = [registro(), registro("PROP-TEST-02")]
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertNotEqual(anterior, self.chave_conferencia(app))
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)
        self.assertEqual(len(app.dataframe[0].value), 2)
        self.conferir(app)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)

    def test_mudar_status_do_candidato_exige_outra_conferencia(self):
        app = self.conferir(self.analisar(self.app()))
        anterior = self.chave_conferencia(app)
        app.session_state["historico"] = [registro(aprovado=True, pago=True)]
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertNotEqual(anterior, self.chave_conferencia(app))
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)

    def test_registro_alheio_nao_exige_conferir_mesmos_candidatos_novamente(self):
        app = self.conferir(self.analisar(self.app()))
        alheio = registro("PROP-OUTRO", cliente_nome="Outro cliente", documento="98765432100", whatsapp="11988880000")
        app.session_state["historico"] = [alheio, registro()]
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(app.session_state["gravacoes"], [PROPOSTA])
        self.assertEqual(app.session_state["leituras"], 2)

    def test_reordenar_historico_nao_invalida_conferencia(self):
        registros = [registro("PROP-TEST-01"), registro("PROP-TEST-02")]
        app = self.conferir(self.analisar(self.app(historico=registros)))
        app.session_state["historico"] = list(reversed(registros))
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)

    def test_falha_na_leitura_preserva_rascunho_e_nao_expoe_detalhe_tecnico(self):
        app = self.conferir(self.analisar(self.app()))
        original = copy.deepcopy(app.session_state["proposta"])
        app.session_state["offline"] = True
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual(app.session_state["proposta"], original)
        self.assertTrue(any("rascunho foi preservado" in e.value for e in app.error))
        self.assertFalse(any("segredo-do-banco" in e.value for e in app.error))
        self.assertEqual(len(app.success), 0)
        app.session_state["offline"] = False
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)
        self.conferir(app)
        self.salvar(app)
        self.assertEqual(app.session_state["gravacoes"], [original])

    def test_dados_inassinaveis_renderizam_erro_e_nao_consultam_ou_gravam(self):
        for caso, campos in dados_inassinaveis():
            with self.subTest(caso=caso):
                app = self.app(historico=[])
                original = proposta_comercial()
                invalida = {**copy.deepcopy(original), **campos}
                antes = repr(invalida)
                app.session_state["proposta"] = invalida
                app.run()
                self.sem_excecao(app)
                self.assertTrue(any("validar os dados" in erro.value for erro in app.error))
                self.assertTrue(any("rascunho foi preservado" in erro.value for erro in app.error))
                self.assertFalse(any("conexão" in erro.value or "segredo-nao-exibir" in erro.value
                                     for erro in app.error))
                self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])
                self.assertEqual(app.session_state["leituras"], 0)
                self.analisar(app)
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["leituras"], 0)
                self.assertEqual(app.session_state["gravacoes"], [])
                self.assertEqual(repr(app.session_state["proposta"]), antes)
                self.assertEqual(app.session_state["origem_site"], {"fonte": "rascunho-importado", "revisado": True})
                # Uma correção completa retoma a consulta normal. Histórico sem
                # candidatos não precisa de uma checkbox extra para recuperação.
                app.session_state["proposta"] = original
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], True)
                self.assertEqual(app.session_state["leituras"], 1)
                self.assertEqual(app.session_state["gravacoes"], [original])

    def test_falha_de_assinatura_invalida_aceite_e_correcao_exige_nova_conferencia(self):
        for caso, campos in dados_inassinaveis():
            with self.subTest(caso=caso):
                app = self.app()
                original = proposta_comercial()
                app.session_state["proposta"] = copy.deepcopy(original)
                self.conferir(self.analisar(app))
                anterior = self.chave_conferencia(app)
                invalida = {**copy.deepcopy(original), **campos}
                antes = repr(invalida)
                app.session_state["proposta"] = invalida
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["leituras"], 1)
                self.assertEqual(app.session_state["gravacoes"], [])
                revisao = app.session_state["_teste_conferencia_duplicidades"]
                self.assertFalse(revisao["confirmada"])
                self.assertIsNone(revisao["resultado"])
                self.assertIsNone(revisao["prova"])
                self.assertNotEqual(self.chave_conferencia(app), anterior)
                self.assertEqual(repr(app.session_state["proposta"]), antes)
                app.session_state["proposta"] = copy.deepcopy(original)
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["leituras"], 2)
                self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)
                self.conferir(app)
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], True)
                self.assertEqual(app.session_state["leituras"], 3)
                self.assertEqual(app.session_state["gravacoes"], [original])

    def test_guard_recusa_assinatura_invalida_com_interface_oculta(self):
        app = self.conferir(self.analisar(self.app()))
        app.checkbox(key="fixture_mostrar").uncheck().run()
        app.session_state["proposta"]["metadata"] = {"arquivo": b"conteudo-invalido"}
        antes = repr(app.session_state["proposta"])
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["leituras"], 1)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual(repr(app.session_state["proposta"]), antes)
        app.checkbox(key="fixture_mostrar").check().run()
        self.sem_excecao(app)
        self.assertTrue(any("validar os dados" in erro.value for erro in app.error))
        self.assertEqual([c.key for c in app.checkbox], ["fixture_mostrar"])

    def test_falha_de_assinatura_apos_renderizar_nao_modifica_widget_criado(self):
        app = self.conferir(self.analisar(self.app()))
        anterior = self.chave_conferencia(app)
        app.session_state["mudanca_no_salvar"] = {"prazo_dias": float("nan")}
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(app.session_state["leituras"], 1)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertNotEqual(self.chave_conferencia(app), anterior)
        self.assertFalse(app.session_state["_teste_conferencia_duplicidades"]["confirmada"])
        self.assertTrue(any("validar os dados" in erro.value for erro in app.error))

    def test_historico_invalido_nao_vira_lista_vazia(self):
        for historico in (None, {}, "leitura incompleta"):
            with self.subTest(historico=historico):
                app = self.app()
                app.session_state["historico"] = historico
                self.salvar(app)
                self.assertIs(app.session_state["ultimo_resultado"], False)
                self.assertEqual(app.session_state["gravacoes"], [])
                self.assertTrue(app.error)
                self.assertEqual(len(app.success), 0)
                self.assertEqual(app.session_state["proposta"], PROPOSTA)

    def test_limpar_depois_de_salvar_nao_reaproveita_aceite_na_proxima_proposta(self):
        app = self.conferir(self.analisar(self.app()))
        anterior = self.chave_conferencia(app)
        self.salvar(app)
        self.assertEqual(len(app.session_state["gravacoes"]), 1)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], False)
        self.assertEqual(len(app.session_state["gravacoes"]), 1)
        self.assertNotEqual(anterior, self.chave_conferencia(app))
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app)).value)

    def test_consultar_historico_so_navega_sem_carregar_ou_alterar_rascunho(self):
        app = self.analisar(self.app(historico=[registro("PROP-TEST-01"), registro("PROP-TEST-02")]))
        original = copy.deepcopy(app.session_state["proposta"])
        geracao = app.session_state["_teste_conferencia_duplicidades"]["geracao"]
        esperado = app.session_state["_teste_conferencia_duplicidades"]["resultado"]["candidatos"][1]["numero"]
        seletor = app.selectbox(key=f"teste_duplicidades_{geracao}_proposta")
        seletor.select(1).run()
        self.clicar(app, f"teste_duplicidades_{geracao}_abrir")
        self.assertEqual(app.session_state["navegacoes"], [esperado])
        self.assertEqual(app.session_state["proposta"], original)
        self.assertEqual(app.session_state["gravacoes"], [])
        self.assertEqual(app.session_state["leituras"], 1)

    def test_tabela_mostra_todos_indicios_sem_contatos_documentos_ou_valores(self):
        historico = [registro(f"PROP-TEST-{i:02d}") for i in range(1, 18)]
        app = self.analisar(self.app(historico=historico))
        tabela = app.dataframe[0].value
        self.assertEqual(len(tabela), len(historico))
        self.assertEqual(set(tabela.columns), {"Proposta", "Data", "Cliente", "Situação", "Motivos", "Itens"})
        conteudo = tabela.to_string()
        self.assertNotIn(PROPOSTA["whatsapp"], conteudo)
        self.assertNotIn(PROPOSTA["documento"], conteudo)
        self.assertNotIn("20.0", conteudo)
        self.assertTrue(any("indício" in e.value and "nova encomenda" in e.value for e in app.caption))

    def test_dois_prefixos_nao_compartilham_confirmacao(self):
        extra = '''
renderizar_conferencia(
    st, st.session_state["proposta"], prefixo="outro",
    carregar_historico=carregar, hoje=st.session_state["hoje"],
)
if st.button("Salvar outro", key="fixture_salvar_outro"):
    st.session_state["outro_resultado"] = validar_salvamento(
        st, st.session_state["proposta"], prefixo="outro",
        carregar_historico=carregar, hoje=st.session_state["hoje"],
    )
'''
        app = self.app(extra=extra)
        self.conferir(self.analisar(app))
        self.clicar(app, "fixture_salvar_outro")
        app.run()
        self.sem_excecao(app)
        self.assertIs(app.session_state["outro_resultado"], False)
        self.assertTrue(app.checkbox(key=self.chave_conferencia(app)).value)
        self.assertFalse(app.checkbox(key=self.chave_conferencia(app, "outro")).value)
        self.conferir(app, "outro")
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertTrue(app.session_state["_outro_conferencia_duplicidades"]["confirmada"])

    def test_sair_e_voltar_mantem_revisao_mas_salvar_reconsulta(self):
        app = self.conferir(self.analisar(self.app()))
        chave = self.chave_conferencia(app)
        app.checkbox(key="fixture_mostrar").uncheck().run()
        app.run()
        self.assertNotIn(chave, app.session_state)
        app.checkbox(key="fixture_mostrar").check().run()
        self.sem_excecao(app)
        self.assertTrue(app.checkbox(key=self.chave_conferencia(app)).value)
        self.assertEqual(app.session_state["leituras"], 1)
        self.salvar(app)
        self.assertIs(app.session_state["ultimo_resultado"], True)
        self.assertEqual(app.session_state["leituras"], 2)


if __name__ == "__main__":
    unittest.main()
