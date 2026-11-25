"""AlphaFest HF65.24.58 RC5 - demonstracao local, ficticia e isolada.

Usa a funcao real renderizar_caixa_projeto extraida de app.py, mas TODOS os
acessos de projeto/arquivos sao substituidos por dados em memoria. Nao importa
app.py, cloud_db.py ou o Manager inteiro. Nenhuma gravacao real e feita.
"""
from __future__ import annotations

import copy
from copy import deepcopy
from datetime import datetime
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ficha_producao_hf58 import (
    artes as _hf58_artes,
    situacao_arte as _hf58_situacao_arte,
    identidade_conferencia_arte as _hf58_identidade_arte,
    registrar_aprovacao_conferida as _hf58_registrar_aprovacao_conferida,
    registrar_mutacao_arte as _hf58_marcar_mutacao_arte,
    ficha_producao_txt as _hf58_ficha_producao_txt,
)
from test_hf58_caixa_projeto_ui import ACTUAL_UI


def verificar_release():
    """Impedir que esta demonstracao seja confundida com a instalacao atual."""
    try:
        version = (ROOT / "VERSAO.txt").read_text(encoding="utf-8").strip()
        manifest = json.loads((ROOT / "UPDATE_MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        raise RuntimeError("Nao foi encontrado o pacote de homologacao RC5 completo.") from erro
    if (not version.endswith("HF65.24.58")
            or manifest.get("version") != version
            or manifest.get("release_candidate") != "RC5"
            or manifest.get("validation", {}).get("status") != "HOMOLOGACAO_PARCIAL"):
        raise RuntimeError("Este demonstrador exige a branch/pacote HF65.24.58 RC5 de homologacao.")
    return version


def agora_local():
    return datetime.now().replace(microsecond=0)


def obter_ou_criar_projeto(proposta):
    return deepcopy(st.session_state["projeto"]), [deepcopy(st.session_state["projeto"])]


def carregar_projetos():
    return [deepcopy(st.session_state["projeto"])]


def atualizar_projeto(projeto):
    # SOMENTE memoria da sessao Streamlit. Nenhum modulo de banco e importado.
    st.session_state["projeto"] = deepcopy(projeto)
    st.session_state["hf58_demo_gravacoes"] = st.session_state.get("hf58_demo_gravacoes", 0) + 1
    return True


def upload_library_file(upload, *, produto_nome, local_upload_dir):
    """Exercita o uploader REAL do Streamlit, mas NAO envia nenhum byte a rede."""
    if not upload or not getattr(upload, "name", ""):
        return None
    if len(upload.getvalue()) > 10 * 1024 * 1024:
        return None
    safe_name = Path(upload.name).name[:130]
    st.session_state["hf58_demo_uploads"] = st.session_state.get("hf58_demo_uploads", 0) + 1
    # endereco reservado e deliberadamente inexistente, apenas para exibir link
    return "https://exemplo.invalid/hf58-simulacao/" + quote(safe_name)


def nome_tipo_arquivo(nome):
    return "imagem" if str(nome).lower().endswith((".png", ".jpg", ".jpeg", ".webp")) else "arquivo"


def dados_ficticios():
    return (
        {
            "id": "PRJ-HF58-DEMONSTRACAO",
            "numero_proposta": "PEDIDO-FICTICIO-HF58",
            "tema": "Aniversario ficticio",
            "observacoes": "Homologacao: conferir os nomes e as duas personalizacoes.",
            "arquivos": [],
            "aprovacao_arte_hf58": {},
        },
        {
            "numero_proposta": "PEDIDO-FICTICIO-HF58",
            "cliente_nome": "CLIENTE FICTICIO - NAO E PEDIDO REAL",
            "data_entrega": "30/11/2026",
            "status": "Em andamento",
            "aprovado": False,
            "itens": [
                {"produto": "Caneca personalizada", "quantidade": 2, "especificacoes": "Nome Ana; tema jardim"},
                {"produto": "Caneca personalizada", "quantidade": 1, "especificacoes": "Nome Pedro; tema espaço"},
            ],
        },
    )


def iniciar():
    if "projeto" not in st.session_state or "proposta" not in st.session_state:
        st.session_state["projeto"], st.session_state["proposta"] = dados_ficticios()
        st.session_state["hf58_demo_gravacoes"] = 0
        st.session_state["hf58_demo_uploads"] = 0


def reiniciar():
    st.session_state.clear()
    st.rerun()


# Extrai so a funcao de UI revisada. NAO executa o app.py.
# Essas mesmas linhas sao exercitadas pelos testes AppTest no GitHub.
exec(compile(ACTUAL_UI, str(ROOT / "app.py"), "exec"), globals())


def main():
    st.set_page_config(page_title="AlphaFest - HF58 Homologacao Isolada", layout="wide")
    try:
        version = verificar_release()
    except RuntimeError as erro:
        st.error(str(erro))
        st.stop()
    iniciar()
    st.title("AlphaFest | Homologacao HF65.24.58 RC5")
    st.warning(
        "SIMULACAO ISOLADA: cliente, pedido, artes e gravacoes sao FICTICIOS. "
        "Os arquivos enviados ficam somente em memoria; nao ha conexao com banco "
        "de producao nem com armazenamento da AlphaFest."
    )
    st.caption("Interface da Caixa do Projeto extraida de app.py. Somente persistencia e armazenamento sao simulados.")
    with st.sidebar:
        st.header("Painel do teste")
        perfil = st.selectbox("Perfil para conferência", ("Jorge", "Anna"), key="hf58_demo_perfil")
        st.button("Reiniciar simulacao", on_click=reiniciar, use_container_width=True)
        st.caption("A cada reinicio, um pedido ficticio e recriado. Nada e salvo fora da sessao.")
        st.markdown("**Checklist:** arte v1 → aprovar → arte v2 → reaprovar → ficha TXT.")
    renderizar_caixa_projeto(st.session_state["proposta"], prefixo=perfil)
    projeto = st.session_state["projeto"]
    proposta = st.session_state["proposta"]
    status, arte = _hf58_situacao_arte(projeto)
    st.divider()
    st.subheader("Conferência do resultado simulado")
    st.write("Situação da arte:", status)
    st.write("Arte mais recente:", (arte or {}).get("nome", "nenhuma"))
    st.write("Atualizações em memória:", st.session_state.get("hf58_demo_gravacoes", 0))
    st.write("Arquivos recebidos pelo simulador:", st.session_state.get("hf58_demo_uploads", 0))
    st.write("Situação comercial do pedido:", proposta.get("status"))
    st.write("Aprovação comercial:", proposta.get("aprovado"))
    st.download_button(
        "Baixar ficha ficticia para conferencia (TXT)",
        data=_hf58_ficha_producao_txt(proposta, projeto, agora_local()),
        file_name="ALPHAFEST_HF58_FICHA_FICTICIA.txt",
        mime="text/plain",
        use_container_width=True,
    )
    with st.expander("Ver dados ficticios em memoria"):
        st.json({"projeto": projeto, "proposta": proposta})
    st.caption(
        f"Versao {version} | Demo local somente para homologacao. "
        "Confirmar o upload real em ambiente de TESTES separado antes de liberar producao."
    )


if __name__ == "__main__":
    main()
