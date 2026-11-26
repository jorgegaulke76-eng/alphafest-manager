"""Homologacao isolada da Caixa do Projeto: envio de arte pela UI real.

O handler de upload e o formulario sao de app.py, carregados em AppTest.
Somente o armazenamento binario e substituido por fixture ficticia (sem rede).
Nao comprova armazenamento real nem substitui teste manual do Manager.
"""
from __future__ import annotations

import unittest
from datetime import datetime

from ficha_producao_hf58 import ficha_producao_txt, situacao_arte
from test_hf58_caixa_projeto_ui import ACTUAL_UI, FIXTURE

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


UPLOAD_SIMULADO = """
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import quote

# O Streamlit recebe um arquivo ficticio quando acionado pelo teste, sem
# ler o disco nem conectar-se ao armazenamento de producao.
def _arquivo_simulado(*args, **kwargs):
    nome = st.session_state.get("hf58_arquivo_simulado")
    if not nome:
        return None
    return SimpleNamespace(name=nome, getvalue=lambda: b"ARTE FICTICIA")

def upload_library_file(upload, *, produto_nome, local_upload_dir):
    st.session_state["hf58_uploads"] = st.session_state.get("hf58_uploads", 0) + 1
    if st.session_state.get("hf58_falha_upload"):
        return None
    return "https://exemplo.invalid/arquivos/" + quote(upload.name)

def agora_local():
    n = st.session_state.get("hf58_relogio", 0) + 1
    st.session_state["hf58_relogio"] = n
    return datetime(2026, 11, 25, 15, 30) + timedelta(microseconds=n)

# O override dura somente a execucao da funcao, sem afetar outros testes.
_original_file_uploader_hf58 = st.file_uploader
st.file_uploader = _arquivo_simulado
try:
    renderizar_caixa_projeto(st.session_state["proposta"], prefixo=st.session_state["perfil"])
finally:
    st.file_uploader = _original_file_uploader_hf58
"""

SCRIPT = FIXTURE + "\n" + ACTUAL_UI + "\n" + UPLOAD_SIMULADO


