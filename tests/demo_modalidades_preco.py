"""Prévia local, sem acesso ao banco ou aos produtos reais."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from catalogo_modalidade_preco_service import (
    MODALIDADES, modalidade_atual, aplicar_modalidade
)
from site_manager_service import avaliar_produto_site
from site_vitrine_service import _preco_br

st.set_page_config(page_title="AlphaFest - Teste de preços", layout="centered")
st.title("AlphaFest | Teste dos tipos de preço")
st.info("Simulação isolada: nenhum produto real ou dado do Supabase será acessado ou salvo.")
if "demo_produto" not in st.session_state:
    st.session_state.demo_produto = {
        "Nome": "Caneca personalizada (EXEMPLO)",
        "Preco": "38,00",
        "ExibirPrecoSite": False,
        "PublicarSite": True,
        "Ativo": True,
    }

produto = st.session_state.demo_produto
st.subheader(produto["Nome"])
st.caption("Valor interno fictício: R$ 38,00 — permanece inalterado")
modos = list(MODALIDADES)
atual = modalidade_atual(produto)
selecionado = st.selectbox(
    "Como mostrar o preço no site",
    modos,
    index=modos.index(atual),
    format_func=lambda m: MODALIDADES[m],
)
if selecionado != atual:
    aplicar_modalidade(produto, selecionado)

leitura = avaliar_produto_site(produto)
preco_site = (
    ("A partir de " if leitura["modalidade_preco_site"] == "a_partir" else "")
    + _preco_br(leitura["preco"])
    if leitura["exibir_preco_site"] else "Consultar valores"
)
st.markdown("#### Prévia da ficha no site")
st.metric("Preço apresentado ao cliente", preco_site)
st.caption("Este teste guarda a escolha apenas na memória desta aba. Não existe botão Salvar.")
