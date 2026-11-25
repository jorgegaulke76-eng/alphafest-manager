"""HF58: testes com Streamlit AppTest da Caixa do Projeto real, sem banco.

Extrai somente renderizar_caixa_projeto() do app.py; nao executa o Manager.
Usa projeto e pedido totalmente ficticios e sem rede nem persistencia.
"""
from __future__ import annotations

import ast
import copy
import unittest
from pathlib import Path

from ficha_producao_hf58 import situacao_arte, ficha_producao_txt

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
             and n.name == "renderizar_caixa_projeto"]
if len(FUNCTIONS) != 1:
    raise AssertionError("A Caixa do Projeto real nao foi localizada uma unica vez.")
ACTUAL_UI = ast.get_source_segment(SOURCE, FUNCTIONS[0])
if not ACTUAL_UI:
    raise AssertionError("Nao foi possivel extrair a UI real da Caixa do Projeto.")

FIXTURE = """
import copy
from copy import deepcopy
from datetime import datetime
import html
import re
import streamlit as st
from ficha_producao_hf58 import (
    artes as _hf58_artes,
    situacao_arte as _hf58_situacao_arte,
    identidade_conferencia_arte as _hf58_identidade_arte,
    registrar_aprovacao_conferida as _hf58_registrar_aprovacao_conferida,
    registrar_mutacao_arte as _hf58_marcar_mutacao_arte,
    ficha_producao_txt as _hf58_ficha_producao_txt,
)

if "projeto" not in st.session_state:
    st.session_state["projeto"] = {
        "id": "PRJ-FICTICIO-58", "numero_proposta": "TESTE-58",
        "tema": "Aniversario ficticio", "observacoes": "Conferir nomes",
        "arquivos": [{"id": "AR1", "nome": "arte_Ana_v1.png", "categoria": "Arte",
                      "arquivado": False, "url": "https://exemplo.invalid/arte1.png"}],
        "aprovacao_arte_hf58": {},
    }
    st.session_state["proposta"] = {
        "numero_proposta": "TESTE-58", "cliente_nome": "Cliente Ficticio",
        "data_entrega": "30/11/2026", "status": "Em andamento", "aprovado": False,
        "itens": [{"produto": "Caneca", "quantidade": 2, "especificacoes": "Nome Ana"},
                  {"produto": "Caneca", "quantidade": 1, "especificacoes": "Nome Pedro"}],
    }
    st.session_state["gravacoes"] = 0
    st.session_state["perfil"] = "Jorge"
    st.session_state["simular_falha"] = False
    st.session_state["alteracao_concorrente"] = False

def agora_local():
    return datetime(2026, 11, 25, 15, 30)

def obter_ou_criar_projeto(proposta):
    return deepcopy(st.session_state["projeto"]), [deepcopy(st.session_state["projeto"])]

def carregar_projetos():
    atual = deepcopy(st.session_state["projeto"])
    if st.session_state.get("alteracao_concorrente"):
        atual["arquivos"].append({
            "id": "AR2", "nome": "arte_substituida_em_outra_sessao.png",
            "categoria": "Arte", "arquivado": False,
            "url": "https://exemplo.invalid/arte2.png",
        })
    return [atual]

def atualizar_projeto(projeto):
    if st.session_state.get("simular_falha"):
        return False
    st.session_state["projeto"] = deepcopy(projeto)
    st.session_state["gravacoes"] += 1
    return True

def upload_library_file(*args, **kwargs):
    raise RuntimeError("O teste nunca envia arquivos.")

def nome_tipo_arquivo(nome):
    return "imagem"
"""

SCRIPT = FIXTURE + "\n" + ACTUAL_UI + """
renderizar_caixa_projeto(st.session_state["proposta"], prefixo=st.session_state["perfil"])
"""