@unittest.skipIf(AppTest is None, "Requer Streamlit AppTest com fixture offline")
class UploadArteHF58InterfaceTest(unittest.TestCase):
    def abrir(self, perfil):
        app = AppTest.from_string(SCRIPT, default_timeout=25).run()
        app.session_state["perfil"] = perfil
        app.session_state["projeto"]["arquivos"] = []
        app.run()
        self.sem_excecoes(app)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_arte")
        return app

    def sem_excecoes(self, app):
        self.assertEqual([e.message for e in app.exception], [])

    def botao(self, app, label):
        return next(b for b in app.button if b.label == label)

    def aprovar(self, app, operador):
        next(t for t in app.text_input if t.label == "Responsável pela conferência da arte").input(operador).run()
        next(c for c in app.checkbox if "versão específica da arte" in c.label).check().run()
        self.botao(app, "Registrar aprovação desta versão").click().run()
        self.sem_excecoes(app)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "aprovada")

    def enviar(self, app, nome, *, categoria="Arte"):
        app.session_state["hf58_arquivo_simulado"] = nome
        app.run()
        self.sem_excecoes(app)
        if categoria != "Arte":
            next(s for s in app.selectbox if s.label == "Classificação").set_value(categoria).run()
        self.botao(app, "📤 Enviar arquivo").click().run()
        self.sem_excecoes(app)
        return app

    def texto_ficha(self, app):
        return ficha_producao_txt(
            app.session_state["proposta"], app.session_state["projeto"],
            datetime(2026, 11, 25, 15, 30),
        ).decode("utf-8-sig")

    def test_jorge_upload_v1_v2_reconfirmacao_e_ficha(self):
        app = self.abrir("Jorge")
        self.assertEqual(app.session_state["gravacoes"], 0)
        self.enviar(app, "teste_arte_v1.png")
        projeto = app.session_state["projeto"]
        self.assertEqual(len(projeto["arquivos"]), 1)
        self.assertEqual(projeto["arquivos"][0]["nome"], "teste_arte_v1.png")
        self.assertEqual(projeto["arquivos"][0]["categoria"], "Arte")
        self.assertEqual(situacao_arte(projeto)[0], "sem_aprovacao")
        self.aprovar(app, "Jorge")
        ficha_v1 = self.texto_ficha(app)
        self.assertIn("APROVADA", ficha_v1)
        self.assertIn("teste_arte_v1.png", ficha_v1)
        self.enviar(app, "teste_arte_v2.png")
        projeto = app.session_state["projeto"]
        self.assertEqual(len(projeto["arquivos"]), 2)
        self.assertNotEqual(projeto["arquivos"][0]["id"], projeto["arquivos"][1]["id"])
        self.assertEqual(situacao_arte(projeto)[0], "revisao_pendente")
        self.assertIn("REVISÃO PENDENTE", self.texto_ficha(app))
        caixa = next(c for c in app.checkbox if "versão específica da arte" in c.label)
        self.assertFalse(caixa.value)
        self.assertTrue(self.botao(app, "Registrar aprovação desta versão").disabled)
        self.aprovar(app, "Jorge")
        final = app.session_state["projeto"]
        self.assertEqual(final["aprovacao_arte_hf58"]["arquivo_id"], final["arquivos"][1]["id"])
        self.assertIn("teste_arte_v2.png", self.texto_ficha(app))
        self.assertIn("Nome Ana", self.texto_ficha(app))
        self.assertIn("Nome Pedro", self.texto_ficha(app))
        self.assertFalse(app.session_state["proposta"]["aprovado"])
        self.assertEqual(app.session_state["proposta"]["status"], "Em andamento")
        self.assertEqual(app.session_state["hf58_uploads"], 2)

    def test_anna_upload_v1_v2_sem_liberar_comercial(self):
        app = self.abrir("Anna")
        self.enviar(app, "arte_Ana_v1.png")
        self.aprovar(app, "Anna")
        self.enviar(app, "arte_Ana_v2.png")
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "revisao_pendente")
        self.aprovar(app, "Anna")
        self.assertIn("APROVADA", self.texto_ficha(app))
        self.assertIn("arte_Ana_v2.png", self.texto_ficha(app))
        self.assertEqual(app.session_state["proposta"]["status"], "Em andamento")

    def test_referencia_nao_invalida_arte_aprovada(self):
        app = self.abrir("Jorge")
        self.enviar(app, "arte_v1.png")
        self.aprovar(app, "Jorge")
        self.enviar(app, "inspiracao.png", categoria="Referência")
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "aprovada")
        self.assertEqual(app.session_state["projeto"]["arquivos"][-1]["categoria"], "Referência")
        self.assertEqual(app.session_state["hf58_uploads"], 2)
        self.assertEqual(app.session_state["gravacoes"], 3)

    def test_upload_sem_arquivo_nao_grava(self):
        app = self.abrir("Anna")
        self.botao(app, "📤 Enviar arquivo").click().run()
        self.sem_excecoes(app)
        self.assertTrue(any("Escolha um arquivo" in x.value for x in app.warning))
        self.assertEqual(app.session_state["gravacoes"], 0)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_arte")

    def test_falha_do_armazenamento_nao_cria_vinculo(self):
        app = self.abrir("Jorge")
        app.session_state["hf58_falha_upload"] = True
        self.enviar(app, "arte_sem_upload.png")
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "sem_arte")
        self.assertEqual(app.session_state["gravacoes"], 0)
        self.assertTrue(any("Não foi possível salvar o arquivo" in e.value for e in app.error))

    def test_falha_na_gravacao_do_vinculo_mantem_arte_original(self):
        app = self.abrir("Anna")
        self.enviar(app, "arte_Ana_v1.png")
        self.aprovar(app, "Anna")
        app.session_state["simular_falha"] = True
        app.session_state["hf58_arquivo_simulado"] = "arte_Ana_v2.png"
        app.run()
        self.botao(app, "📤 Enviar arquivo").click().run()
        self.sem_excecoes(app)
        self.assertTrue(any("vinculo ao projeto nao foi confirmado" in e.value for e in app.error))
        self.assertEqual(len(app.session_state["projeto"]["arquivos"]), 1)
        self.assertEqual(situacao_arte(app.session_state["projeto"])[0], "aprovada")
        self.assertEqual(app.session_state["gravacoes"], 2)
        self.assertEqual(app.session_state["proposta"]["status"], "Em andamento")

if __name__ == "__main__":
    unittest.main()
