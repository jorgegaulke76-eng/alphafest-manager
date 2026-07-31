import streamlit as st
import pandas as pd
import json
import os
import html
import re
import urllib.parse
from urllib.parse import quote
from datetime import datetime, date
import altair as alt
import base64

from cloud_db import (
    connection_test,
    load_document,
    save_document,
    upload_catalog_image,
)

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Orçamento Alphafest", layout="wide")
ARQUIVO_HISTORICO = "historico_orcamentos.json"
ARQUIVO_CATALOGO = "catalogo_db.json"
ARQUIVO_CLIENTES = "clientes_db.json"
ARQUIVO_PRODUCAO = "producao_db.json"
VERSAO_APP = "3.2.1"
PASTA_UPLOADS = "uploads"
os.makedirs(PASTA_UPLOADS, exist_ok=True)

# --- INICIALIZAÇÃO DE SEGURANÇA ---
if "form_key" not in st.session_state: st.session_state.form_key = 0
if "temp_itens" not in st.session_state: st.session_state.temp_itens = []

# --- ACESSO OPCIONAL POR SENHA ---
def verificar_acesso():
    try:
        senha_configurada = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        senha_configurada = ""
    if not senha_configurada:
        return
    if st.session_state.get("acesso_liberado"):
        return
    st.title("🔐 Alphafest Manager")
    senha_digitada = st.text_input("Senha de acesso", type="password")
    if st.button("Entrar", type="primary"):
        if senha_digitada == senha_configurada:
            st.session_state.acesso_liberado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()


verificar_acesso()

# --- FUNÇÕES AUXILIARES ---
def formatar_msg_whatsapp(prop):
    """Monta a mensagem compacta aprovada para envio pelo WhatsApp."""
    prop = prop or {}

    numero_proposta = str(prop.get("numero_proposta", "")).strip() or "N/A"
    data_emissao = str(prop.get("data_geracao", prop.get("data", ""))).strip() or "N/A"
    cliente = str(prop.get("cliente_nome", prop.get("cliente", ""))).strip() or "N/A"
    documento = str(prop.get("documento", prop.get("cliente_cpf_cnpj", ""))).strip() or "N/A"
    entrega = str(prop.get("data_entrega", "")).strip() or "A combinar"
    prazo = str(prop.get("prazo_dias", "10")).strip() or "10"
    frete = str(prop.get("frete_tipo", "Retirada em Itatiba")).strip() or "Retirada em Itatiba"
    validade = str(prop.get("validade_dias", "5")).strip() or "5"

    def numero(valor, padrao=0.0):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    def qtd_txt(valor):
        qtd = numero(valor)
        return str(int(qtd)) if qtd.is_integer() else f"{qtd:.2f}".rstrip("0").rstrip(".").replace(".", ",")

    def moeda(valor):
        return f"R$ {numero(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    itens = prop.get("itens", []) or []
    itens_txt = []
    subtotal_calculado = 0.0
    for indice, item in enumerate(itens, start=1):
        produto = str(item.get("produto", "")).strip() or "Produto não informado"
        detalhes = str(item.get("especificacoes", "")).strip() or "Não informado"
        quantidade = numero(item.get("quantidade", 0))
        valor_unitario = numero(item.get("valor_unitario", 0))
        subtotal_item = quantidade * valor_unitario
        subtotal_calculado += subtotal_item
        itens_txt.extend([
            f"*{indice}. {produto}*",
            f"   *Detalhes:* {detalhes}",
            f"   *Qtd:* {qtd_txt(quantidade)} un. | *Unitário:* {moeda(valor_unitario)} | *Subtotal:* {moeda(subtotal_item)}",
            "",
        ])

    if not itens_txt:
        itens_txt = ["Nenhum item informado", ""]

    desconto = numero(prop.get("desconto", prop.get("desconto_valor", 0)))
    subtotal_salvo = prop.get("subtotal")
    subtotal = numero(subtotal_salvo, subtotal_calculado)
    if subtotal_salvo is None or subtotal <= 0:
        subtotal = subtotal_calculado
    total_salvo = prop.get("valor_total", prop.get("total"))
    total = numero(total_salvo, max(subtotal - desconto, 0.0))
    if total_salvo is None:
        total = max(subtotal - desconto, 0.0)

    unidade_prazo = "dia útil" if prazo == "1" else "dias úteis"
    unidade_validade = "dia corrido" if validade == "1" else "dias corridos"
    sep = "────────────────────────"

    linhas = [
        "*PROPOSTA ALPHAFEST ITATIBA*",
        f"*Nº:* {numero_proposta}",
        f"*Emissão:* {data_emissao}",
        "",
        f"*CLIENTE:* {cliente}",
        f"*CPF/CNPJ:* {documento}",
        sep,
        "*ITENS DO PEDIDO*",
        "",
    ]
    linhas.extend(itens_txt)
    linhas.extend([
        sep,
        f"*Subtotal:* {moeda(subtotal)}",
        f"*Desconto:* - {moeda(desconto)}",
        f"*VALOR TOTAL DO PEDIDO:* {moeda(total)}",
        sep,
        f"*Previsão de Entrega:* {entrega}",
        f"*Prazo de Produção:* {prazo} {unidade_prazo}",
        f"*Frete/Entrega:* {frete}",
        f"*Validade:* {validade} {unidade_validade}",
        sep,
        "*PAGAMENTO VIA PIX:*",
        "*Clique no link para pagar:* https://linkspix.app/alphafestitatiba",
        "",
        "* Titular: Ana Lúcia Zepelini",
        "* Banco: Cora SCD (403)",
        "* Agência: 0001 | Conta: 2515972-5",
        "* Empresa: ANA LUCIA VIEIRA ZEPELINI 29480359880",
        "",
        "*Somente após realizado o pagamento e nos enviando o comprovante daremos seguimento ao seu pedido!*",
    ])
    return "\n".join(linhas)

def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    return ""


def encontrar_logo_base64():
    """Localiza automaticamente o logo existente no repositório."""
    nomes_preferidos = [
        "logo.png", "Logo.png", "LOGO.png", "logo_alphafest.png",
        "alphafest.png", "logo.jpg", "logo.jpeg", "logo.webp",
    ]
    for nome in nomes_preferidos:
        if os.path.exists(nome):
            return get_image_base64(nome), os.path.splitext(nome)[1].lower()

    extensoes = (".png", ".jpg", ".jpeg", ".webp")
    candidatos = []
    try:
        for nome in os.listdir("."):
            nome_lower = nome.lower()
            if nome_lower.endswith(extensoes) and ("logo" in nome_lower or "alpha" in nome_lower):
                candidatos.append(nome)
    except OSError:
        candidatos = []

    if candidatos:
        candidatos.sort(key=lambda n: ("logo" not in n.lower(), len(n)))
        nome = candidatos[0]
        return get_image_base64(nome), os.path.splitext(nome)[1].lower()
    return "", ""

def carregar_historico():
    """Carrega propostas do Supabase, com fallback automático para JSON local."""
    dados = load_document("historico_orcamentos", ARQUIVO_HISTORICO, [])
    return dados if isinstance(dados, list) else []


def salvar_historico_completo(historico):
    """Salva no Supabase e mantém uma cópia JSON local de contingência."""
    if not isinstance(historico, list):
        raise ValueError("O histórico precisa ser uma lista de propostas.")
    save_document("historico_orcamentos", historico, ARQUIVO_HISTORICO)

def alternar_status(num_proposta, campo, novo_valor):
    historico = carregar_historico()
    for p in historico:
        if p.get("numero_proposta") == num_proposta: p[campo] = novo_valor
    salvar_historico_completo(historico)

def excluir_proposta(num_proposta):
    historico = [p for p in carregar_historico() if p.get("numero_proposta") != num_proposta]
    salvar_historico_completo(historico)
    st.rerun()

def criar_grafico_profissional(df, campo_categoria, campo_valor, titulo, horizontal=False, formato=",.2f"):
    """Cria gráfico Altair com validação para evitar erros nos relatórios."""
    if df is None or df.empty:
        return None
    if campo_categoria not in df.columns or campo_valor not in df.columns:
        return None

    dados = df[[campo_categoria, campo_valor]].copy()
    dados[campo_categoria] = dados[campo_categoria].fillna("Não informado").astype(str)
    dados[campo_valor] = pd.to_numeric(dados[campo_valor], errors="coerce").fillna(0)
    dados = dados[dados[campo_valor] >= 0]
    if dados.empty:
        return None

    tooltip = [
        alt.Tooltip(f"{campo_categoria}:N", title=campo_categoria.replace("_", " ").title()),
        alt.Tooltip(f"{campo_valor}:Q", title=campo_valor.replace("_", " ").title(), format=formato),
    ]

    if horizontal:
        ordem = alt.SortField(field=campo_valor, order="descending")
        grafico = (
            alt.Chart(dados)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X(f"{campo_valor}:Q", title=None),
                y=alt.Y(f"{campo_categoria}:N", title=None, sort=ordem),
                tooltip=tooltip,
            )
        )
    else:
        ordem = alt.SortField(field=campo_valor, order="descending")
        grafico = (
            alt.Chart(dados)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X(f"{campo_categoria}:N", title=None, sort=ordem),
                y=alt.Y(f"{campo_valor}:Q", title=None),
                tooltip=tooltip,
            )
        )

    return grafico.properties(title=titulo, height=max(280, min(620, len(dados) * 34)))


