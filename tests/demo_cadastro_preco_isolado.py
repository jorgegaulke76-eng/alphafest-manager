"""Teste local de cadastro e edição com salvamento em arquivo temporário.
Não importa app.py, cloud_db ou configurações do Supabase.
"""
from pathlib import Path
import json
import tempfile
import streamlit as st
from catalogo_modalidade_preco_service import MODALIDADES, modalidade_atual, aplicar_modalidade
from site_manager_service import avaliar_produto_site
from site_vitrine_service import _preco_br

st.set_page_config(page_title="AlphaFest - Cadastro isolado", layout="centered")
st.title("AlphaFest | Cadastro de teste isolado")
st.info("Somente dados fictícios. O salvamento usa um arquivo temporário fora do projeto. Nenhum acesso ao Supabase.")
if "catalogo_teste_pasta" not in st.session_state:
    st.session_state.catalogo_teste_pasta = tempfile.mkdtemp(prefix="alphafest_precos_")
arquivo = Path(st.session_state.catalogo_teste_pasta) / "catalogo_ficticio.json"
if not arquivo.exists():
    arquivo.write_text("[]", encoding="utf-8")

def ler():
    return json.loads(arquivo.read_text(encoding="utf-8"))

catalogo = ler()
abas = st.tabs(["Cadastrar produto", "Editar produto", "Consultar registros"])
with abas[0]:
    with st.form("cadastro_ficticio"):
        nome = st.text_input("Nome do produto", "Caneca de teste")
        preco = st.text_input("Valor interno", "38,00")
        modo = st.selectbox("Como mostrar o preço no site", list(MODALIDADES), format_func=lambda m: MODALIDADES[m], key="cadastro_preco")
        salvar = st.form_submit_button("Salvar produto fictício")
    if salvar:
        produto = {"Nome":nome.strip(), "Preco":preco.strip(), "Descricao":"Produto fictício", "Imagens":["https://example.com/teste.png"], "PublicarSite":True, "Ativo":True}
        aplicar_modalidade(produto, modo)
        if not produto["Nome"]:
            st.error("Informe um nome.")
        else:
            catalogo.append(produto)
            arquivo.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("Produto fictício salvo no arquivo temporário.")
with abas[1]:
    catalogo = ler()
    if not catalogo:
        st.info("Cadastre um produto fictício primeiro.")
    else:
        indice = st.selectbox("Produto fictício para editar", range(len(catalogo)), format_func=lambda i:catalogo[i]["Nome"])
        produto = catalogo[indice]
        with st.form("edicao_ficticia"):
            novo_nome = st.text_input("Nome", produto["Nome"])
            novo_preco = st.text_input("Valor interno", produto["Preco"])
            atual = modalidade_atual(produto)
            modo_edicao = st.selectbox("Como mostrar o preço no site", list(MODALIDADES), index=list(MODALIDADES).index(atual), format_func=lambda m: MODALIDADES[m], key="edicao_preco")
            salvar_edicao = st.form_submit_button("Salvar edição fictícia")
        if salvar_edicao:
            produto["Nome"] = novo_nome.strip()
            produto["Preco"] = novo_preco.strip()
            aplicar_modalidade(produto, modo_edicao)
            arquivo.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("Edição fictícia salva.")
with abas[2]:
    for produto in ler():
        leitura = avaliar_produto_site(produto)
        exibicao = (("A partir de " if leitura["modalidade_preco_site"] == "a_partir" else "") + _preco_br(leitura["preco"])) if leitura["exibir_preco_site"] else "Consultar valores"
        st.write(f"**{produto['Nome']}** | Interno: {produto['Preco']} | Site: {exibicao}")
st.caption("O arquivo fica na pasta temporária do Windows e não participa do catálogo oficial.")
