import streamlit as st
import pandas as pd
import json
import os
import html
import re
import urllib.parse
from urllib.parse import quote
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import altair as alt
import base64

# Importação resiliente da camada de dados.
# Evita que uma atualização parcial de cloud_db.py derrube todo o aplicativo.
try:
    import cloud_db as _cloud_db
except Exception as _cloud_import_error:
    _cloud_db = None
else:
    _cloud_import_error = None

def _read_json_fallback(path, default):
    try:
        with open(path, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception:
        return default

def _write_json_fallback(path, value):
    try:
        with open(path, "w", encoding="utf-8") as arquivo:
            json.dump(value, arquivo, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def load_document(document_key, local_path, default):
    func = getattr(_cloud_db, "load_document", None) if _cloud_db else None
    return func(document_key, local_path, default) if callable(func) else _read_json_fallback(local_path, default)

def save_document(document_key, value, local_path):
    func = getattr(_cloud_db, "save_document", None) if _cloud_db else None
    return func(document_key, value, local_path) if callable(func) else _write_json_fallback(local_path, value)

def connection_test():
    func = getattr(_cloud_db, "connection_test", None) if _cloud_db else None
    if callable(func):
        return func()
    detalhe = f" ({type(_cloud_import_error).__name__})" if _cloud_import_error else ""
    return False, "Camada online indisponível" + detalhe + " — usando arquivos JSON locais."

def upload_catalog_image(upload, local_upload_dir="uploads"):
    func = getattr(_cloud_db, "upload_catalog_image", None) if _cloud_db else None
    if callable(func):
        return func(upload, local_upload_dir)
    if upload is None:
        return ""
    Path(local_upload_dir).mkdir(parents=True, exist_ok=True)
    nome = re.sub(r"[^A-Za-z0-9._-]", "_", str(upload.name))
    destino = Path(local_upload_dir) / f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{nome}"
    destino.write_bytes(bytes(upload.getbuffer()))
    return str(destino).replace("\\", "/")

def upload_library_file(upload, produto_nome="produto", local_upload_dir="biblioteca_uploads"):
    func = getattr(_cloud_db, "upload_library_file", None) if _cloud_db else None
    if callable(func):
        return func(upload, produto_nome=produto_nome, local_upload_dir=local_upload_dir)
    if upload is None:
        return ""
    produto_seguro = re.sub(r"[^A-Za-z0-9._-]", "_", str(produto_nome).strip()) or "produto"
    pasta = Path(local_upload_dir) / produto_seguro
    pasta.mkdir(parents=True, exist_ok=True)
    nome = re.sub(r"[^A-Za-z0-9._-]", "_", str(upload.name))
    destino = pasta / f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{nome}"
    destino.write_bytes(bytes(upload.getbuffer()))
    return str(destino).replace("\\", "/")

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Orçamento Alphafest", layout="wide")
ARQUIVO_HISTORICO = "historico_orcamentos.json"
ARQUIVO_CATALOGO = "catalogo_db.json"
ARQUIVO_CLIENTES = "clientes_db.json"
ARQUIVO_PRODUCAO = "producao_db.json"
ARQUIVO_EMPRESA = "empresa_config.json"
ARQUIVO_PROJETOS = "projetos_db.json"
ARQUIVO_CAMPANHAS = "campanhas_db.json"
ARQUIVO_ATENDIMENTOS = "atendimentos_db.json"
ARQUIVO_SEGMENTOS = "segmentos_db.json"
VERSAO_APP = "3.9.2"
PASTA_UPLOADS = "uploads"
os.makedirs(PASTA_UPLOADS, exist_ok=True)

FUSO_PADRAO = "America/Sao_Paulo"

def agora_local():
    """Data e hora oficiais do sistema, independentes do fuso do servidor."""
    try:
        fuso = str(carregar_config_empresa().get("fuso_horario", FUSO_PADRAO)).strip()
    except Exception:
        fuso = FUSO_PADRAO
    try:
        return datetime.now(ZoneInfo(fuso or FUSO_PADRAO))
    except Exception:
        return datetime.now(ZoneInfo(FUSO_PADRAO))

def hoje_local():
    return agora_local().date()

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

# --- CONFIGURAÇÃO DA EMPRESA ---
CONFIG_EMPRESA_PADRAO = {
    "nome": "Alphafest",
    "nome_maiusculo": "ALPHAFEST",
    "slogan": "O poder de estar presente em cada presente...",
    "subtitulo": "Personalizados & Balões",
    "cnpj": "24.374.857/0001-30",
    "ie": "382105300112",
    "endereco": "Avenida Manoel Verginio de Almeida, 442 - Alto Santa Cruz - Itatiba - SP",
    "cep": "13251-530",
    "email": "alphafesti@gmail.com",
    "celular": "(11) 97294-9533",
    "whatsapp_catalogo": "11972949533",
    "cidade": "Itatiba",
    "uf": "SP",
    "pix_link": "https://linkspix.app/alphafestitatiba",
    "pix_titular": "Ana Lúcia Zepelini",
    "pix_banco": "Cora SCD (403)",
    "pix_agencia": "0001",
    "pix_conta": "2515972-5",
    "pix_empresa": "ANA LUCIA VIEIRA ZEPELINI 29480359880",
    "prazo_padrao": "10",
    "validade_padrao": "5",
    "frete_padrao": "Retirada em Itatiba",
    "fuso_horario": "America/Sao_Paulo",
}

def carregar_config_empresa():
    dados = load_document("config_empresa", ARQUIVO_EMPRESA, CONFIG_EMPRESA_PADRAO)
    config = dict(CONFIG_EMPRESA_PADRAO)
    if isinstance(dados, dict):
        config.update({k: v for k, v in dados.items() if v is not None})
    return config

USUARIOS_ADMIN = {
    "jorgegaulke76@gmail.com": {"nome": "Jorge", "perfil": "Administrador"},
    "alphafesti@gmail.com": {"nome": "Anna", "perfil": "Administradora"},
    "annazepelini@gmail.com": {"nome": "Anna", "perfil": "Administradora"},
}

def obter_email_usuario_autenticado():
    """Tenta obter o e-mail do login OIDC do Streamlit, quando configurado."""
    try:
        usuario = st.user
        email = getattr(usuario, "email", None)
        if not email and hasattr(usuario, "get"):
            email = usuario.get("email")
        if email:
            return str(email).strip().lower()
    except Exception:
        pass
    return ""

def obter_usuario_atual():
    email = obter_email_usuario_autenticado()
    if email in USUARIOS_ADMIN:
        dados = dict(USUARIOS_ADMIN[email])
        dados["email"] = email
        dados["automatico"] = True
        return dados

    nome_fallback = st.session_state.get("usuario_atual_fallback", "Anna")
    email_fallback = "jorgegaulke76@gmail.com" if nome_fallback == "Jorge" else "alphafesti@gmail.com"
    dados = dict(USUARIOS_ADMIN[email_fallback])
    dados["email"] = email_fallback
    dados["automatico"] = False
    return dados

def saudacao_por_hora(nome):
    hora = agora_local().hour
    if hora < 12:
        periodo = "Bom dia"
    elif hora < 18:
        periodo = "Boa tarde"
    else:
        periodo = "Boa noite"
    return f"{periodo}, {nome}!"

def salvar_config_empresa(config):
    if not isinstance(config, dict):
        raise ValueError("A configuração da empresa precisa ser um dicionário.")
    dados = dict(CONFIG_EMPRESA_PADRAO)
    dados.update(config)
    save_document("config_empresa", dados, ARQUIVO_EMPRESA)

# --- FUNÇÕES AUXILIARES ---
def formatar_msg_whatsapp(prop):
    """Monta a mensagem compacta aprovada para envio pelo WhatsApp."""
    prop = prop or {}
    empresa = carregar_config_empresa()

    numero_proposta = str(prop.get("numero_proposta", "")).strip() or "N/A"
    data_emissao = str(prop.get("data_geracao", prop.get("data", ""))).strip() or "N/A"
    cliente = str(prop.get("cliente_nome", prop.get("cliente", ""))).strip() or "N/A"
    documento = str(prop.get("documento", prop.get("cliente_cpf_cnpj", ""))).strip() or "N/A"
    entrega = str(prop.get("data_entrega", "")).strip() or "A combinar"
    prazo = str(prop.get("prazo_dias", empresa.get("prazo_padrao", "10"))).strip() or str(empresa.get("prazo_padrao", "10"))
    frete = str(prop.get("frete_tipo", empresa.get("frete_padrao", "Retirada em Itatiba"))).strip() or str(empresa.get("frete_padrao", "Retirada em Itatiba"))
    validade = str(prop.get("validade_dias", empresa.get("validade_padrao", "5"))).strip() or str(empresa.get("validade_padrao", "5"))

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
        f"*PROPOSTA {str(empresa.get('nome_maiusculo', empresa.get('nome', 'EMPRESA'))).upper()} {str(empresa.get('cidade', '')).upper()}*".strip(),
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
        f"*Clique no link para pagar:* {empresa.get('pix_link', '')}",
        "",
        f"* Titular: {empresa.get('pix_titular', '')}",
        f"* Banco: {empresa.get('pix_banco', '')}",
        f"* Agência: {empresa.get('pix_agencia', '')} | Conta: {empresa.get('pix_conta', '')}",
        f"* Empresa: {empresa.get('pix_empresa', '')}",
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

    empresa = carregar_config_empresa()
    empresa_nome = str(empresa.get("nome", "Empresa"))
    empresa_cnpj = str(empresa.get("cnpj", ""))
    empresa_ie = str(empresa.get("ie", ""))
    empresa_endereco = str(empresa.get("endereco", ""))
    empresa_cep = str(empresa.get("cep", ""))
    empresa_email = str(empresa.get("email", ""))
    empresa_celular = str(empresa.get("celular", ""))

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
        st.session_state.form_entrega = hoje_local()

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
    st.session_state.form_entrega = hoje_local()
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
                "id": f"CLI-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                "nome": nome,
                "documento": documento,
                "whatsapp": whatsapp,
                "email": "",
                "aniversario": "",
                "observacoes": "",
                "origem": "Histórico de propostas",
                "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
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
        "data": agora_local().strftime("%d/%m/%Y %H:%M"),
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
                "timeline": [{"data": agora_local().strftime("%d/%m/%Y %H:%M"), "descricao": "Pedido incluído no fluxo"}],
                "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
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
            tarefa["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
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
    dias = (data_item - hoje_local()).days
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
def gerar_conteudo_catalogo_gratuito(nome, categoria, subcategoria="", ideias="", preco="", processos=None):
    """Gera textos comerciais sem API paga, usando modelos editáveis e dados do produto."""
    nome = str(nome or "").strip()
    categoria = str(categoria or "").strip()
    subcategoria = str(subcategoria or "").strip()
    ideias = re.sub(r"\s+", " ", str(ideias or "").strip())
    processos = [str(x).strip() for x in (processos or []) if str(x).strip()]

    produto = nome or "Produto personalizado"
    classificacao = " / ".join(x for x in [categoria, subcategoria] if x) or "Personalizados"
    complemento = ideias.rstrip(" .")
    detalhe = f" {complemento}." if complemento else ""
    processo_txt = ", ".join(processos)
    producao_txt = f" Produção com {processo_txt.lower()}, conforme a necessidade do pedido." if processo_txt else ""

    descricao_curta = (
        f"{produto} personalizado pela {CONFIG_EMPRESA.get('nome', 'Alphafest')}, "
        f"ideal para festas, presentes e ocasiões especiais.{detalhe}"
    ).strip()

    descricao_completa = (
        f"O {produto} é desenvolvido de forma personalizada para combinar com o tema, as cores "
        f"e os detalhes escolhidos pelo cliente. Faz parte da categoria {classificacao} e recebe "
        f"acabamento cuidadoso em todas as etapas.{detalhe}{producao_txt} "
        "Por se tratar de um item personalizado, cores, medidas, composição e prazo podem variar "
        "conforme o modelo aprovado e a disponibilidade de materiais. Entre em contato para confirmar "
        "as opções de personalização e a data desejada."
    ).strip()

    termos = [produto, categoria, subcategoria, "personalizado", "festa", "presente", CONFIG_EMPRESA.get("cidade", "")]
    if ideias:
        termos += re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", ideias)[:6]
    palavras = []
    for termo in termos:
        termo = str(termo).strip().lower()
        if termo and termo not in palavras:
            palavras.append(termo)
    palavras_chave = ", ".join(palavras[:12])

    def hashtag(texto):
        texto = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", str(texto).title())
        return f"#{texto}" if texto else ""

    tags_base = [produto, categoria, subcategoria, CONFIG_EMPRESA.get("nome", "Alphafest"), "Personalizados", "Festa", CONFIG_EMPRESA.get("cidade", "Itatiba")]
    hashtags_lista = []
    for item in tags_base:
        tag = hashtag(item)
        if tag and tag.lower() not in [x.lower() for x in hashtags_lista]:
            hashtags_lista.append(tag)
    hashtags = " ".join(hashtags_lista[:10])

    preco_txt = str(preco or "").strip()
    chamada_preco = f" Valor sugerido: R$ {preco_txt}." if preco_txt else ""
    whatsapp = CONFIG_EMPRESA.get("celular", "")
    legenda = (
        f"✨ {produto} personalizado para tornar cada comemoração ainda mais especial!\n\n"
        f"{descricao_curta}\n\n"
        f"Personalizamos conforme o tema e os detalhes do seu evento.{chamada_preco}\n"
        f"📲 Peça seu orçamento pelo WhatsApp {whatsapp}.\n\n{hashtags}"
    ).strip()

    descricao_marketplace = (
        f"{produto} personalizado | {classificacao}\n\n"
        f"{descricao_completa}\n\n"
        "INFORMAÇÕES IMPORTANTES:\n"
        "• Produto personalizado e produzido sob encomenda.\n"
        "• Envie os dados de personalização após a compra.\n"
        "• A produção começa após a confirmação dos dados e, quando necessário, da aprovação da arte.\n"
        "• Consulte o prazo antes da compra para eventos com data marcada.\n"
        "• Pequenas variações de cor podem ocorrer conforme a tela e o lote do material."
    ).strip()

    descricao_shopee = (
        f"{produto} personalizado para sua festa ou ocasião especial.\n\n"
        f"{descricao_curta}\n\n"
        "COMO PERSONALIZAR:\n"
        "1. Faça o pedido.\n"
        "2. Envie tema, nome, idade, cores e demais informações pelo chat.\n"
        "3. Aguarde a confirmação e a aprovação da arte, quando aplicável.\n\n"
        "Produção sob encomenda. Consulte prazo e disponibilidade antes de finalizar a compra."
    ).strip()

    return {
        "descricao_curta": descricao_curta,
        "descricao_completa": descricao_completa,
        "palavras_chave": palavras_chave,
        "legenda": legenda,
        "hashtags": hashtags,
        "mercado_livre": descricao_marketplace,
        "shopee": descricao_shopee,
    }


CAMPANHAS_PADRAO = [
    {"id": "CAMP-JAN-BRANCO", "nome": "Janeiro Branco", "tipo": "Nacional", "categoria": "Conscientização", "data_inicio": "2026-01-01", "data_fim": "2026-01-31", "recorrencia": "Anual", "antecedencia_dias": 45, "regiao": "Brasil", "produtos": [], "observacoes": "Campanha de conscientização sobre saúde mental.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-VOLTA-AULAS", "nome": "Volta às Aulas", "tipo": "Personalizada", "categoria": "Escolar", "data_inicio": "2026-01-20", "data_fim": "2026-02-10", "recorrencia": "Anual", "antecedencia_dias": 45, "regiao": "Editar conforme calendário local", "produtos": ["Etiquetas", "Lembrancinhas", "Personalizados escolares"], "observacoes": "Ajustar as datas conforme as escolas da cidade.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-DIA-MAES", "nome": "Dia das Mães", "tipo": "Nacional", "categoria": "Comercial", "data_inicio": "2026-05-01", "data_fim": "2026-05-10", "recorrencia": "Anual", "antecedencia_dias": 60, "regiao": "Brasil", "produtos": [], "observacoes": "Atualize a data final a cada ano.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-DIA-PAIS", "nome": "Dia dos Pais", "tipo": "Nacional", "categoria": "Comercial", "data_inicio": "2026-08-01", "data_fim": "2026-08-09", "recorrencia": "Anual", "antecedencia_dias": 60, "regiao": "Brasil", "produtos": [], "observacoes": "Atualize a data final a cada ano.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-OUTUBRO-ROSA", "nome": "Outubro Rosa", "tipo": "Nacional", "categoria": "Conscientização", "data_inicio": "2026-10-01", "data_fim": "2026-10-31", "recorrencia": "Anual", "antecedencia_dias": 60, "regiao": "Brasil", "produtos": ["Bubble rosa", "Balões", "Lembrancinhas", "Topos"], "observacoes": "Campanha de conscientização sobre o câncer de mama.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-NOVEMBRO-AZUL", "nome": "Novembro Azul", "tipo": "Nacional", "categoria": "Conscientização", "data_inicio": "2026-11-01", "data_fim": "2026-11-30", "recorrencia": "Anual", "antecedencia_dias": 60, "regiao": "Brasil", "produtos": ["Bubble azul", "Balões", "Lembrancinhas", "Topos"], "observacoes": "Campanha de conscientização sobre a saúde do homem.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-BLACK-FRIDAY", "nome": "Black Friday", "tipo": "Nacional", "categoria": "Comercial", "data_inicio": "2026-11-20", "data_fim": "2026-11-30", "recorrencia": "Anual", "antecedencia_dias": 60, "regiao": "Brasil", "produtos": [], "observacoes": "Definir produtos e condições da promoção.", "status": "Planejamento", "ativa": True},
    {"id": "CAMP-NATAL", "nome": "Natal", "tipo": "Nacional", "categoria": "Comercial", "data_inicio": "2026-11-15", "data_fim": "2026-12-24", "recorrencia": "Anual", "antecedencia_dias": 90, "regiao": "Brasil", "produtos": [], "observacoes": "Planejar catálogo, presentes e decoração com antecedência.", "status": "Planejamento", "ativa": True},
]


def carregar_campanhas():
    dados = load_document("campanhas_db", ARQUIVO_CAMPANHAS, [])
    if not isinstance(dados, list):
        dados = []
    if not dados:
        dados = [dict(item) for item in CAMPANHAS_PADRAO]
        save_document("campanhas_db", dados, ARQUIVO_CAMPANHAS)
    return dados


def salvar_campanhas(lista):
    if not isinstance(lista, list):
        raise ValueError("O calendário comercial precisa ser uma lista.")
    save_document("campanhas_db", lista, ARQUIVO_CAMPANHAS)


# --- CENTRAL DE ATENDIMENTO / CRM INTELIGENTE (3.9.2) ---
SEGMENTOS_PADRAO = [
    "Pessoa Física", "Empresa / CNPJ", "Boleira", "Doceira", "Confeiteira",
    "Escola", "Professor(a)", "Buffet", "Decoradora", "Igreja", "Loja",
    "Parceiro", "Clínica", "Academia", "Esportes", "Beach Tennis",
    "Tênis", "Basquete", "Futebol", "Vôlei", "Outros",
]
INTERESSES_PADRAO = [
    "Papelaria personalizada", "Papel de arroz", "Balões", "Bubble",
    "Impressão 3D", "Laser", "Lembrancinhas", "Gráfica rápida",
    "Brindes", "Camisetas", "Medalhas", "Troféus", "Banners",
]
STATUS_ATENDIMENTO = [
    "Novo contato", "Catálogo solicitado", "Catálogo enviado",
    "Orçamento solicitado", "Orçamento em elaboração", "Aguardando cliente",
    "Pedido aprovado", "Comprovante recebido", "Arte aprovada",
    "Em produção", "Pronto", "Entregue", "Pós-venda", "Arquivado",
]
CONFIG_ATENDIMENTO_PADRAO = {
    "modo": "Manual",
    "boas_vindas": "Assistido",
    "catalogo": "Assistido",
    "orcamento": "Manual",
    "comprovante": "Manual",
    "aprovacao_arte": "Manual",
    "duvidas_negociacao": "Manual",
    "integracao_whatsapp": False,
    "sla_atencao_min": 30,
    "sla_urgente_min": 60,
}

def carregar_atendimentos():
    dados = load_document("atendimentos_db", ARQUIVO_ATENDIMENTOS, {"config": CONFIG_ATENDIMENTO_PADRAO, "itens": []})
    if not isinstance(dados, dict):
        dados = {"config": dict(CONFIG_ATENDIMENTO_PADRAO), "itens": []}
    config = dict(CONFIG_ATENDIMENTO_PADRAO)
    config.update(dados.get("config") or {})
    itens = dados.get("itens") if isinstance(dados.get("itens"), list) else []
    return {"config": config, "itens": itens}

def salvar_atendimentos(dados):
    save_document("atendimentos_db", dados, ARQUIVO_ATENDIMENTOS)

def carregar_segmentos():
    dados = load_document("segmentos_db", ARQUIVO_SEGMENTOS, SEGMENTOS_PADRAO)
    return dados if isinstance(dados, list) and dados else list(SEGMENTOS_PADRAO)

def salvar_segmentos(lista):
    lista_limpa = sorted({str(x).strip() for x in lista if str(x).strip()}, key=str.lower)
    save_document("segmentos_db", lista_limpa, ARQUIVO_SEGMENTOS)

def sugerir_tipo_atendimento(texto):
    t = str(texto or "").lower()
    if any(x in t for x in ["catálogo", "catalogo", "modelos", "o que vocês fazem", "o que voces fazem"]):
        return "Catálogo solicitado"
    if any(x in t for x in ["orçamento", "orcamento", "valor", "preço", "preco", "quanto custa"]):
        return "Orçamento solicitado"
    if any(x in t for x in ["comprovante", "paguei", "pagamento", "pix"]):
        return "Comprovante recebido"
    if any(x in t for x in ["aprovado", "aprovada", "pode fazer", "gostei da arte"]):
        return "Arte aprovada"
    return "Novo contato"

def resposta_sugerida_atendimento(item, empresa=None):
    empresa = empresa or carregar_config_empresa()
    nome = str(item.get("cliente", "")).strip() or "cliente"
    status = item.get("status", "Novo contato")
    if status == "Catálogo solicitado":
        return f"Olá, {nome}! 😊 Vou enviar nosso catálogo para você conhecer as opções da {empresa.get('nome', 'empresa')}. Depois me diga quais produtos chamaram mais sua atenção."
    if status == "Orçamento solicitado":
        return f"Olá, {nome}! Recebi sua solicitação de orçamento. Vou organizar as informações e retorno com a proposta. Se puder, envie tema, quantidade e data desejada."
    if status == "Comprovante recebido":
        return f"Olá, {nome}! Comprovante recebido. Obrigado! Vamos conferir e dar andamento ao seu pedido."
    if status == "Arte aprovada":
        return f"Perfeito, {nome}! Arte aprovada. Vamos seguir para a próxima etapa do seu pedido."
    return f"Olá, {nome}! Recebemos sua mensagem e já vamos atender você. 😊"

def minutos_aguardando(item):
    criado = str(item.get("criado_em", ""))
    for formato in ("%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(criado[:19], formato).replace(tzinfo=agora_local().tzinfo)
            return max(0, int((agora_local() - dt).total_seconds() // 60))
        except Exception:
            pass
    return 0

def faixa_sla_atendimento(item, config=None):
    """Retorna ícone, rótulo e prioridade numérica conforme o tempo de espera."""
    config = config or CONFIG_ATENDIMENTO_PADRAO
    minutos = minutos_aguardando(item)
    atencao = max(1, int(config.get("sla_atencao_min", 30) or 30))
    urgente = max(atencao + 1, int(config.get("sla_urgente_min", 60) or 60))
    if minutos >= urgente:
        return "🔴", "Urgente", 3
    if minutos >= atencao:
        return "🟡", "Atenção", 2
    return "🟢", "No prazo", 1


def tempo_aguardando_formatado(item):
    minutos = minutos_aguardando(item)
    horas, mins = divmod(minutos, 60)
    if horas >= 24:
        dias, horas = divmod(horas, 24)
        return f"{dias}d {horas:02d}h {mins:02d}min"
    return f"{horas:02d}h {mins:02d}min"


def proxima_acao_atendimento(item):
    status = str(item.get("status", "Novo contato"))
    mapa = {
        "Novo contato": "Ler e responder",
        "Catálogo solicitado": "Enviar catálogo",
        "Catálogo enviado": "Aguardar retorno",
        "Orçamento solicitado": "Criar orçamento",
        "Orçamento em elaboração": "Finalizar orçamento",
        "Aguardando cliente": "Acompanhar retorno",
        "Pedido aprovado": "Confirmar dados do pedido",
        "Comprovante recebido": "Conferir pagamento",
        "Arte aprovada": "Liberar produção",
        "Em produção": "Atualizar andamento",
        "Pronto": "Combinar entrega/retirada",
        "Entregue": "Fazer pós-venda",
        "Pós-venda": "Concluir atendimento",
        "Arquivado": "Nenhuma ação",
    }
    return mapa.get(status, "Verificar atendimento")


def _data_iso_segura(valor):
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    return None


def periodo_campanha_no_ano(campanha, ano=None):
    """Retorna início e fim aplicáveis ao ano informado."""
    ano = int(ano or hoje_local().year)
    inicio_base = _data_iso_segura(campanha.get("data_inicio"))
    fim_base = _data_iso_segura(campanha.get("data_fim")) or inicio_base
    if not inicio_base:
        return None, None
    if str(campanha.get("recorrencia", "Evento único")) == "Anual":
        try:
            inicio = date(ano, inicio_base.month, inicio_base.day)
        except ValueError:
            inicio = date(ano, inicio_base.month, 28)
        try:
            fim = date(ano, fim_base.month, fim_base.day)
        except ValueError:
            fim = date(ano, fim_base.month, 28)
        if fim < inicio:
            fim = date(ano + 1, fim_base.month, fim_base.day)
        return inicio, fim
    return inicio_base, fim_base


def proxima_ocorrencia_campanha(campanha, referencia=None):
    referencia = referencia or hoje_local()
    inicio, fim = periodo_campanha_no_ano(campanha, referencia.year)
    if not inicio:
        return None, None
    if str(campanha.get("recorrencia", "Evento único")) == "Anual" and fim < referencia:
        inicio, fim = periodo_campanha_no_ano(campanha, referencia.year + 1)
    return inicio, fim


def campanhas_em_oportunidade(referencia=None, limite_dias=120):
    referencia = referencia or hoje_local()
    oportunidades = []
    for campanha in carregar_campanhas():
        if not campanha.get("ativa", True):
            continue
        inicio, fim = proxima_ocorrencia_campanha(campanha, referencia)
        if not inicio:
            continue
        dias = (inicio - referencia).days
        antecedencia = int(campanha.get("antecedencia_dias", 30) or 30)
        em_periodo = inicio <= referencia <= fim
        if em_periodo or (-7 <= dias <= max(limite_dias, antecedencia)):
            item = dict(campanha)
            item["inicio_calculado"] = inicio
            item["fim_calculado"] = fim
            item["dias_para_inicio"] = dias
            item["em_periodo"] = em_periodo
            oportunidades.append(item)
    return sorted(oportunidades, key=lambda x: (0 if x["em_periodo"] else 1, x["inicio_calculado"]))

def carregar_projetos():
    dados = load_document("projetos_db", ARQUIVO_PROJETOS, [])
    return dados if isinstance(dados, list) else []


def salvar_projetos(lista):
    if not isinstance(lista, list):
        raise ValueError("A memória de projetos precisa ser uma lista.")
    save_document("projetos_db", lista, ARQUIVO_PROJETOS)


def obter_ou_criar_projeto(proposta):
    """Retorna a Caixa do Projeto ligada à proposta, criando-a quando necessário."""
    numero = str(proposta.get("numero_proposta", "")).strip()
    projetos = carregar_projetos()
    projeto = next((p for p in projetos if str(p.get("numero_proposta", "")) == numero), None)
    if projeto:
        return projeto, projetos
    itens = proposta.get("itens", []) or []
    temas = []
    for item in itens:
        esp = str(item.get("especificacoes", ""))
        m = re.search(r"Tema:\s*([^|]+)", esp, re.I)
        if m and m.group(1).strip():
            temas.append(m.group(1).strip())
    projeto = {
        "id": f"PRJ-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
        "numero_proposta": numero,
        "cliente_nome": proposta.get("cliente_nome", ""),
        "whatsapp": proposta.get("whatsapp", proposta.get("cliente_wa", "")),
        "data_entrega": proposta.get("data_entrega", ""),
        "tema": ", ".join(dict.fromkeys(temas)),
        "produtos": [str(i.get("produto", "")).strip() for i in itens if str(i.get("produto", "")).strip()],
        "arquivos": [],
        "observacoes": "",
        "modelo": False,
        "favorito": False,
        "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
        "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
    }
    projetos.insert(0, projeto)
    salvar_projetos(projetos)
    return projeto, projetos


def atualizar_projeto(projeto_atualizado):
    projetos = carregar_projetos()
    pid = projeto_atualizado.get("id")
    projeto_atualizado["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
    encontrado = False
    for i, projeto in enumerate(projetos):
        if projeto.get("id") == pid:
            projetos[i] = projeto_atualizado
            encontrado = True
            break
    if not encontrado:
        projetos.insert(0, projeto_atualizado)
    salvar_projetos(projetos)


def texto_busca_projeto(projeto):
    partes = [
        projeto.get("id", ""), projeto.get("numero_proposta", ""), projeto.get("cliente_nome", ""),
        projeto.get("whatsapp", ""), projeto.get("tema", ""), projeto.get("observacoes", ""),
        " ".join(projeto.get("produtos", []) or []),
    ]
    for arq in projeto.get("arquivos", []) or []:
        partes.extend([arq.get("nome", ""), arq.get("categoria", ""), arq.get("descricao", ""), " ".join(arq.get("tags", []) or [])])
    return " ".join(str(x) for x in partes).lower()


def renderizar_caixa_projeto(proposta, prefixo="historico"):
    """Caixa do Projeto: arquivos, observações e reutilização ligados ao pedido."""
    projeto, _ = obter_ou_criar_projeto(proposta)
    projeto = dict(projeto)
    st.markdown("#### 📦 Caixa do Projeto")
    st.caption("Guarde artes, arquivos de produção, fotos finais e observações deste pedido.")
    kbase = f"{prefixo}_{projeto.get('id')}"

    c1, c2, c3 = st.columns(3)
    c1.write(f"**Projeto:** {projeto.get('id', '—')}")
    c2.write(f"**Tema:** {projeto.get('tema') or 'Não informado'}")
    c3.write(f"**Arquivos:** {len([a for a in projeto.get('arquivos', []) if not a.get('arquivado')])}")

    observacoes = st.text_area(
        "Observações internas do projeto",
        value=str(projeto.get("observacoes", "")),
        key=f"proj_obs_{kbase}",
        height=90,
    )
    o1, o2, o3 = st.columns(3)
    modelo = o1.checkbox("♻️ Modelo reutilizável", value=bool(projeto.get("modelo")), key=f"proj_modelo_{kbase}")
    favorito = o2.checkbox("⭐ Projeto favorito", value=bool(projeto.get("favorito")), key=f"proj_fav_{kbase}")
    if o3.button("💾 Salvar projeto", key=f"proj_salvar_{kbase}", use_container_width=True):
        projeto["observacoes"] = observacoes.strip()
        projeto["modelo"] = bool(modelo)
        projeto["favorito"] = bool(favorito)
        atualizar_projeto(projeto)
        st.success("Caixa do Projeto atualizada.")
        st.rerun()

    with st.expander("➕ Adicionar arquivo ao projeto", expanded=False):
        upload = st.file_uploader("Escolher arquivo", type=None, key=f"proj_upload_{kbase}")
        u1, u2 = st.columns(2)
        categoria = u1.selectbox(
            "Classificação",
            ["Arte", "Arquivo de produção", "Foto final", "Referência", "Vídeo", "Manual/Dica", "Outro"],
            key=f"proj_cat_{kbase}",
        )
        tags = u2.text_input("Tags", placeholder="Ex.: Stitch, azul, corte", key=f"proj_tags_{kbase}")
        descricao = st.text_input("Descrição", placeholder="Ex.: arte final aprovada", key=f"proj_desc_{kbase}")
        mestre = st.checkbox("⭐ Marcar como arquivo mestre", key=f"proj_mestre_{kbase}")
        if st.button("📤 Enviar arquivo", key=f"proj_enviar_{kbase}", type="primary", use_container_width=True):
            if upload is None:
                st.warning("Escolha um arquivo.")
            else:
                caminho = upload_library_file(upload, produto_nome=f"projetos/{projeto.get('id', 'projeto')}", local_upload_dir="projetos_uploads")
                if not caminho:
                    st.error("Não foi possível salvar o arquivo.")
                else:
                    arquivos = list(projeto.get("arquivos", []) or [])
                    if mestre:
                        for arq in arquivos:
                            arq["mestre"] = False
                    arquivos.append({
                        "id": f"PARQ-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                        "nome": str(upload.name),
                        "url": caminho,
                        "tipo": nome_tipo_arquivo(upload.name),
                        "categoria": categoria,
                        "tags": [x.strip() for x in tags.split(",") if x.strip()],
                        "descricao": descricao.strip(),
                        "mestre": bool(mestre),
                        "arquivado": False,
                        "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
                    })
                    projeto["arquivos"] = arquivos
                    atualizar_projeto(projeto)
                    st.success("Arquivo adicionado ao projeto.")
                    st.rerun()

    ativos = [(i, a) for i, a in enumerate(projeto.get("arquivos", []) or []) if not a.get("arquivado")]
    if ativos:
        for i, arq in ativos:
            a1, a2, a3 = st.columns([1, 5, 2])
            a1.write("⭐" if arq.get("mestre") else ("📷" if arq.get("categoria") == "Foto final" else "📄"))
            a2.markdown(f"**{html.escape(str(arq.get('nome', 'Arquivo')))}**")
            a2.caption(f"{arq.get('categoria', 'Arquivo')} • {arq.get('criado_em', '')}")
            if arq.get("descricao"):
                a2.write(arq.get("descricao"))
            if arq.get("tags"):
                a2.caption("Tags: " + " • ".join(arq.get("tags", [])))
            if arq.get("url"):
                a3.link_button("Abrir / baixar", arq.get("url"), use_container_width=True)
            if a3.button("📦 Arquivar", key=f"proj_arq_{kbase}_{i}", use_container_width=True):
                projeto["arquivos"][i]["arquivado"] = True
                projeto["arquivos"][i]["mestre"] = False
                atualizar_projeto(projeto)
                st.rerun()
    else:
        st.info("Nenhum arquivo vinculado a este projeto ainda.")


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


def gerar_html_catalogo(produtos, titulo=None, mostrar_precos=True):
    produtos = produtos or []
    empresa = carregar_config_empresa()
    if not titulo:
        titulo = f"Catálogo {empresa.get('nome', 'Empresa')}"
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
            descricao = html.escape(str(produto.get("DescricaoCurta", produto.get("Descricao", ""))))
            imagens = produto.get("Imagens", []) or []
            primeira = imagens[0] if imagens else ""
            src = primeira if str(primeira).startswith(("http://", "https://")) else imagem_data_uri(primeira)
            imagem_html = f'<img src="{src}" alt="{nome}" onclick="abrirImagem(this.src)">' if src else '<div class="sem-imagem">Sem imagem</div>'
            preco_html = f'<div class="preco">{html.escape(formatar_preco_catalogo(produto.get("Preco")))}</div>' if mostrar_precos else ''
            msg = quote(f"Olá! Gostaria de informações sobre: {produto.get('Nome', 'produto')}")
            numero_wpp = re.sub(r"\D", "", str(empresa.get("whatsapp_catalogo", "")))
            if numero_wpp and not numero_wpp.startswith("55"):
                numero_wpp = "55" + numero_wpp
            cards.append(f'<article class="card">{imagem_html}<div class="card-body"><h3>{nome}</h3><p>{descricao}</p>{preco_html}<a class="btn" target="_blank" href="https://wa.me/{numero_wpp}?text={msg}">Consultar no WhatsApp</a></div></article>')
        cards_por_categoria.append(f'<section id="{slug_html(categoria)}"><h2>{html.escape(categoria)}</h2><div class="grid">{"".join(cards)}</div></section>')

    links = "".join(f'<a href="#{slug_html(c)}">{html.escape(c)}</a>' for c in categorias)
    logo_tag = f'<img class="logo" src="{logo_src}">' if logo_src else ''
    corpo = ''.join(cards_por_categoria) if cards_por_categoria else '<div class="intro">Nenhum produto selecionado.</div>'
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titulo)}</title><style>
    *{{box-sizing:border-box}} body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f5f6f8;color:#20252b}} .layout{{display:flex;min-height:100vh}} aside{{width:260px;background:#18222d;color:#fff;padding:24px 18px;position:sticky;top:0;height:100vh;overflow:auto}} .logo{{max-width:180px;max-height:95px;display:block;margin:0 auto 18px;object-fit:contain}} aside h1{{font-size:20px;text-align:center;margin:8px 0 22px}} nav a{{display:block;color:#eef2f7;text-decoration:none;padding:11px 10px;border-bottom:1px solid rgba(255,255,255,.12)}} main{{flex:1;padding:32px;max-width:1400px}} .intro{{background:#fff;padding:22px;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.06);margin-bottom:28px}} section{{scroll-margin-top:20px;margin-bottom:42px}} section h2{{border-bottom:3px solid #202b36;padding-bottom:9px}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:22px}} .card{{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 5px 18px rgba(0,0,0,.08);display:flex;flex-direction:column}} .card img,.sem-imagem{{width:100%;height:220px;object-fit:cover;background:#e9edf2;display:flex;align-items:center;justify-content:center;cursor:pointer}} .card-body{{padding:18px;display:flex;flex-direction:column;flex:1}} .card h3{{margin:0 0 10px}} .card p{{line-height:1.45;flex:1}} .preco{{font-size:22px;font-weight:800;margin:12px 0;color:#147a42}} .btn{{display:block;text-align:center;background:#25d366;color:#fff;text-decoration:none;padding:12px;border-radius:9px;font-weight:800}} footer{{text-align:center;color:#6b7280;padding:30px}} #modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:999;align-items:center;justify-content:center}} #modal img{{max-width:92vw;max-height:90vh}} @media(max-width:760px){{.layout{{display:block}}aside{{width:100%;height:auto;position:relative}}main{{padding:18px}}nav{{display:flex;gap:5px;overflow:auto}}nav a{{white-space:nowrap;border:1px solid rgba(255,255,255,.18);border-radius:8px}}}}
    </style></head><body><div class="layout"><aside>{logo_tag}<h1>{html.escape(titulo)}</h1><nav>{links}</nav></aside><main><div class="intro"><h1>{html.escape(titulo)}</h1><p>Seleção preparada por {html.escape(str(empresa.get("nome", "Empresa")))}. Consulte disponibilidade, personalização e prazo pelo WhatsApp.</p></div>{corpo}<footer>{html.escape(str(empresa.get("nome", "Empresa")))} - {html.escape(str(empresa.get("slogan", "")))}</footer></main></div><div id="modal" onclick="this.style.display='none'"><img id="modal-img"></div><script>function abrirImagem(src){{document.getElementById('modal-img').src=src;document.getElementById('modal').style.display='flex';}}</script></body></html>'''


def salvar_upload_catalogo(upload):
    """Salva a imagem no Supabase Storage, com fallback para a pasta uploads."""
    return upload_catalog_image(upload, PASTA_UPLOADS)


def salvar_arquivo_biblioteca(upload, produto_nome="produto"):
    """Salva um arquivo individual da memória da empresa."""
    return upload_library_file(upload, produto_nome=produto_nome, local_upload_dir="biblioteca_uploads")

def nome_tipo_arquivo(nome):
    ext = Path(str(nome)).suffix.lower().lstrip(".")
    mapa = {
        "png": "Imagem", "jpg": "Imagem", "jpeg": "Imagem", "webp": "Imagem",
        "pdf": "PDF", "svg": "Vetor/Corte", "stl": "Impressão 3D",
        "cdr": "CorelDRAW", "ai": "Adobe Illustrator", "dxf": "Corte/Laser",
        "zip": "Arquivo compactado", "rar": "Arquivo compactado",
        "mp4": "Vídeo", "mov": "Vídeo", "avi": "Vídeo",
    }
    return mapa.get(ext, ext.upper() if ext else "Arquivo")


# --- SIDEBAR ---
with st.sidebar:
    empresa_sidebar = carregar_config_empresa()
    logo_sidebar_b64, logo_sidebar_ext = encontrar_logo_base64()
    if logo_sidebar_b64:
        mime_sidebar = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".png": "image/png",
        }.get(logo_sidebar_ext, "image/png")
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; width:100%; margin:4px 0 12px 0;">
                <img src="data:{mime_sidebar};base64,{logo_sidebar_b64}"
                     style="display:block; width:140px; max-width:72%; height:auto; object-fit:contain; margin:0 auto;">
            </div>
            <div style="text-align:center; width:100%;">
                <div style="font-size:1.15rem; font-weight:800; letter-spacing:.5px;">{html.escape(str(empresa_sidebar.get("nome_maiusculo", empresa_sidebar.get("nome", "EMPRESA"))))}</div>
                <div style="font-size:.82rem; opacity:.75; margin-top:5px;">{html.escape(str(empresa_sidebar.get("subtitulo", "")))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='text-align:center'><div style='font-size:1.15rem;font-weight:800'>"
            + html.escape(str(empresa_sidebar.get("nome_maiusculo", empresa_sidebar.get("nome", "EMPRESA"))))
            + "</div><div style='font-size:.82rem;opacity:.75;margin-top:5px'>"
            + html.escape(str(empresa_sidebar.get("subtitulo", "")))
            + "</div></div>",
            unsafe_allow_html=True,
        )
    st.divider()
    st.subheader("🔒 Painel de Segurança")
    conectado, mensagem_banco = connection_test()
    if conectado:
        st.success("🟢 Banco online conectado")
    else:
        st.warning(f"🟡 {mensagem_banco}")

    email_detectado = obter_email_usuario_autenticado()
    if email_detectado in USUARIOS_ADMIN:
        usuario_sidebar = USUARIOS_ADMIN[email_detectado]
        st.caption(f"👤 {usuario_sidebar['nome']} • {usuario_sidebar['perfil']}")
    else:
        st.selectbox(
            "👤 Usuário atual",
            ["Anna", "Jorge"],
            key="usuario_atual_fallback",
            help="A identificação automática funciona quando o login Google/OIDC está configurado no Streamlit.",
        )
        st.caption("Acesso administrativo completo")

    h_atual = carregar_historico()
    st.download_button("📥 BAIXAR BACKUP", data=json.dumps(h_atual, ensure_ascii=False, indent=4), file_name="backup_historico.json", mime="application/json", type="primary", use_container_width=True)
    st.download_button("📦 BACKUP DO CATÁLOGO", data=json.dumps(carregar_catalogo(), ensure_ascii=False, indent=4), file_name="backup_catalogo.json", mime="application/json", use_container_width=True)
    st.download_button("👥 BACKUP DE CLIENTES", data=json.dumps(carregar_clientes(), ensure_ascii=False, indent=4), file_name="backup_clientes.json", mime="application/json", use_container_width=True)

    dados_sidebar_at = carregar_atendimentos()
    abertos_sidebar_at = [a for a in dados_sidebar_at.get("itens", []) if a.get("status") not in ("Entregue", "Pós-venda", "Arquivado")]
    if abertos_sidebar_at:
        st.divider()
        st.markdown("**📱 Atendimento agora**")
        st.caption(f"🔔 {len(abertos_sidebar_at)} pendente(s) · 💰 {sum(1 for a in abertos_sidebar_at if 'Orçamento' in str(a.get('status', '')))} orçamento(s)")
        urgentes_sidebar = sum(1 for a in abertos_sidebar_at if faixa_sla_atendimento(a, dados_sidebar_at.get("config"))[2] == 3)
        if urgentes_sidebar:
            st.error(f"{urgentes_sidebar} atendimento(s) urgente(s)")

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
    st.caption(str(empresa_sidebar.get("slogan", "")))

# --- ESTADO DO FORMULÁRIO ---
empresa_form = carregar_config_empresa()
def iniciar_estado(nome, valor):
    if nome not in st.session_state:
        st.session_state[nome] = valor

iniciar_estado("form_cliente", "")
iniciar_estado("form_documento", "")
iniciar_estado("form_whatsapp", "")
iniciar_estado("form_desconto", 0.0)
iniciar_estado("form_entrega", hoje_local())
iniciar_estado("form_prazo", str(empresa_form.get("prazo_padrao", "10")))
iniciar_estado("form_frete", str(empresa_form.get("frete_padrao", "Retirada em Itatiba")))
iniciar_estado("form_validade", str(empresa_form.get("validade_padrao", "5")))
iniciar_estado("editar_numero", None)
iniciar_estado("alerta_proposta_numero", None)

# Deve acontecer antes da criação dos widgets vinculados às chaves form_*.
aplicar_limpeza_formulario_pendente()
aplicar_proposta_pendente_no_formulario()

# --- ALERTAS DE ENTREGA MELHORADOS ---
hoje = hoje_local()
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

_dados_atendimento_badge = carregar_atendimentos()
_qtd_atendimento_badge = sum(1 for _a in _dados_atendimento_badge.get("itens", []) if _a.get("status") not in ("Entregue", "Pós-venda", "Arquivado"))
_rotulo_atendimento = f"📥 Atendimento ({_qtd_atendimento_badge})" if _qtd_atendimento_badge else "📥 Atendimento"

aba0, aba_atendimento, aba1, aba2, aba3, aba4, aba5, aba6, aba8, aba9, aba7 = st.tabs([
    "🏠 Central do Dia",
    _rotulo_atendimento,
    "➕ Novo Orçamento",
    "📋 Histórico",
    "🎯 Fluxo de Pedidos",
    "📊 Relatórios",
    "📦 Catálogo",
    "👥 Clientes",
    "🧠 Memória",
    "📅 Calendário Comercial",
    "⚙️ Configurações",
])

with aba0:
    usuario_atual = obter_usuario_atual()
    empresa_central = carregar_config_empresa()
    hoje_central = hoje_local()
    dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    data_extenso = f"{dias_semana[hoje_central.weekday()]}, {hoje_central.day} de {meses[hoje_central.month-1]} de {hoje_central.year}"

    st.markdown(
        f"<h1 style='text-align:center;margin-bottom:4px;'>☀️ {html.escape(saudacao_por_hora(usuario_atual['nome']))}</h1>"
        f"<p style='text-align:center;color:#6b7280;margin-top:0;'>{html.escape(data_extenso.capitalize())}</p>"
        f"<p style='text-align:center;font-style:italic;'>{html.escape(str(empresa_central.get('slogan', '')))}</p>",
        unsafe_allow_html=True,
    )
    if not usuario_atual.get("automatico"):
        st.caption("A saudação está usando o usuário selecionado na barra lateral. Para identificação automática por e-mail, configure o login Google/OIDC do Streamlit.")

    historico_central = carregar_historico()
    tarefas_central = sincronizar_producao_com_propostas()
    tarefas_ativas_central = [t for t in tarefas_central if t.get("ativa", True)]

    entregas_hoje_central = [p for p in historico_central if data_entrega_segura(p.get("data_entrega")) == hoje_central and not p.get("entregue", False)]
    pedidos_atrasados_central = [p for p in historico_central if (data_entrega_segura(p.get("data_entrega")) or date.max) < hoje_central and not p.get("entregue", False)]
    aguardando_aprovacao_central = [t for t in tarefas_ativas_central if normalizar_status_fluxo(t.get("status")) == "Aguardando aprovação"]
    em_producao_central = [t for t in tarefas_ativas_central if normalizar_status_fluxo(t.get("status")) in ["Pronto para produzir", "Em produção", "Montagem/acabamento"]]
    prontos_central = [t for t in tarefas_ativas_central if normalizar_status_fluxo(t.get("status")) == "Pronto"]
    pendentes_pagamento_central = [p for p in historico_central if not p.get("pago", False) and not p.get("entregue", False)]
    valor_previsto_hoje = sum(calcular_valores_proposta(p)[2] for p in entregas_hoje_central)

    dados_atendimento_central = carregar_atendimentos()
    atendimentos_abertos_central = [a for a in dados_atendimento_central.get("itens", []) if a.get("status") not in ("Entregue", "Pós-venda", "Arquivado")]
    orcamentos_whatsapp_central = [a for a in atendimentos_abertos_central if a.get("status") in ("Orçamento solicitado", "Orçamento em elaboração")]
    catalogos_whatsapp_central = [a for a in atendimentos_abertos_central if a.get("status") == "Catálogo solicitado"]
    aguardando_resposta_central = [a for a in atendimentos_abertos_central if minutos_aguardando(a) >= 30]
    if atendimentos_abertos_central:
        st.subheader("📥 Caixa de atendimento")
        wa1, wa2, wa3, wa4 = st.columns(4)
        wa1.metric("Novos / pendentes", len(atendimentos_abertos_central))
        wa2.metric("Orçamentos", len(orcamentos_whatsapp_central))
        wa3.metric("Catálogos", len(catalogos_whatsapp_central))
        wa4.metric("Aguardando +30 min", len(aguardando_resposta_central))
        mais_urgentes = sorted(atendimentos_abertos_central, key=minutos_aguardando, reverse=True)[:5]
        for item in mais_urgentes:
            mins = minutos_aguardando(item)
            cor = "🔴" if mins >= 60 else "🟡" if mins >= 30 else "🟢"
            st.write(f"{cor} **{item.get('cliente', 'Contato')}** · {item.get('status', 'Novo contato')} · há {mins} min")
        st.caption("Abra a aba Atendimento para responder, classificar ou criar orçamento.")
        st.divider()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🚨 Atrasados", len(pedidos_atrasados_central))
    c2.metric("📦 Entregas hoje", len(entregas_hoje_central))
    c3.metric("🟡 Aprovação", len(aguardando_aprovacao_central))
    c4.metric("🔵 Em produção", len(em_producao_central))
    c5.metric("✅ Prontos", len(prontos_central))
    c6.metric("💰 Previsto hoje", f"R$ {valor_previsto_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.divider()
    st.subheader("🎯 O que fazer agora")
    prioridade = None
    motivo = ""
    if pedidos_atrasados_central:
        prioridade = sorted(pedidos_atrasados_central, key=lambda p: data_entrega_segura(p.get("data_entrega")) or date.max)[0]
        motivo = "Pedido atrasado — verificar imediatamente"
    elif entregas_hoje_central:
        prioridade = entregas_hoje_central[0]
        motivo = "Entrega prevista para hoje"
    elif aguardando_aprovacao_central:
        tarefa = aguardando_aprovacao_central[0]
        prioridade = next((p for p in historico_central if p.get("numero_proposta") == tarefa.get("numero_proposta")), None)
        motivo = "Aguardando aprovação do cliente"
    elif pendentes_pagamento_central:
        prioridade = pendentes_pagamento_central[0]
        motivo = "Pagamento pendente"

    if prioridade:
        _, _, total_prioridade = calcular_valores_proposta(prioridade)
        with st.container(border=True):
            st.markdown(f"### {html.escape(str(prioridade.get('cliente_nome', 'Cliente')))}")
            st.write(f"**Pedido:** {prioridade.get('numero_proposta', '—')}  •  **Entrega:** {prioridade.get('data_entrega', 'A combinar')}")
            st.write(f"**Motivo:** {motivo}")
            st.write(f"**Valor:** R$ {total_prioridade:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            if st.button("📋 Selecionar no Histórico", key="central_abrir_prioridade", type="primary"):
                st.session_state.alerta_proposta_numero = prioridade.get("numero_proposta")
                st.info("Pedido selecionado. Abra a aba Histórico para consultar os detalhes.")
    else:
        st.success("Nenhuma prioridade crítica neste momento. Tudo em dia!")

    st.divider()
    st.subheader("🚨 Atenção")
    alertas_central = []
    for p in pedidos_atrasados_central[:5]:
        alertas_central.append(("🚨", p.get("numero_proposta"), p.get("cliente_nome"), f"Atrasado desde {p.get('data_entrega', '—')}"))
    for p in entregas_hoje_central[:5]:
        alertas_central.append(("📦", p.get("numero_proposta"), p.get("cliente_nome"), "Entrega hoje"))
    for t in aguardando_aprovacao_central[:5]:
        alertas_central.append(("🟡", t.get("numero_proposta"), t.get("cliente_nome"), "Aguardando aprovação"))
    if alertas_central:
        for icone, numero, cliente, texto in alertas_central[:10]:
            st.write(f"{icone} **{numero} — {cliente}** · {texto}")
    else:
        st.info("Nenhum alerta importante agora.")

    st.divider()
    st.subheader("🎯 Oportunidades comerciais")
    oportunidades_central = campanhas_em_oportunidade(hoje_central, limite_dias=90)
    if oportunidades_central:
        for oportunidade in oportunidades_central[:5]:
            inicio = oportunidade.get("inicio_calculado")
            fim = oportunidade.get("fim_calculado")
            dias = oportunidade.get("dias_para_inicio", 0)
            if oportunidade.get("em_periodo"):
                chamada = "Campanha em andamento"
            elif dias == 0:
                chamada = "Começa hoje"
            elif dias == 1:
                chamada = "Começa amanhã"
            else:
                chamada = f"Faltam {dias} dias"
            produtos = oportunidade.get("produtos", []) or []
            with st.container(border=True):
                cc1, cc2 = st.columns([5, 2])
                cc1.markdown(f"**{oportunidade.get('nome', 'Campanha')}** · {chamada}")
                cc1.caption(
                    f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')} · "
                    f"{oportunidade.get('tipo', 'Personalizada')}"
                )
                if produtos:
                    cc1.write("Produtos sugeridos: " + ", ".join(map(str, produtos[:6])))
                cc2.info(f"Preparar com {int(oportunidade.get('antecedencia_dias', 30) or 30)} dias")
        st.caption("Cadastre datas locais, escolares e campanhas próprias na aba Calendário Comercial.")
    else:
        st.info("Nenhuma campanha próxima. Use o Calendário Comercial para cadastrar novas oportunidades.")

    st.divider()
    st.subheader("🔎 Pesquisa rápida")
    busca_central = st.text_input("Cliente, telefone, pedido, produto ou tema", key="busca_central_dia").strip().lower()
    if busca_central:
        resultados = [p for p in historico_central if busca_central in normalizar_texto_busca(p)]
        st.caption(f"{len(resultados)} resultado(s)")
        for p in resultados[:10]:
            _, _, total_resultado = calcular_valores_proposta(p)
            st.write(f"• **{p.get('numero_proposta', '—')} — {p.get('cliente_nome', 'Cliente')}** · {p.get('data_entrega', 'Sem data')} · R$ {total_resultado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

with aba_atendimento:
    st.header("📥 Central de Atendimento")
    st.caption("Organize contatos do WhatsApp em modo manual, assistido ou automático. A integração oficial poderá ser conectada depois sem alterar este fluxo.")
    dados_at = carregar_atendimentos()
    config_at = dados_at["config"]
    itens_at = dados_at["itens"]

    tab_fila, tab_novo, tab_config = st.tabs(["📋 Fila de atendimento", "➕ Registrar contato", "⚙️ Modos e automações"])

    with tab_fila:
        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        busca_at = f1.text_input("Pesquisar cliente, telefone ou mensagem", key="busca_atendimento").strip().lower()
        status_filtro = f2.selectbox("Status", ["Todos"] + STATUS_ATENDIMENTO, key="filtro_status_at")
        prioridade_filtro = f3.selectbox("Prioridade", ["Todas", "Urgente", "Alta", "Normal", "Baixa"], key="filtro_prior_at")
        responsavel_filtro = f4.selectbox("Responsável", ["Todos", "Anna", "Jorge", "Sem responsável"], key="filtro_resp_at")
        filtrados = []
        for item in itens_at:
            base = " ".join(str(item.get(k, "")) for k in ["cliente", "telefone", "mensagem", "status", "assunto", "responsavel"]).lower()
            if busca_at and busca_at not in base:
                continue
            if status_filtro != "Todos" and item.get("status") != status_filtro:
                continue
            if prioridade_filtro != "Todas" and item.get("prioridade", "Normal") != prioridade_filtro:
                continue
            resp_item = str(item.get("responsavel", "")).strip() or "Sem responsável"
            if responsavel_filtro != "Todos" and resp_item != responsavel_filtro:
                continue
            filtrados.append(item)

        # Primeiro aparecem os itens com SLA mais crítico; depois, os mais antigos.
        filtrados = sorted(
            filtrados,
            key=lambda x: (
                x.get("status") in ("Arquivado", "Entregue", "Pós-venda"),
                -faixa_sla_atendimento(x, config_at)[2],
                -minutos_aguardando(x),
            ),
        )
        m1, m2, m3, m4, m5 = st.columns(5)
        abertos = [x for x in itens_at if x.get("status") not in ("Arquivado", "Entregue", "Pós-venda")]
        m1.metric("Em aberto", len(abertos))
        m2.metric("Orçamentos", sum(1 for x in abertos if "Orçamento" in x.get("status", "")))
        m3.metric("Catálogos", sum(1 for x in abertos if x.get("status") == "Catálogo solicitado"))
        m4.metric("Atenção", sum(1 for x in abertos if faixa_sla_atendimento(x, config_at)[2] == 2))
        m5.metric("Urgentes", sum(1 for x in abertos if faixa_sla_atendimento(x, config_at)[2] == 3))

        if not filtrados:
            st.info("Nenhum atendimento encontrado.")
        for item in filtrados:
            icone_sla, rotulo_sla, _ = faixa_sla_atendimento(item, config_at)
            tempo_txt = tempo_aguardando_formatado(item)
            responsavel_atual = str(item.get("responsavel", "")).strip() or "Sem responsável"
            titulo = f"{icone_sla} {item.get('cliente', 'Contato')} · {item.get('status', 'Novo contato')} · {tempo_txt} · {responsavel_atual}"
            with st.expander(titulo):
                st.caption(f"SLA: {rotulo_sla} · Próxima ação sugerida: **{proxima_acao_atendimento(item)}**")
                a1, a2 = st.columns([2, 1])
                with a1:
                    st.write(f"**WhatsApp:** {item.get('telefone') or 'Não informado'}")
                    st.write(f"**Mensagem:** {item.get('mensagem') or 'Sem mensagem registrada'}")
                    st.caption(f"Criado em {item.get('criado_em', '—')} · Origem: {item.get('origem', 'Manual')}")
                    sugestao = resposta_sugerida_atendimento(item)
                    resposta = st.text_area("Resposta sugerida / manual", value=item.get("resposta_rascunho") or sugestao, key=f"resp_{item.get('id')}")
                with a2:
                    novo_status = st.selectbox("Status", STATUS_ATENDIMENTO, index=STATUS_ATENDIMENTO.index(item.get("status")) if item.get("status") in STATUS_ATENDIMENTO else 0, key=f"status_at_{item.get('id')}")
                    nova_prioridade = st.selectbox("Prioridade", ["Urgente", "Alta", "Normal", "Baixa"], index=["Urgente", "Alta", "Normal", "Baixa"].index(item.get("prioridade", "Normal")) if item.get("prioridade", "Normal") in ["Urgente", "Alta", "Normal", "Baixa"] else 2, key=f"prior_at_{item.get('id')}")
                    novo_responsavel = st.selectbox("Responsável", ["Sem responsável", "Anna", "Jorge"], index=["Sem responsável", "Anna", "Jorge"].index(responsavel_atual) if responsavel_atual in ["Sem responsável", "Anna", "Jorge"] else 0, key=f"resp_at_{item.get('id')}")
                    modo_conversa = st.selectbox("Modo desta conversa", ["Manual", "Assistido", "Automático"], index=["Manual", "Assistido", "Automático"].index(item.get("modo", config_at.get("modo", "Manual"))) if item.get("modo", config_at.get("modo", "Manual")) in ["Manual", "Assistido", "Automático"] else 0, key=f"modo_at_{item.get('id')}")

                b1, b2, b3 = st.columns(3)
                if b1.button("💾 Salvar", key=f"salvar_at_{item.get('id')}", use_container_width=True):
                    item.update({"status": novo_status, "prioridade": nova_prioridade, "responsavel": "" if novo_responsavel == "Sem responsável" else novo_responsavel, "modo": modo_conversa, "resposta_rascunho": resposta, "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    salvar_atendimentos(dados_at)
                    st.rerun()
                telefone_limpo = re.sub(r"\D", "", str(item.get("telefone", "")))
                numero_wa = telefone_limpo if telefone_limpo.startswith("55") else f"55{telefone_limpo}"
                link_wa = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(resposta)}" if telefone_limpo else ""
                if link_wa:
                    b2.link_button("📱 Responder", link_wa, use_container_width=True)
                if b3.button("➕ Criar orçamento", key=f"orc_at_{item.get('id')}", use_container_width=True):
                    st.session_state.form_cliente = item.get("cliente", "")
                    st.session_state.form_whatsapp = item.get("telefone", "")
                    st.session_state.form_observacoes = item.get("mensagem", "")
                    item["status"] = "Orçamento em elaboração"
                    item["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                    salvar_atendimentos(dados_at)
                    st.success("Dados preparados. Abra a aba Novo Orçamento.")

                q1, q2, q3, q4 = st.columns(4)
                if q1.button("✅ Atendido", key=f"atendido_{item.get('id')}", use_container_width=True):
                    item.update({"status": "Aguardando cliente", "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if q2.button("⏳ Aguardar cliente", key=f"aguardar_{item.get('id')}", use_container_width=True):
                    item.update({"status": "Aguardando cliente", "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if q3.button("🏁 Concluir", key=f"concluir_{item.get('id')}", use_container_width=True):
                    item.update({"status": "Pós-venda", "concluido_em": agora_local().strftime("%d/%m/%Y %H:%M"), "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if q4.button("📦 Arquivar", key=f"arquivar_{item.get('id')}", use_container_width=True):
                    item.update({"status": "Arquivado", "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    salvar_atendimentos(dados_at)
                    st.rerun()

    with tab_novo:
        st.subheader("Registrar mensagem ou contato")
        n1, n2 = st.columns(2)
        nome_at = n1.text_input("Nome / identificação", key="novo_at_nome")
        telefone_at = n2.text_input("WhatsApp", key="novo_at_telefone")
        mensagem_at = st.text_area("Mensagem recebida", key="novo_at_mensagem", placeholder="Ex.: Gostaria do catálogo de topos e um orçamento para sábado")
        sugestao_status = sugerir_tipo_atendimento(mensagem_at)
        n3, n4, n5 = st.columns(3)
        status_at = n3.selectbox("Classificação", STATUS_ATENDIMENTO, index=STATUS_ATENDIMENTO.index(sugestao_status), key="novo_at_status")
        prioridade_at = n4.selectbox("Prioridade", ["Urgente", "Alta", "Normal", "Baixa"], index=2, key="novo_at_prioridade")
        responsavel_at = n5.selectbox("Responsável", ["Sem responsável", "Anna", "Jorge"], key="novo_at_responsavel")
        if st.button("➕ Adicionar à fila", type="primary", use_container_width=True):
            if not nome_at.strip() and not telefone_at.strip():
                st.warning("Informe pelo menos um nome ou WhatsApp.")
            else:
                itens_at.append({
                    "id": f"AT-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                    "cliente": nome_at.strip() or "Contato sem nome",
                    "telefone": telefone_at.strip(),
                    "mensagem": mensagem_at.strip(),
                    "status": status_at,
                    "prioridade": prioridade_at,
                    "responsavel": "" if responsavel_at == "Sem responsável" else responsavel_at,
                    "modo": config_at.get("modo", "Manual"),
                    "origem": "Registro manual",
                    "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
                })
                salvar_atendimentos(dados_at)
                st.success("Contato incluído na fila.")
                st.rerun()

    with tab_config:
        st.subheader("Modo geral de atendimento")
        modo_geral = st.radio("Escolha como o FestManager deve atuar", ["Manual", "Assistido", "Automático"], index=["Manual", "Assistido", "Automático"].index(config_at.get("modo", "Manual")), horizontal=True)
        st.caption("Manual: apenas alerta. Assistido: prepara a resposta. Automático: permitido somente para respostas simples configuradas abaixo.")
        st.markdown("#### Regras por tipo de mensagem")
        regras = {}
        labels = {"boas_vindas": "Boas-vindas", "catalogo": "Solicitação de catálogo", "orcamento": "Pedido de orçamento", "comprovante": "Comprovante recebido", "aprovacao_arte": "Aprovação de arte", "duvidas_negociacao": "Dúvidas e negociações"}
        for chave, label in labels.items():
            regras[chave] = st.selectbox(label, ["Manual", "Assistido", "Automático"], index=["Manual", "Assistido", "Automático"].index(config_at.get(chave, "Manual")), key=f"regra_{chave}")
        st.markdown("#### Tempo máximo de espera (SLA)")
        sla1, sla2 = st.columns(2)
        sla_atencao = sla1.number_input("Amarelo após (minutos)", min_value=1, max_value=1440, value=int(config_at.get("sla_atencao_min", 30)), step=5)
        sla_urgente = sla2.number_input("Vermelho após (minutos)", min_value=int(sla_atencao) + 1, max_value=2880, value=max(int(sla_atencao) + 1, int(config_at.get("sla_urgente_min", 60))), step=5)
        st.warning("A leitura automática do WhatsApp ainda não está conectada. Esta versão organiza a fila e os modos de atendimento; a conexão oficial exigirá WhatsApp Business Platform e webhook.")
        if st.button("💾 Salvar modos de atendimento", type="primary"):
            config_at.update({"modo": modo_geral, "sla_atencao_min": int(sla_atencao), "sla_urgente_min": int(sla_urgente), **regras})
            salvar_atendimentos(dados_at)
            st.success("Configurações salvas.")
            st.rerun()


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
            numero = st.session_state.editar_numero or f"PROP-{agora_local().strftime('%Y%m%d%H%M%S')}"
            antigo = {}
            if st.session_state.editar_numero:
                antigo = next((p for p in carregar_historico() if p.get("numero_proposta") == numero), {})

            dados = {
                **antigo,
                "numero_proposta": numero,
                "data_geracao": antigo.get("data_geracao", agora_local().strftime("%d/%m/%Y")),
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

            st.divider()
            renderizar_caixa_projeto(prop, prefixo="hist")


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

    def formulario_catalogo(indice_edicao=None):
        item_edicao = (
            catalogo[indice_edicao]
            if indice_edicao is not None and 0 <= indice_edicao < len(catalogo)
            else None
        )
        item_edicao = dict(item_edicao or {})
        sufixo = str(indice_edicao) if indice_edicao is not None else "novo"
        pendente = st.session_state.pop(f"cat_geracao_pendente_{sufixo}", None)
        if isinstance(pendente, dict):
            mapa_campos = {
                "descricao_curta": f"cat_desc_curta_{sufixo}",
                "descricao_completa": f"cat_desc_{sufixo}",
                "palavras_chave": f"cat_palavras_{sufixo}",
                "legenda": f"cat_legenda_{sufixo}",
                "hashtags": f"cat_hashtags_{sufixo}",
                "mercado_livre": f"cat_ml_{sufixo}",
                "shopee": f"cat_shopee_{sufixo}",
            }
            for campo, chave in mapa_campos.items():
                if campo in pendente:
                    st.session_state[chave] = pendente[campo]
            st.session_state[f"cat_geracao_ok_{sufixo}"] = True

        titulo_form = "✏️ Editar produto" if item_edicao else "➕ Adicionar produto"
        st.subheader(titulo_form)
        if item_edicao:
            st.info(f"Editando: {item_edicao.get('Nome', 'Produto')}")

        tab_info, tab_producao, tab_marketing, tab_midias = st.tabs([
            "📦 Informações", "⚙️ Produção", "📣 Marketing", "🧠 Arquivos, artes e fotos"
        ])

        with tab_info:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                categoria_cat = c1.text_input(
                    "Categoria *", value=item_edicao.get("Categoria", ""), key=f"cat_categoria_{sufixo}"
                )
                subcategoria_cat = c1.text_input(
                    "Subcategoria", value=item_edicao.get("Subcategoria", ""), key=f"cat_subcategoria_{sufixo}"
                )
                codigo_cat = c1.text_input(
                    "Código interno", value=item_edicao.get("CodigoInterno", ""), key=f"cat_codigo_{sufixo}"
                )
                nome_cat = c1.text_input(
                    "Nome do produto *", value=item_edicao.get("Nome", ""), key=f"cat_nome_{sufixo}"
                )
                descricao_curta_cat = c1.text_area(
                    "Descrição curta", value=item_edicao.get("DescricaoCurta", item_edicao.get("Descricao", "")),
                    height=100, key=f"cat_desc_curta_{sufixo}"
                )
                descricao_cat = c2.text_area(
                    "Descrição completa", value=item_edicao.get("DescricaoCompleta", item_edicao.get("Descricao", "")),
                    height=180, key=f"cat_desc_{sufixo}"
                )
                preco_cat = c2.text_input(
                    "Preço sugerido", value=str(item_edicao.get("Preco", "")), key=f"cat_preco_{sufixo}"
                )
                custo_cat = c2.text_input(
                    "Custo (opcional)", value=str(item_edicao.get("Custo", "")), key=f"cat_custo_{sufixo}"
                )
                tempo_cat = c2.text_input(
                    "Tempo médio de produção", value=str(item_edicao.get("TempoProducao", "")),
                    placeholder="Ex.: 30 minutos, 2 horas, 3 dias", key=f"cat_tempo_{sufixo}"
                )
                preco_num = valor_float(str(preco_cat).replace("R$", "").replace(".", "").replace(",", "."))
                custo_num = valor_float(str(custo_cat).replace("R$", "").replace(".", "").replace(",", "."))
                if preco_num > 0 and custo_num >= 0:
                    margem = preco_num - custo_num
                    margem_pct = (margem / preco_num * 100) if preco_num else 0
                    c2.caption(f"Margem estimada: R$ {margem:,.2f} ({margem_pct:.1f}%)".replace(",", "X").replace(".", ",").replace("X", "."))

                st.divider()
                st.markdown("#### ✨ Preenchimento automático gratuito")
                st.caption("Informe algumas características e deixe o sistema preparar descrições e textos de marketing. Você poderá revisar tudo antes de salvar.")
                ideias_geracao = st.text_area(
                    "Características, materiais, diferenciais e informações importantes",
                    value=item_edicao.get("IdeiasGeracao", ""),
                    placeholder="Ex.: feito em papel fotográfico, personalizado com nome e idade, acompanha palito, tamanho aproximado...",
                    key=f"cat_ideias_geracao_{sufixo}",
                )
                g1, g2, g3 = st.columns(3)
                gerar_tudo = g1.button("✨ Gerar tudo", use_container_width=True, key=f"cat_gerar_tudo_{sufixo}")
                gerar_descricoes = g2.button("📝 Só descrições", use_container_width=True, key=f"cat_gerar_desc_{sufixo}")
                gerar_marketing = g3.button("📣 Só marketing", use_container_width=True, key=f"cat_gerar_mkt_{sufixo}")

                if gerar_tudo or gerar_descricoes or gerar_marketing:
                    if not nome_cat.strip():
                        st.warning("Informe o nome do produto antes de gerar o conteúdo.")
                    else:
                        gerado = gerar_conteudo_catalogo_gratuito(
                            nome_cat, categoria_cat, subcategoria_cat, ideias_geracao, preco_cat, []
                        )
                        if gerar_descricoes:
                            gerado = {k: v for k, v in gerado.items() if k in {"descricao_curta", "descricao_completa"}}
                        elif gerar_marketing:
                            gerado = {k: v for k, v in gerado.items() if k not in {"descricao_curta", "descricao_completa"}}
                        st.session_state[f"cat_geracao_pendente_{sufixo}"] = gerado
                        st.rerun()

                if st.session_state.pop(f"cat_geracao_ok_{sufixo}", False):
                    st.success("Conteúdo preenchido automaticamente. Revise os textos antes de salvar.")

        with tab_producao:
            st.caption("Marque somente os processos que normalmente fazem parte deste produto.")
            processos_atuais = set(item_edicao.get("Processos", []) or [])
            processos_opcoes = ["Arte", "Impressão", "Corte", "Laser", "Impressão 3D", "Balões", "Montagem", "Acabamento"]
            processos_cat = st.multiselect(
                "Processos necessários", processos_opcoes,
                default=[x for x in processos_opcoes if x in processos_atuais],
                key=f"cat_processos_{sufixo}"
            )
            campos_personalizacao = st.multiselect(
                "Campos de personalização sugeridos",
                ["Tema", "Nome", "Idade", "Cor", "Data do evento", "Tamanho", "Frase", "Observações"],
                default=item_edicao.get("CamposPersonalizacao", ["Tema", "Nome", "Idade", "Cor", "Observações"]),
                key=f"cat_campos_personalizacao_{sufixo}"
            )
            observacao_interna = st.text_area(
                "Observações internas de produção", value=item_edicao.get("ObservacaoInterna", ""),
                key=f"cat_obs_interna_{sufixo}"
            )

        with tab_marketing:
            palavras_chave = st.text_input(
                "Palavras-chave (separadas por vírgula)", value=item_edicao.get("PalavrasChave", ""),
                key=f"cat_palavras_{sufixo}"
            )
            legenda_instagram = st.text_area(
                "Legenda para Instagram/Facebook", value=item_edicao.get("LegendaSocial", ""),
                key=f"cat_legenda_{sufixo}"
            )
            hashtags = st.text_area(
                "Hashtags", value=item_edicao.get("Hashtags", ""), key=f"cat_hashtags_{sufixo}"
            )
            texto_ml = st.text_area(
                "Descrição para Mercado Livre", value=item_edicao.get("DescricaoMercadoLivre", ""),
                key=f"cat_ml_{sufixo}"
            )
            texto_shopee = st.text_area(
                "Descrição para Shopee", value=item_edicao.get("DescricaoShopee", ""),
                key=f"cat_shopee_{sufixo}"
            )

        with tab_midias:
            st.markdown("#### 🧠 Memória do produto")
            st.caption("Adicione os arquivos individualmente conforme forem criados ou encontrados. Eles ficam vinculados a este produto.")
            arquivos_atuais = list(item_edicao.get("ArquivosBiblioteca", []) or [])
            arq_upload = st.file_uploader(
                "➕ Adicionar um arquivo",
                type=None,
                accept_multiple_files=False,
                key=f"cat_arquivo_memoria_{sufixo}",
                help="Aceita imagens, PDF, SVG, STL, ZIP, vídeos e arquivos de produção.",
            )
            ac1, ac2 = st.columns(2)
            arq_categoria = ac1.selectbox(
                "Classificação",
                ["Arte", "Arquivo de produção", "Foto final", "Referência", "Vídeo", "Manual/Dica", "Outro"],
                key=f"cat_arquivo_categoria_{sufixo}",
            )
            arq_tags = ac2.text_input(
                "Tags", placeholder="Ex.: Stitch, azul, menina, laser", key=f"cat_arquivo_tags_{sufixo}"
            )
            arq_descricao = st.text_input(
                "Descrição do arquivo", placeholder="Ex.: arquivo final aprovado para corte", key=f"cat_arquivo_desc_{sufixo}"
            )
            arq_mestre = st.checkbox("⭐ Marcar como arquivo mestre", key=f"cat_arquivo_mestre_{sufixo}")
            if st.button("📤 Enviar e vincular arquivo", key=f"cat_enviar_arquivo_{sufixo}", use_container_width=True):
                if not item_edicao:
                    st.warning("Salve o produto primeiro. Depois abra Editar para adicionar arquivos à memória.")
                elif arq_upload is None:
                    st.warning("Escolha um arquivo para enviar.")
                else:
                    caminho = salvar_arquivo_biblioteca(arq_upload, item_edicao.get("Nome", "produto"))
                    if caminho:
                        if arq_mestre:
                            for arq in arquivos_atuais:
                                arq["mestre"] = False
                        arquivos_atuais.append({
                            "id": f"ARQ-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                            "nome": str(arq_upload.name),
                            "url": caminho,
                            "tipo": nome_tipo_arquivo(arq_upload.name),
                            "categoria": arq_categoria,
                            "tags": [x.strip() for x in arq_tags.split(",") if x.strip()],
                            "descricao": arq_descricao.strip(),
                            "mestre": bool(arq_mestre),
                            "arquivado": False,
                            "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
                        })
                        item_edicao["ArquivosBiblioteca"] = arquivos_atuais
                        catalogo[indice_edicao] = item_edicao
                        salvar_catalogo(catalogo)
                        st.success("Arquivo vinculado com sucesso.")
                        st.rerun()
                    else:
                        st.error("Não foi possível salvar o arquivo.")

            ativos = [(j, a) for j, a in enumerate(arquivos_atuais) if not a.get("arquivado")]
            arquivados = [(j, a) for j, a in enumerate(arquivos_atuais) if a.get("arquivado")]
            if ativos:
                st.markdown(f"##### Arquivos vinculados ({len(ativos)})")
                for j, arq in ativos:
                    with st.container(border=True):
                        i1, i2, i3 = st.columns([1, 5, 2])
                        i1.write("⭐" if arq.get("mestre") else "📄")
                        i2.markdown(f"**{arq.get('nome', 'Arquivo')}**")
                        i2.caption(f"{arq.get('categoria', arq.get('tipo', 'Arquivo'))} • {arq.get('criado_em', '')}")
                        if arq.get("descricao"):
                            i2.write(arq.get("descricao"))
                        if arq.get("tags"):
                            i2.caption("Tags: " + " • ".join(arq.get("tags", [])))
                        if arq.get("url"):
                            i3.link_button("Abrir / baixar", arq.get("url"), use_container_width=True)
                        if i3.button("⭐ Mestre" if not arq.get("mestre") else "✓ Mestre", key=f"arq_mestre_{sufixo}_{j}", use_container_width=True, disabled=bool(arq.get("mestre"))):
                            for outro in arquivos_atuais:
                                outro["mestre"] = False
                            arquivos_atuais[j]["mestre"] = True
                            item_edicao["ArquivosBiblioteca"] = arquivos_atuais
                            catalogo[indice_edicao] = item_edicao
                            salvar_catalogo(catalogo)
                            st.rerun()
                        if i3.button("📦 Arquivar", key=f"arq_arquivar_{sufixo}_{j}", use_container_width=True):
                            arquivos_atuais[j]["arquivado"] = True
                            arquivos_atuais[j]["mestre"] = False
                            item_edicao["ArquivosBiblioteca"] = arquivos_atuais
                            catalogo[indice_edicao] = item_edicao
                            salvar_catalogo(catalogo)
                            st.rerun()
            if arquivados:
                with st.expander(f"📦 Arquivados ({len(arquivados)})"):
                    for j, arq in arquivados:
                        r1, r2 = st.columns([5, 1])
                        r1.write(f"{arq.get('nome', 'Arquivo')} — {arq.get('categoria', '')}")
                        if r2.button("Restaurar", key=f"arq_restaurar_{sufixo}_{j}"):
                            arquivos_atuais[j]["arquivado"] = False
                            item_edicao["ArquivosBiblioteca"] = arquivos_atuais
                            catalogo[indice_edicao] = item_edicao
                            salvar_catalogo(catalogo)
                            st.rerun()

            st.divider()
            st.markdown("#### 🖼️ Galeria e publicação")
            urls_existentes = [x for x in (item_edicao.get("Imagens", []) or []) if str(x).startswith("http")]
            urls_cat = st.text_area(
                "URLs de imagens (uma por linha)", value="\n".join(urls_existentes),
                key=f"cat_urls_{sufixo}"
            )
            fotos_cat = st.file_uploader(
                "Enviar uma ou mais fotos", type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True, key=f"cat_fotos_{sufixo}"
            )
            publicar_site = st.checkbox(
                "Publicar no site/catálogo online", value=bool(item_edicao.get("PublicarSite", False)),
                key=f"cat_publicar_{sufixo}"
            )
            destaque_cat = st.checkbox(
                "Produto em destaque", value=bool(item_edicao.get("Destaque", False)),
                key=f"cat_destaque_{sufixo}"
            )
            if item_edicao.get("Imagens"):
                st.caption(f"{len(item_edicao.get('Imagens', []))} imagem(ns) já cadastrada(s).")

        b1, b2 = st.columns(2)
        salvar = b1.button(
            "💾 Salvar alterações" if item_edicao else "💾 Salvar produto", type="primary",
            use_container_width=True, key=f"cat_salvar_{sufixo}"
        )
        cancelar = b2.button(
            "↩️ Cancelar edição" if item_edicao else "🧹 Limpar", use_container_width=True,
            key=f"cat_cancelar_{sufixo}"
        )

        if salvar:
            if not nome_cat.strip() or not categoria_cat.strip():
                st.warning("Informe pelo menos o nome e a categoria.")
            else:
                imagens = [u.strip() for u in urls_cat.splitlines() if u.strip()]
                imagens.extend([x for x in item_edicao.get("Imagens", []) if not str(x).startswith("http")])
                for foto in fotos_cat or []:
                    caminho_novo = salvar_upload_catalogo(foto)
                    if caminho_novo:
                        imagens.insert(0, caminho_novo)
                # Mantém campos futuros/desconhecidos existentes ao editar.
                registro = dict(item_edicao)
                registro.update({
                    "Nome": nome_cat.strip(), "Categoria": categoria_cat.strip(),
                    "Subcategoria": subcategoria_cat.strip(), "CodigoInterno": codigo_cat.strip(),
                    "Imagens": list(dict.fromkeys(imagens)),
                    "Descricao": descricao_curta_cat.strip() or descricao_cat.strip(),
                    "DescricaoCurta": descricao_curta_cat.strip(), "DescricaoCompleta": descricao_cat.strip(),
                    "IdeiasGeracao": ideias_geracao.strip(),
                    "Preco": preco_cat.strip(), "Custo": custo_cat.strip(), "TempoProducao": tempo_cat.strip(),
                    "Processos": processos_cat, "CamposPersonalizacao": campos_personalizacao,
                    "ObservacaoInterna": observacao_interna.strip(), "PalavrasChave": palavras_chave.strip(),
                    "LegendaSocial": legenda_instagram.strip(), "Hashtags": hashtags.strip(),
                    "DescricaoMercadoLivre": texto_ml.strip(), "DescricaoShopee": texto_shopee.strip(),
                    "PublicarSite": publicar_site, "Destaque": destaque_cat,
                    "ArquivosBiblioteca": list(item_edicao.get("ArquivosBiblioteca", []) or []),
                    "AtualizadoEm": agora_local().isoformat(timespec="seconds"),
                })
                if item_edicao:
                    catalogo[indice_edicao] = registro
                else:
                    registro["CriadoEm"] = agora_local().isoformat(timespec="seconds")
                    catalogo.append(registro)
                salvar_catalogo(catalogo)
                st.session_state.catalogo_edit_index = None
                st.success("Produto salvo com sucesso.")
                st.rerun()

        if cancelar:
            st.session_state.catalogo_edit_index = None
            for chave in list(st.session_state.keys()):
                if str(chave).startswith("cat_") and str(chave).endswith(f"_{sufixo}"):
                    st.session_state.pop(chave, None)
            st.rerun()

    # Quando o usuário clica em Editar, o formulário ocupa a tela do catálogo.
    # Isso evita o problema de o Streamlit permanecer na aba "Produtos" após o rerun.
    if st.session_state.catalogo_edit_index is not None:
        formulario_catalogo(st.session_state.catalogo_edit_index)
    else:
        aba_cad, aba_lista, aba_cliente = st.tabs([
            "➕ Cadastrar",
            "📋 Produtos",
            "📤 Catálogo para cliente",
        ])

        with aba_cad:
            formulario_catalogo(None)

        with aba_lista:
            termo_cat = st.text_input(
                "🔎 Pesquisar produto ou categoria",
                key="pesquisa_catalogo",
            ).strip().lower()
            filtrados = [
                (i, p) for i, p in enumerate(catalogo)
                if not termo_cat
                or termo_cat in (f"{p.get('Nome','')} {p.get('Categoria','')} {p.get('Subcategoria','')} {p.get('CodigoInterno','')} {p.get('Descricao','')} {p.get('PalavrasChave','')} " + " ".join(
                    f"{a.get('nome','')} {a.get('descricao','')} {' '.join(a.get('tags', []) or [])}"
                    for a in (p.get('ArquivosBiblioteca', []) or [])
                )).lower()
            ]
            st.write(f"**{len(filtrados)} produto(s)**")
            for i, produto_cat in filtrados:
                with st.container(border=True):
                    cimg, cinfo, cacoes = st.columns([1, 5, 2])
                    imgs = produto_cat.get("Imagens", []) or []
                    if imgs:
                        try:
                            cimg.image(imgs[0], width=100)
                        except Exception:
                            cimg.write("📷")
                    else:
                        cimg.write("📷")
                    nome_produto = str(produto_cat.get("Nome", "Produto"))
                    cinfo.markdown(f"### {'⭐ ' if produto_cat.get('Destaque') else ''}{nome_produto}")
                    subt = str(produto_cat.get("Subcategoria", "")).strip()
                    categoria_txt = str(produto_cat.get("Categoria", "")) + (f" / {subt}" if subt else "")
                    cinfo.write(
                        f"**Categoria:** {categoria_txt}  |  "
                        f"**Preço:** {formatar_preco_catalogo(produto_cat.get('Preco'))}"
                    )
                    descricao_lista = produto_cat.get("DescricaoCurta", produto_cat.get("Descricao", ""))
                    cinfo.caption(descricao_lista)
                    # Estatísticas calculadas a partir do histórico, sem duplicar dados no produto.
                    vendas_qtd = 0.0
                    vendas_valor = 0.0
                    ultima_venda = "—"
                    for proposta_hist in carregar_historico():
                        for item_hist in proposta_hist.get("itens", []) or []:
                            if str(item_hist.get("produto", "")).strip().casefold() == nome_produto.strip().casefold():
                                qtd_hist = valor_float(item_hist.get("quantidade", 0))
                                unit_hist = valor_float(item_hist.get("valor_unitario", 0))
                                vendas_qtd += qtd_hist
                                vendas_valor += qtd_hist * unit_hist
                                if ultima_venda == "—":
                                    ultima_venda = str(proposta_hist.get("data_geracao", "—"))
                    cinfo.caption(
                        f"Vendido: {vendas_qtd:g} un. | Receita histórica: {formatar_preco_catalogo(vendas_valor)} | Última venda: {ultima_venda}"
                    )
                    processos_lista = produto_cat.get("Processos", []) or []
                    if processos_lista:
                        cinfo.caption("Processos: " + " • ".join(processos_lista))
                    arquivos_memoria = [a for a in (produto_cat.get("ArquivosBiblioteca", []) or []) if not a.get("arquivado")]
                    if arquivos_memoria:
                        mestres = sum(1 for a in arquivos_memoria if a.get("mestre"))
                        cinfo.caption(f"🧠 Memória: {len(arquivos_memoria)} arquivo(s)" + (f" • {mestres} mestre" if mestres else ""))
                    if produto_cat.get("PublicarSite"):
                        cinfo.success("🌐 Marcado para publicação no site")
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
                        st.session_state.temp_itens.append({
                            "produto": produto_cat.get("Nome", ""),
                            "especificacoes": produto_cat.get("Descricao", ""),
                            "quantidade": 1,
                            "valor_unitario": preco_num,
                        })
                        st.success("Produto adicionado ao orçamento. Abra a aba Novo Orçamento.")

        with aba_cliente:
            if not catalogo:
                st.info("Cadastre produtos para gerar um catálogo.")
            else:
                categorias_disponiveis = sorted({
                    str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria"
                    for p in catalogo
                })
                titulo_cliente = st.text_input(
                    "Título do catálogo",
                    value="Seleção Alphafest",
                    key="titulo_catalogo_cliente",
                )
                categorias_cliente = st.multiselect(
                    "Categorias",
                    categorias_disponiveis,
                    default=categorias_disponiveis[:1],
                    key="categorias_catalogo_cliente",
                )
                produtos_base = [
                    p for p in catalogo
                    if (str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria")
                    in categorias_cliente
                ]
                nomes_disponiveis = [str(p.get("Nome", "Produto")) for p in produtos_base]
                nomes_selecionados = st.multiselect(
                    "Produtos específicos",
                    nomes_disponiveis,
                    default=nomes_disponiveis,
                    key="produtos_catalogo_cliente",
                )
                mostrar_precos = st.checkbox(
                    "Mostrar preços",
                    value=True,
                    key="mostrar_precos_catalogo",
                )
                selecao_cliente = [
                    p for p in produtos_base
                    if str(p.get("Nome", "Produto")) in nomes_selecionados
                ]
                st.caption(f"O catálogo do cliente terá {len(selecao_cliente)} produto(s).")
                html_cliente = gerar_html_catalogo(
                    selecao_cliente,
                    titulo_cliente or "Seleção Alphafest",
                    mostrar_precos,
                )
                st.download_button(
                    "📥 Gerar catálogo HTML para o cliente",
                    data=html_cliente,
                    file_name=f"{slug_html(titulo_cliente).lower()}.html",
                    mime="text/html",
                    type="primary",
                    use_container_width=True,
                )
                st.download_button(
                    "📚 Gerar catálogo completo",
                    data=gerar_html_catalogo(catalogo, "Catálogo Completo Alphafest", True),
                    file_name="catalogo_completo_alphafest.html",
                    mime="text/html",
                    use_container_width=True,
                )

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
            base = " ".join(str(cli.get(c, "")) for c in ["nome", "documento", "whatsapp", "email", "observacoes", "cidade", "origem_cliente", "segmentos", "interesses", "campanhas_interesse"]).lower()
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
                    st.write(f"**Cidade:** {cli.get('cidade') or 'Não informado'}")
                    if cli.get("segmentos"):
                        st.write("**Perfis:** " + ", ".join(cli.get("segmentos", [])))
                    if cli.get("interesses"):
                        st.write("**Interesses:** " + ", ".join(cli.get("interesses", [])))
                    st.write(f"**Potencial comercial:** {'⭐' * int(cli.get('potencial', 0) or 0) or 'Não avaliado'}")
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
        cli_email = c2.text_input("E-mail (opcional)", value=cliente_edicao.get("email", "") if cliente_edicao else "", key=f"cli_email_{edit_id}")
        cli_aniv = c2.text_input("Aniversário / Data especial (opcional)", value=cliente_edicao.get("aniversario", "") if cliente_edicao else "", key=f"cli_aniv_{edit_id}")
        cli_cidade = c2.text_input("Cidade (opcional)", value=cliente_edicao.get("cidade", "") if cliente_edicao else "", key=f"cli_cidade_{edit_id}")
        segmentos_disponiveis = carregar_segmentos()
        cli_segmentos = st.multiselect("Perfis comerciais (opcional, pode marcar vários)", segmentos_disponiveis, default=cliente_edicao.get("segmentos", []) if cliente_edicao else [], key=f"cli_segmentos_{edit_id}")
        cli_interesses = st.multiselect("Interesses (opcional)", INTERESSES_PADRAO, default=cliente_edicao.get("interesses", []) if cliente_edicao else [], key=f"cli_interesses_{edit_id}")
        campanhas_nomes = [c.get("nome") for c in carregar_campanhas() if c.get("ativa", True)]
        cli_campanhas = st.multiselect("Campanhas de interesse (opcional)", campanhas_nomes, default=cliente_edicao.get("campanhas_interesse", []) if cliente_edicao else [], key=f"cli_campanhas_{edit_id}")
        cli_potencial = st.slider("Potencial comercial (opcional)", 0, 5, int(cliente_edicao.get("potencial", 0) or 0) if cliente_edicao else 0, help="0 = ainda não avaliado; 5 = alto potencial")
        opcoes_origem = ["Não informado", "WhatsApp", "Instagram", "Facebook", "TikTok", "Google", "Indicação", "Mercado Livre", "Shopee", "Loja", "Outro"]
        origem_atual = cliente_edicao.get("origem_cliente", "Não informado") if cliente_edicao else "Não informado"
        if origem_atual not in opcoes_origem:
            origem_atual = "Não informado"
        cli_origem = st.selectbox("Origem do cliente (opcional)", opcoes_origem, index=opcoes_origem.index(origem_atual), key=f"cli_origem_cliente_{edit_id}")
        cli_obs = st.text_area("Observações internas (opcional)", value=cliente_edicao.get("observacoes", "") if cliente_edicao else "", key=f"cli_obs_{edit_id}")
        st.caption("Somente o nome/identificação é necessário. O cadastro pode ser enriquecido aos poucos, sem bloquear o atendimento.")
        with st.expander("⚙️ Gerenciar perfis comerciais"):
            novo_segmento = st.text_input("Adicionar novo perfil/segmento", key=f"novo_segmento_{edit_id}")
            gs1, gs2 = st.columns(2)
            if gs1.button("Adicionar perfil", key=f"add_segmento_{edit_id}", use_container_width=True):
                if novo_segmento.strip():
                    salvar_segmentos(carregar_segmentos() + [novo_segmento.strip()])
                    st.rerun()
            segmento_remover = gs2.selectbox("Remover perfil", ["—"] + carregar_segmentos(), key=f"rem_segmento_{edit_id}")
            if st.button("Remover perfil selecionado", key=f"btn_rem_segmento_{edit_id}") and segmento_remover != "—":
                salvar_segmentos([x for x in carregar_segmentos() if x != segmento_remover])
                st.rerun()
        ac1, ac2 = st.columns(2)
        if ac1.button("💾 Salvar cliente", type="primary", use_container_width=True):
            if not cli_nome.strip():
                st.warning("Informe o nome do cliente.")
            else:
                registro_cli = {
                    "id": cliente_edicao.get("id") if cliente_edicao else f"CLI-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                    "nome": cli_nome.strip(),
                    "documento": cli_doc.strip(),
                    "whatsapp": cli_wa.strip(),
                    "email": cli_email.strip(),
                    "aniversario": cli_aniv.strip(),
                    "cidade": cli_cidade.strip(),
                    "segmentos": cli_segmentos,
                    "interesses": cli_interesses,
                    "campanhas_interesse": cli_campanhas,
                    "potencial": cli_potencial,
                    "origem_cliente": "" if cli_origem == "Não informado" else cli_origem,
                    "observacoes": cli_obs.strip(),
                    "origem": cliente_edicao.get("origem", "Cadastro manual") if cliente_edicao else "Cadastro manual",
                    "criado_em": cliente_edicao.get("criado_em", agora_local().strftime("%d/%m/%Y %H:%M")) if cliente_edicao else agora_local().strftime("%d/%m/%Y %H:%M"),
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



with aba8:
    st.header("🧠 Memória da Empresa")
    st.caption("Encontre projetos, temas, clientes, produtos e arquivos em poucos segundos.")
    projetos_memoria = carregar_projetos()
    busca_memoria = st.text_input(
        "🔎 Pesquisar na memória",
        placeholder="Tema, cliente, produto, pedido, arquivo ou tag",
        key="busca_memoria_empresa",
    ).strip().lower()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Projetos", len(projetos_memoria))
    m2.metric("Modelos", sum(1 for p in projetos_memoria if p.get("modelo")))
    m3.metric("Favoritos", sum(1 for p in projetos_memoria if p.get("favorito")))
    m4.metric("Arquivos", sum(len([a for a in p.get("arquivos", []) or [] if not a.get("arquivado")]) for p in projetos_memoria))

    if busca_memoria:
        projetos_filtrados = [p for p in projetos_memoria if busca_memoria in texto_busca_projeto(p)]
    else:
        projetos_filtrados = projetos_memoria

    filtro_memoria = st.radio(
        "Mostrar",
        ["Todos", "Modelos reutilizáveis", "Favoritos"],
        horizontal=True,
        key="filtro_memoria",
    )
    if filtro_memoria == "Modelos reutilizáveis":
        projetos_filtrados = [p for p in projetos_filtrados if p.get("modelo")]
    elif filtro_memoria == "Favoritos":
        projetos_filtrados = [p for p in projetos_filtrados if p.get("favorito")]

    st.caption(f"{len(projetos_filtrados)} projeto(s) encontrado(s)")
    if not projetos_filtrados:
        st.info("A memória será preenchida conforme as Caixas de Projeto forem abertas no Histórico.")
    for projeto in projetos_filtrados:
        estrelas = "⭐ " if projeto.get("favorito") else ""
        modelo_txt = " • ♻️ Modelo" if projeto.get("modelo") else ""
        titulo = f"{estrelas}{projeto.get('numero_proposta') or projeto.get('id')} — {projeto.get('cliente_nome') or 'Cliente'}{modelo_txt}"
        with st.expander(titulo):
            c1, c2 = st.columns(2)
            c1.write(f"**Tema:** {projeto.get('tema') or 'Não informado'}")
            c1.write(f"**Produtos:** {', '.join(projeto.get('produtos', []) or []) or 'Não informado'}")
            c2.write(f"**Entrega:** {projeto.get('data_entrega') or 'Não informada'}")
            c2.write(f"**Atualizado:** {projeto.get('atualizado_em') or projeto.get('criado_em', '')}")
            if projeto.get("observacoes"):
                st.write(f"**Observações:** {projeto.get('observacoes')}")
            arquivos = [a for a in projeto.get("arquivos", []) or [] if not a.get("arquivado")]
            if arquivos:
                st.markdown("#### Arquivos")
                for arq in arquivos:
                    x1, x2 = st.columns([5, 2])
                    x1.write(f"{'⭐ ' if arq.get('mestre') else ''}{arq.get('nome', 'Arquivo')} — {arq.get('categoria', '')}")
                    if arq.get("url"):
                        x2.link_button("Abrir / baixar", arq.get("url"), use_container_width=True)
            proposta_origem = next((p for p in carregar_historico() if p.get("numero_proposta") == projeto.get("numero_proposta")), None)
            if proposta_origem:
                b1, b2 = st.columns(2)
                if b1.button("📋 Duplicar como novo pedido", key=f"mem_dup_{projeto.get('id')}", use_container_width=True):
                    carregar_proposta_no_formulario(proposta_origem, duplicar=True)
                    st.session_state._mensagem_sucesso_pendente = "Modelo carregado em Novo Orçamento."
                    st.rerun()
                b2.download_button(
                    "📄 Baixar HTML original",
                    gerar_html(proposta_origem),
                    file_name=f"{proposta_origem.get('numero_proposta', 'pedido')}.html",
                    mime="text/html",
                    key=f"mem_html_{projeto.get('id')}",
                    use_container_width=True,
                )



with aba9:
    st.header("📅 Calendário Comercial Inteligente")
    st.caption("Cadastre datas nacionais, locais, escolares e campanhas próprias. O sistema avisa quando é hora de começar a divulgação.")

    campanhas = carregar_campanhas()
    if "campanha_edit_id" not in st.session_state:
        st.session_state.campanha_edit_id = None

    visao_cal, lista_cal, cadastro_cal = st.tabs(["🎯 Oportunidades", "📋 Campanhas", "➕ Cadastrar / Editar"])

    with visao_cal:
        hoje_cal = hoje_local()
        oportunidades = campanhas_em_oportunidade(hoje_cal, limite_dias=180)
        ativas = [c for c in campanhas if c.get("ativa", True)]
        em_andamento = [c for c in oportunidades if c.get("em_periodo")]
        proximas_30 = [c for c in oportunidades if not c.get("em_periodo") and 0 <= c.get("dias_para_inicio", 9999) <= 30]
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Campanhas ativas", len(ativas))
        v2.metric("Em andamento", len(em_andamento))
        v3.metric("Próximos 30 dias", len(proximas_30))
        v4.metric("Locais/personalizadas", sum(1 for c in ativas if c.get("tipo") in ["Local", "Personalizada", "Interna"]))

        filtro_periodo = st.selectbox("Exibir oportunidades dos próximos", [30, 60, 90, 180, 365], index=2, format_func=lambda x: f"{x} dias")
        oportunidades = campanhas_em_oportunidade(hoje_cal, limite_dias=filtro_periodo)
        if not oportunidades:
            st.info("Nenhuma campanha nesse período.")
        for campanha in oportunidades:
            inicio = campanha["inicio_calculado"]
            fim = campanha["fim_calculado"]
            dias = campanha["dias_para_inicio"]
            if campanha["em_periodo"]:
                destaque = "🟢 Em andamento"
            elif dias <= int(campanha.get("antecedencia_dias", 30) or 30):
                destaque = f"🟠 Hora de preparar · faltam {dias} dias"
            else:
                destaque = f"🔵 Faltam {dias} dias"
            with st.container(border=True):
                a, b = st.columns([5, 2])
                a.markdown(f"### {campanha.get('nome', 'Campanha')}")
                a.write(destaque)
                a.caption(f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')} · {campanha.get('tipo')} · {campanha.get('regiao') or 'Sem região'}")
                produtos = campanha.get("produtos", []) or []
                if produtos:
                    a.write("**Produtos relacionados:** " + ", ".join(map(str, produtos)))
                if campanha.get("observacoes"):
                    a.write(campanha.get("observacoes"))
                b.write(f"**Status:** {campanha.get('status', 'Planejamento')}")
                if b.button("✏️ Editar", key=f"camp_op_edit_{campanha.get('id')}", use_container_width=True):
                    st.session_state.campanha_edit_id = campanha.get("id")
                    st.rerun()

    with lista_cal:
        busca_camp = st.text_input("🔎 Buscar campanha", placeholder="Nome, tipo, cidade, produto ou observação").strip().lower()
        tipo_camp = st.selectbox("Tipo", ["Todos", "Nacional", "Local", "Interna", "Personalizada"])
        mostrar_inativas = st.checkbox("Mostrar desativadas")
        filtradas = []
        for campanha in campanhas:
            texto = " ".join([
                str(campanha.get("nome", "")), str(campanha.get("tipo", "")), str(campanha.get("categoria", "")),
                str(campanha.get("regiao", "")), str(campanha.get("observacoes", "")),
                " ".join(map(str, campanha.get("produtos", []) or [])),
            ]).lower()
            if busca_camp and busca_camp not in texto:
                continue
            if tipo_camp != "Todos" and campanha.get("tipo") != tipo_camp:
                continue
            if not mostrar_inativas and not campanha.get("ativa", True):
                continue
            filtradas.append(campanha)
        st.caption(f"{len(filtradas)} campanha(s)")
        for campanha in sorted(filtradas, key=lambda c: (proxima_ocorrencia_campanha(c)[0] or date.max, c.get("nome", ""))):
            inicio, fim = proxima_ocorrencia_campanha(campanha)
            titulo = f"{'✅' if campanha.get('ativa', True) else '⏸️'} {campanha.get('nome')} — {campanha.get('tipo')}"
            with st.expander(titulo):
                c1, c2 = st.columns(2)
                c1.write(f"**Próximo período:** {inicio.strftime('%d/%m/%Y') if inicio else 'Sem data'} a {fim.strftime('%d/%m/%Y') if fim else 'Sem data'}")
                c1.write(f"**Região:** {campanha.get('regiao') or 'Não informada'}")
                c2.write(f"**Antecedência:** {campanha.get('antecedencia_dias', 30)} dias")
                c2.write(f"**Recorrência:** {campanha.get('recorrencia', 'Evento único')}")
                if campanha.get("produtos"):
                    st.write("**Produtos:** " + ", ".join(map(str, campanha.get("produtos", []))))
                if campanha.get("observacoes"):
                    st.write("**Observações:** " + str(campanha.get("observacoes")))
                x1, x2, x3 = st.columns(3)
                if x1.button("✏️ Editar", key=f"camp_edit_{campanha.get('id')}", use_container_width=True):
                    st.session_state.campanha_edit_id = campanha.get("id")
                    st.rerun()
                if x2.button("⏯️ Ativar/Desativar", key=f"camp_toggle_{campanha.get('id')}", use_container_width=True):
                    campanha["ativa"] = not campanha.get("ativa", True)
                    campanha["atualizado_em"] = agora_local().isoformat()
                    salvar_campanhas(campanhas)
                    st.rerun()
                if x3.button("🗑️ Excluir", key=f"camp_del_{campanha.get('id')}", use_container_width=True):
                    salvar_campanhas([c for c in campanhas if c.get("id") != campanha.get("id")])
                    st.rerun()

    with cadastro_cal:
        edit_id = st.session_state.campanha_edit_id
        atual = next((c for c in campanhas if c.get("id") == edit_id), None)
        if atual:
            st.info(f"Editando: {atual.get('nome')}")
        with st.form(f"form_campanha_{edit_id or 'nova'}"):
            nome_camp = st.text_input("Nome da campanha/evento", value=str(atual.get("nome", "")) if atual else "")
            c1, c2, c3 = st.columns(3)
            tipo = c1.selectbox("Tipo", ["Nacional", "Local", "Interna", "Personalizada"], index=["Nacional", "Local", "Interna", "Personalizada"].index(atual.get("tipo", "Personalizada")) if atual and atual.get("tipo") in ["Nacional", "Local", "Interna", "Personalizada"] else 3)
            categoria = c2.text_input("Categoria", value=str(atual.get("categoria", "Comercial")) if atual else "Comercial")
            status = c3.selectbox("Status", ["Ideia", "Planejamento", "Em produção", "Publicado", "Concluído"], index=["Ideia", "Planejamento", "Em produção", "Publicado", "Concluído"].index(atual.get("status", "Planejamento")) if atual and atual.get("status") in ["Ideia", "Planejamento", "Em produção", "Publicado", "Concluído"] else 1)
            inicio_atual = _data_iso_segura(atual.get("data_inicio")) if atual else hoje_local()
            fim_atual = _data_iso_segura(atual.get("data_fim")) if atual else hoje_local()
            d1, d2, d3 = st.columns(3)
            data_inicio = d1.date_input("Data inicial", value=inicio_atual or hoje_local())
            data_fim = d2.date_input("Data final", value=fim_atual or inicio_atual or hoje_local())
            recorrencia = d3.selectbox("Recorrência", ["Evento único", "Anual"], index=1 if atual and atual.get("recorrencia") == "Anual" else 0)
            c1, c2 = st.columns(2)
            antecedencia = c1.number_input("Começar campanha quantos dias antes?", min_value=0, max_value=365, value=int(atual.get("antecedencia_dias", 30) or 30) if atual else 30)
            regiao = c2.text_input("Cidade / região / escola", value=str(atual.get("regiao", "")) if atual else "")
            produtos_txt = st.text_area("Produtos relacionados (um por linha ou separados por vírgula)", value="\n".join(map(str, atual.get("produtos", []) or [])) if atual else "")
            observacoes = st.text_area("Observações e ideias da campanha", value=str(atual.get("observacoes", "")) if atual else "")
            ativa = st.checkbox("Campanha ativa", value=bool(atual.get("ativa", True)) if atual else True)
            salvar = st.form_submit_button("💾 Salvar campanha", type="primary", use_container_width=True)
        if salvar:
            if not nome_camp.strip():
                st.warning("Informe o nome da campanha.")
            elif data_fim < data_inicio:
                st.warning("A data final não pode ser anterior à data inicial.")
            else:
                produtos = [x.strip() for x in re.split(r"[,\n;]+", produtos_txt) if x.strip()]
                registro = {
                    "id": atual.get("id") if atual else f"CAMP-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                    "nome": nome_camp.strip(), "tipo": tipo, "categoria": categoria.strip(),
                    "data_inicio": data_inicio.isoformat(), "data_fim": data_fim.isoformat(),
                    "recorrencia": recorrencia, "antecedencia_dias": int(antecedencia),
                    "regiao": regiao.strip(), "produtos": produtos, "observacoes": observacoes.strip(),
                    "status": status, "ativa": ativa,
                    "criado_em": atual.get("criado_em", agora_local().isoformat()) if atual else agora_local().isoformat(),
                    "atualizado_em": agora_local().isoformat(),
                }
                if atual:
                    campanhas = [registro if c.get("id") == atual.get("id") else c for c in campanhas]
                else:
                    campanhas.append(registro)
                salvar_campanhas(campanhas)
                st.session_state.campanha_edit_id = None
                st.session_state._mensagem_sucesso_pendente = "Campanha salva no Calendário Comercial."
                st.rerun()
        if atual and st.button("Cancelar edição", key="cancelar_edicao_campanha"):
            st.session_state.campanha_edit_id = None
            st.rerun()



with aba7:
    st.header("⚙️ Configurações da Empresa")
    st.caption("Os dados salvos aqui são usados no painel, WhatsApp, HTML da proposta e catálogo do cliente.")
    config_atual = carregar_config_empresa()

    with st.form("form_config_empresa"):
        st.subheader("Identidade")
        c1, c2 = st.columns(2)
        nome_empresa = c1.text_input("Nome da empresa", value=str(config_atual.get("nome", "")))
        nome_maiusculo = c2.text_input("Nome no painel", value=str(config_atual.get("nome_maiusculo", "")))
        subtitulo_empresa = c1.text_input("Subtítulo", value=str(config_atual.get("subtitulo", "")))
        slogan_empresa = c2.text_input("Slogan", value=str(config_atual.get("slogan", "")))

        st.subheader("Dados cadastrais")
        c1, c2 = st.columns(2)
        cnpj_empresa = c1.text_input("CNPJ", value=str(config_atual.get("cnpj", "")))
        ie_empresa = c2.text_input("Inscrição Estadual", value=str(config_atual.get("ie", "")))
        endereco_empresa = st.text_input("Endereço completo", value=str(config_atual.get("endereco", "")))
        c1, c2, c3 = st.columns([1, 2, 1])
        cep_empresa = c1.text_input("CEP", value=str(config_atual.get("cep", "")))
        cidade_empresa = c2.text_input("Cidade", value=str(config_atual.get("cidade", "")))
        uf_empresa = c3.text_input("UF", value=str(config_atual.get("uf", "")), max_chars=2)
        c1, c2 = st.columns(2)
        email_empresa = c1.text_input("E-mail", value=str(config_atual.get("email", "")))
        celular_empresa = c2.text_input("Celular", value=str(config_atual.get("celular", "")))
        whatsapp_catalogo = st.text_input("WhatsApp do catálogo (somente números)", value=str(config_atual.get("whatsapp_catalogo", "")))

        st.subheader("Pagamento PIX")
        pix_link = st.text_input("Link de pagamento PIX", value=str(config_atual.get("pix_link", "")))
        c1, c2 = st.columns(2)
        pix_titular = c1.text_input("Titular", value=str(config_atual.get("pix_titular", "")))
        pix_banco = c2.text_input("Banco", value=str(config_atual.get("pix_banco", "")))
        c1, c2 = st.columns(2)
        pix_agencia = c1.text_input("Agência", value=str(config_atual.get("pix_agencia", "")))
        pix_conta = c2.text_input("Conta", value=str(config_atual.get("pix_conta", "")))
        pix_empresa = st.text_input("Empresa / favorecido", value=str(config_atual.get("pix_empresa", "")))

        st.subheader("Padrões dos novos orçamentos")
        c1, c2, c3 = st.columns(3)
        prazo_padrao = c1.text_input("Prazo padrão (dias úteis)", value=str(config_atual.get("prazo_padrao", "10")))
        validade_padrao = c2.text_input("Validade padrão (dias)", value=str(config_atual.get("validade_padrao", "5")))
        frete_padrao = c3.text_input("Frete/entrega padrão", value=str(config_atual.get("frete_padrao", "Retirada em Itatiba")))
        fuso_horario = st.text_input(
            "Fuso horário do sistema",
            value=str(config_atual.get("fuso_horario", FUSO_PADRAO)),
            help="Para Itatiba/SP, use America/Sao_Paulo.",
        )

        salvar_config = st.form_submit_button("💾 Salvar configurações", type="primary", use_container_width=True)

    if salvar_config:
        nova_config = {
            "nome": nome_empresa.strip(),
            "nome_maiusculo": nome_maiusculo.strip() or nome_empresa.strip().upper(),
            "subtitulo": subtitulo_empresa.strip(),
            "slogan": slogan_empresa.strip(),
            "cnpj": cnpj_empresa.strip(),
            "ie": ie_empresa.strip(),
            "endereco": endereco_empresa.strip(),
            "cep": cep_empresa.strip(),
            "cidade": cidade_empresa.strip(),
            "uf": uf_empresa.strip().upper(),
            "email": email_empresa.strip(),
            "celular": celular_empresa.strip(),
            "whatsapp_catalogo": re.sub(r"\D", "", whatsapp_catalogo),
            "pix_link": pix_link.strip(),
            "pix_titular": pix_titular.strip(),
            "pix_banco": pix_banco.strip(),
            "pix_agencia": pix_agencia.strip(),
            "pix_conta": pix_conta.strip(),
            "pix_empresa": pix_empresa.strip(),
            "prazo_padrao": prazo_padrao.strip() or "10",
            "validade_padrao": validade_padrao.strip() or "5",
            "frete_padrao": frete_padrao.strip() or "Retirada em Itatiba",
            "fuso_horario": fuso_horario.strip() or FUSO_PADRAO,
        }
        salvar_config_empresa(nova_config)
        st.success("Configurações salvas. O sistema será atualizado agora.")
        st.rerun()

    st.info("A logo e o QR Code continuam sendo carregados dos arquivos logo.png e pix.png do repositório.")