def gerar_html(proposta):
    """Gera uma proposta comercial A4, visualmente profissional e pronta para impressão/PDF.

    Recebe diretamente o dicionário salvo no historico_orcamentos.json, evitando
    divergência entre os campos usados na tela de Histórico e os campos do HTML.
    """
    proposta = proposta or {}

    numero = proposta.get("numero_proposta", "")
    data = proposta.get("data_geracao", proposta.get("data", ""))
    cliente = proposta.get("cliente_nome", proposta.get("cliente", ""))
    documento = proposta.get("documento", proposta.get("cliente_cpf_cnpj", ""))
    whatsapp = proposta.get("whatsapp", proposta.get("cliente_wa", ""))
    data_entrega = proposta.get("data_entrega", "")
    itens = proposta.get("itens", []) or []
    subtotal = proposta.get("subtotal", 0)
    desconto = proposta.get("desconto", proposta.get("desconto_valor", 0))
    total = proposta.get("valor_total", proposta.get("total", 0))
    pagamento = proposta.get("pagamento", "Pagamento via PIX: https://linkspix.app/alphafestitatiba")
    observacoes = proposta.get("observacoes", "")
    prazo_dias = str(proposta.get("prazo_dias", "10")).strip() or "10"
    frete_tipo = str(proposta.get("frete_tipo", "Retirada em Itatiba")).strip() or "Retirada em Itatiba"
    validade_dias = str(proposta.get("validade_dias", "5")).strip() or "5"


    def esc(valor, vazio="Não informado"):
        if valor is None:
            return vazio
        texto = str(valor).strip()
        return html.escape(texto) if texto else vazio

    def moeda(valor):
        try:
            return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "R$ 0,00"

    def data_br(valor):
        if valor is None:
            return ""
        texto = str(valor).strip()

        # Datas ISO: 2026-07-31 ou 2026-07-31T...
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
        if m:
            return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

        # Datas já no padrão brasileiro
        m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})", texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        return esc(texto, "")

    numero_txt = esc(numero)
    data_txt = data_br(data)
    cliente_txt = esc(cliente)
    documento_txt = esc(documento)
    whatsapp_txt = esc(whatsapp)
    entrega_txt = data_br(data_entrega) or "A combinar"

    linhas = []

    for item in itens or []:
        produto = esc(item.get("produto", ""), "Produto não informado")
        especificacoes = esc(
            item.get("especificacoes", ""),
            "—"
        )

        try:
            quantidade = float(item.get("quantidade", 0))
        except (TypeError, ValueError):
            quantidade = 0

        quantidade_txt = (
            str(int(quantidade))
            if quantidade.is_integer()
            else f"{quantidade:.2f}".replace(".", ",")
        )

        try:
            valor_unitario = float(item.get("valor_unitario", 0))
        except (TypeError, ValueError):
            valor_unitario = 0

        total_item = quantidade * valor_unitario

        linhas.append(f"""
            <tr>
                <td class="produto">
                    <strong>{produto}</strong>
                </td>
                <td class="spec">{especificacoes}</td>
                <td class="qtd">{quantidade_txt}</td>
                <td class="money">{moeda(valor_unitario)}</td>
                <td class="money total-item">{moeda(total_item)}</td>
            </tr>
        """)

    if not linhas:
        linhas.append("""
            <tr>
                <td colspan="5" class="empty-row">Nenhum item informado.</td>
            </tr>
        """)

    desconto_valor = 0
    try:
        desconto_valor = float(desconto or 0)
    except (TypeError, ValueError):
        desconto_valor = 0

    subtotal_valor = 0
    try:
        subtotal_valor = float(subtotal or 0)
    except (TypeError, ValueError):
        subtotal_valor = 0

    # Propostas antigas podem não ter o campo subtotal.
    if subtotal_valor == 0 and itens:
        for item in itens:
            try:
                subtotal_valor += float(item.get("quantidade", 0)) * float(item.get("valor_unitario", 0))
            except (TypeError, ValueError, AttributeError):
                pass

    total_valor = 0
    try:
        total_valor = float(total or 0)
    except (TypeError, ValueError):
        total_valor = 0

    if total_valor == 0 and subtotal_valor:
        total_valor = max(0, subtotal_valor - desconto_valor)

    observacoes_txt = esc(observacoes, "Nenhuma observação adicional.")
    pagamento_txt = esc(pagamento, "A combinar")

    empresa_nome = "Alphafest"
    empresa_cnpj = "24.374.857/0001-30"
    empresa_ie = "382105300112"
    empresa_endereco = "Avenida Manoel Verginio de Almeida, 442 - Alto Santa Cruz - Itatiba - SP"
    empresa_cep = "13251-530"
    empresa_email = "alphafesti@gmail.com"
    empresa_celular = "(11) 9724-9533"

    logo_base64, logo_ext = encontrar_logo_base64()
    mime_logo = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"
    }.get(logo_ext, "image/png")
    logo_html = (
        f'<img class="brand-logo" src="data:{mime_logo};base64,{logo_base64}" alt="Logo Alphafest">'
        if logo_base64 else '<div class="brand-mark">AF</div>'
    )

    pix_base64 = get_image_base64("pix.png")
    pix_qr_html = (
        f'<img class="pix-qr" src="data:image/png;base64,{pix_base64}" alt="QR Code PIX">'
        if pix_base64 else ''
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proposta {numero_txt} - {cliente_txt}</title>

<style>
    @page {{
        size: A4;
        margin: 12mm;
    }}

    * {{
        box-sizing: border-box;
    }}

    html, body {{
        margin: 0;
        padding: 0;
        background: #eef1f5;
        color: #20252b;
        font-family: Arial, Helvetica, sans-serif;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}

    body {{
        padding: 24px;
    }}

    .page {{
        width: 210mm;
        min-height: 297mm;
        margin: 0 auto;
        background: #ffffff;
        box-shadow: 0 8px 30px rgba(0,0,0,.10);
        overflow: hidden;
    }}

    .top-line {{
        height: 6px;
        background: linear-gradient(90deg, #111827, #374151, #9ca3af);
    }}

    .header {{
        padding: 25px 30px 20px;
        display: flex;
        justify-content: space-between;
        gap: 30px;
        align-items: flex-start;
        border-bottom: 1px solid #e5e7eb;
    }}

    .brand {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}

    .brand-logo {{
        width: 94px;
        max-height: 78px;
        object-fit: contain;
        flex: 0 0 auto;
    }}

    .company-info {{
        font-size: 9.5px;
        line-height: 1.45;
        color: #4b5563;
        margin-top: 7px;
    }}

    .company-info strong {{
        color: #111827;
    }}

    .brand-mark {{
        width: 52px;
        height: 52px;
        border-radius: 13px;
        background: #111827;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 21px;
        font-weight: 800;
        letter-spacing: -1px;
    }}

    .brand-name {{
        font-size: 25px;
        line-height: 1;
        font-weight: 900;
        letter-spacing: .5px;
        color: #111827;
    }}

    .brand-subtitle {{
        margin-top: 6px;
        font-size: 10px;
        color: #6b7280;
        letter-spacing: .5px;
    }}

    .proposal-meta {{
        text-align: right;
        min-width: 180px;
    }}

    .proposal-label {{
        font-size: 10px;
        color: #6b7280;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
    }}

    .proposal-number {{
        margin-top: 4px;
        font-size: 23px;
        font-weight: 900;
        color: #111827;
    }}

    .proposal-date {{
        margin-top: 5px;
        font-size: 11px;
        color: #6b7280;
    }}

    .content {{
        padding: 22px 30px 28px;
    }}

    .section-title {{
        display: flex;
        align-items: center;
        gap: 9px;
        margin: 0 0 11px;
        font-size: 11px;
        font-weight: 900;
        color: #111827;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .section-title::before {{
        content: "";
        width: 4px;
        height: 16px;
        border-radius: 3px;
        background: #111827;
    }}

    .client-card {{
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        background: #fafafa;
        padding: 16px;
        margin-bottom: 23px;
    }}

    .client-grid {{
        display: grid;
        grid-template-columns: 1.8fr 1fr 1fr 1fr;
        gap: 14px;
    }}

    .field-label {{
        font-size: 9px;
        color: #6b7280;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .7px;
        margin-bottom: 5px;
    }}

    .field-value {{
        font-size: 12px;
        color: #111827;
        font-weight: 600;
        word-break: break-word;
    }}

    .client-main .field-value {{
        font-size: 15px;
        font-weight: 800;
    }}

    .delivery {{
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px dashed #d1d5db;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}

    .delivery strong {{
        color: #111827;
    }}

    .badge {{
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #111827;
        color: #fff;
        font-size: 10px;
        font-weight: 800;
    }}

    table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 20px;
    }}

    thead th {{
        background: #111827;
        color: #fff;
        padding: 11px 9px;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .7px;
        text-align: left;
    }}

    thead th.qtd,
    thead th.money {{
        text-align: right;
    }}

    tbody td {{
        padding: 12px 9px;
        border-top: 1px solid #edf0f2;
        font-size: 10px;
        vertical-align: top;
    }}

    tbody tr:nth-child(even) td {{
        background: #fafafa;
    }}

    td.produto {{
        width: 25%;
        color: #111827;
    }}

    td.spec {{
        width: 36%;
        color: #6b7280;
        line-height: 1.45;
    }}

    td.qtd {{
        width: 8%;
        text-align: right;
        font-weight: 700;
        white-space: nowrap;
    }}

    td.money {{
        width: 15%;
        text-align: right;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }}

    td.total-item {{
        font-weight: 800;
        color: #111827;
    }}

    .empty-row {{
        text-align: center;
        color: #9ca3af;
        padding: 22px !important;
    }}

    .bottom-grid {{
        display: grid;
        grid-template-columns: 1.35fr .65fr;
        gap: 18px;
        align-items: start;
    }}

    .info-card {{
        border: 1px solid #e5e7eb;
        border-radius: 11px;
        padding: 15px;
        background: #fff;
        margin-bottom: 13px;
    }}

    .info-card-title {{
        font-size: 10px;
        font-weight: 900;
        color: #111827;
        text-transform: uppercase;
        letter-spacing: .8px;
        margin-bottom: 8px;
    }}

    .info-text {{
        font-size: 10px;
        line-height: 1.55;
        color: #4b5563;
        white-space: pre-line;
    }}

    .totals {{
        border-radius: 12px;
        background: #f7f7f8;
        border: 1px solid #e5e7eb;
        padding: 16px;
    }}

    .total-row {{
        display: flex;
        justify-content: space-between;
        gap: 15px;
        padding: 7px 0;
        font-size: 11px;
        color: #4b5563;
    }}

    .total-row.discount {{
        color: #15803d;
    }}

    .grand-total {{
        margin-top: 7px;
        padding-top: 13px;
        border-top: 2px solid #111827;
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 12px;
    }}

    .grand-total span:first-child {{
        font-size: 11px;
        font-weight: 900;
        color: #111827;
        text-transform: uppercase;
        letter-spacing: .7px;
    }}

    .grand-total .value {{
        font-size: 21px;
        font-weight: 900;
        color: #111827;
        white-space: nowrap;
    }}

    .payment-highlight {{
        background: #111827;
        color: #fff;
        border-radius: 11px;
        padding: 15px;
        margin-bottom: 13px;
    }}

    .payment-highlight .info-card-title {{
        color: #fff;
    }}

    .payment-highlight .info-text {{
        color: #e5e7eb;
    }}

    .payment-layout {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
    }}

    .payment-copy {{
        flex: 1;
        min-width: 0;
    }}

    .pix-qr {{
        width: 112px;
        height: 112px;
        object-fit: contain;
        padding: 6px;
        border-radius: 10px;
        background: #ffffff;
        flex: 0 0 auto;
    }}

    .footer {{
        margin-top: 24px;
        padding: 17px 30px;
        background: #111827;
        color: #fff;
        display: flex;
        justify-content: space-between;
        gap: 25px;
        align-items: center;
    }}

    .footer-brand {{
        font-size: 13px;
        font-weight: 900;
        letter-spacing: .5px;
    }}

    .footer-contact {{
        text-align: right;
        font-size: 9px;
        line-height: 1.5;
        color: #d1d5db;
    }}

    .validity {{
        margin-top: 18px;
        font-size: 8.5px;
        line-height: 1.45;
        color: #9ca3af;
        text-align: center;
    }}

    @media print {{
        html, body {{
            background: #fff;
        }}

        body {{
            padding: 0;
        }}

        .page {{
            width: 100%;
            min-height: auto;
            margin: 0;
            box-shadow: none;
        }}

        .no-print {{
            display: none !important;
        }}

        tr, .client-card, .info-card, .totals, .payment-highlight {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}
    }}

    @media (max-width: 800px) {{
        body {{
            padding: 0;
        }}

        .page {{
            width: 100%;
        }}

        .header {{
            flex-direction: column;
        }}

        .proposal-meta {{
            text-align: left;
        }}

        .client-grid,
        .bottom-grid {{
            grid-template-columns: 1fr 1fr;
        }}

        .payment-layout {{
            align-items: flex-start;
        }}

        .pix-qr {{
            width: 96px;
            height: 96px;
        }}

        .footer {{
            flex-direction: column;
            align-items: flex-start;
        }}

        .footer-contact {{
            text-align: left;
        }}
    }}
</style>
</head>

<body>
<div class="page">

    <div class="top-line"></div>

    <header class="header">
        <div class="brand">
            {logo_html}
            <div>
                <div class="brand-name">{empresa_nome}</div>
                <div class="company-info">
                    <strong>CNPJ:</strong> {empresa_cnpj} &nbsp; | &nbsp; <strong>IE:</strong> {empresa_ie}<br>
                    {empresa_endereco}<br>
                    <strong>CEP:</strong> {empresa_cep}<br>
                    <strong>Email:</strong> {empresa_email}<br>
                    <strong>Celular:</strong> {empresa_celular}
                </div>
            </div>
        </div>

        <div class="proposal-meta">
            <div class="proposal-label">Orçamento</div>
            <div class="proposal-number">#{numero_txt}</div>
            <div class="proposal-date">Emissão: {data_txt}</div>
        </div>
    </header>

    <main class="content">

        <div class="section-title">Dados do cliente</div>

        <section class="client-card">
            <div class="client-grid">

                <div class="client-main">
                    <div class="field-label">Cliente / Razão Social</div>
                    <div class="field-value">{cliente_txt}</div>
                </div>

                <div>
                    <div class="field-label">CPF / CNPJ</div>
                    <div class="field-value">{documento_txt}</div>
                </div>

                <div>
                    <div class="field-label">WhatsApp</div>
                    <div class="field-value">{whatsapp_txt}</div>
                </div>

                <div>
                    <div class="field-label">Proposta</div>
                    <div class="field-value">#{numero_txt}</div>
                </div>

            </div>

            <div class="delivery">
                <div>
                    <span class="field-label">Previsão de entrega</span><br>
                    <strong>{entrega_txt}</strong>
                </div>
            </div>
        </section>

        <div class="section-title">Itens da proposta</div>

        <table>
            <thead>
                <tr>
                    <th>Produto</th>
                    <th>Especificações</th>
                    <th class="qtd">Qtd.</th>
                    <th class="money">Valor unit.</th>
                    <th class="money">Total</th>
                </tr>
            </thead>
            <tbody>
                {''.join(linhas)}
            </tbody>
        </table>

        <div class="bottom-grid">

            <div>
                <div class="section-title">Condições comerciais</div>

                <div class="payment-highlight">
                    <div class="payment-layout">
                        <div class="payment-copy">
                            <div class="info-card-title">Pagamento via PIX</div>
                            <div class="info-text">{pagamento_txt}</div>
                        </div>
                        {pix_qr_html}
                    </div>
                </div>

                <div class="info-card">
                    <div class="info-card-title">Observações</div>
                    <div class="info-text">{observacoes_txt}</div>
                </div>

                <div class="info-card">
                    <div class="info-card-title">Validade e produção</div>
                    <div class="info-text">
                        Esta proposta está sujeita à disponibilidade de materiais e à confirmação do pedido.
                        Prazo de produção: {prazo_dias} dias úteis.<br>Frete/Entrega: {esc(frete_tipo)}.<br>Validade da proposta: {validade_dias} dias corridos.
                    </div>
                </div>
            </div>

            <div>
                <div class="section-title">Resumo financeiro</div>

                <div class="totals">
                    <div class="total-row">
                        <span>Subtotal</span>
                        <strong>{moeda(subtotal_valor)}</strong>
                    </div>

                    <div class="total-row discount">
                        <span>Desconto</span>
                        <strong>- {moeda(desconto_valor)}</strong>
                    </div>

                    <div class="grand-total">
                        <span>Total</span>
                        <span class="value">{moeda(total_valor)}</span>
                    </div>
                </div>
            </div>

        </div>

        <div class="validity">
            Documento gerado eletronicamente • Proposta #{numero_txt} • {empresa_nome}
        </div>

    </main>

    <footer class="footer">
        <div class="footer-brand">O poder de estar presente em cada presente...</div>
        <div class="footer-contact">
            CNPJ: {empresa_cnpj}<br>
            Celular: {empresa_celular}<br>
            Email: {empresa_email}
        </div>
    </footer>

</div>
</body>
</html>"""


# --- RECURSOS DA VERSÃO 2.1 ---
def valor_float(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


def calcular_valores_proposta(prop):
    itens = prop.get("itens", []) or []
    subtotal = sum(valor_float(i.get("quantidade")) * valor_float(i.get("valor_unitario")) for i in itens)
    desconto = valor_float(prop.get("desconto", prop.get("desconto_valor", 0)))
    total = prop.get("valor_total", prop.get("total"))
    total = valor_float(total, max(subtotal - desconto, 0)) if total is not None else max(subtotal - desconto, 0)
    return subtotal, desconto, total


def atualizar_proposta(numero_original, dados_atualizados):
    historico = carregar_historico()
    for indice, proposta in enumerate(historico):
        if proposta.get("numero_proposta") == numero_original:
            historico[indice] = dados_atualizados
            salvar_historico_completo(historico)
            return True
    return False


def carregar_proposta_no_formulario(prop, duplicar=False):
    """Agenda o carregamento para o próximo rerun.

    No Streamlit, uma chave ligada a um widget não pode ser alterada depois que
    o widget já foi criado no mesmo ciclo. Por isso, guardamos os dados em uma
    chave temporária e aplicamos antes da criação dos campos no próximo rerun.
    """
    st.session_state._proposta_pendente_formulario = {
        "prop": dict(prop),
        "duplicar": bool(duplicar),
    }


def aplicar_proposta_pendente_no_formulario():
    pendente = st.session_state.pop("_proposta_pendente_formulario", None)
    if not pendente:
        return

    prop = pendente.get("prop", {}) or {}
    duplicar = bool(pendente.get("duplicar", False))

    st.session_state.temp_itens = [dict(item) for item in prop.get("itens", []) or []]
    st.session_state.form_cliente = prop.get("cliente_nome", prop.get("cliente", ""))
    st.session_state.form_documento = prop.get("documento", prop.get("cliente_cpf_cnpj", ""))
    st.session_state.form_whatsapp = prop.get("whatsapp", prop.get("cliente_wa", ""))
    st.session_state.form_desconto = valor_float(prop.get("desconto", prop.get("desconto_valor", 0)))
    st.session_state.form_prazo = str(prop.get("prazo_dias", "10"))
    st.session_state.form_frete = str(prop.get("frete_tipo", "Retirada em Itatiba"))
    st.session_state.form_validade = str(prop.get("validade_dias", "5"))
    try:
        st.session_state.form_entrega = datetime.strptime(
            str(prop.get("data_entrega", "")), "%d/%m/%Y"
        ).date()
    except (TypeError, ValueError):
        st.session_state.form_entrega = date.today()

    st.session_state.editar_numero = None if duplicar else prop.get("numero_proposta")
    st.session_state.form_key += 1


def agendar_limpeza_formulario():
    """Limpa o formulário no próximo rerun, antes da criação dos widgets."""
    st.session_state._limpar_formulario_pendente = True


def aplicar_limpeza_formulario_pendente():
    if not st.session_state.pop("_limpar_formulario_pendente", False):
        return

    st.session_state.temp_itens = []
    st.session_state.editar_numero = None
    st.session_state.form_cliente = ""
    st.session_state.form_documento = ""
    st.session_state.form_whatsapp = ""
    st.session_state.form_desconto = 0.0
    st.session_state.form_entrega = date.today()
    st.session_state.form_prazo = "10"
    st.session_state.form_frete = "Retirada em Itatiba"
    st.session_state.form_validade = "5"
    st.session_state.form_key += 1


def remover_item_temp(indice):
    if 0 <= indice < len(st.session_state.temp_itens):
        st.session_state.temp_itens.pop(indice)
        st.rerun()


def data_entrega_segura(valor):
    try:
        return datetime.strptime(str(valor), "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def normalizar_texto_busca(prop):
    partes = [
        prop.get("numero_proposta", ""), prop.get("cliente_nome", ""),
        prop.get("whatsapp", prop.get("cliente_wa", "")),
        prop.get("documento", prop.get("cliente_cpf_cnpj", "")),
    ]
    partes.extend(item.get("produto", "") for item in prop.get("itens", []) or [])
    return " ".join(str(p) for p in partes).lower()


# --- CLIENTES (VERSÃO 3.1) ---
def carregar_clientes():
    """Carrega o cadastro de clientes do Supabase, com fallback em JSON local."""
    dados = load_document("clientes_db", ARQUIVO_CLIENTES, [])
    return dados if isinstance(dados, list) else []


def salvar_clientes(lista):
    if not isinstance(lista, list):
        raise ValueError("O cadastro de clientes precisa ser uma lista.")
    save_document("clientes_db", lista, ARQUIVO_CLIENTES)


def normalizar_texto_cliente(valor):
    return re.sub(r"\s+", " ", str(valor or "").strip())


def chave_cliente(nome, documento="", whatsapp=""):
    documento_limpo = re.sub(r"\D", "", str(documento or ""))
    whatsapp_limpo = re.sub(r"\D", "", str(whatsapp or ""))
    if documento_limpo:
        return f"doc:{documento_limpo}"
    if whatsapp_limpo:
        return f"wa:{whatsapp_limpo}"
    return f"nome:{normalizar_texto_cliente(nome).lower()}"


def sincronizar_clientes_do_historico():
    """Inclui no cadastro clientes encontrados nas propostas, sem apagar dados manuais."""
    clientes = carregar_clientes()
    por_chave = {
        chave_cliente(c.get("nome"), c.get("documento"), c.get("whatsapp")): c
        for c in clientes
        if normalizar_texto_cliente(c.get("nome"))
    }
    alterado = False
    for prop in carregar_historico():
        nome = normalizar_texto_cliente(prop.get("cliente_nome", prop.get("cliente", "")))
        if not nome:
            continue
        documento = normalizar_texto_cliente(prop.get("documento", prop.get("cliente_cpf_cnpj", "")))
        whatsapp = normalizar_texto_cliente(prop.get("whatsapp", prop.get("cliente_wa", "")))
        chave = chave_cliente(nome, documento, whatsapp)
        if chave not in por_chave:
            novo = {
                "id": f"CLI-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "nome": nome,
                "documento": documento,
                "whatsapp": whatsapp,
                "email": "",
                "aniversario": "",
                "observacoes": "",
                "origem": "Histórico de propostas",
                "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            clientes.append(novo)
            por_chave[chave] = novo
            alterado = True
        else:
            atual = por_chave[chave]
            if not atual.get("documento") and documento:
                atual["documento"] = documento
                alterado = True
            if not atual.get("whatsapp") and whatsapp:
                atual["whatsapp"] = whatsapp
                alterado = True
    if alterado:
        salvar_clientes(clientes)
    return clientes


def propostas_do_cliente(cliente):
    chave = chave_cliente(cliente.get("nome"), cliente.get("documento"), cliente.get("whatsapp"))
    propostas = []
    for prop in carregar_historico():
        pchave = chave_cliente(
            prop.get("cliente_nome", prop.get("cliente", "")),
            prop.get("documento", prop.get("cliente_cpf_cnpj", "")),
            prop.get("whatsapp", prop.get("cliente_wa", "")),
        )
        if pchave == chave:
            propostas.append(prop)
    return propostas


def carregar_cliente_no_orcamento(cliente):
    """Agenda o cliente para o formulário sem copiar itens de pedido anterior."""
    carregar_proposta_no_formulario({
        "cliente_nome": cliente.get("nome", ""),
        "documento": cliente.get("documento", ""),
        "whatsapp": cliente.get("whatsapp", ""),
        "itens": [],
        "desconto": 0.0,
        "prazo_dias": "10",
        "frete_tipo": "Retirada em Itatiba",
        "validade_dias": "5",
    }, duplicar=True)



# --- FLUXO DE PEDIDOS (VERSÃO 3.2.1) ---
STATUS_FLUXO = [
    "Pedido recebido",
    "Arte pendente",
    "Arte em desenvolvimento",
    "Aguardando aprovação",
    "Arte aprovada",
    "Pronto para produzir",
    "Em produção",
    "Montagem/acabamento",
    "Pronto",
    "Entregue",
]

PROCESSOS_FLUXO = [
    "Criação/ajuste de arte",
    "Impressão papelaria",
    "Papel de arroz",
    "Corte/laser",
    "Impressão 3D",
    "Balões",
    "Montagem",
    "Acabamento",
    "Separação",
    "Entrega/instalação",
    "Outro",
]

PRIORIDADES_FLUXO = ["Normal", "Alta", "Urgente"]


def carregar_producao():
    dados = load_document("producao_db", ARQUIVO_PRODUCAO, [])
    return dados if isinstance(dados, list) else []


def salvar_producao(lista):
    if not isinstance(lista, list):
        raise ValueError("O fluxo de pedidos precisa ser uma lista.")
    save_document("producao_db", lista, ARQUIVO_PRODUCAO)


def inferir_processos(produto, especificacoes=""):
    texto = f"{produto} {especificacoes}".lower()
    processos = []
    if any(x in texto for x in ["personaliz", "tema:", "nome:", "topo", "convite", "caixa", "tag"]):
        processos.append("Criação/ajuste de arte")
    if "papel de arroz" in texto or "papel arroz" in texto:
        processos.append("Papel de arroz")
    if any(x in texto for x in ["3d", "pla", "impressão 3d", "impressao 3d"]):
        processos.append("Impressão 3D")
    if any(x in texto for x in ["laser", "mdf", "acrílico", "acrilico"]):
        processos.append("Corte/laser")
    if any(x in texto for x in ["balão", "balao", "bubble", "balloon", "arco"]):
        processos.append("Balões")
    if any(x in texto for x in ["papelaria", "topo", "caixa", "adesivo", "tag", "convite", "banner", "faixa"]):
        processos.append("Impressão papelaria")
    if any(x in texto for x in ["montagem", "cachepô", "cachepo", "lembranc", "tubolata", "centro de mesa"]):
        processos.append("Montagem")
    if not processos:
        processos = ["Montagem", "Acabamento"]
    # mantém ordem e remove repetições
    return list(dict.fromkeys(processos))


def status_inicial_fluxo(produto, especificacoes=""):
    processos = inferir_processos(produto, especificacoes)
    return "Arte pendente" if "Criação/ajuste de arte" in processos else "Pronto para produzir"


def normalizar_status_fluxo(status, entregue=False):
    if entregue:
        return "Entregue"
    mapa_antigo = {
        "A fazer": "Pronto para produzir",
        "Em produção": "Em produção",
        "Aguardando aprovação": "Aguardando aprovação",
        "Pronto": "Pronto",
        "Entregue": "Entregue",
    }
    status = mapa_antigo.get(status, status)
    return status if status in STATUS_FLUXO else "Pedido recebido"


def adicionar_evento_timeline(tarefa, descricao):
    timeline = tarefa.get("timeline")
    if not isinstance(timeline, list):
        timeline = []
    timeline.append({
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "descricao": descricao,
    })
    tarefa["timeline"] = timeline[-50:]


def sincronizar_producao_com_propostas():
    """Cria um fluxo por item de proposta e preserva as alterações manuais."""
    tarefas = carregar_producao()
    existentes = {t.get("id"): t for t in tarefas}
    ids_ativos = set()
    alterado = False
    for prop in carregar_historico():
        numero = str(prop.get("numero_proposta", "SEM-NUMERO"))
        for indice, item in enumerate(prop.get("itens", []) or []):
            tarefa_id = f"{numero}::{indice}"
            ids_ativos.add(tarefa_id)
            produto = item.get("produto", "Produto não informado")
            especificacoes = item.get("especificacoes", "")
            processos = inferir_processos(produto, especificacoes)
            status_base = "Entregue" if prop.get("entregue", False) else status_inicial_fluxo(produto, especificacoes)
            base = {
                "id": tarefa_id,
                "numero_proposta": numero,
                "indice_item": indice,
                "cliente_nome": prop.get("cliente_nome", "Cliente não informado"),
                "whatsapp": prop.get("whatsapp", prop.get("cliente_wa", "")),
                "data_entrega": prop.get("data_entrega", ""),
                "produto": produto,
                "especificacoes": especificacoes,
                "quantidade": item.get("quantidade", 0),
                "status": status_base,
                "prioridade": "Normal",
                "processos": processos,
                "necessita_arte": "Criação/ajuste de arte" in processos,
                "observacao_interna": "",
                "timeline": [{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "descricao": "Pedido incluído no fluxo"}],
                "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            if tarefa_id not in existentes:
                tarefas.append(base)
                existentes[tarefa_id] = base
                alterado = True
            else:
                atual = existentes[tarefa_id]
                for campo in ["cliente_nome", "whatsapp", "data_entrega", "produto", "especificacoes", "quantidade"]:
                    if atual.get(campo) != base[campo]:
                        atual[campo] = base[campo]
                        alterado = True
                if not isinstance(atual.get("processos"), list):
                    atual["processos"] = processos
                    alterado = True
                if "necessita_arte" not in atual:
                    atual["necessita_arte"] = "Criação/ajuste de arte" in atual.get("processos", [])
                    alterado = True
                novo_status = normalizar_status_fluxo(atual.get("status"), prop.get("entregue", False))
                if atual.get("status") != novo_status:
                    atual["status"] = novo_status
                    alterado = True
                if not isinstance(atual.get("timeline"), list):
                    atual["timeline"] = []
                    alterado = True
    for tarefa in tarefas:
        ativa = tarefa.get("id") in ids_ativos
        if tarefa.get("ativa") != ativa:
            tarefa["ativa"] = ativa
            alterado = True
    if alterado:
        salvar_producao(tarefas)
    return tarefas


def salvar_tarefa_producao(tarefa_id, novos_dados):
    tarefas = carregar_producao()
    numero = novos_dados.get("numero_proposta")
    for tarefa in tarefas:
        if tarefa.get("id") == tarefa_id:
            status_anterior = normalizar_status_fluxo(tarefa.get("status"))
            tarefa.update(novos_dados)
            tarefa["status"] = normalizar_status_fluxo(tarefa.get("status"))
            tarefa["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            if status_anterior != tarefa["status"]:
                adicionar_evento_timeline(tarefa, f"Status alterado de {status_anterior} para {tarefa['status']}")
            else:
                adicionar_evento_timeline(tarefa, "Dados do fluxo atualizados")
            break
    salvar_producao(tarefas)
    if numero:
        relacionadas = [t for t in tarefas if t.get("numero_proposta") == numero and t.get("ativa", True)]
        if relacionadas and all(normalizar_status_fluxo(t.get("status")) == "Entregue" for t in relacionadas):
            alternar_status(numero, "entregue", True)


def classe_prazo_producao(data_txt, status):
    if normalizar_status_fluxo(status) == "Entregue":
        return "Concluído"
    data_item = data_entrega_segura(data_txt)
    if not data_item:
        return "Sem data"
    dias = (data_item - date.today()).days
    if dias < 0:
        return "Atrasado"
    if dias == 0:
        return "Hoje"
    if dias == 1:
        return "Amanhã"
    if dias <= 3:
        return "Próximos 3 dias"
    return "Futuro"

# --- CATÁLOGO INTEGRADO ---
def carregar_catalogo():
    """Carrega catálogo do Supabase, com fallback automático para JSON local."""
    dados = load_document("catalogo_db", ARQUIVO_CATALOGO, [])
    return dados if isinstance(dados, list) else []


def salvar_catalogo(lista):
    if not isinstance(lista, list):
        raise ValueError("O catálogo precisa ser uma lista de produtos.")
    save_document("catalogo_db", lista, ARQUIVO_CATALOGO)


def imagem_data_uri(path):
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower().replace(".", "") or "png"
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{get_image_base64(path)}"


def slug_html(texto):
    texto = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(texto).strip())
    return texto.strip("_") or "categoria"


def formatar_preco_catalogo(valor):
    texto = str(valor or "").strip().replace("R$", "").strip()
    try:
        numero = float(texto.replace(".", "").replace(",", ".")) if "," in texto else float(texto)
        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return f"R$ {texto}" if texto else "Preço sob consulta"


def gerar_html_catalogo(produtos, titulo="Catálogo Alphafest", mostrar_precos=True):
    produtos = produtos or []
    logo_b64, logo_ext = encontrar_logo_base64()
    ext = logo_ext.replace(".", "") or "png"
    if ext == "jpg":
        ext = "jpeg"
    logo_src = f"data:image/{ext};base64,{logo_b64}" if logo_b64 else ""

    categorias = []
    for produto in produtos:
        categoria = str(produto.get("Categoria", "Sem categoria")).strip() or "Sem categoria"
        if categoria not in categorias:
            categorias.append(categoria)

    cards_por_categoria = []
    for categoria in categorias:
        cards = []
        selecionados = [p for p in produtos if (str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria") == categoria]
        for produto in selecionados:
            nome = html.escape(str(produto.get("Nome", "Produto")))
            descricao = html.escape(str(produto.get("Descricao", "")))
            imagens = produto.get("Imagens", []) or []
            primeira = imagens[0] if imagens else ""
            src = primeira if str(primeira).startswith(("http://", "https://")) else imagem_data_uri(primeira)
            imagem_html = f'<img src="{src}" alt="{nome}" onclick="abrirImagem(this.src)">' if src else '<div class="sem-imagem">Sem imagem</div>'
            preco_html = f'<div class="preco">{html.escape(formatar_preco_catalogo(produto.get("Preco")))}</div>' if mostrar_precos else ''
            msg = quote(f"Olá! Gostaria de informações sobre: {produto.get('Nome', 'produto')}")
            cards.append(f'<article class="card">{imagem_html}<div class="card-body"><h3>{nome}</h3><p>{descricao}</p>{preco_html}<a class="btn" target="_blank" href="https://wa.me/5511972949533?text={msg}">Consultar no WhatsApp</a></div></article>')
        cards_por_categoria.append(f'<section id="{slug_html(categoria)}"><h2>{html.escape(categoria)}</h2><div class="grid">{"".join(cards)}</div></section>')

    links = "".join(f'<a href="#{slug_html(c)}">{html.escape(c)}</a>' for c in categorias)
    logo_tag = f'<img class="logo" src="{logo_src}">' if logo_src else ''
    corpo = ''.join(cards_por_categoria) if cards_por_categoria else '<div class="intro">Nenhum produto selecionado.</div>'
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titulo)}</title><style>
    *{{box-sizing:border-box}} body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f5f6f8;color:#20252b}} .layout{{display:flex;min-height:100vh}} aside{{width:260px;background:#18222d;color:#fff;padding:24px 18px;position:sticky;top:0;height:100vh;overflow:auto}} .logo{{max-width:180px;max-height:95px;display:block;margin:0 auto 18px;object-fit:contain}} aside h1{{font-size:20px;text-align:center;margin:8px 0 22px}} nav a{{display:block;color:#eef2f7;text-decoration:none;padding:11px 10px;border-bottom:1px solid rgba(255,255,255,.12)}} main{{flex:1;padding:32px;max-width:1400px}} .intro{{background:#fff;padding:22px;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.06);margin-bottom:28px}} section{{scroll-margin-top:20px;margin-bottom:42px}} section h2{{border-bottom:3px solid #202b36;padding-bottom:9px}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:22px}} .card{{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 5px 18px rgba(0,0,0,.08);display:flex;flex-direction:column}} .card img,.sem-imagem{{width:100%;height:220px;object-fit:cover;background:#e9edf2;display:flex;align-items:center;justify-content:center;cursor:pointer}} .card-body{{padding:18px;display:flex;flex-direction:column;flex:1}} .card h3{{margin:0 0 10px}} .card p{{line-height:1.45;flex:1}} .preco{{font-size:22px;font-weight:800;margin:12px 0;color:#147a42}} .btn{{display:block;text-align:center;background:#25d366;color:#fff;text-decoration:none;padding:12px;border-radius:9px;font-weight:800}} footer{{text-align:center;color:#6b7280;padding:30px}} #modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:999;align-items:center;justify-content:center}} #modal img{{max-width:92vw;max-height:90vh}} @media(max-width:760px){{.layout{{display:block}}aside{{width:100%;height:auto;position:relative}}main{{padding:18px}}nav{{display:flex;gap:5px;overflow:auto}}nav a{{white-space:nowrap;border:1px solid rgba(255,255,255,.18);border-radius:8px}}}}
    </style></head><body><div class="layout"><aside>{logo_tag}<h1>{html.escape(titulo)}</h1><nav>{links}</nav></aside><main><div class="intro"><h1>{html.escape(titulo)}</h1><p>Seleção preparada pela Alphafest Itatiba. Consulte disponibilidade, personalização e prazo pelo WhatsApp.</p></div>{corpo}<footer>Alphafest Itatiba - O poder de estar presente em cada presente...</footer></main></div><div id="modal" onclick="this.style.display='none'"><img id="modal-img"></div><script>function abrirImagem(src){{document.getElementById('modal-img').src=src;document.getElementById('modal').style.display='flex';}}</script></body></html>'''


def salvar_upload_catalogo(upload):
    """Salva a imagem no Supabase Storage, com fallback para a pasta uploads."""
    return upload_catalog_image(upload, PASTA_UPLOADS)


# --- SIDEBAR ---
with st.sidebar:
    logo_sidebar_b64, _ = encontrar_logo_base64()
    if logo_sidebar_b64:
        try:
            st.image(base64.b64decode(logo_sidebar_b64), width=150)
        except Exception:
            pass
    st.markdown("### ALPHAFEST")
    st.caption("Personalizados & Balões")
    st.divider()
    st.subheader("🔒 Painel de Segurança")
    conectado, mensagem_banco = connection_test()
    if conectado:
        st.success("🟢 Banco online conectado")
    else:
        st.warning(f"🟡 {mensagem_banco}")
    h_atual = carregar_historico()
    st.download_button("📥 BAIXAR BACKUP", data=json.dumps(h_atual, ensure_ascii=False, indent=4), file_name="backup_historico.json", mime="application/json", type="primary", use_container_width=True)
    st.download_button("📦 BACKUP DO CATÁLOGO", data=json.dumps(carregar_catalogo(), ensure_ascii=False, indent=4), file_name="backup_catalogo.json", mime="application/json", use_container_width=True)
    st.download_button("👥 BACKUP DE CLIENTES", data=json.dumps(carregar_clientes(), ensure_ascii=False, indent=4), file_name="backup_clientes.json", mime="application/json", use_container_width=True)
    backup_enviado = st.file_uploader("💾 RESTAURAR BACKUP", type=["json"], key="restaurar_historico")
    if backup_enviado is not None and st.button("Restaurar agora", use_container_width=True):
        try:
            restaurado = json.load(backup_enviado)
            if not isinstance(restaurado, list):
                raise ValueError("O backup precisa conter uma lista de propostas.")
            salvar_historico_completo(restaurado)
            st.success("Backup restaurado.")
            st.rerun()
        except Exception as erro:
            st.error(f"Não foi possível restaurar: {erro}")
    st.divider()
    st.caption("📌 Sistema de Orçamentos e Catálogo")
    st.caption(f"Versão {VERSAO_APP}")
    st.caption("O poder de estar presente em cada presente...")

# --- ESTADO DO FORMULÁRIO ---
def iniciar_estado(nome, valor):
    if nome not in st.session_state:
        st.session_state[nome] = valor

iniciar_estado("form_cliente", "")
iniciar_estado("form_documento", "")
iniciar_estado("form_whatsapp", "")
iniciar_estado("form_desconto", 0.0)
iniciar_estado("form_entrega", date.today())
iniciar_estado("form_prazo", "10")
iniciar_estado("form_frete", "Retirada em Itatiba")
iniciar_estado("form_validade", "5")
iniciar_estado("editar_numero", None)
iniciar_estado("alerta_proposta_numero", None)

# Deve acontecer antes da criação dos widgets vinculados às chaves form_*.
aplicar_limpeza_formulario_pendente()
aplicar_proposta_pendente_no_formulario()

# --- ALERTAS DE ENTREGA MELHORADOS ---
hoje = date.today()
alertas_hoje, alertas_atrasados, alertas_proximos = [], [], []
for p in carregar_historico():
    entrega = data_entrega_segura(p.get("data_entrega"))
    if not entrega or p.get("entregue", False):
        continue
    dias = (entrega - hoje).days
    if dias < 0:
        alertas_atrasados.append((p, abs(dias)))
    elif dias == 0:
        alertas_hoje.append(p)
    elif dias <= 3:
        alertas_proximos.append((p, dias))

def renderizar_alertas_clicaveis(titulo, alertas, tipo, prefixo):
    if not alertas:
        return
    if tipo == "atrasado":
        st.error(titulo)
        pares = [(p, f"{dias} dia(s) em atraso") for p, dias in alertas]
    elif tipo == "hoje":
        st.warning(titulo)
        pares = [(p, "Entrega hoje") for p in alertas]
    else:
        st.info(titulo)
        pares = [(p, f"Entrega em {dias} dia(s)") for p, dias in alertas]

    for p, situacao in pares:
        numero_alerta = p.get("numero_proposta", "SEM-NÚMERO")
        cliente_alerta = p.get("cliente_nome", "Cliente não informado")
        c1, c2 = st.columns([7, 1])
        c1.write(f"**{numero_alerta} — {cliente_alerta}** · {situacao}")
        if c2.button("Abrir", key=f"abrir_alerta_{prefixo}_{tipo}_{numero_alerta}", use_container_width=True):
            st.session_state.alerta_proposta_numero = numero_alerta
            st.rerun()

def renderizar_painel_alertas(prefixo):
    renderizar_alertas_clicaveis("🚨 Entregas atrasadas", alertas_atrasados, "atrasado", prefixo)
    renderizar_alertas_clicaveis("⚠️ Entregas para hoje", alertas_hoje, "hoje", prefixo)
    renderizar_alertas_clicaveis("📅 Próximas entregas", alertas_proximos, "proximo", prefixo)

    if not st.session_state.alerta_proposta_numero:
        return

    proposta_alerta = next(
        (p for p in carregar_historico() if p.get("numero_proposta") == st.session_state.alerta_proposta_numero),
        None,
    )
    if not proposta_alerta:
        st.session_state.alerta_proposta_numero = None
        return

    _, _, total_alerta = calcular_valores_proposta(proposta_alerta)
    with st.expander(
        f"🔎 Proposta {proposta_alerta.get('numero_proposta')} — {proposta_alerta.get('cliente_nome')}",
        expanded=True,
    ):
        st.write(f"**Entrega:** {proposta_alerta.get('data_entrega', 'Não informada')}")
        st.write(f"**WhatsApp:** {proposta_alerta.get('whatsapp', proposta_alerta.get('cliente_wa', 'Não informado')) or 'Não informado'}")
        st.write("**Itens:**")
        for item in proposta_alerta.get("itens", []) or []:
            st.write(
                f"• {item.get('produto', 'Produto')} — Qtd: {item.get('quantidade', 0)} — "
                f"R$ {valor_float(item.get('valor_unitario')):,.2f}"
            )
            if item.get("especificacoes"):
                st.caption(item.get("especificacoes"))
        st.write(
            f"**Total:** R$ {total_alerta:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        a1, a2, a3 = st.columns(3)
        if a1.button("✏️ Editar proposta", key=f"editar_alerta_{prefixo}_{proposta_alerta.get('numero_proposta')}"):
            carregar_proposta_no_formulario(proposta_alerta, duplicar=False)
            st.session_state.alerta_proposta_numero = None
            st.rerun()
        a2.download_button(
            "📄 Baixar HTML",
            gerar_html(proposta_alerta),
            file_name=f"{proposta_alerta.get('numero_proposta', 'proposta')}.html",
            mime="text/html",
            key=f"html_alerta_{prefixo}_{proposta_alerta.get('numero_proposta')}",
        )
        if a3.button("Fechar", key=f"fechar_alerta_{prefixo}_{proposta_alerta.get('numero_proposta')}"):
            st.session_state.alerta_proposta_numero = None
            st.rerun()

mensagem_sucesso = st.session_state.pop("_mensagem_sucesso_pendente", None)
if mensagem_sucesso:
    st.success(mensagem_sucesso)

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["➕ Novo Orçamento", "📋 Histórico", "🎯 Fluxo de Pedidos", "📊 Relatórios", "📦 Catálogo", "👥 Clientes"])

with aba1:
    # Cabeçalho centralizado da área de orçamento.
    logo_aba1_b64, _ = encontrar_logo_base64()
    if logo_aba1_b64:
        col_logo_esq, col_logo_centro, col_logo_dir = st.columns([1, 1, 1])
        with col_logo_centro:
            try:
                st.image(base64.b64decode(logo_aba1_b64), use_container_width=True)
            except Exception:
                pass
    st.markdown(
        "<h1 style='text-align:center; margin-bottom:0;'>📄 ORÇAMENTOS ALPHAFEST</h1>"
        "<p style='text-align:center; margin-top:4px; color:#6b7280;'>"
        "Personalizados • Impressão 3D • Papelaria</p>",
        unsafe_allow_html=True,
    )
    renderizar_painel_alertas("novo_orcamento")

    if st.session_state.editar_numero:
        st.info(f"✏️ Editando a proposta {st.session_state.editar_numero}")
        if st.button("Cancelar edição"):
            agendar_limpeza_formulario()
            st.rerun()

    nome = st.text_input("Nome / Razão Social", key="form_cliente")
    c1, c2 = st.columns(2)
    doc = c1.text_input("CPF / CNPJ", key="form_documento")
    wa = c2.text_input("WhatsApp", key="form_whatsapp")

    prod = st.text_input("Produto", key=f"produto_novo_{st.session_state.form_key}")
    with st.expander("🎨 Personalização & Especificações", expanded=True):
        c1, c2 = st.columns(2)
        et = c1.text_input("Tema / Ocasião", key=f"tema_{st.session_state.form_key}")
        en = c1.text_input("Nome(s) Personalizado(s)", key=f"nome_item_{st.session_state.form_key}")
        ec = c1.text_input("Cor / Material", key=f"cor_{st.session_state.form_key}")
        ei = c2.text_input("Idade / Data do Evento", key=f"idade_{st.session_state.form_key}")
        eg = c2.text_input("Outros Detalhes", key=f"obs_item_{st.session_state.form_key}")

    q = st.number_input("Qtd", min_value=1, value=1, key=f"qtd_{st.session_state.form_key}")
    v = st.number_input("Valor Unitário (R$)", value=0.0, step=0.5, key=f"valor_{st.session_state.form_key}")

    if st.button("➕ Adicionar Item"):
        if not prod.strip():
            st.warning("Informe o produto antes de adicionar.")
        else:
            detalhes = f"Tema: {et} | Nome: {en} | Idade: {ei} | Cor: {ec} | Obs: {eg}"
            st.session_state.temp_itens.append({"produto": prod, "especificacoes": detalhes, "quantidade": q, "valor_unitario": v})
            st.session_state.form_key += 1
            st.rerun()

    if st.session_state.temp_itens:
        st.write("📋 **Itens da proposta:**")
        for idx, item in enumerate(st.session_state.temp_itens):
            col_info, col_remover = st.columns([8, 1])
            col_info.write(f"**{idx + 1}. {item.get('produto')}** — Qtd: {item.get('quantidade')} — R$ {valor_float(item.get('valor_unitario')):,.2f}")
            col_info.caption(item.get("especificacoes", ""))
            if col_remover.button("🗑️", key=f"remover_item_{idx}", help="Remover item"):
                remover_item_temp(idx)

        st.divider()
        c1, c2, c3 = st.columns(3)
        desc = c1.number_input("Desconto (R$)", min_value=0.0, step=0.5, key="form_desconto")
        dt_entrega = c2.date_input("📅 Data Entrega", key="form_entrega")
        prazo = c3.text_input("Prazo de Produção (dias úteis)", key="form_prazo")
        c4, c5 = st.columns(2)
        frete = c4.text_input("Frete/Entrega", key="form_frete")
        validade = c5.text_input("Validade (dias corridos)", key="form_validade")

        subtotal = sum(valor_float(i['quantidade']) * valor_float(i['valor_unitario']) for i in st.session_state.temp_itens)
        total = max(subtotal - desc, 0.0)
        st.metric("Valor total", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        rotulo_salvar = "💾 SALVAR ALTERAÇÕES" if st.session_state.editar_numero else "🚀 SALVAR PROPOSTA"
        if st.button(rotulo_salvar, type="primary"):
            numero = st.session_state.editar_numero or f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            antigo = {}
            if st.session_state.editar_numero:
                antigo = next((p for p in carregar_historico() if p.get("numero_proposta") == numero), {})

            dados = {
                **antigo,
                "numero_proposta": numero,
                "data_geracao": antigo.get("data_geracao", datetime.now().strftime("%d/%m/%Y")),
                "data_entrega": dt_entrega.strftime("%d/%m/%Y"),
                "cliente_nome": nome.strip(),
                "documento": doc.strip(),
                "whatsapp": wa.strip(),
                # Mantém também os nomes antigos para compatibilidade com registros e telas antigas.
                "cliente_cpf_cnpj": doc.strip(),
                "cliente_wa": wa.strip(),
                "itens": list(st.session_state.temp_itens),
                "subtotal": subtotal,
                "desconto": desc,
                "desconto_valor": desc,
                "valor_total": total,
                "prazo_dias": prazo,
                "frete_tipo": frete,
                "validade_dias": validade,
                "pago": antigo.get("pago", False),
                "entregue": antigo.get("entregue", False),
            }

            if st.session_state.editar_numero:
                atualizar_proposta(numero, dados)
            else:
                h = carregar_historico()
                h.insert(0, dados)
                salvar_historico_completo(h)

            agendar_limpeza_formulario()
            st.session_state._mensagem_sucesso_pendente = "Proposta salva com sucesso."
            st.rerun()

with aba2:
    renderizar_painel_alertas("historico")

    historico = carregar_historico()
    busca = st.text_input("🔎 Pesquisar por cliente, proposta, telefone ou produto")
    if busca.strip():
        termo = busca.strip().lower()
        historico = [p for p in historico if termo in normalizar_texto_busca(p)]
    st.caption(f"{len(historico)} proposta(s) encontrada(s)")

    for prop in historico:
        num_p = prop.get("numero_proposta", "SEM-NÚMERO")
        cliente_p = prop.get("cliente_nome", "Cliente não informado")
        subtotal_p, desconto_p, total_p = calcular_valores_proposta(prop)
        pago_p = bool(prop.get("pago", False))
        entregue_p = bool(prop.get("entregue", False))
        proposta_fechada = pago_p and entregue_p

        if proposta_fechada:
            status_txt = "✅ FECHADA"
        else:
            status = []
            if pago_p:
                status.append("Pago")
            if entregue_p:
                status.append("Entregue")
            status_txt = " • ".join(status) if status else "Pendente"

        with st.expander(f"{num_p} - {cliente_p} | R$ {total_p:,.2f} | {status_txt}"):
            if proposta_fechada:
                st.success("✅ Pedido fechado: pagamento recebido e entrega concluída.")
            st.write(f"📅 **Entrega:** {prop.get('data_entrega', 'Não informada')}")
            whatsapp_hist = prop.get("whatsapp", prop.get("cliente_wa", "")) or "Não informado"
            documento_hist = prop.get("documento", prop.get("cliente_cpf_cnpj", "")) or "Não informado"
            st.write(f"📱 **WhatsApp:** {whatsapp_hist}")
            st.write(f"🪪 **CPF/CNPJ:** {documento_hist}")
            for item in prop.get('itens', []):
                st.write(f"• {item.get('produto', '')} (Qtd: {item.get('quantidade', 0)})")

            c1, c2 = st.columns(2)
            c1.link_button("📱 Enviar WhatsApp", f"https://wa.me/?text={quote(formatar_msg_whatsapp(prop))}", use_container_width=True)
            c2.download_button("📄 Gerar HTML", gerar_html(prop), file_name=f"{num_p}.html", mime="text/html", use_container_width=True)

            c3, c4, c5 = st.columns(3)
            if c3.button("✏️ Editar", key=f"editar_{num_p}", use_container_width=True):
                carregar_proposta_no_formulario(prop, duplicar=False)
                st.rerun()
            if c4.button("📋 Duplicar pedido", key=f"duplicar_{num_p}", use_container_width=True):
                carregar_proposta_no_formulario(prop, duplicar=True)
                st.rerun()
            if c5.button("🗑️ Excluir", key=f"del_{num_p}", use_container_width=True):
                excluir_proposta(num_p)

            s1, s2 = st.columns(2)
            s1.checkbox("Pago", value=prop.get("pago", False), key=f"p_{num_p}", on_change=alternar_status, args=(num_p, "pago", not prop.get("pago", False)))
            s2.checkbox("Entregue", value=prop.get("entregue", False), key=f"e_{num_p}", on_change=alternar_status, args=(num_p, "entregue", not prop.get("entregue", False)))


with aba3:
    st.markdown("<h2 style='text-align:center;'>🎯 Fluxo de Pedidos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#6b7280;'>Mostra o que precisa ser feito agora, da arte até a entrega.</p>", unsafe_allow_html=True)

    tarefas = sincronizar_producao_com_propostas()
    tarefas_ativas = [t for t in tarefas if t.get("ativa", True)]

    atrasados = sum(1 for t in tarefas_ativas if classe_prazo_producao(t.get("data_entrega"), t.get("status")) == "Atrasado")
    hoje_fluxo = sum(1 for t in tarefas_ativas if classe_prazo_producao(t.get("data_entrega"), t.get("status")) == "Hoje")
    aprovacao = sum(1 for t in tarefas_ativas if normalizar_status_fluxo(t.get("status")) == "Aguardando aprovação")
    produzir = sum(1 for t in tarefas_ativas if normalizar_status_fluxo(t.get("status")) in ["Arte aprovada", "Pronto para produzir"])
    prontos = sum(1 for t in tarefas_ativas if normalizar_status_fluxo(t.get("status")) == "Pronto")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🚨 Atrasados", atrasados)
    m2.metric("⚠️ Para hoje", hoje_fluxo)
    m3.metric("🟡 Aguardando aprovação", aprovacao)
    m4.metric("🔵 Prontos para produzir", produzir)
    m5.metric("✅ Prontos", prontos)

    visao, artes, producao, entregas = st.tabs(["📌 Visão geral", "🎨 Artes", "⚙️ Produção", "📦 Prontos/entregas"])

    def renderizar_cartoes_fluxo(lista, prefixo):
        if not lista:
            st.info("Nenhum item nesta etapa.")
            return
        ordem_prioridade = {"Urgente": 0, "Alta": 1, "Normal": 2}
        lista = sorted(lista, key=lambda t: (
            data_entrega_segura(t.get("data_entrega")) or date.max,
            ordem_prioridade.get(t.get("prioridade", "Normal"), 9),
            str(t.get("cliente_nome", "")),
        ))
        for tarefa in lista:
            tid = tarefa.get("id")
            status_atual = normalizar_status_fluxo(tarefa.get("status"))
            prazo = classe_prazo_producao(tarefa.get("data_entrega"), status_atual)
            icone = {"Atrasado": "🚨", "Hoje": "⚠️", "Amanhã": "📅", "Concluído": "✅"}.get(prazo, "📌")
            titulo = f"{icone} {tarefa.get('data_entrega') or 'Sem data'} | {tarefa.get('cliente_nome')} | {tarefa.get('produto')}"
            with st.expander(titulo, expanded=(prazo in ["Atrasado", "Hoje"])):
                st.write(f"**Pedido:** {tarefa.get('numero_proposta')}  •  **Qtd.:** {tarefa.get('quantidade')}  •  **Status:** {status_atual}")
                if tarefa.get("whatsapp"):
                    st.write(f"**WhatsApp:** {tarefa.get('whatsapp')}")
                st.write(f"**Detalhes:** {tarefa.get('especificacoes') or 'Não informado'}")
                st.caption(f"Prazo: {prazo} • Atualizado em: {tarefa.get('atualizado_em', '—')}")

                c1, c2 = st.columns(2)
                novo_status = c1.selectbox("Etapa atual", STATUS_FLUXO, index=STATUS_FLUXO.index(status_atual), key=f"fluxo_status_{prefixo}_{tid}")
                prioridade_atual = tarefa.get("prioridade", "Normal") if tarefa.get("prioridade", "Normal") in PRIORIDADES_FLUXO else "Normal"
                prioridade = c2.selectbox("Prioridade", PRIORIDADES_FLUXO, index=PRIORIDADES_FLUXO.index(prioridade_atual), key=f"fluxo_prio_{prefixo}_{tid}")

                processos_atuais = [p for p in tarefa.get("processos", []) if p in PROCESSOS_FLUXO]
                processos = st.multiselect("Processos necessários", PROCESSOS_FLUXO, default=processos_atuais, key=f"fluxo_proc_{prefixo}_{tid}")
                necessita_arte = st.checkbox("Necessita criação ou ajuste de arte", value=bool(tarefa.get("necessita_arte", False)), key=f"fluxo_arte_{prefixo}_{tid}")
                observacao = st.text_area("Observação interna", value=str(tarefa.get("observacao_interna", "")), key=f"fluxo_obs_{prefixo}_{tid}")

                b1, b2 = st.columns(2)
                if b1.button("💾 Salvar andamento", key=f"salvar_fluxo_{prefixo}_{tid}", type="primary", use_container_width=True):
                    salvar_tarefa_producao(tid, {
                        "numero_proposta": tarefa.get("numero_proposta"),
                        "status": novo_status,
                        "prioridade": prioridade,
                        "processos": processos,
                        "necessita_arte": necessita_arte,
                        "observacao_interna": observacao.strip(),
                    })
                    st.success("Andamento atualizado.")
                    st.rerun()
                if b2.button("📋 Selecionar pedido no histórico", key=f"hist_fluxo_{prefixo}_{tid}", use_container_width=True):
                    st.session_state.alerta_proposta_numero = tarefa.get("numero_proposta")
                    st.info("A proposta foi selecionada. Abra a aba Histórico para consultá-la.")

                timeline = tarefa.get("timeline", [])
                if timeline:
                    with st.expander("🕒 Linha do tempo"):
                        for evento in reversed(timeline[-12:]):
                            st.write(f"**{evento.get('data', '')}** — {evento.get('descricao', '')}")

    with visao:
        f1, f2, f3 = st.columns(3)
        prazo_filtro = f1.selectbox("Prazo", ["Todos", "Atrasado", "Hoje", "Amanhã", "Próximos 3 dias", "Futuro", "Sem data", "Concluído"], key="fluxo_prazo")
        status_filtro = f2.selectbox("Etapa", ["Todas"] + STATUS_FLUXO, key="fluxo_etapa")
        prioridade_filtro = f3.selectbox("Prioridade", ["Todas"] + PRIORIDADES_FLUXO, key="fluxo_prioridade")
        busca = st.text_input("🔎 Buscar por cliente, pedido, produto, tema, nome ou detalhes", key="fluxo_busca").strip().lower()
        filtradas = []
        for t in tarefas_ativas:
            status = normalizar_status_fluxo(t.get("status"))
            prazo = classe_prazo_producao(t.get("data_entrega"), status)
            texto = " ".join(str(t.get(k, "")) for k in ["cliente_nome", "numero_proposta", "produto", "especificacoes", "whatsapp"]).lower()
            if prazo_filtro != "Todos" and prazo != prazo_filtro: continue
            if status_filtro != "Todas" and status != status_filtro: continue
            if prioridade_filtro != "Todas" and t.get("prioridade", "Normal") != prioridade_filtro: continue
            if busca and busca not in texto: continue
            filtradas.append(t)
        st.caption(f"{len(filtradas)} item(ns) encontrado(s).")
        renderizar_cartoes_fluxo(filtradas, "geral")

    with artes:
        lista_artes = [t for t in tarefas_ativas if bool(t.get("necessita_arte")) and normalizar_status_fluxo(t.get("status")) in ["Pedido recebido", "Arte pendente", "Arte em desenvolvimento", "Aguardando aprovação", "Arte aprovada"]]
        renderizar_cartoes_fluxo(lista_artes, "artes")

    with producao:
        lista_producao = [t for t in tarefas_ativas if normalizar_status_fluxo(t.get("status")) in ["Arte aprovada", "Pronto para produzir", "Em produção", "Montagem/acabamento"]]
        renderizar_cartoes_fluxo(lista_producao, "producao")

    with entregas:
        lista_entregas = [t for t in tarefas_ativas if normalizar_status_fluxo(t.get("status")) in ["Pronto", "Entregue"]]
        renderizar_cartoes_fluxo(lista_entregas, "entregas")


with aba4:
    h = carregar_historico()
    if not h:
        st.info("📊 Ainda não existem propostas cadastradas para gerar relatórios.")
    else:
        registros = []
        produtos = []
        for p in h:
            subtotal, desconto, total = calcular_valores_proposta(p)
            registros.append({
                "numero_proposta": p.get("numero_proposta", ""),
                "cliente_nome": p.get("cliente_nome", "Não informado") or "Não informado",
                "data_geracao": p.get("data_geracao", ""),
                "data_entrega": p.get("data_entrega", ""),
                "valor_total": total,
                "pago": bool(p.get("pago", False)),
                "entregue": bool(p.get("entregue", False)),
            })
            for item in p.get("itens", []) or []:
                qtd = valor_float(item.get("quantidade"))
                unit = valor_float(item.get("valor_unitario"))
                produtos.append({"produto": str(item.get("produto", "Não informado")).strip() or "Não informado", "quantidade": qtd, "faturamento": qtd * unit, "pago": bool(p.get("pago", False))})

        df = pd.DataFrame(registros)
        df["Data"] = pd.to_datetime(df["data_geracao"], dayfirst=True, errors="coerce")
        total_orcado = float(df["valor_total"].sum())
        total_recebido = float(df.loc[df["pago"], "valor_total"].sum())
        total_pendente = total_orcado - total_recebido
        ticket_medio = total_orcado / len(df) if len(df) else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📝 Propostas", len(df))
        m2.metric("💰 Total Orçado", f"R$ {total_orcado:,.2f}")
        m3.metric("✅ Recebido", f"R$ {total_recebido:,.2f}")
        m4.metric("⏳ A Receber", f"R$ {total_pendente:,.2f}")
        st.metric("🎯 Ticket médio", f"R$ {ticket_medio:,.2f}")

        periodo = st.selectbox("Período de agrupamento", ["Dia", "Semana", "Mês", "Ano"])
        df_data = df.dropna(subset=["Data"]).copy()
        if periodo == "Dia": df_data["Periodo"] = df_data["Data"].dt.strftime("%d/%m/%Y")
        elif periodo == "Semana": df_data["Periodo"] = df_data["Data"].dt.to_period("W").apply(lambda x: x.start_time)
        elif periodo == "Mês": df_data["Periodo"] = df_data["Data"].dt.to_period("M").dt.to_timestamp()
        else: df_data["Periodo"] = df_data["Data"].dt.to_period("Y").dt.to_timestamp()

        if not df_data.empty:
            vendas = df_data.groupby("Periodo", as_index=False)["valor_total"].sum()
            st.subheader("📈 Orçamentos por período")
            st.line_chart(vendas.set_index("Periodo")["valor_total"], use_container_width=True)

        st.subheader("👥 Clientes com maior valor orçado")
        clientes = df.groupby("cliente_nome", as_index=False)["valor_total"].sum().sort_values("valor_total", ascending=False).head(15)
        grafico_clientes = criar_grafico_profissional(clientes, "cliente_nome", "valor_total", "Total por cliente", horizontal=True)
        if grafico_clientes: st.altair_chart(grafico_clientes, use_container_width=True)

        if produtos:
            df_prod = pd.DataFrame(produtos)
            ranking = df_prod.groupby("produto", as_index=False).agg(quantidade=("quantidade", "sum"), faturamento=("faturamento", "sum")).sort_values("quantidade", ascending=False).head(15)
            st.subheader("🏆 Produtos mais vendidos")
            grafico_prod = criar_grafico_profissional(ranking, "produto", "quantidade", "Quantidade por produto", horizontal=True, formato=".0f")
            if grafico_prod: st.altair_chart(grafico_prod, use_container_width=True)
            st.dataframe(ranking, use_container_width=True, hide_index=True)

            pagos = df_prod[df_prod["pago"]].groupby("produto", as_index=False).agg(quantidade=("quantidade", "sum"), faturamento=("faturamento", "sum")).sort_values("faturamento", ascending=False).head(15)
            st.subheader("✅ Produtos efetivamente pagos")
            if not pagos.empty:
                grafico_pagos = criar_grafico_profissional(pagos, "produto", "faturamento", "Faturamento de produtos pagos", horizontal=True)
                if grafico_pagos: st.altair_chart(grafico_pagos, use_container_width=True)
                st.dataframe(pagos, use_container_width=True, hide_index=True)
            else:
                st.info("Ainda não existem produtos em propostas marcadas como pagas.")



with aba5:
    st.header("📦 Catálogo Alphafest")
    st.caption("Cadastro interno e geração de seleções específicas para consulta do cliente.")
    catalogo = carregar_catalogo()
    if "catalogo_edit_index" not in st.session_state:
        st.session_state.catalogo_edit_index = None
    aba_cad, aba_lista, aba_cliente = st.tabs(["➕ Cadastrar / Editar", "📋 Produtos", "📤 Catálogo para cliente"])

    with aba_cad:
        indice_edicao = st.session_state.catalogo_edit_index
        item_edicao = catalogo[indice_edicao] if indice_edicao is not None and 0 <= indice_edicao < len(catalogo) else None
        st.subheader("✏️ Editar produto" if item_edicao else "➕ Adicionar produto")
        c1, c2 = st.columns(2)
        categoria_cat = c1.text_input("Categoria", value=item_edicao.get("Categoria", "") if item_edicao else "", key=f"cat_categoria_{indice_edicao}")
        nome_cat = c1.text_input("Nome do produto", value=item_edicao.get("Nome", "") if item_edicao else "", key=f"cat_nome_{indice_edicao}")
        descricao_cat = c1.text_area("Descrição", value=item_edicao.get("Descricao", "") if item_edicao else "", key=f"cat_desc_{indice_edicao}")
        preco_cat = c2.text_input("Preço", value=str(item_edicao.get("Preco", "")) if item_edicao else "", key=f"cat_preco_{indice_edicao}")
        urls_cat = c2.text_area("URLs de imagens (uma por linha)", value="\n".join([x for x in (item_edicao.get("Imagens", []) if item_edicao else []) if str(x).startswith("http")]), key=f"cat_urls_{indice_edicao}")
        foto_cat = c2.file_uploader("Enviar foto", type=["png", "jpg", "jpeg", "webp"], key=f"cat_foto_{indice_edicao}")
        b1, b2 = st.columns(2)
        if b1.button("💾 Salvar produto", type="primary", use_container_width=True):
            if not nome_cat.strip() or not categoria_cat.strip():
                st.warning("Informe pelo menos o nome e a categoria.")
            else:
                imagens = [u.strip() for u in urls_cat.splitlines() if u.strip()]
                if item_edicao:
                    imagens.extend([x for x in item_edicao.get("Imagens", []) if not str(x).startswith("http")])
                caminho_novo = salvar_upload_catalogo(foto_cat)
                if caminho_novo:
                    imagens.insert(0, caminho_novo)
                registro = {"Nome": nome_cat.strip(), "Categoria": categoria_cat.strip(), "Imagens": imagens, "Descricao": descricao_cat.strip(), "Preco": preco_cat.strip()}
                if item_edicao:
                    catalogo[indice_edicao] = registro
                else:
                    catalogo.append(registro)
                salvar_catalogo(catalogo)
                st.session_state.catalogo_edit_index = None
                st.success("Produto salvo.")
                st.rerun()
        if item_edicao and b2.button("Cancelar edição", use_container_width=True):
            st.session_state.catalogo_edit_index = None
            st.rerun()

    with aba_lista:
        termo_cat = st.text_input("🔎 Pesquisar produto ou categoria", key="pesquisa_catalogo").strip().lower()
        filtrados = [(i,p) for i,p in enumerate(catalogo) if not termo_cat or termo_cat in f"{p.get('Nome','')} {p.get('Categoria','')} {p.get('Descricao','')}".lower()]
        st.write(f"**{len(filtrados)} produto(s)**")
        for i, produto_cat in filtrados:
            with st.container(border=True):
                cimg, cinfo, cacoes = st.columns([1,5,2])
                imgs = produto_cat.get("Imagens", []) or []
                if imgs:
                    try:
                        cimg.image(imgs[0], width=100)
                    except Exception:
                        cimg.write("📷")
                else:
                    cimg.write("📷")
                cinfo.markdown(f"### {produto_cat.get('Nome','Produto')}")
                cinfo.write(f"**Categoria:** {produto_cat.get('Categoria','')}  |  **Preço:** {formatar_preco_catalogo(produto_cat.get('Preco'))}")
                cinfo.caption(produto_cat.get("Descricao", ""))
                if cacoes.button("✏️ Editar", key=f"cat_editar_{i}", use_container_width=True):
                    st.session_state.catalogo_edit_index = i
                    st.rerun()
                if cacoes.button("🗑️ Excluir", key=f"cat_excluir_{i}", use_container_width=True):
                    catalogo.pop(i)
                    salvar_catalogo(catalogo)
                    st.rerun()
                if cacoes.button("➕ Orçamento", key=f"cat_orcamento_{i}", use_container_width=True):
                    preco_txt = str(produto_cat.get("Preco", "0")).replace("R$", "").strip()
                    preco_num = valor_float(preco_txt.replace(".", "").replace(",", "."))
                    st.session_state.temp_itens.append({"produto": produto_cat.get("Nome", ""), "especificacoes": produto_cat.get("Descricao", ""), "quantidade": 1, "valor_unitario": preco_num})
                    st.success("Produto adicionado ao orçamento. Abra a aba Novo Orçamento.")

    with aba_cliente:
        if not catalogo:
            st.info("Cadastre produtos para gerar um catálogo.")
        else:
            categorias_disponiveis = sorted({str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria" for p in catalogo})
            titulo_cliente = st.text_input("Título do catálogo", value="Seleção Alphafest", key="titulo_catalogo_cliente")
            categorias_cliente = st.multiselect("Categorias", categorias_disponiveis, default=categorias_disponiveis[:1], key="categorias_catalogo_cliente")
            produtos_base = [p for p in catalogo if (str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria") in categorias_cliente]
            nomes_disponiveis = [p.get("Nome", "Produto") for p in produtos_base]
            nomes_selecionados = st.multiselect("Produtos específicos", nomes_disponiveis, default=nomes_disponiveis, key="produtos_catalogo_cliente")
            mostrar_precos = st.checkbox("Mostrar preços", value=True, key="mostrar_precos_catalogo")
            selecao_cliente = [p for p in produtos_base if p.get("Nome", "Produto") in nomes_selecionados]
            st.caption(f"O catálogo do cliente terá {len(selecao_cliente)} produto(s).")
            html_cliente = gerar_html_catalogo(selecao_cliente, titulo_cliente or "Seleção Alphafest", mostrar_precos)
            st.download_button("📥 Gerar catálogo HTML para o cliente", data=html_cliente, file_name=f"{slug_html(titulo_cliente).lower()}.html", mime="text/html", type="primary", use_container_width=True)
            st.download_button("📚 Gerar catálogo completo", data=gerar_html_catalogo(catalogo, "Catálogo Completo Alphafest", True), file_name="catalogo_completo_alphafest.html", mime="text/html", use_container_width=True)

with aba6:
    st.header("👥 Clientes")
    st.caption("Cadastro, pesquisa e histórico de relacionamento com a Alphafest.")

    clientes = sincronizar_clientes_do_historico()
    if "cliente_edit_id" not in st.session_state:
        st.session_state.cliente_edit_id = None

    aba_cli_lista, aba_cli_cadastro = st.tabs(["🔎 Consultar clientes", "➕ Cadastrar / Editar"])

    with aba_cli_lista:
        termo_cli = st.text_input(
            "Pesquisar por nome, CPF/CNPJ, WhatsApp, e-mail ou observação",
            key="pesquisa_clientes_v31",
        ).strip().lower()

        filtrados_cli = []
        for cli in clientes:
            base = " ".join(str(cli.get(c, "")) for c in ["nome", "documento", "whatsapp", "email", "observacoes"]).lower()
            if not termo_cli or termo_cli in base:
                filtrados_cli.append(cli)

        total_clientes = len(clientes)
        clientes_com_pedidos = sum(1 for cli in clientes if propostas_do_cliente(cli))
        total_propostas_clientes = sum(len(propostas_do_cliente(cli)) for cli in clientes)
        m1, m2, m3 = st.columns(3)
        m1.metric("Clientes cadastrados", total_clientes)
        m2.metric("Clientes com propostas", clientes_com_pedidos)
        m3.metric("Propostas vinculadas", total_propostas_clientes)

        st.write(f"**{len(filtrados_cli)} cliente(s) encontrado(s)**")
        for cli in sorted(filtrados_cli, key=lambda x: str(x.get("nome", "")).lower()):
            propostas_cli = propostas_do_cliente(cli)
            totais = [calcular_valores_proposta(p)[2] for p in propostas_cli]
            total_orcado_cli = sum(totais)
            total_pago_cli = sum(calcular_valores_proposta(p)[2] for p in propostas_cli if p.get("pago", False))
            ultima_data = "—"
            if propostas_cli:
                ordenadas = sorted(
                    propostas_cli,
                    key=lambda p: data_entrega_segura(p.get("data_geracao")) or date.min,
                    reverse=True,
                )
                ultima_data = ordenadas[0].get("data_geracao", "—")

            titulo_cli = f"{cli.get('nome', 'Cliente')} — {len(propostas_cli)} proposta(s)"
            with st.expander(titulo_cli):
                cinfo, cstats = st.columns([1.3, 1])
                with cinfo:
                    st.write(f"**CPF/CNPJ:** {cli.get('documento') or 'Não informado'}")
                    st.write(f"**WhatsApp:** {cli.get('whatsapp') or 'Não informado'}")
                    st.write(f"**E-mail:** {cli.get('email') or 'Não informado'}")
                    st.write(f"**Aniversário/Data especial:** {cli.get('aniversario') or 'Não informado'}")
                    if cli.get("observacoes"):
                        st.write(f"**Observações:** {cli.get('observacoes')}")
                with cstats:
                    st.metric("Total orçado", f"R$ {total_orcado_cli:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.metric("Total recebido", f"R$ {total_pago_cli:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.caption(f"Última proposta: {ultima_data}")

                b1, b2, b3 = st.columns(3)
                if b1.button("➕ Novo orçamento", key=f"cli_orc_{cli.get('id')}", use_container_width=True):
                    carregar_cliente_no_orcamento(cli)
                    st.rerun()
                if b2.button("✏️ Editar cliente", key=f"cli_edit_{cli.get('id')}", use_container_width=True):
                    st.session_state.cliente_edit_id = cli.get("id")
                    st.rerun()
                if b3.button("🗑️ Excluir cadastro", key=f"cli_del_{cli.get('id')}", use_container_width=True):
                    restantes = [c for c in clientes if c.get("id") != cli.get("id")]
                    salvar_clientes(restantes)
                    st.rerun()

                if propostas_cli:
                    st.markdown("#### Histórico de propostas")
                    linhas_cli = []
                    for pcli in propostas_cli:
                        _, _, total_cli = calcular_valores_proposta(pcli)
                        linhas_cli.append({
                            "Proposta": pcli.get("numero_proposta", ""),
                            "Emissão": pcli.get("data_geracao", ""),
                            "Entrega": pcli.get("data_entrega", ""),
                            "Total": total_cli,
                            "Pago": "Sim" if pcli.get("pago") else "Não",
                            "Entregue": "Sim" if pcli.get("entregue") else "Não",
                        })
                    st.dataframe(
                        pd.DataFrame(linhas_cli),
                        use_container_width=True,
                        hide_index=True,
                        column_config={"Total": st.column_config.NumberColumn(format="R$ %.2f")},
                    )

    with aba_cli_cadastro:
        edit_id = st.session_state.cliente_edit_id
        cliente_edicao = next((c for c in clientes if c.get("id") == edit_id), None)
        st.subheader("✏️ Editar cliente" if cliente_edicao else "➕ Novo cliente")
        c1, c2 = st.columns(2)
        cli_nome = c1.text_input("Nome / Razão Social", value=cliente_edicao.get("nome", "") if cliente_edicao else "", key=f"cli_nome_{edit_id}")
        cli_doc = c1.text_input("CPF / CNPJ", value=cliente_edicao.get("documento", "") if cliente_edicao else "", key=f"cli_doc_{edit_id}")
        cli_wa = c1.text_input("WhatsApp", value=cliente_edicao.get("whatsapp", "") if cliente_edicao else "", key=f"cli_wa_{edit_id}")
        cli_email = c2.text_input("E-mail", value=cliente_edicao.get("email", "") if cliente_edicao else "", key=f"cli_email_{edit_id}")
        cli_aniv = c2.text_input("Aniversário / Data especial", value=cliente_edicao.get("aniversario", "") if cliente_edicao else "", key=f"cli_aniv_{edit_id}")
        cli_obs = c2.text_area("Observações", value=cliente_edicao.get("observacoes", "") if cliente_edicao else "", key=f"cli_obs_{edit_id}")
        ac1, ac2 = st.columns(2)
        if ac1.button("💾 Salvar cliente", type="primary", use_container_width=True):
            if not cli_nome.strip():
                st.warning("Informe o nome do cliente.")
            else:
                registro_cli = {
                    "id": cliente_edicao.get("id") if cliente_edicao else f"CLI-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "nome": cli_nome.strip(),
                    "documento": cli_doc.strip(),
                    "whatsapp": cli_wa.strip(),
                    "email": cli_email.strip(),
                    "aniversario": cli_aniv.strip(),
                    "observacoes": cli_obs.strip(),
                    "origem": cliente_edicao.get("origem", "Cadastro manual") if cliente_edicao else "Cadastro manual",
                    "criado_em": cliente_edicao.get("criado_em", datetime.now().strftime("%d/%m/%Y %H:%M")) if cliente_edicao else datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
                if cliente_edicao:
                    clientes = [registro_cli if c.get("id") == edit_id else c for c in clientes]
                else:
                    existente = next((c for c in clientes if chave_cliente(c.get("nome"), c.get("documento"), c.get("whatsapp")) == chave_cliente(cli_nome, cli_doc, cli_wa)), None)
                    if existente:
                        st.warning("Já existe um cliente com o mesmo documento, WhatsApp ou nome.")
                        st.stop()
                    clientes.append(registro_cli)
                salvar_clientes(clientes)
                st.session_state.cliente_edit_id = None
                st.success("Cliente salvo.")
                st.rerun()
        if cliente_edicao and ac2.button("Cancelar edição", use_container_width=True):
            st.session_state.cliente_edit_id = None
            st.rerun()

