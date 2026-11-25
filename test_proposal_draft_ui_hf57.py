"""AppTest real + serviço HF57, sem app.py, banco, rede ou arquivos escritos.

AppTest 1.51 não oferece ação de upload/download. A fixture renderiza o uploader
real e fornece UploadedFile real no limite de entrada da UI, incluindo seu
callback de alteração. Ela não afirma testar a transferência pelo navegador.
Os bytes e o botão real de download são conferidos, sem baixar no navegador.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import date, datetime, timezone
import logging
from pathlib import Path
import unittest

from proposal_draft_service_hf57 import capturar_rascunho, exportar_rascunho, importar_rascunho

logging.disable(logging.CRITICAL)
try:
    from streamlit.testing.v1 import AppTest
    from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
    from streamlit.proto.Common_pb2 import FileURLs
except ImportError:
    AppTest = None


ESTADO = {
    "form_cliente": "Alice de Teste", "form_documento": "00123456789", "form_whatsapp": "11999990000",
    "form_evento": "Aniversário", "form_observacoes": "Mensagem recebida do site:\nNome Ana · Tema Espaço",
    "form_desconto": 2.0, "form_entrega": date(2026, 12, 1), "form_prazo": "10",
    "form_frete": "Entrega", "form_taxa_entrega": 5.0, "form_validade": "5", "form_key": 0,
    "temp_itens": [{"produto": "Caneca", "especificacoes": "Nome Ana | Tema Espaço",
                    "quantidade": 2, "valor_unitario": 20.0, "produto_catalogo_id": "CAT-01",
                    "metadata": {"arquivo": "arte-ana.pdf", "cores": ["azul", "prata"]}}],
    "alheio": {"preservar": True},
}


def documento(estado=None, *, anna=False):
    return capturar_rascunho(deepcopy(ESTADO if estado is None else estado), anna=anna,
                            agora=datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc),
                            versao_manager="65.24.57")


def com_pendencias():
    estado = deepcopy(ESTADO)
    estado.update(produto_novo_0_livre="Copo", nome_item_0="Bia", qtd_0=3, valor_0=12.5)
    estado["_hf53_edicao_jorge"] = {"indice": 0, "original": deepcopy(ESTADO["temp_itens"][0]), "token": 2}
    estado["hf53_item_jorge_2_especificacoes"] = "Nome Lia | Tema Espaço"
    return documento(estado)


BASE = '''
from copy import deepcopy
import datetime
import streamlit as st
from proposal_draft_service_hf57 import capturar_rascunho
from proposal_draft_ui_hf57 import renderizar_exportacao, renderizar_retomada, renderizar_referencias

if "formulario" not in st.session_state:
    st.session_state["formulario"] = __ESTADO__
    st.session_state["agora"] = "2026-11-25T15:00:00+00:00"
    st.session_state["versao"] = "65.24.57"
    st.session_state["erro_captura"] = None
    st.session_state["arquivos"] = {"teste": None, "outro": None}
    st.session_state["eventos_upload"] = {}
    st.session_state["chaves_upload"] = {}
    st.session_state["aberturas"] = []
    st.session_state["tentativas"] = 0
    st.session_state["modo_abrir"] = "ok"
    st.session_state["perfil_destino"] = "jorge"
    st.session_state["origem"] = {}
    st.session_state["pendencias"] = {"item_nao_adicionado": [], "edicao_item": []}
    st.session_state["dispensas"] = 0
    st.session_state["modo_dispensar"] = "ok"

class UploaderUI:
    def __init__(self, prefixo):
        self.prefixo = prefixo
    def __getattr__(self, name):
        return getattr(st, name)
    def file_uploader(self, *args, **kwargs):
        anterior = st.session_state["chaves_upload"].get(self.prefixo)
        evento = st.session_state["eventos_upload"].pop(self.prefixo, False)
        if anterior is not None and anterior != kwargs["key"] and not evento:
            st.session_state["arquivos"][self.prefixo] = None
        st.session_state["chaves_upload"][self.prefixo] = kwargs["key"]
        st.file_uploader(*args, **kwargs)
        if evento:
            kwargs["on_change"](*kwargs["args"])
        return st.session_state["arquivos"].get(self.prefixo)

def capturar():
    if st.session_state["erro_captura"] == "esperado":
        raise ValueError("Rascunho inválido: formulario.desconto deve ser um número finito.")
    if st.session_state["erro_captura"]:
        raise RuntimeError("segredo-interno-nao-exibir")
    return capturar_rascunho(st.session_state["formulario"], anna=False,
        agora=datetime.datetime.fromisoformat(st.session_state["agora"]),
        versao_manager=st.session_state["versao"])

def abrir(dados):
    st.session_state["tentativas"] += 1
    if st.session_state["modo_abrir"] == "erro":
        raise RuntimeError("segredo-interno-nao-exibir")
    if st.session_state["modo_abrir"] == "value_error":
        raise ValueError("segredo-interno-nao-exibir")
    if st.session_state["modo_abrir"] == "recusar":
        return False
    st.session_state["aberturas"].append({"perfil_destino": st.session_state["perfil_destino"], "dados": deepcopy(dados)})
    return True

def dispensar():
    if st.session_state["modo_dispensar"] == "erro":
        raise RuntimeError("segredo-interno-nao-exibir")
    if st.session_state["modo_dispensar"] == "recusar":
        return False
    st.session_state["dispensas"] += 1
    st.session_state["pendencias"] = {"item_nao_adicionado": [], "edicao_item": []}
    return True

if st.checkbox("Mostrar exportação", value=True, key="fixture_exportacao"):
    renderizar_exportacao(st, capturar, prefixo="teste")
if st.checkbox("Mostrar retomada", value=True, key="fixture_retomada"):
    renderizar_retomada(UploaderUI("teste"), abrir, prefixo="teste")
else:
    # O widget oculto perde seu arquivo; a revisão própria deve sobreviver.
    st.session_state["arquivos"]["teste"] = None
renderizar_referencias(st, st.session_state["origem"], st.session_state["pendencias"],
    prefixo="teste", dispensar_pendencias=dispensar,
    contexto=st.session_state["formulario"].get("form_key", 0))
'''


@unittest.skipIf(AppTest is None, "Requer Streamlit para testar a interface real")
class RascunhoPortatilUITest(unittest.TestCase):
    def app(self, extra=""):
        app = AppTest.from_string(BASE.replace("__ESTADO__", repr(ESTADO)) + extra, default_timeout=20).run()
        self.sem_excecao(app)
        return app

    def sem_excecao(self, app):
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def clicar(self, app, key):
        app.button(key=key).click().run()
        self.sem_excecao(app)
        return app

    def upload(self, app, doc=None, *, conteudo=None, nome="rascunho.json", prefixo="teste"):
        raw = exportar_rascunho(documento() if doc is None else doc) if conteudo is None else conteudo
        arquivo = UploadedFile(UploadedFileRec("fixture-" + prefixo, nome, "application/json", raw), FileURLs())
        app.session_state["arquivos"][prefixo] = arquivo
        app.session_state["eventos_upload"][prefixo] = True
        app.run()
        self.sem_excecao(app)
        return app

    def revisao(self, app, prefixo="teste"):
        return app.session_state[f"_{prefixo}_rascunho_retomada"]

    def conferir(self, app, *, novo=True, prefixo="teste"):
        geracao = self.revisao(app, prefixo)["geracao"]
        app.checkbox(key=f"{prefixo}_retomada_{geracao}_conferida").check().run()
        self.sem_excecao(app)
        if novo and self.revisao(app, prefixo)["documento"]["origem"]["numero_proposta"]:
            app.checkbox(key=f"{prefixo}_retomada_{geracao}_novo").check().run()
            self.sem_excecao(app)
        return app

    def test_preparar_gera_download_real_sem_alterar_formulario(self):
        app = self.app()
        self.assertEqual(len(app.get("download_button")), 0)
        self.clicar(app, "teste_preparar_rascunho")
        preparado = app.session_state["_teste_rascunho_exportacao"]
        self.assertEqual(importar_rascunho(preparado["dados"]), documento())
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertTrue(app.get("download_button")[0].proto.ignore_rerun)
        self.assertEqual(app.session_state["formulario"], ESTADO)
        self.assertEqual(app.session_state["aberturas"], [])
        self.assertTrue(any("2026-11-25T15:00:00" in c.value for c in app.caption))
        self.assertTrue(any("Campos ainda não enviados" in c.value for c in app.caption))

    def test_formulario_incompleto_sem_itens_exporta_e_retoma(self):
        app = self.app()
        app.session_state["formulario"] = {}
        self.clicar(app, "teste_preparar_rascunho")
        doc = importar_rascunho(app.session_state["_teste_rascunho_exportacao"]["dados"])
        self.assertEqual(doc["formulario"]["itens"], [])
        self.assertEqual(doc["formulario"]["cliente"], "")
        self.assertIsNone(doc["formulario"]["entrega"])
        self.conferir(self.upload(app, doc))
        self.clicar(app, "teste_retomar_rascunho")
        self.assertEqual(app.session_state["aberturas"][0]["dados"]["itens"], [])
        self.assertIsNone(app.session_state["aberturas"][0]["dados"]["entrega"])
        self.assertEqual(app.session_state["formulario"], {})

    def test_horario_e_versao_novos_nao_invalidam_download_preparado(self):
        app = self.clicar(self.app(), "teste_preparar_rascunho")
        antes = app.session_state["_teste_rascunho_exportacao"]["dados"]
        app.session_state["agora"] = "2026-11-25T16:00:00+00:00"
        app.session_state["versao"] = "65.24.58"
        app.run()
        self.sem_excecao(app)
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertEqual(app.session_state["_teste_rascunho_exportacao"]["dados"], antes)

    def test_mudancas_do_rascunho_invalidam_download_ate_nova_preparacao(self):
        mudancas = ({"form_cliente": "Bia"}, {"form_desconto": 3},
                    {"form_observacoes": "Nova mensagem"}, {"editar_numero": "PROP-02"},
                    {"produto_novo_0_livre": "Copo", "nome_item_0": "Lia"},
                    {"temp_itens": [{**ESTADO["temp_itens"][0], "valor_unitario": 21.5}]},
                    {"temp_itens": [{**ESTADO["temp_itens"][0], "metadata": {"arquivo": "nova-arte.pdf"}}]})
        for mudanca in mudancas:
            with self.subTest(campos=tuple(mudanca)):
                app = self.clicar(self.app(), "teste_preparar_rascunho")
                antigos = app.session_state["_teste_rascunho_exportacao"]["dados"]
                app.session_state["formulario"].update(deepcopy(mudanca))
                app.run()
                self.sem_excecao(app)
                self.assertEqual(len(app.get("download_button")), 0)
                self.assertFalse(app.session_state["_teste_rascunho_exportacao"]["valido"])
                self.assertEqual(app.session_state["_teste_rascunho_exportacao"]["dados"], antigos)
                self.clicar(app, "teste_preparar_rascunho")
                self.assertEqual(len(app.get("download_button")), 1)
                self.assertNotEqual(app.session_state["_teste_rascunho_exportacao"]["dados"], antigos)

    def test_erro_de_captura_preserva_estado_e_recuperacao_pede_preparar(self):
        for modo in ("esperado", "inesperado"):
            with self.subTest(modo=modo):
                app = self.clicar(self.app(), "teste_preparar_rascunho")
                antes = app.session_state["_teste_rascunho_exportacao"]["dados"]
                app.session_state["erro_captura"] = modo
                app.run()
                self.sem_excecao(app)
                self.assertEqual(len(app.get("download_button")), 0)
                self.assertTrue(app.error)
                self.assertFalse(any("segredo-interno" in e.value for e in app.error))
                self.assertEqual(app.session_state["formulario"], ESTADO)
                self.assertEqual(app.session_state["_teste_rascunho_exportacao"]["dados"], antes)
                app.session_state["erro_captura"] = None
                app.run()
                self.assertEqual(len(app.get("download_button")), 0)
                self.clicar(app, "teste_preparar_rascunho")
                self.assertEqual(len(app.get("download_button")), 1)

    def test_exportacao_sobrevive_ao_ocultar_sem_capturar_texto_nao_enviado(self):
        app = self.clicar(self.app(), "teste_preparar_rascunho")
        antes = app.session_state["_teste_rascunho_exportacao"]["dados"]
        app.checkbox(key="fixture_exportacao").uncheck().run()
        app.checkbox(key="fixture_exportacao").check().run()
        self.sem_excecao(app)
        self.assertEqual(app.session_state["_teste_rascunho_exportacao"]["dados"], antes)
        self.assertEqual(len(app.get("download_button")), 1)

    def test_previa_preserva_linhas_origem_condicoes_e_metadata(self):
        doc = documento()
        doc["formulario"]["itens"].append({**deepcopy(doc["formulario"]["itens"][0]), "especificacoes": "Nome Bia"})
        app = self.upload(self.app(), doc)
        self.assertEqual(self.revisao(app)["documento"], doc)
        self.assertEqual(list(app.dataframe[0].value["Personalização"]), ["Nome Ana | Tema Espaço", "Nome Bia"])
        self.assertEqual(app.dataframe[1].value.iloc[0]["Valor"], "R$ 2,00")
        self.assertTrue(any(doc["formulario"]["observacoes"] == t.value for t in app.text))
        self.assertTrue(app.button(key="teste_retomar_rascunho").disabled)
        self.assertEqual(app.session_state["aberturas"], [])

    def test_retomada_conferida_enfileira_novo_sem_escrever_formulario(self):
        app = self.conferir(self.upload(self.app()))
        self.clicar(app, "teste_retomar_rascunho")
        self.assertEqual(app.session_state["tentativas"], 1)
        dados = app.session_state["aberturas"][0]["dados"]
        self.assertTrue(dados["_hf57_retomada"])
        self.assertEqual(dados["itens"], ESTADO["temp_itens"])
        self.assertNotIn("numero_proposta", dados)
        self.assertNotIn("atendimento_id", dados)
        self.assertNotIn("projeto_id", dados)
        self.assertEqual(app.session_state["formulario"], ESTADO)
        self.assertTrue(self.revisao(app)["encaminhada"])
        app.run()
        self.assertEqual(app.session_state["tentativas"], 1)

    def test_edicao_anterior_exige_ciencia_especifica_de_novo_orcamento(self):
        doc = documento({**ESTADO, "editar_numero": "PROP-ANTERIOR", "_atendimento_origem_id": "AT-01"})
        app = self.upload(self.app(), doc)
        self.conferir(app, novo=False)
        self.assertTrue(app.button(key="teste_retomar_rascunho").disabled)
        self.assertTrue(any("não atualizará" in e.value and "PROP-ANTERIOR" in e.value for e in app.warning))
        self.conferir(app)
        self.clicar(app, "teste_retomar_rascunho")
        dados = app.session_state["aberturas"][0]["dados"]
        self.assertEqual(dados["_hf57_origem"]["numero_proposta"], "PROP-ANTERIOR")
        self.assertNotIn("atendimento_id", dados)

    def test_trocar_arquivo_ou_conteudo_invalida_todos_os_aceites(self):
        doc = documento({**ESTADO, "editar_numero": "PROP-01"})
        for campo in ("cliente", "horario", "metadata"):
            with self.subTest(campo=campo):
                app = self.conferir(self.upload(self.app(), doc))
                anterior = self.revisao(app)["geracao"]
                alterado = deepcopy(doc)
                if campo == "cliente":
                    alterado["formulario"]["cliente"] = "Bia"
                elif campo == "horario":
                    alterado["criado_em"] = "2026-11-25T16:00:00+00:00"
                else:
                    alterado["formulario"]["itens"][0]["metadata"]["arquivo"] = "novo.pdf"
                self.upload(app, alterado)
                self.assertNotEqual(self.revisao(app)["geracao"], anterior)
                self.assertFalse(self.revisao(app)["conferida"])
                self.assertFalse(self.revisao(app)["novo_confirmado"])
                self.assertTrue(app.button(key="teste_retomar_rascunho").disabled)

    def test_remover_arquivo_invalida_e_reenviar_nao_reaproveita_aceite(self):
        app = self.conferir(self.upload(self.app()))
        anterior = self.revisao(app)["geracao"]
        app.session_state["arquivos"]["teste"] = None
        app.session_state["eventos_upload"]["teste"] = True
        app.run()
        self.sem_excecao(app)
        self.assertNotIn("_teste_rascunho_retomada", app.session_state)
        self.upload(app)
        self.assertGreater(self.revisao(app)["geracao"], anterior)
        self.assertFalse(self.revisao(app)["conferida"])

    def test_ocultar_e_voltar_preserva_revisao_e_aceite_sem_widget_de_upload(self):
        app = self.conferir(self.upload(self.app()))
        anterior = self.revisao(app)["geracao"]
        app.checkbox(key="fixture_retomada").uncheck().run()
        app.run()
        app.checkbox(key="fixture_retomada").check().run()
        self.sem_excecao(app)
        self.assertIsNone(app.session_state["arquivos"]["teste"])
        self.assertEqual(self.revisao(app)["geracao"], anterior)
        self.assertTrue(self.revisao(app)["conferida"])
        self.clicar(app, "teste_retomar_rascunho")
        self.assertEqual(app.session_state["tentativas"], 1)

    def test_limpar_revisao_afeta_so_arquivo_e_nao_formulario_ou_download(self):
        app = self.clicar(self.app(), "teste_preparar_rascunho")
        preparado = deepcopy(app.session_state["_teste_rascunho_exportacao"])
        self.conferir(self.upload(app))
        self.clicar(app, "teste_limpar_revisao")
        self.assertNotIn("_teste_rascunho_retomada", app.session_state)
        self.assertIsNone(app.session_state["arquivos"]["teste"])
        self.assertEqual(app.session_state["formulario"], ESTADO)
        self.assertEqual(app.session_state["_teste_rascunho_exportacao"], preparado)

    def test_callback_recusa_ou_erro_preserva_revisao_para_tentar_novamente(self):
        for modo in ("recusar", "erro", "value_error"):
            with self.subTest(modo=modo):
                app = self.conferir(self.upload(self.app()))
                geracao = self.revisao(app)["geracao"]
                app.session_state["modo_abrir"] = modo
                self.clicar(app, "teste_retomar_rascunho")
                self.assertEqual(app.session_state["aberturas"], [])
                self.assertEqual(self.revisao(app)["geracao"], geracao)
                self.assertTrue(self.revisao(app)["conferida"])
                self.assertFalse(self.revisao(app)["encaminhada"])
                self.assertFalse(any("segredo-interno" in e.value for e in app.error))
                app.session_state["modo_abrir"] = "ok"
                self.clicar(app, "teste_retomar_rascunho")
                self.assertEqual(len(app.session_state["aberturas"]), 1)
                self.assertEqual(app.session_state["formulario"], ESTADO)

    def test_reabrir_depois_de_cancelar_fluxo_exige_nova_conferencia(self):
        app = self.conferir(self.upload(self.app()))
        self.clicar(app, "teste_retomar_rascunho")
        geracao = self.revisao(app)["geracao"]
        self.clicar(app, "teste_reabrir_revisao")
        self.assertGreater(self.revisao(app)["geracao"], geracao)
        self.assertFalse(self.revisao(app)["conferida"])
        self.assertFalse(self.revisao(app)["encaminhada"])
        self.assertTrue(app.button(key="teste_retomar_rascunho").disabled)
        self.conferir(app)
        self.clicar(app, "teste_retomar_rascunho")
        self.assertEqual(app.session_state["tentativas"], 2)

    def test_arquivo_invalido_nao_vira_retomada_e_preserva_formulario(self):
        for conteudo in (b"{json quebrado", b"[]", b'{"schema_version":1,"schema_version":2}'):
            with self.subTest(conteudo=conteudo):
                app = self.conferir(self.upload(self.app()))
                self.upload(app, conteudo=conteudo)
                self.assertTrue(app.error)
                self.assertFalse(self.revisao(app)["conferida"])
                self.assertEqual(app.session_state["aberturas"], [])
                self.assertEqual(app.session_state["formulario"], ESTADO)

    def test_limite_do_upload_e_checado_antes_de_getvalue(self):
        class Grande(UploadedFile):
            chamadas = 0
            def getvalue(self):
                type(self).chamadas += 1
                raise AssertionError("getvalue não deveria ser chamado")
        app = self.app()
        arquivo = Grande(UploadedFileRec("grande", "grande.json", "application/json", b"{}"), FileURLs())
        arquivo.size = 2 * 1024 * 1024 + 1
        app.session_state["arquivos"]["teste"] = arquivo
        app.session_state["eventos_upload"]["teste"] = True
        app.run()
        self.sem_excecao(app)
        self.assertEqual(Grande.chamadas, 0)
        self.assertTrue(any("2 MiB" in erro.value for erro in app.error))

    def test_numeros_invalidos_para_salvar_permanecem_rascunho_sem_correcao(self):
        doc = documento()
        doc["formulario"]["itens"][0]["quantidade"] = 0
        doc["formulario"]["itens"][0]["valor_unitario"] = -2
        app = self.conferir(self.upload(self.app(), doc))
        self.clicar(app, "teste_retomar_rascunho")
        self.assertEqual(app.session_state["aberturas"][0]["dados"]["itens"], doc["formulario"]["itens"])
        self.assertTrue(any("antes de salvar" in c.value for c in app.caption))

    def test_arquivo_de_jorge_pode_ser_revisado_para_anna_sem_herdar_destino(self):
        extra = '\nrenderizar_retomada(UploaderUI("outro"), abrir, prefixo="outro")\n'
        app = self.app(extra)
        self.upload(app, prefixo="outro")
        self.conferir(self.upload(app))
        self.assertFalse(self.revisao(app, "outro")["conferida"])
        app.session_state["perfil_destino"] = "anna"
        self.clicar(app, "teste_retomar_rascunho")
        abertura = app.session_state["aberturas"][0]
        self.assertEqual(abertura["perfil_destino"], "anna")
        self.assertEqual(abertura["dados"]["_hf57_origem"]["perfil"], "jorge")
        self.assertFalse(self.revisao(app, "outro")["conferida"])

    def carregar_referencias(self, app):
        doc = com_pendencias()
        doc["pendencias"]["item_nao_adicionado"].append({**deepcopy(doc["pendencias"]["item_nao_adicionado"][0]), "produto_livre": "Balão"})
        doc["pendencias"]["edicao_item"].append({**deepcopy(doc["pendencias"]["edicao_item"][0]), "indice": 1})
        app.session_state["origem"] = {**doc["origem"], "criado_em": doc["criado_em"], "manager_version": doc["manager_version"]}
        app.session_state["pendencias"] = doc["pendencias"]
        app.run()
        self.sem_excecao(app)
        return app

    def confirmar_referencias(self, app):
        geracao = app.session_state["_teste_rascunho_referencias"]["geracao"]
        app.checkbox(key=f"teste_referencias_{geracao}_conferidas").check().run()
        self.sem_excecao(app)

    def test_referencias_multiplas_e_dispensa_afetam_somente_notas_manuais(self):
        app = self.carregar_referencias(self.app())
        origem = deepcopy(app.session_state["origem"])
        rotulos = [e.label for e in app.expander]
        self.assertIn("Item não adicionado 1", rotulos)
        self.assertIn("Item não adicionado 2", rotulos)
        self.assertIn("Edição pendente 1 · item 1", rotulos)
        self.assertIn("Edição pendente 2 · item 2", rotulos)
        self.assertTrue(app.button(key="teste_dispensar_pendencias").disabled)
        self.confirmar_referencias(app)
        self.clicar(app, "teste_dispensar_pendencias")
        self.assertEqual(app.session_state["dispensas"], 1)
        self.assertEqual(app.session_state["pendencias"], {"item_nao_adicionado": [], "edicao_item": []})
        self.assertEqual(app.session_state["origem"], origem)
        self.assertEqual(app.session_state["formulario"], ESTADO)
        self.assertTrue(any("permanecem como estavam" in s.value for s in app.success))

    def test_falha_na_dispensa_preserva_informacoes_e_formulario(self):
        for modo in ("recusar", "erro"):
            with self.subTest(modo=modo):
                app = self.carregar_referencias(self.app())
                pendencias = deepcopy(app.session_state["pendencias"])
                app.session_state["modo_dispensar"] = modo
                self.confirmar_referencias(app)
                self.clicar(app, "teste_dispensar_pendencias")
                self.assertEqual(app.session_state["dispensas"], 0)
                self.assertEqual(app.session_state["pendencias"], pendencias)
                self.assertEqual(app.session_state["formulario"], ESTADO)
                self.assertFalse(any("segredo-interno" in e.value for e in app.error))

    def test_mudar_referencias_invalida_confirmacao_de_dispensa(self):
        app = self.carregar_referencias(self.app())
        self.confirmar_referencias(app)
        anterior = app.session_state["_teste_rascunho_referencias"]["geracao"]
        app.session_state["pendencias"]["item_nao_adicionado"][0]["produto_livre"] = "Nova informação"
        app.run()
        self.sem_excecao(app)
        self.assertGreater(app.session_state["_teste_rascunho_referencias"]["geracao"], anterior)
        self.assertTrue(app.button(key="teste_dispensar_pendencias").disabled)
        self.assertEqual(app.session_state["dispensas"], 0)

    def test_reimportar_mesmas_referencias_em_novo_formulario_nao_herda_aceite(self):
        app = self.carregar_referencias(self.app())
        pendencias = deepcopy(app.session_state["pendencias"])
        origem = deepcopy(app.session_state["origem"])
        anterior = app.session_state["_teste_rascunho_referencias"]["geracao"]
        self.confirmar_referencias(app)
        self.clicar(app, "teste_dispensar_pendencias")
        self.assertTrue(app.success)
        # A retomada do mesmo arquivo preserva o conteúdo, mas cria outro
        # formulário. O aceite deve acompanhar essa geração nova do root.
        app.session_state["formulario"]["form_key"] += 1
        app.session_state["pendencias"] = pendencias
        app.run()
        self.sem_excecao(app)
        revisao = app.session_state["_teste_rascunho_referencias"]
        self.assertGreater(revisao["geracao"], anterior)
        self.assertFalse(app.checkbox(key=f"teste_referencias_{revisao['geracao']}_conferidas").value)
        self.assertTrue(app.button(key="teste_dispensar_pendencias").disabled)
        self.assertEqual(len(app.success), 0)
        self.assertEqual(app.session_state["dispensas"], 1)
        self.assertEqual(app.session_state["pendencias"], pendencias)
        self.assertEqual(app.session_state["origem"], origem)

    def test_formulario_sem_referencias_limpa_revisao_e_preserva_contador(self):
        app = self.carregar_referencias(self.app())
        self.confirmar_referencias(app)
        self.clicar(app, "teste_dispensar_pendencias")
        contador = app.session_state["_teste_rascunho_referencias_sequencia"]
        self.assertTrue(app.success)
        app.session_state["origem"] = {}
        app.session_state["formulario"]["form_key"] += 1
        app.run()
        self.sem_excecao(app)
        self.assertNotIn("_teste_rascunho_referencias", app.session_state)
        self.assertEqual(app.session_state["_teste_rascunho_referencias_sequencia"], contador)
        self.assertEqual(len(app.success), 0)
        self.assertNotIn("Informações recuperadas do rascunho", [e.label for e in app.expander])
        self.assertEqual(app.session_state["formulario"]["temp_itens"], ESTADO["temp_itens"])

    def test_metadata_nao_json_recusa_exportacao_sem_apagar_rascunho(self):
        app = self.app()
        app.session_state["formulario"]["temp_itens"][0]["metadata"] = {"arquivo": b"nao-json"}
        app.run()
        self.sem_excecao(app)
        self.assertTrue(app.error)
        self.assertEqual(len(app.get("download_button")), 0)
        self.assertEqual(app.session_state["formulario"]["temp_itens"][0]["metadata"], {"arquivo": b"nao-json"})


class RerunModalTest(unittest.TestCase):
    def test_exportar_e_dispensar_nao_executam_rerun_global(self):
        tree = ast.parse(Path(__file__).with_name("proposal_draft_ui_hf57.py").read_text(encoding="utf-8"))
        calls = [(node.name, sub.func.attr) for node in tree.body if isinstance(node, ast.FunctionDef)
                 for sub in ast.walk(node) if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                 and sub.func.attr == "rerun"]
        self.assertEqual(calls, [("renderizar_retomada", "rerun")])


if __name__ == "__main__":
    unittest.main()