@unittest.skipIf(AppTest is None, "Requer o Streamlit AppTest real no GitHub Actions")
class CaixaProjetoUIHF58Test(unittest.TestCase):
    def app(self, perfil="Jorge"):
        app = AppTest.from_string(SCRIPT, default_timeout=20).run()
        app.session_state["perfil"] = perfil
        app.run()
        self.sem_excecoes(app)
        return app

    def sem_excecoes(self, app):
        self.assertEqual([e.message for e in app.exception], [])

    def botao(self, app, texto):
        return next(b for b in app.button if b.label == texto)

    def caixa(self, app):
        return next(c for c in app.checkbox if "versão específica da arte" in c.label)

    def responsavel(self, app):
        return next(t for t in app.text_input if t.label == "Responsável pela conferência da arte")

    def aprovar(self, app, responsavel):
        self.responsavel(app).input(responsavel).run()
        self.caixa(app).check().run()
        self.sem_excecoes(app)
        self.assertFalse(self.botao(app, "Registrar aprovação desta versão").disabled)
        self.botao(app, "Registrar aprovação desta versão").click().run()
        self.sem_excecoes(app)

    def test_jorge_registra_aprovacao_sem_aprovar_pedido_comercial(self):
        app = self.app("Jorge")
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_aprovacao")
        self.assertTrue(self.botao(app, "Registrar aprovação desta versão").disabled)
        self.assertEqual(app.session_state["gravacoes"], 0)
        self.aprovar(app, "Jorge")
        projeto = app.session_state["projeto"]
        self.assertEqual(situacao_arte(projeto)[0], "aprovada")
        self.assertEqual(projeto["aprovacao_arte_hf58"]["responsavel"], "Jorge")
        self.assertEqual(projeto["aprovacao_arte_hf58"]["arquivo_id"], "AR1")
        self.assertEqual(app.session_state["gravacoes"], 1)
        self.assertFalse(app.session_state["proposta"]["aprovado"])
        self.assertEqual(app.session_state["proposta"]["status"], "Em andamento")

    def test_anna_arte_v2_exige_reconfirmacao_individual(self):
        app = self.app("Anna")
        self.aprovar(app, "Anna")
        anterior = copy.deepcopy(app.session_state["projeto"])
        novo = copy.deepcopy(anterior)
        novo["arquivos"].append({
            "id": "AR2", "nome": "arte_Ana_v2.png", "categoria": "Arte",
            "arquivado": False, "url": "https://exemplo.invalid/v2.png",
        })
        app.session_state["projeto"] = novo
        app.run()
        self.sem_excecoes(app)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "revisao_pendente")
        self.assertFalse(self.caixa(app).value)
        self.assertTrue(self.botao(app, "Registrar aprovação desta versão").disabled)
        self.aprovar(app, "Anna")
        self.assertEqual(app.session_state["projeto"]["aprovacao_arte_hf58"]["arquivo_id"], "AR2")
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "aprovada")

    def test_referencia_substituida_com_mesmo_id_nao_reaproveita_aceite(self):
        app = self.app("Jorge")
        self.responsavel(app).input("Jorge").run()
        self.caixa(app).check().run()
        self.assertTrue(self.caixa(app).value)
        projeto = copy.deepcopy(app.session_state["projeto"])
        projeto["arquivos"][0]["url"] = "https://exemplo.invalid/arte1-corrigida.png"
        app.session_state["projeto"] = projeto
        app.run()
        self.sem_excecoes(app)
        self.assertFalse(self.caixa(app).value)
        self.assertTrue(self.botao(app, "Registrar aprovação desta versão").disabled)
        self.assertEqual(app.session_state["gravacoes"], 0)

    def test_concorrencia_rejeita_confirmacao_sem_sobrescrever_projeto(self):
        app = self.app("Anna")
        app.session_state["alteracao_concorrente"] = True
        self.aprovar(app, "Anna")
        self.assertEqual(app.session_state["gravacoes"], 0)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_aprovacao")
        self.assertTrue(any("arte mudou" in e.message.lower() for e in app.error))

    def test_falha_no_banco_nao_anuncia_aprovacao(self):
        app = self.app("Jorge")
        app.session_state["simular_falha"] = True
        self.aprovar(app, "Jorge")
        self.assertEqual(app.session_state["gravacoes"], 0)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_aprovacao")
        self.assertTrue(any("Não foi possível salvar" in e.message for e in app.error))

    def test_arquivar_arte_invalida_aprovacao_sem_alterar_pedido(self):
        app = self.app("Anna")
        self.aprovar(app, "Anna")
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "aprovada")
        self.botao(app, "📦 Arquivar").click().run()
        self.sem_excecoes(app)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_arte")
        self.assertEqual(app.session_state["gravacoes"], 2)
        self.assertFalse(app.session_state["proposta"]["aprovado"])
        self.assertFalse(any(b.label == "Registrar aprovação desta versão" for b in app.button))

    def test_ficha_producao_mantem_duas_personalizacoes_no_perfil_anna(self):
        app = self.app("Anna")
        projeto = app.session_state["projeto"]
        pedido = app.session_state["proposta"]
        ficha = ficha_producao_txt(pedido, projeto, __import__("datetime").datetime(2026,11,25,15,30)).decode("utf-8-sig")
        self.assertIn("Nome Ana", ficha)
        self.assertIn("Nome Pedro", ficha)
        self.assertIn("NÃO APROVADA", ficha)
        self.assertEqual(len(pedido["itens"]), 2)
        self.assertEqual(pedido["status"], "Em andamento")

if __name__ == "__main__":
    unittest.main()
