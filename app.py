import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
import html
import re
import secrets
import urllib.parse
from urllib.parse import quote
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import altair as alt
import base64
import io
import zipfile
import hashlib
import time
import copy
import requests

_BOOT_PROCESS_STARTED_AT = time.perf_counter()

from config import APP_VERSION, DATA_VERSION, DEFAULT_TIMEZONE, DOCUMENT_CACHE_TTL_SECONDS, CONNECTION_CACHE_TTL_SECONDS
from clientes_inteligencia import renderizar_inteligencia_clientes
from constants import STATUS_FLUXO, PROCESSOS_FLUXO, PRIORIDADES_FLUXO
from painel_indicadores import calcular_indicadores_unificados
from alpha_live import registrar_atividade, obter_operacao_online
from thu_executivo import calcular_briefing, renderizar_briefing_thu
from alpha_core import calcular_alpha_core
from executive_center import renderizar_centro_executivo
try:
    from thu_embedded import THU_AVATAR_B64
except Exception:
    THU_AVATAR_B64 = ""
try:
    from thu_poses_embedded import THU_JOINHA_B64, THU_DICA_B64, THU_COMEMORANDO_B64, THU_ENTREGA_B64
except Exception:
    THU_JOINHA_B64 = THU_DICA_B64 = THU_COMEMORANDO_B64 = THU_ENTREGA_B64 = ""
try:
    from alpha_intelligence import render_alpha_intelligence
    ALPHA_INTELLIGENCE_IMPORT_ERROR = ""
except Exception as _alpha_import_exc:
    render_alpha_intelligence = None
    ALPHA_INTELLIGENCE_IMPORT_ERROR = str(_alpha_import_exc)

try:
    from central_oportunidades import render_central_oportunidades
    CENTRAL_OPORTUNIDADES_IMPORT_ERROR = ""
except Exception as _opp_import_exc:
    render_central_oportunidades = None
    CENTRAL_OPORTUNIDADES_IMPORT_ERROR = str(_opp_import_exc)

try:
    from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
except Exception:
    Image = ImageOps = ImageDraw = ImageFont = ImageFilter = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# Importação resiliente da camada de dados.
# Evita que uma atualização parcial de cloud_db.py derrube todo o aplicativo.
try:
    import cloud_db as _cloud_db
except Exception as _cloud_import_error:
    _cloud_db = None
else:
    _cloud_import_error = None

def _segredo_app(nome, padrao=""):
    """Lê segredo do Streamlit ou variável de ambiente sem derrubar a tela."""
    try:
        valor = st.secrets.get(nome, padrao)
        if valor not in (None, ""):
            return str(valor)
    except Exception:
        pass
    return str(os.getenv(nome, padrao) or padrao)


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


def _document_cache():
    if "_document_cache" not in st.session_state:
        st.session_state["_document_cache"] = {}
    return st.session_state["_document_cache"]

def invalidate_document_cache(document_key=None):
    cache = _document_cache()
    if document_key is None:
        cache.clear()
    else:
        cache.pop(str(document_key), None)

def load_document(document_key, local_path, default, force_refresh=False):
    """Carrega cada documento no máximo uma vez por TTL em cada sessão.

    Isso evita dezenas de consultas repetidas ao Supabase durante os reruns do
    Streamlit. O cache é atualizado imediatamente após qualquer gravação e
    expira rapidamente para que alterações feitas em outro computador apareçam.
    """
    key = str(document_key)
    cache = _document_cache()
    now = time.monotonic()
    cached = cache.get(key)
    if not force_refresh and cached and (now - cached["time"] < DOCUMENT_CACHE_TTL_SECONDS):
        return copy.deepcopy(cached["value"])

    func = getattr(_cloud_db, "load_document", None) if _cloud_db else None
    value = func(document_key, local_path, default) if callable(func) else _read_json_fallback(local_path, default)
    cache[key] = {"time": now, "value": copy.deepcopy(value)}
    return copy.deepcopy(value)

def save_document(document_key, value, local_path):
    func = getattr(_cloud_db, "save_document", None) if _cloud_db else None
    result = func(document_key, value, local_path) if callable(func) else _write_json_fallback(local_path, value)
    _document_cache()[str(document_key)] = {
        "time": time.monotonic(),
        "value": copy.deepcopy(value),
    }
    return result

def connection_test(force_refresh=False):
    cache_key = "_connection_test_cache"
    cached = st.session_state.get(cache_key)
    now = time.monotonic()
    if not force_refresh and cached and (now - cached["time"] < CONNECTION_CACHE_TTL_SECONDS):
        return cached["value"]

    func = getattr(_cloud_db, "connection_test", None) if _cloud_db else None
    if callable(func):
        value = func()
    else:
        detalhe = f" ({type(_cloud_import_error).__name__})" if _cloud_import_error else ""
        value = (False, "Camada online indisponível" + detalhe + " — usando arquivos JSON locais.")
    st.session_state[cache_key] = {"time": now, "value": value}
    return value

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

# --- BLINDAGEM 14.2.4: BOOT MANAGER, FEATURE FLAGS E DIAGNÓSTICO ---
DEFAULT_FEATURE_FLAGS = {
    "marketing_studio": True,
    "marketing_preview": True,
    "marketing_ai": False,
    "campanha_mestre": False,
    "diagnostico_avancado": True,
}

def feature_flags():
    """Chaves locais e seguras. Recursos experimentais permanecem desligados por padrão."""
    flags = dict(DEFAULT_FEATURE_FLAGS)
    try:
        cfg = _read_json_fallback("feature_flags.json", {})
        if isinstance(cfg, dict):
            for chave in flags:
                if chave in cfg:
                    flags[chave] = bool(cfg[chave])
    except Exception:
        pass
    return flags

def feature_enabled(nome, default=False):
    return bool(feature_flags().get(str(nome), default))

def _boot_registry():
    if "_boot_registry_1424" not in st.session_state:
        st.session_state["_boot_registry_1424"] = {}
    return st.session_state["_boot_registry_1424"]

def registrar_boot(etapa, status="ok", detalhe="", duracao=None):
    _boot_registry()[str(etapa)] = {
        "status": str(status),
        "detalhe": str(detalhe or ""),
        "duracao": float(duracao or 0.0),
        "registrado_em": datetime.now().isoformat(timespec="seconds"),
    }

def executar_etapa_segura(nome, funcao, *, critico=False):
    """Executa manutenção isolada. Uma falha não derruba a interface."""
    inicio = time.perf_counter()
    try:
        resultado = funcao()
        registrar_boot(nome, "ok", duracao=time.perf_counter() - inicio)
        return resultado
    except Exception as exc:
        registrar_boot(nome, "erro", f"{type(exc).__name__}: {exc}", time.perf_counter() - inicio)
        if critico:
            raise
        return None

def diagnostico_boot_1424():
    registros = dict(_boot_registry())
    registros.setdefault("Processo Python", {
        "status": "ok",
        "detalhe": "Aplicação iniciou e chegou à interface.",
        "duracao": max(0.0, time.perf_counter() - _BOOT_PROCESS_STARTED_AT),
        "registrado_em": datetime.now().isoformat(timespec="seconds"),
    })
    registros.setdefault("Camada de dados", {
        "status": "ok" if _cloud_db is not None else "contingencia",
        "detalhe": "cloud_db disponível" if _cloud_db is not None else f"JSON local: {_cloud_import_error}",
        "duracao": 0.0,
        "registrado_em": datetime.now().isoformat(timespec="seconds"),
    })
    registros.setdefault("Alpha Intelligence", {
        "status": "ok" if render_alpha_intelligence is not None else "isolado",
        "detalhe": ALPHA_INTELLIGENCE_IMPORT_ERROR,
        "duracao": 0.0,
        "registrado_em": datetime.now().isoformat(timespec="seconds"),
    })
    registros.setdefault("Central de oportunidades", {
        "status": "ok" if render_central_oportunidades is not None else "isolado",
        "detalhe": CENTRAL_OPORTUNIDADES_IMPORT_ERROR,
        "duracao": 0.0,
        "registrado_em": datetime.now().isoformat(timespec="seconds"),
    })
    return registros

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
ARQUIVO_BACKUP_CONFIG = "backup_config.json"
ARQUIVO_AUDITORIA = "auditoria_db.json"
ARQUIVO_LIXEIRA = "lixeira_db.json"
ARQUIVO_SYSTEM_META = "system_meta.json"
ARQUIVO_COMPONENTES = "componentes_db.json"
ARQUIVO_MARKETING = "marketing_db.json"
ARQUIVO_INTEGRACOES = "integracoes_db.json"
ARQUIVO_INTELIGENCIA = "alpha_intelligence_db.json"
ARQUIVO_USUARIOS = "usuarios_config.json"
ARQUIVO_ORIENTACOES_THU = "orientacoes_thu.json"
CANAIS_ATENDIMENTO = ["WhatsApp", "Instagram", "Facebook", "Site / Catálogo", "Telefone", "Balcão", "Outro"]
VERSAO_APP = APP_VERSION
VERSAO_DADOS = DATA_VERSION
PASTA_UPLOADS = "uploads"
os.makedirs(PASTA_UPLOADS, exist_ok=True)

FUSO_PADRAO = DEFAULT_TIMEZONE

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

def registro_eh_de_hoje(valor):
    """Aceita datas ISO ou brasileiras e informa se pertencem ao dia local atual."""
    if not valor:
        return False
    texto = str(valor).strip()
    formatos = (
        "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).date() == hoje_local()
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date() == hoje_local()
    except (ValueError, TypeError):
        return False

# --- INICIALIZAÇÃO DE SEGURANÇA ---
if "form_key" not in st.session_state: st.session_state.form_key = 0
if "temp_itens" not in st.session_state: st.session_state.temp_itens = []
if "jornada_itens" not in st.session_state: st.session_state.jornada_itens = []
if "jornada_rascunho_id" not in st.session_state: st.session_state.jornada_rascunho_id = ""

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


ABAS_SISTEMA = [
    ("central", "🏠 Central do Dia"),
    ("atendimento", "📥 Multicanal"),
    ("crm", "🎯 CRM Inteligente"),
    ("alpha", "🤖 Alpha"),
    ("intelligence", "🧠 Intelligence"),
    ("clientes_360", "🧠 Clientes 360"),
    ("crescimento", "📸 Alpha Marketing"),
    ("jornada", "🚀 Jornada"),
    ("projeto", "🧩 Projeto Personalizado"),
    ("novo_orcamento", "➕ Novo Orçamento"),
    ("historico", "📋 Histórico"),
    ("fluxo", "🎯 Fluxo de Pedidos"),
    ("relatorios", "📊 Relatórios"),
    ("executivo", "📈 Executivo"),
    ("catalogo", "📦 Catálogo"),
    ("relacionamentos", "🌐 Relacionamentos"),
    ("memoria", "🧠 Memória"),
    ("conhecimento", "🧩 Conhecimento"),
    ("calendario", "📅 Calendário Comercial"),
    ("configuracoes", "⚙️ Configurações"),
]


def indice_aba(chave):
    """Retorna o índice real da aba pela chave, evitando atalhos quebrados quando novas abas são incluídas."""
    for indice, (chave_aba, _) in enumerate(ABAS_SISTEMA):
        if chave_aba == chave:
            return indice
    return 0


def rerun_na_aba(chave, mensagem=None):
    """Reabre somente o módulo solicitado, sem renderizar todas as páginas."""
    st.session_state["_pagina_principal"] = str(chave)
    st.session_state["_aba_principal_destino"] = indice_aba(chave)
    if mensagem:
        st.session_state["_mensagem_sucesso_pendente"] = mensagem
    st.rerun()


PERMISSOES_PADRAO_ANNA = {
    "central", "atendimento", "crm", "jornada", "projeto", "novo_orcamento",
    "historico", "fluxo", "catalogo", "relacionamentos"
}

ACOES_PADRAO = ["visualizar", "criar", "editar", "aprovar", "exportar", "excluir", "configurar", "publicar"]


def configuracao_usuarios_padrao():
    todas = [chave for chave, _ in ABAS_SISTEMA]
    return {
        "usuarios": {
            "jorgegaulke76@gmail.com": {
                "nome": "Jorge", "perfil": "Administrador", "abas": todas,
                "acoes": {chave: ACOES_PADRAO for chave in todas}, "favoritos": ["executivo", "intelligence", "crescimento"]
            },
            "alphafesti@gmail.com": {
                "nome": "Anna", "perfil": "Operacional", "abas": sorted(PERMISSOES_PADRAO_ANNA),
                "acoes": {chave: ["visualizar", "criar", "editar", "aprovar", "exportar"] for chave in PERMISSOES_PADRAO_ANNA},
                "favoritos": ["atendimento", "novo_orcamento", "catalogo"]
            },
            "annazepelini@gmail.com": {
                "nome": "Anna", "perfil": "Operacional", "abas": sorted(PERMISSOES_PADRAO_ANNA),
                "acoes": {chave: ["visualizar", "criar", "editar", "aprovar", "exportar"] for chave in PERMISSOES_PADRAO_ANNA},
                "favoritos": ["atendimento", "novo_orcamento", "catalogo"]
            },
        }
    }


def carregar_config_usuarios():
    dados = load_document("usuarios_config", ARQUIVO_USUARIOS, configuracao_usuarios_padrao())
    if not isinstance(dados, dict) or not isinstance(dados.get("usuarios"), dict):
        return configuracao_usuarios_padrao()
    padrao = configuracao_usuarios_padrao()
    for email, cfg in padrao["usuarios"].items():
        dados["usuarios"].setdefault(email, cfg)
    return dados


def salvar_config_usuarios(dados):
    save_document("usuarios_config", dados, ARQUIVO_USUARIOS)


def obter_perfil_configurado(usuario=None):
    usuario = usuario or obter_usuario_atual()
    email = str(usuario.get("email", "")).lower()
    dados = carregar_config_usuarios().get("usuarios", {})
    cfg = dados.get(email)
    if cfg:
        return cfg
    nome = str(usuario.get("nome", "")).casefold()
    if nome == "jorge":
        return configuracao_usuarios_padrao()["usuarios"]["jorgegaulke76@gmail.com"]
    return configuracao_usuarios_padrao()["usuarios"]["alphafesti@gmail.com"]


def usuario_pode_ver_aba(chave, usuario=None):
    return chave in set(obter_perfil_configurado(usuario).get("abas", []))


def usuario_pode_acao(chave_aba, acao, usuario=None):
    cfg = obter_perfil_configurado(usuario)
    return acao in set((cfg.get("acoes") or {}).get(chave_aba, []))


def aplicar_visibilidade_abas(usuario=None):
    """Adapta a navegação principal ao perfil sem alterar os módulos existentes."""
    usuario = usuario or obter_usuario_atual()
    permitidas = set(obter_perfil_configurado(usuario).get("abas", []))
    regras = []
    prefixo = 'div[data-testid="stElementContainer"]:has(#fest-main-tabs-marker) + div[data-testid="stElementContainer"] div[data-baseweb="tab-list"]'

    # A Anna trabalha exclusivamente pela Central Operacional. A barra horizontal
    # completa fica escondida para reduzir distrações e deixar a tela mais enxuta.
    # Os módulos continuam preservados no código e permanecem visíveis ao Jorge.
    if usuario_em_operacao_protegida(usuario):
        # No perfil operacional da Anna não existe navegação por abas. A regra
        # anterior dependia da posição do marcador no DOM e deixou de funcionar
        # após uma atualização do Streamlit. Esta regra direta é proposital:
        # na Central da Anna não há st.tabs internos necessários, portanto
        # ocultar a lista de abas garante uma interface realmente enxuta.
        regras.append('div[data-baseweb="tab-list"], .stTabs [role="tablist"], [data-testid="stTabs"] [role="tablist"] { display:none !important; visibility:hidden !important; height:0 !important; min-height:0 !important; max-height:0 !important; margin:0 !important; padding:0 !important; overflow:hidden !important; border:0 !important; }')
        regras.append('div[data-testid="stTabs"], .stTabs { margin-top:0 !important; padding-top:0 !important; }')
        regras.append('div[data-testid="stTabs"] > div:first-child, .stTabs > div:first-child { height:0 !important; min-height:0 !important; margin:0 !important; padding:0 !important; overflow:hidden !important; }')
        regras.append('#fest-main-tabs-marker { display:none !important; height:0 !important; margin:0 !important; padding:0 !important; }')
    else:
        for indice, (chave, _) in enumerate(ABAS_SISTEMA, start=1):
            if chave not in permitidas:
                regras.append(f'{prefixo} > button:nth-child({indice}) {{ display:none !important; }}')

    st.markdown("<div id='fest-main-tabs-marker'></div><style>" + "".join(regras) + "</style>", unsafe_allow_html=True)

def solicitar_navegacao_aba(indice, mensagem=None):
    """Agenda a abertura de um módulo principal no próximo rerun."""
    try:
        idx = int(indice)
    except (TypeError, ValueError):
        idx = 0
    idx = max(0, min(idx, len(ABAS_SISTEMA) - 1))
    st.session_state["_pagina_principal"] = ABAS_SISTEMA[idx][0]
    st.session_state["_aba_principal_destino"] = idx
    if mensagem:
        st.session_state["_mensagem_sucesso_pendente"] = mensagem
    st.rerun()


def executar_navegacao_aba_pendente():
    """Resolve navegação pendente sem JavaScript e sem manter todas as abas carregadas."""
    indice = st.session_state.pop("_aba_principal_destino", None)
    if indice is not None:
        try:
            idx = max(0, min(int(indice), len(ABAS_SISTEMA) - 1))
            st.session_state["_pagina_principal"] = ABAS_SISTEMA[idx][0]
        except (TypeError, ValueError):
            pass


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
        try:
            cfg = carregar_config_usuarios().get("usuarios", {}).get(email, {})
            if cfg:
                dados["perfil"] = cfg.get("perfil", dados.get("perfil"))
                dados["nome"] = cfg.get("nome", dados.get("nome"))
        except Exception:
            pass
        return dados

    nome_fallback = st.session_state.get("usuario_atual_fallback", "Anna")
    email_fallback = "jorgegaulke76@gmail.com" if nome_fallback == "Jorge" else "alphafesti@gmail.com"
    dados = dict(USUARIOS_ADMIN[email_fallback])
    dados["email"] = email_fallback
    dados["automatico"] = False
    try:
        cfg = carregar_config_usuarios().get("usuarios", {}).get(email_fallback, {})
        if cfg:
            dados["perfil"] = cfg.get("perfil", dados.get("perfil"))
            dados["nome"] = cfg.get("nome", dados.get("nome"))
    except Exception:
        pass
    return dados

def usuario_em_operacao_protegida(usuario=None):
    """Mantém o atendimento isolado de módulos técnicos/experimentais."""
    usuario = usuario or obter_usuario_atual()
    return str(usuario.get("nome", "")).strip().casefold() == "anna"

def pode_executar_acoes_tecnicas(usuario=None):
    """Ações de conexão, diagnóstico e atualização ficam reservadas ao Jorge."""
    usuario = usuario or obter_usuario_atual()
    return str(usuario.get("nome", "")).strip().casefold() == "jorge"

def saudacao_por_hora(nome):
    hora = agora_local().hour
    if hora < 12:
        periodo = "Bom dia"
    elif hora < 18:
        periodo = "Boa tarde"
    else:
        periodo = "Boa noite"
    return f"{periodo}, {nome}!"

def _renderizar_alpha_live_conteudo():
    online, eventos = obter_operacao_online()
    st.markdown("### 🟢 AlphaFest Live")
    st.caption("Equipe e atividades em tempo real. O painel mostra somente o contexto operacional, nunca o conteúdo digitado.")

    if online:
        colunas = st.columns(min(3, len(online)))
        for idx, atividade in enumerate(online):
            nome = html.escape(str(atividade.get("nome") or "Equipe"))
            acao = html.escape(str(atividade.get("acao") or "Online"))
            modulo = html.escape(str(atividade.get("modulo") or "Central"))
            tempo = int(atividade.get("segundos", 0))
            texto_tempo = "agora" if tempo < 10 else (f"há {tempo}s" if tempo < 60 else f"há {max(1, tempo // 60)} min")
            icone = "👩" if nome.casefold() == "anna" else ("👨" if nome.casefold() == "jorge" else "👤")
            card_html = (
                f"<div style='border:1px solid #bbf7d0;border-left:6px solid #16a34a;border-radius:14px;padding:12px 14px;background:#f0fdf4;min-height:120px;'>"
                f"<div style='font-weight:800;font-size:1.05rem;'>🟢 {icone} {nome}</div>"
                f"<div style='margin-top:8px;font-weight:700;'>{acao}</div>"
                f"<div style='color:#52606d;font-size:.9rem;'>{modulo}</div>"
                f"<div style='color:#15803d;font-size:.82rem;margin-top:8px;'>Atualizado {texto_tempo}</div>"
                "</div>"
            )
            with colunas[idx % len(colunas)]:
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("⚪ Nenhum colaborador possui atividade recente nesta janela de 3 minutos.")

    with st.expander("🕘 Linha do tempo da equipe", expanded=False):
        if not eventos:
            st.caption("Ainda não há eventos concluídos registrados.")
        for evento in eventos[:15]:
            try:
                horario = datetime.fromisoformat(str(evento.get("em", ""))).strftime("%H:%M")
            except Exception:
                horario = "--:--"
            detalhe = f" — {evento.get('detalhe')}" if evento.get("detalhe") else ""
            st.markdown(f"**{horario}** · **{evento.get('nome', 'Equipe')}** · {evento.get('acao', '')}{detalhe}")

def renderizar_alpha_live():
    """Atualiza o painel sem recarregar o restante do perfil Jorge."""
    _renderizar_alpha_live_conteudo()

try:
    renderizar_alpha_live_auto = st.fragment(run_every="15s")(renderizar_alpha_live)
except Exception:
    renderizar_alpha_live_auto = renderizar_alpha_live


def frase_motivacional_anna():
    """Retorna uma mensagem original, firme e positiva, estável durante todo o dia."""
    frases = [
        "Faça o básico muito bem feito. É assim que a excelência aparece.",
        "Constância transforma esforço em resultado. Hoje é mais um passo.",
        "Velocidade com atenção encanta o cliente e fortalece a AlphaFest.",
        "Organização traz leveza. Um atendimento de cada vez, sempre com qualidade.",
        "Cada orçamento enviado abre uma nova oportunidade de realizar um sonho.",
        "Comece pelo que precisa ser feito. O ritmo vem durante o caminho.",
        "Pequenos avanços todos os dias constroem grandes resultados.",
        "Quem cuida dos detalhes entrega muito mais do que um produto.",
        "Disciplina dá direção. Carinho no atendimento cria confiança.",
        "Hoje é um ótimo dia para fazer melhor, com calma, foco e constância.",
        "Cliente bem atendido lembra da experiência e volta pela confiança.",
        "Resultado é consequência de presença, organização e ação.",
    ]
    indice = hoje_local().toordinal() % len(frases)
    return frases[indice]


def renderizar_boas_vindas_anna(resumo=None):
    """Cabeçalho leve e motivador da Central da Anna."""
    agora = agora_local()
    dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    data_extenso = f"{dias[agora.weekday()]}, {agora.day:02d} de {meses[agora.month-1]} de {agora.year}"
    saudacao = saudacao_por_hora("Anna")
    frase = frase_motivacional_anna()

    st.markdown(
        f"""
        <div style="padding:1.25rem 1.35rem;border-radius:18px;
                    background:linear-gradient(135deg,#eef7ff 0%,#ffffff 60%,#f7fbff 100%);
                    border:1px solid rgba(31,119,180,.18);box-shadow:0 8px 24px rgba(31,119,180,.08);
                    margin-bottom:.9rem;">
          <div style="font-size:1.55rem;font-weight:800;line-height:1.2;">☀️ {html.escape(saudacao)}</div>
          <div style="margin-top:.25rem;color:#5b6470;font-size:.92rem;">{html.escape(data_extenso.capitalize())}</div>
          <div style="margin-top:.85rem;font-size:1.04rem;font-weight:700;color:#1f2937;">🎯 Mensagem do dia</div>
          <div style="margin-top:.35rem;font-size:1.02rem;line-height:1.55;color:#263442;"><em>“{html.escape(frase)}”</em></div>
          <div style="margin-top:.8rem;color:#4a6075;font-size:.94rem;">💙 O poder de estar presente em cada presente.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if resumo:
        st.caption(resumo)

CONFIG_ORIENTACOES_THU_PADRAO = {
    "ativo": True,
    "frequencia": "Uma vez por sessão",
    "duracao_segundos": 10,
    "posicao": "Centro",
    "tamanho": "Grande",
    "telas": {
        "novo_orcamento": True,
        "atualizar_orcamento": True,
        "cadastrar_produto": True,
        "atualizar_catalogo": True,
        "novo_cliente": False,
    },
    "mensagens": {
        "novo_orcamento": [
            "DIGITE O NOME DO CLIENTE SEMPRE EM LETRAS MAIÚSCULAS.",
            "CONFIRA SE O TELEFONE ESTÁ IGUAL AO CADASTRADO NO WHATSAPP.",
            "PREENCHA TEMA, COR, TAMANHO, QUANTIDADE E OBSERVAÇÕES COMPLETAMENTE.",
            "UMA DESCRIÇÃO BEM FEITA MELHORA AS BUSCAS E O APRENDIZADO DO THU.",
        ],
        "atualizar_orcamento": [
            "ANTES DE SALVAR, CONFIRA NOME, TELEFONE, TEMA, COR E QUANTIDADES.",
            "REGISTRE TODA ALTERAÇÃO PEDIDA PELO CLIENTE NAS OBSERVAÇÕES.",
        ],
        "cadastrar_produto": [
            "CADASTRE O NOME DO PRODUTO EM MAIÚSCULAS E ESCOLHA O GRUPO CORRETO.",
            "INFORME DESCRIÇÃO COMPLETA, COR, TEMA, MEDIDAS E MATERIAIS.",
            "USE FOTOS NÍTIDAS E QUE REPRESENTEM CORRETAMENTE O PRODUTO.",
        ],
        "atualizar_catalogo": [
            "CONFIRA SE PREÇO, DESCRIÇÃO, GRUPO E FOTOS CONTINUAM ATUAIS.",
            "MANTENHA O PADRÃO DE NOMES E CATEGORIAS PARA FACILITAR AS BUSCAS.",
        ],
        "novo_cliente": [
            "CONFIRA O NOME COMPLETO E O TELEFONE EXATAMENTE COMO APARECEM NO WHATSAPP.",
        ],
    },
}

ROTULOS_TELAS_THU = {
    "novo_orcamento": "Novo orçamento",
    "atualizar_orcamento": "Atualizar orçamento",
    "cadastrar_produto": "Cadastrar produto",
    "atualizar_catalogo": "Atualizar catálogo",
    "novo_cliente": "Novo cliente",
}


def carregar_orientacoes_thu():
    dados = load_document(
        "orientacoes_thu",
        ARQUIVO_ORIENTACOES_THU,
        CONFIG_ORIENTACOES_THU_PADRAO,
    )
    if not isinstance(dados, dict):
        dados = {}
    cfg = copy.deepcopy(CONFIG_ORIENTACOES_THU_PADRAO)
    cfg.update({k: v for k, v in dados.items() if k not in ("telas", "mensagens")})
    cfg["telas"].update(dados.get("telas", {}) if isinstance(dados.get("telas"), dict) else {})
    mensagens = dados.get("mensagens", {}) if isinstance(dados.get("mensagens"), dict) else {}
    for tela, padrao in CONFIG_ORIENTACOES_THU_PADRAO["mensagens"].items():
        recebidas = mensagens.get(tela, padrao)
        cfg["mensagens"][tela] = [str(x).strip() for x in recebidas if str(x).strip()] if isinstance(recebidas, list) else list(padrao)
    return cfg


def salvar_orientacoes_thu(config):
    return bool(save_document("orientacoes_thu", config, ARQUIVO_ORIENTACOES_THU))


@st.cache_data(show_spinner=False)
def _imagem_thu_base64(tela=None):
    """Carrega o mascote oficial do THU com fallback embutido no código.

    O fallback evita o círculo azul mesmo quando uma ferramenta de publicação
    ignora subpastas de assets durante a atualização do Streamlit Cloud.
    """
    pasta_projeto = Path(__file__).resolve().parent
    mapa_pose = {
        "novo_orcamento": "thu_joinha.png",
        "atualizar_orcamento": "thu_dica.png",
        "cadastrar_produto": "thu_dica.png",
        "atualizar_catalogo": "thu_dica.png",
        "novo_cliente": "thu_joinha.png",
        "entrega": "thu_entrega.png",
        "comemoracao": "thu_comemorando.png",
    }
    pose = mapa_pose.get(str(tela or ""), "thu_joinha.png")
    candidatos = [
        pasta_projeto / "assets" / "thu" / pose,
        pasta_projeto / "assets" / "thu" / "thu_joinha.png",
        pasta_projeto / "assets" / "thu" / "thu_avatar.jpg",
        pasta_projeto / "assets" / "thu" / "thu_oficial.png",
        pasta_projeto / "Mascote Alphafest.png",
    ]
    for caminho in candidatos:
        if not caminho.is_file():
            continue
        try:
            extensao = caminho.suffix.lower().lstrip(".") or "png"
            if extensao == "jpg":
                extensao = "jpeg"
            conteudo = base64.b64encode(caminho.read_bytes()).decode("ascii")
            if conteudo:
                return conteudo, extensao
        except OSError:
            continue
    # Garantia final: cada pose oficial também viaja embutida no código.
    poses_embutidas = {
        "thu_joinha.png": THU_JOINHA_B64,
        "thu_dica.png": THU_DICA_B64,
        "thu_comemorando.png": THU_COMEMORANDO_B64,
        "thu_entrega.png": THU_ENTREGA_B64,
    }
    pose_b64 = poses_embutidas.get(pose) or THU_JOINHA_B64
    if pose_b64:
        return pose_b64, "png"
    if THU_AVATAR_B64:
        return THU_AVATAR_B64, "jpeg"
    return "", "png"


def mostrar_orientacao_thu(tela, token=None):
    """Exibe o THU oficial em um aviso visual, temporário e sem rerun."""
    cfg = carregar_orientacoes_thu()
    if not cfg.get("ativo", True) or not cfg.get("telas", {}).get(tela, False):
        return
    mensagens = cfg.get("mensagens", {}).get(tela, [])
    mensagens = [str(x).strip() for x in mensagens if str(x).strip()]
    if not mensagens:
        return

    usuario = obter_usuario_atual()
    email = str(usuario.get("email", "usuario")).lower()
    frequencia = str(cfg.get("frequencia", "Uma vez por sessão"))
    hoje = hoje_local().isoformat()
    if frequencia == "Uma vez por dia":
        chave = f"thu_dica_dia_{email}_{tela}_{hoje}"
    elif frequencia == "Sempre que abrir a tela":
        chave = f"thu_dica_abertura_{email}_{tela}_{token or 'padrao'}"
    else:
        chave = f"thu_dica_sessao_{email}_{tela}"
    if st.session_state.get(chave):
        return
    st.session_state[chave] = True

    contador = int(st.session_state.get(f"thu_indice_{tela}", 0))
    mensagem = mensagens[contador % len(mensagens)]
    st.session_state[f"thu_indice_{tela}"] = contador + 1

    duracao = max(4, min(30, int(cfg.get("duracao_segundos", 10) or 10)))
    posicao = str(cfg.get("posicao", "Centro"))
    tamanho = str(cfg.get("tamanho", "Grande"))
    largura = {"Médio": "560px", "Grande": "700px", "Extra grande": "820px"}.get(tamanho, "700px")
    if posicao == "Esquerda":
        alinhamento = "left:24px;right:auto;transform:none;"
    elif posicao == "Direita":
        alinhamento = "right:24px;left:auto;transform:none;"
    else:
        alinhamento = "left:50%;right:auto;transform:translateX(-50%);"

    imagem, formato_imagem = _imagem_thu_base64(tela)
    imagem_html = (
        f'<img src="data:image/{formato_imagem};base64,{imagem}" alt="Mascote oficial THU" class="thu-live-avatar">'
        if imagem else '<div class="thu-live-fallback">THU</div>'
    )
    mensagem_segura = html.escape(mensagem)
    nome_usuario = html.escape(str(usuario.get("nome") or "Anna").split()[0].title())
    animacao_saida = max(3, duracao - 1)

    st.markdown(
        f"""
        <style>
        @keyframes thuLiveEntrar {{
          0% {{ opacity:0; margin-top:-26px; }}
          100% {{ opacity:1; margin-top:0; }}
        }}
        @keyframes thuLiveSair {{
          0%, 84% {{ opacity:1; visibility:visible; }}
          100% {{ opacity:0; visibility:hidden; pointer-events:none; }}
        }}
        .thu-live-card {{
          position:fixed; top:76px; {alinhamento}
          z-index:999999; width:min({largura}, calc(100vw - 32px));
          display:flex; align-items:center; gap:22px;
          padding:20px 24px; border-radius:24px;
          background:linear-gradient(135deg,#ffffff 0%,#edf7ff 58%,#dcefff 100%);
          border:3px solid #1687d9;
          box-shadow:0 18px 55px rgba(0,72,130,.32), 0 0 0 6px rgba(22,135,217,.10);
          color:#102a43;
          animation:thuLiveEntrar .45s ease-out both, thuLiveSair 1s ease-in {animacao_saida}s forwards;
        }}
        .thu-live-avatar {{
          width:165px; height:205px; object-fit:contain; object-position:center bottom; flex:0 0 165px;
          border-radius:20px; background:transparent; border:none;
        }}
        .thu-live-fallback {{
          width:132px;height:132px;border-radius:50%;display:grid;place-items:center;
          background:#1687d9;color:white;font-size:2rem;font-weight:900;
        }}
        .thu-live-content {{ flex:1; min-width:0; }}
        .thu-live-kicker {{
          display:inline-block; padding:5px 12px; border-radius:999px;
          background:#1687d9; color:#fff; font-weight:900; font-size:.82rem;
          letter-spacing:.05em; text-transform:uppercase;
        }}
        .thu-live-title {{ margin:9px 0 5px; font-size:1.55rem; font-weight:900; color:#074f88; }}
        .thu-live-message {{ font-size:1.14rem; line-height:1.48; font-weight:800; color:#142f45; }}
        .thu-live-signature {{ margin-top:10px; color:#42647e; font-size:.88rem; font-weight:700; }}
        .thu-live-progress {{ height:5px; margin-top:14px; background:rgba(22,135,217,.15); border-radius:99px; overflow:hidden; }}
        .thu-live-progress::after {{
          content:""; display:block; height:100%; width:100%; background:#1687d9;
          transform-origin:left; animation:thuTempo {duracao}s linear forwards;
        }}
        @keyframes thuTempo {{ from {{ transform:scaleX(1); }} to {{ transform:scaleX(0); }} }}
        @media (max-width:680px) {{
          .thu-live-card {{ top:58px; padding:14px; gap:12px; align-items:flex-start; }}
          .thu-live-avatar {{ width:100px;height:100px;flex-basis:100px; }}
          .thu-live-title {{ font-size:1.15rem; }}
          .thu-live-message {{ font-size:.96rem; }}
        }}
        </style>
        <div class="thu-live-card" role="status" aria-live="polite">
          {imagem_html}
          <div class="thu-live-content">
            <span class="thu-live-kicker">THU TEM UM RECADO</span>
            <div class="thu-live-title">Olá, {nome_usuario}! 👋</div>
            <div class="thu-live-message">{mensagem_segura}</div>
            <div class="thu-live-signature">💙 THU — Assistente da AlphaFest</div>
            <div class="thu-live-progress"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_configuracoes_orientacoes_thu():
    if not pode_executar_acoes_tecnicas():
        st.warning("Somente o Jorge pode alterar as orientações do THU.")
        return
    cfg = carregar_orientacoes_thu()
    st.subheader("🎓 Orientações do THU")
    st.caption("Controle os lembretes temporários exibidos para a Anna. Eles não bloqueiam campos, não salvam dados e não recarregam a página.")

    with st.form("form_orientacoes_thu"):
        c1, c2, c3 = st.columns([1, 1.2, 1])
        ativo = c1.checkbox("Avisos ativos", value=bool(cfg.get("ativo", True)))
        frequencias = ["Uma vez por sessão", "Uma vez por dia", "Sempre que abrir a tela"]
        freq_atual = str(cfg.get("frequencia", frequencias[0]))
        frequencia = c2.selectbox("Frequência", frequencias, index=frequencias.index(freq_atual) if freq_atual in frequencias else 0)
        duracao = c3.number_input("Tempo na tela (segundos)", min_value=4, max_value=30, value=int(cfg.get("duracao_segundos", 10) or 10), help="O cartão do THU desaparece sozinho e não interrompe a digitação.")

        v1, v2 = st.columns(2)
        opcoes_posicao = ["Centro", "Esquerda", "Direita"]
        pos_atual = str(cfg.get("posicao", "Centro"))
        posicao = v1.selectbox("Posição do THU", opcoes_posicao, index=opcoes_posicao.index(pos_atual) if pos_atual in opcoes_posicao else 0)
        opcoes_tamanho = ["Médio", "Grande", "Extra grande"]
        tam_atual = str(cfg.get("tamanho", "Grande"))
        tamanho = v2.selectbox("Tamanho do aviso", opcoes_tamanho, index=opcoes_tamanho.index(tam_atual) if tam_atual in opcoes_tamanho else 1)

        st.markdown("#### Telas habilitadas")
        colunas = st.columns(3)
        telas_novas = {}
        for indice, (chave_tela, rotulo) in enumerate(ROTULOS_TELAS_THU.items()):
            telas_novas[chave_tela] = colunas[indice % 3].checkbox(rotulo, value=bool(cfg.get("telas", {}).get(chave_tela, False)), key=f"thu_tela_{chave_tela}")

        st.markdown("#### Mensagens dinâmicas")
        st.caption("Digite uma mensagem por linha. O THU alternará as mensagens automaticamente.")
        mensagens_novas = {}
        for chave_tela, rotulo in ROTULOS_TELAS_THU.items():
            with st.expander(rotulo, expanded=chave_tela in ("novo_orcamento", "cadastrar_produto")):
                atual = "\n".join(cfg.get("mensagens", {}).get(chave_tela, []))
                texto = st.text_area("Mensagens (uma por linha)", value=atual, height=130, key=f"thu_msgs_{chave_tela}")
                mensagens_novas[chave_tela] = [linha.strip() for linha in texto.splitlines() if linha.strip()]

        salvar = st.form_submit_button("💾 Salvar orientações do THU", type="primary", use_container_width=True)

    if salvar:
        nova_cfg = {
            "ativo": bool(ativo),
            "frequencia": frequencia,
            "duracao_segundos": int(duracao),
            "posicao": posicao,
            "tamanho": tamanho,
            "telas": telas_novas,
            "mensagens": mensagens_novas,
        }
        if salvar_orientacoes_thu(nova_cfg):
            st.success("Orientações do THU salvas. As novas regras valerão nas próximas aberturas.")
        else:
            st.error("Não foi possível salvar as orientações do THU.")

    st.divider()
    st.markdown("#### Prévia")
    tela_previa = st.selectbox("Tela da prévia", list(ROTULOS_TELAS_THU), format_func=lambda x: ROTULOS_TELAS_THU[x], key="thu_previa_tela")
    mensagens = cfg.get("mensagens", {}).get(tela_previa, [])
    if mensagens:
        imagem, formato_imagem = _imagem_thu_base64(tela_previa)
        img = f'<img src="data:image/{formato_imagem};base64,{imagem}" style="width:110px;height:110px;object-fit:cover;object-position:center 20%;border-radius:16px;background:white">' if imagem else ""
        st.markdown(f"""
        <div style="display:flex;gap:18px;align-items:center;padding:18px;border-radius:22px;border:3px solid #1687d9;background:linear-gradient(135deg,#fff,#e9f6ff);box-shadow:0 12px 30px rgba(0,72,130,.18)">
          {img}<div><div style="font-weight:900;color:#1687d9;font-size:.82rem">THU TEM UM RECADO</div>
          <div style="font-size:1.15rem;font-weight:900;margin:.3rem 0">Olá! 👋</div>
          <div style="font-weight:800">{html.escape(mensagens[0])}</div></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Nenhuma mensagem cadastrada para esta tela.")

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

def carregar_historico(force_refresh=False):
    """Carrega propostas do Supabase, com fallback automático para JSON local."""
    dados = load_document("historico_orcamentos", ARQUIVO_HISTORICO, [], force_refresh=force_refresh)
    return dados if isinstance(dados, list) else []


def salvar_historico_completo(historico):
    """Salva no Supabase e mantém uma cópia JSON local de contingência.

    Retorna ``True`` somente quando o banco online confirma o upsert. O retorno
    é usado pelos formulários para impedir que uma janela seja fechada antes da
    persistência real dos dados.
    """
    if not isinstance(historico, list):
        raise ValueError("O histórico precisa ser uma lista de propostas.")
    return bool(save_document("historico_orcamentos", historico, ARQUIVO_HISTORICO))

def registrar_evento_proposta(proposta, descricao, usuario="Sistema"):
    timeline = proposta.get("timeline") if isinstance(proposta.get("timeline"), list) else []
    timeline.append({
        "data": agora_local().strftime("%d/%m/%Y %H:%M"),
        "descricao": str(descricao or "Atualização").strip(),
        "usuario": str(usuario or "Sistema"),
    })
    proposta["timeline"] = timeline[-100:]
    proposta["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")


def alternar_status(num_proposta, campo, novo_valor):
    historico = carregar_historico()
    proposta_alterada = None
    for p in historico:
        if p.get("numero_proposta") == num_proposta:
            valor_anterior = bool(p.get(campo, False))
            p[campo] = novo_valor
            proposta_alterada = p
            if valor_anterior != bool(novo_valor):
                rotulos = {"pago": "Pagamento confirmado", "entregue": "Entrega concluída", "aprovado": "Orçamento aprovado"}
                acao = rotulos.get(campo, campo.replace("_", " ").title())
                registrar_evento_proposta(p, acao if novo_valor else f"{acao} desmarcado")
            break
    salvar_historico_completo(historico)
    if proposta_alterada and campo == "aprovado" and novo_valor:
        sincronizar_producao_com_propostas()
        tarefas = carregar_producao()
        mudou = False
        for tarefa in tarefas:
            if tarefa.get("numero_proposta") == num_proposta and tarefa.get("ativa", True):
                atual = normalizar_status_fluxo(tarefa.get("status"))
                if atual == "Pedido recebido":
                    tarefa["status"] = status_inicial_fluxo(tarefa.get("produto", ""), tarefa.get("especificacoes", ""))
                    adicionar_evento_timeline(tarefa, "Orçamento aprovado e pedido liberado para operação")
                    tarefa["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                    mudou = True
        if mudou:
            salvar_producao(tarefas)

def excluir_proposta(num_proposta):
    historico_atual = carregar_historico()
    proposta = next((p for p in historico_atual if p.get("numero_proposta") == num_proposta), None)
    if proposta:
        enviar_para_lixeira("Proposta", proposta, num_proposta)
    historico = [p for p in historico_atual if p.get("numero_proposta") != num_proposta]
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


def valor_bool(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    return str(valor or "").strip().casefold() in {"1", "true", "sim", "yes", "ok", "pago", "aprovado", "entregue"}


def proposta_encerrada(prop):
    status = str(prop.get("status_comercial") or prop.get("situacao_comercial") or prop.get("status") or "").strip().casefold()
    return valor_bool(prop.get("encerrado")) or status in {
        "encerrado", "encerrada", "encerrado sem retorno", "encerrado por preço", "encerrado por preco",
        "encerrado pelo cliente", "encerrado por prazo", "cancelado", "cancelada", "recusado", "recusada",
        "arquivado", "arquivada", "excluído", "excluida", "excluída",
    }


def proposta_concluida(prop):
    """Uma proposta só deixa a operação quando os três marcos estão confirmados."""
    return (
        valor_bool(prop.get("aprovado"))
        and valor_bool(prop.get("pago"))
        and valor_bool(prop.get("entregue"))
    )


def proposta_ativa_operacional(prop):
    """Fonte única para listas e contadores operacionais da Anna, Jorge e THU."""
    return not proposta_encerrada(prop) and not proposta_concluida(prop)


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


def carregar_proposta_no_formulario(prop_atual, duplicar=False):
    """Agenda o carregamento para o próximo rerun.

    No Streamlit, uma chave ligada a um widget não pode ser alterada depois que
    o widget já foi criado no mesmo ciclo. Por isso, guardamos os dados em uma
    chave temporária e aplicamos antes da criação dos campos no próximo rerun.
    """
    st.session_state._proposta_pendente_formulario = {
        "prop": dict(prop_atual),
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


def remover_item_temp(indice, aba_destino=None):
    if 0 <= indice < len(st.session_state.temp_itens):
        st.session_state.temp_itens.pop(indice)
        if aba_destino:
            rerun_na_aba(aba_destino)
        else:
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


def _valor_preenchido(valor):
    if isinstance(valor, (list, dict)):
        return bool(valor)
    return bool(str(valor or "").strip())


def _pontuacao_cadastro_relacionamento(cliente):
    """Prioriza o cadastro manual/mais completo ao consolidar duplicidades seguras."""
    campos = ["documento", "whatsapp", "email", "cidade", "aniversario", "observacoes", "segmentos", "interesses", "papeis"]
    pontos = sum(1 for campo in campos if _valor_preenchido(cliente.get(campo)))
    origem = str(cliente.get("origem", cliente.get("origem_cliente", ""))).casefold()
    if "histórico" not in origem and "historico" not in origem:
        pontos += 3
    if cliente.get("politica_atendimento"):
        pontos += 2
    if cliente.get("classificacao_relacionamento") not in (None, "", "Não classificado"):
        pontos += 1
    return pontos


def consolidar_cadastros_duplicados_relacionamentos(clientes=None, historico=None, salvar=True):
    """Consolida apenas duplicidades seguras e preserva o cadastro mais completo.

    A consolidação automática exige nome exato normalizado e, além disso, identificadores
    iguais ou ausência de documento/WhatsApp em pelo menos um dos cadastros. Propostas são
    religadas ao cadastro canônico; nenhuma proposta é removida.
    """
    clientes = list(clientes if clientes is not None else carregar_clientes())
    historico = list(historico if historico is not None else carregar_historico())
    grupos = {}
    for cli in clientes:
        nome = normalizar_texto_cliente(cli.get("nome", "")).casefold()
        if nome:
            grupos.setdefault(nome, []).append(cli)

    removidos = set()
    alterou_clientes = False
    alterou_historico = False
    consolidados = 0

    for _, grupo in grupos.items():
        ativos = [c for c in grupo if id(c) not in removidos]
        if len(ativos) < 2:
            continue
        canonico = max(ativos, key=_pontuacao_cadastro_relacionamento)
        garantir_id_relacionamento(canonico)
        for duplicado in ativos:
            if duplicado is canonico or id(duplicado) in removidos:
                continue
            doc_c = re.sub(r"\D", "", str(canonico.get("documento", "")))
            doc_d = re.sub(r"\D", "", str(duplicado.get("documento", "")))
            wa_c = re.sub(r"\D", "", str(canonico.get("whatsapp", "")))
            wa_d = re.sub(r"\D", "", str(duplicado.get("whatsapp", "")))
            identificador_conflitante = (doc_c and doc_d and doc_c != doc_d) or (wa_c and wa_d and wa_c != wa_d)
            if identificador_conflitante:
                continue

            # Preenche apenas lacunas do cadastro canônico; nunca sobrescreve dado manual atual.
            for campo, valor in duplicado.items():
                if campo in {"id", "nome", "criado_em"}:
                    continue
                if not _valor_preenchido(canonico.get(campo)) and _valor_preenchido(valor):
                    canonico[campo] = valor
                    alterou_clientes = True

            dup_id = str(duplicado.get("id", "")).strip()
            can_id = str(canonico.get("id", "")).strip()
            for prop in historico:
                prop_id = str(prop.get("relacionamento_id", "")).strip()
                nome_prop = normalizar_texto_cliente(prop.get("cliente_nome", prop.get("cliente", ""))).casefold()
                if (dup_id and prop_id == dup_id) or (not prop_id and nome_prop == normalizar_texto_cliente(canonico.get("nome", "")).casefold()):
                    prop["relacionamento_id"] = can_id
                    alterou_historico = True
            removidos.add(id(duplicado))
            alterou_clientes = True
            consolidados += 1

    if removidos:
        clientes = [c for c in clientes if id(c) not in removidos]
    if salvar:
        if alterou_clientes:
            salvar_clientes(clientes)
        if alterou_historico:
            salvar_historico_completo(historico)
    return clientes, historico, {"consolidados": consolidados, "clientes_alterados": alterou_clientes, "historico_alterado": alterou_historico}


def sincronizar_clientes_do_historico():
    """Inclui clientes das propostas e consolida duplicidades seguras sem perder dados."""
    clientes = carregar_clientes()
    historico = carregar_historico()
    clientes, historico, _ = consolidar_cadastros_duplicados_relacionamentos(clientes, historico, salvar=True)

    por_doc, por_wa, por_nome = {}, {}, {}
    for c in clientes:
        nome = normalizar_texto_cliente(c.get("nome", "")).casefold()
        doc = re.sub(r"\D", "", str(c.get("documento", "")))
        wa = re.sub(r"\D", "", str(c.get("whatsapp", "")))
        if doc: por_doc.setdefault(doc, []).append(c)
        if wa: por_wa.setdefault(wa, []).append(c)
        if nome: por_nome.setdefault(nome, []).append(c)

    alterado = False
    historico_alterado = False
    for prop in historico:
        nome = normalizar_texto_cliente(prop.get("cliente_nome", prop.get("cliente", "")))
        if not nome:
            continue
        documento = normalizar_texto_cliente(prop.get("documento", prop.get("cliente_cpf_cnpj", "")))
        whatsapp = normalizar_texto_cliente(prop.get("whatsapp", prop.get("cliente_wa", "")))
        doc = re.sub(r"\D", "", documento)
        wa = re.sub(r"\D", "", whatsapp)
        nome_norm = nome.casefold()
        candidatos = []
        if doc and len(por_doc.get(doc, [])) == 1:
            candidatos = por_doc[doc]
        elif wa and len(por_wa.get(wa, [])) == 1:
            candidatos = por_wa[wa]
        elif len(por_nome.get(nome_norm, [])) == 1:
            candidatos = por_nome[nome_norm]

        if candidatos:
            atual = candidatos[0]
            garantir_id_relacionamento(atual)
            if prop.get("relacionamento_id") != atual.get("id"):
                prop["relacionamento_id"] = atual.get("id")
                historico_alterado = True
            if not atual.get("documento") and documento:
                atual["documento"] = documento; alterado = True
            if not atual.get("whatsapp") and whatsapp:
                atual["whatsapp"] = whatsapp; alterado = True
            continue

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
        por_nome.setdefault(nome_norm, []).append(novo)
        if doc: por_doc.setdefault(doc, []).append(novo)
        if wa: por_wa.setdefault(wa, []).append(novo)
        prop["relacionamento_id"] = novo["id"]
        alterado = True
        historico_alterado = True

    if alterado:
        salvar_clientes(clientes)
    if historico_alterado:
        salvar_historico_completo(historico)
    return clientes




def _digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _campos_identidade_registro(registro):
    """Extrai os campos de identidade usados para ligar qualquer módulo ao cadastro mestre."""
    return {
        "id": str(registro.get("relacionamento_id", registro.get("cliente_id", "")) or "").strip(),
        "nome": normalizar_texto_cliente(registro.get("cliente_nome", registro.get("cliente", registro.get("nome_cliente", registro.get("nome", ""))))).casefold(),
        "documento": _digitos(registro.get("documento", registro.get("cliente_cpf_cnpj", registro.get("cpf_cnpj", "")))),
        "whatsapp": _telefone_chave(registro.get("whatsapp", registro.get("cliente_wa", registro.get("telefone", "")))),
    }


def _indices_cadastro_mestre(clientes):
    por_id, por_doc, por_wa, por_nome = {}, {}, {}, {}
    for cli in clientes:
        garantir_id_relacionamento(cli)
        cid = str(cli.get("id", "")).strip()
        nome = normalizar_texto_cliente(cli.get("nome", "")).casefold()
        doc = _digitos(cli.get("documento", ""))
        wa = _telefone_chave(cli.get("whatsapp", ""))
        if cid:
            por_id[cid] = cli
        if doc:
            por_doc.setdefault(doc, []).append(cli)
        if wa:
            por_wa.setdefault(wa, []).append(cli)
        if nome:
            por_nome.setdefault(nome, []).append(cli)
    return por_id, por_doc, por_wa, por_nome


def _localizar_no_cadastro_mestre(registro, indices):
    por_id, por_doc, por_wa, por_nome = indices
    ident = _campos_identidade_registro(registro)
    if ident["id"] and ident["id"] in por_id:
        return por_id[ident["id"]]
    for chave, mapa in ((ident["documento"], por_doc), (ident["whatsapp"], por_wa), (ident["nome"], por_nome)):
        if chave and len(mapa.get(chave, [])) == 1:
            return mapa[chave][0]
    return None


def _vincular_lista_cadastro_mestre(itens, indices):
    alterados = 0
    sem_vinculo = 0
    for item in itens or []:
        if not isinstance(item, dict):
            continue
        cli = _localizar_no_cadastro_mestre(item, indices)
        if cli:
            cid = str(cli.get("id", "")).strip()
            if cid and str(item.get("relacionamento_id", "")).strip() != cid:
                item["relacionamento_id"] = cid
                alterados += 1
        elif any(_campos_identidade_registro(item).values()):
            sem_vinculo += 1
    return alterados, sem_vinculo


def sincronizar_cadastro_mestre(salvar=True):
    """Vincula os módulos ao relacionamento mestre sem apagar dados históricos.

    Os dados pessoais continuam preservados dentro dos documentos antigos para auditoria,
    porém todas as telas podem consultar o cadastro atual pelo relacionamento_id.
    """
    clientes = carregar_clientes()
    historico = carregar_historico()
    clientes, historico, consolidacao = consolidar_cadastros_duplicados_relacionamentos(clientes, historico, salvar=False)
    indices = _indices_cadastro_mestre(clientes)
    total_ids = sum(1 for c in clientes if c.get("id"))

    resultados = {
        "relacionamentos": len(clientes),
        "ids_validos": total_ids,
        "duplicidades_consolidadas": consolidacao.get("consolidados", 0),
        "modulos": {},
        "alteracoes": 0,
        "sem_vinculo": 0,
    }

    docs = [
        ("Orçamentos", historico, lambda v: salvar_historico_completo(v)),
        ("Projetos", carregar_projetos(), lambda v: salvar_projetos(v)),
        ("Produção", carregar_producao(), lambda v: salvar_producao(v)),
        ("Campanhas", load_document("campanhas_db", ARQUIVO_CAMPANHAS, []), lambda v: save_document("campanhas_db", v, ARQUIVO_CAMPANHAS)),
    ]
    atendimentos = carregar_atendimentos()
    docs.append(("Atendimentos", atendimentos.get("itens", []), None))

    for nome, itens, salvador in docs:
        if not isinstance(itens, list):
            itens = []
        alterados, sem_vinculo = _vincular_lista_cadastro_mestre(itens, indices)
        resultados["modulos"][nome] = {"registros": len(itens), "vinculados_agora": alterados, "sem_vinculo": sem_vinculo}
        resultados["alteracoes"] += alterados
        resultados["sem_vinculo"] += sem_vinculo
        if salvar and alterados:
            if nome == "Atendimentos":
                atendimentos["itens"] = itens
                salvar_atendimentos(atendimentos)
            elif salvador:
                salvador(itens)

    if salvar:
        salvar_clientes(clientes)
        if consolidacao.get("historico_alterado") and not resultados["modulos"]["Orçamentos"]["vinculados_agora"]:
            salvar_historico_completo(historico)
    return resultados


def dados_atuais_cadastro_mestre(registro):
    """Retorna identidade atual, mantendo o documento operacional original intacto."""
    cli = _localizar_no_cadastro_mestre(registro, _indices_cadastro_mestre(carregar_clientes()))
    if not cli:
        return dict(registro)
    visao = dict(registro)
    mapa = {
        "cliente_nome": "nome",
        "whatsapp": "whatsapp",
        "documento": "documento",
        "email": "email",
        "cidade": "cidade",
    }
    for destino, origem in mapa.items():
        if cli.get(origem):
            visao[destino] = cli.get(origem)
    visao["relacionamento_id"] = cli.get("id")
    return visao

PAPEIS_RELACIONAMENTO = [
    "Cliente", "Fornecedor", "Parceiro comercial", "Prestador de serviço",
    "Freelancer", "Transportadora", "Influenciador / Indicador",
    "Concorrente monitorado", "Ex-cliente", "Contato em observação"
]
NIVEIS_ATENDIMENTO = ["Normal", "Somente manual", "Atenção", "Monitorado", "Bloqueado"]
CLASSIFICACOES_RELACIONAMENTO = ["Não classificado", "Bronze", "Prata", "Ouro", "VIP", "Atenção", "Restrito", "Bloqueado"]
PRIORIDADES_FORNECEDOR = ["Não definida", "Preferencial", "Alternativo", "Emergencial"]

def papeis_relacionamento(cliente):
    papeis = cliente.get("papeis", []) or []
    if isinstance(papeis, str):
        papeis = [x.strip() for x in papeis.split(",") if x.strip()]
    if not papeis:
        papeis = ["Cliente"]
    return list(dict.fromkeys(papeis))

def politica_atendimento(cliente):
    politica = cliente.get("politica_atendimento", {}) or {}
    return {
        "nivel": politica.get("nivel", "Normal"),
        "motivo": politica.get("motivo", ""),
        "permitir_resposta": bool(politica.get("permitir_resposta", True)),
        "permitir_catalogo": bool(politica.get("permitir_catalogo", True)),
        "permitir_orcamento": bool(politica.get("permitir_orcamento", True)),
        "permitir_campanhas": bool(politica.get("permitir_campanhas", True)),
        "exigir_pagamento_antecipado": bool(politica.get("exigir_pagamento_antecipado", False)),
        "exigir_aprovacao_gestor": bool(politica.get("exigir_aprovacao_gestor", False)),
    }

def localizar_relacionamento(nome="", whatsapp=""):
    chave_wa = _telefone_chave(whatsapp)
    nome_norm = normalizar_texto_cliente(nome).casefold()
    for cli in carregar_clientes():
        if chave_wa and _telefone_chave(cli.get("whatsapp")) == chave_wa:
            return cli
        if nome_norm and normalizar_texto_cliente(cli.get("nome")).casefold() == nome_norm:
            return cli
    return None

def relacionamento_da_proposta(prop):
    """Retorna o cadastro atual vinculado à proposta, priorizando relacionamento_id."""
    clientes = carregar_clientes()
    rel_id = str(prop.get("relacionamento_id", "")).strip()
    if rel_id:
        encontrado = next((c for c in clientes if str(c.get("id", "")).strip() == rel_id), None)
        if encontrado:
            return encontrado
    nome = prop.get("cliente_nome", prop.get("cliente", ""))
    whatsapp = prop.get("whatsapp", prop.get("cliente_wa", ""))
    return localizar_relacionamento(nome, whatsapp)


def proposta_com_dados_atuais(prop):
    """Cria uma visão da proposta usando os dados atuais do relacionamento.

    Itens, valores, datas e status continuam vindo da proposta histórica.
    """
    atual = relacionamento_da_proposta(prop)
    if not atual:
        return dict(prop), None
    visao = dict(prop)
    nome = atual.get("nome") or visao.get("cliente_nome", visao.get("cliente", ""))
    documento = atual.get("documento") or visao.get("documento", visao.get("cliente_cpf_cnpj", ""))
    whatsapp = atual.get("whatsapp") or visao.get("whatsapp", visao.get("cliente_wa", ""))
    visao.update({
        "cliente_nome": nome,
        "cliente": nome,
        "documento": documento,
        "cliente_cpf_cnpj": documento,
        "whatsapp": whatsapp,
        "cliente_wa": whatsapp,
        "email": atual.get("email", visao.get("email", "")),
        "cidade": atual.get("cidade", visao.get("cidade", "")),
        "relacionamento_id": atual.get("id", visao.get("relacionamento_id", "")),
    })
    return visao, atual


def resumo_restricao_relacionamento(cliente):
    if not cliente:
        return None
    politica = politica_atendimento(cliente)
    nivel = politica.get("nivel", "Normal")
    papeis = papeis_relacionamento(cliente)
    restrito = nivel != "Normal" or "Concorrente monitorado" in papeis or not politica.get("permitir_resposta", True)
    if not restrito:
        return None
    return {"nivel": nivel, "motivo": politica.get("motivo", ""), "papeis": papeis, **politica}

def propostas_do_cliente(cliente):
    rel_id = str(cliente.get("id", "")).strip()
    chave = chave_cliente(cliente.get("nome"), cliente.get("documento"), cliente.get("whatsapp"))
    propostas = []
    for prop in carregar_historico():
        if rel_id and str(prop.get("relacionamento_id", "")).strip() == rel_id:
            propostas.append(prop)
            continue
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



def garantir_id_relacionamento(cliente):
    """Garante um identificador estável sem alterar outros campos."""
    if not cliente.get("id"):
        cliente["id"] = f"REL-{agora_local().strftime('%Y%m%d%H%M%S%f')}"
    return cliente["id"]


def consolidar_vinculos_relacionamentos(salvar=True):
    """Vincula propostas antigas ao relacionamento atual por documento, WhatsApp ou nome exato.
    Nunca apaga nem mescla propostas. Casos ambíguos são apenas relatados.
    """
    clientes = carregar_clientes()
    historico = carregar_historico()
    por_doc, por_wa, por_nome = {}, {}, {}
    alterou_clientes = False
    for cli in clientes:
        if not cli.get("id"):
            garantir_id_relacionamento(cli); alterou_clientes = True
        doc = re.sub(r"\D", "", str(cli.get("documento", "")))
        wa = re.sub(r"\D", "", str(cli.get("whatsapp", "")))
        nome = normalizar_texto_cliente(cli.get("nome", "")).casefold()
        if doc: por_doc.setdefault(doc, []).append(cli)
        if wa: por_wa.setdefault(wa, []).append(cli)
        if nome: por_nome.setdefault(nome, []).append(cli)
    vinculadas = 0
    ambiguas = []
    sem_correspondencia = []
    for prop in historico:
        atual_id = str(prop.get("relacionamento_id", "")).strip()
        if atual_id and any(c.get("id") == atual_id for c in clientes):
            continue
        doc = re.sub(r"\D", "", str(prop.get("documento", prop.get("cliente_cpf_cnpj", ""))))
        wa = re.sub(r"\D", "", str(prop.get("whatsapp", prop.get("cliente_wa", ""))))
        nome = normalizar_texto_cliente(prop.get("cliente_nome", prop.get("cliente", ""))).casefold()
        candidatos = []
        if doc and len(por_doc.get(doc, [])) == 1:
            candidatos = por_doc[doc]
        elif wa and len(por_wa.get(wa, [])) == 1:
            candidatos = por_wa[wa]
        elif nome and len(por_nome.get(nome, [])) == 1:
            candidatos = por_nome[nome]
        else:
            conjunto = []
            for lista in (por_doc.get(doc, []) if doc else [], por_wa.get(wa, []) if wa else [], por_nome.get(nome, []) if nome else []):
                for c in lista:
                    if c not in conjunto: conjunto.append(c)
            if len(conjunto) == 1: candidatos = conjunto
            elif len(conjunto) > 1:
                ambiguas.append({"proposta": prop.get("numero_proposta", ""), "cliente": prop.get("cliente_nome", ""), "candidatos": [c.get("nome", "") for c in conjunto]})
                continue
        if candidatos:
            cli = candidatos[0]
            prop["relacionamento_id"] = cli.get("id")
            vinculadas += 1
        else:
            sem_correspondencia.append({"proposta": prop.get("numero_proposta", ""), "cliente": prop.get("cliente_nome", "")})
    if salvar:
        if alterou_clientes: salvar_clientes(clientes)
        if vinculadas: salvar_historico_completo(historico)
    return {"vinculadas": vinculadas, "ambiguas": ambiguas, "sem_correspondencia": sem_correspondencia, "total_propostas": len(historico)}



CANAL_MIDIA_CONFIG = {
    "Instagram Feed": {"size": (1080, 1350), "tipo": "imagem", "rotulo": "Instagram Feed", "plataforma": "instagram", "arquivo": "PNG", "cor": "#E4405F"},
    "Instagram Story": {"size": (1080, 1920), "tipo": "imagem", "rotulo": "Instagram Story", "plataforma": "instagram", "arquivo": "PNG", "cor": "#E4405F"},
    "Facebook": {"size": (1080, 1080), "tipo": "imagem", "rotulo": "Facebook", "plataforma": "facebook", "arquivo": "PNG", "cor": "#1877F2"},
    "Status WhatsApp": {"size": (1080, 1920), "tipo": "imagem", "rotulo": "Status WhatsApp", "plataforma": "whatsapp", "arquivo": "PNG", "cor": "#25D366"},
    "Carrossel": {"size": (1080, 1350), "tipo": "imagem", "rotulo": "Carrossel Instagram", "plataforma": "instagram", "arquivo": "PNG", "cor": "#E4405F"},
    "Reel": {"size": (1080, 1920), "tipo": "video", "rotulo": "Instagram Reel", "plataforma": "instagram", "arquivo": "MP4", "cor": "#E4405F"},
    "TikTok": {"size": (1080, 1920), "tipo": "video", "rotulo": "TikTok", "plataforma": "tiktok", "arquivo": "MP4", "cor": "#111111"},
    "YouTube Shorts": {"size": (1080, 1920), "tipo": "video", "rotulo": "YouTube Shorts", "plataforma": "youtube", "arquivo": "MP4", "cor": "#FF0000"},
    "YouTube Horizontal": {"size": (1920, 1080), "tipo": "video", "rotulo": "YouTube Horizontal", "plataforma": "youtube", "arquivo": "MP4", "cor": "#FF0000"},
}

PLATFORM_ICON_FILES = {
    "instagram": "assets/platforms/instagram.svg",
    "facebook": "assets/platforms/facebook.svg",
    "whatsapp": "assets/platforms/whatsapp.svg",
    "tiktok": "assets/platforms/tiktok.svg",
    "youtube": "assets/platforms/youtube.svg",
}

def _ler_bytes_midia(origem):
    """Converte uploads, bytes, caminhos, data URLs e URLs remotas em bytes.

    As imagens do catálogo podem estar salvas como caminho local, URL pública do
    Supabase ou data URL. O preview do Streamlit aceita todos esses formatos,
    mas o Pillow precisa receber os bytes reais do arquivo.
    """
    if origem is None:
        return b""
    if isinstance(origem, (bytes, bytearray, memoryview)):
        return bytes(origem)
    if hasattr(origem, "getbuffer"):
        try:
            return bytes(origem.getbuffer())
        except Exception:
            pass
    if hasattr(origem, "read"):
        try:
            posicao = origem.tell() if hasattr(origem, "tell") else None
            if hasattr(origem, "seek"):
                origem.seek(0)
            dados = origem.read()
            if posicao is not None and hasattr(origem, "seek"):
                origem.seek(posicao)
            if dados:
                return bytes(dados)
        except Exception:
            pass

    texto = str(origem).strip()
    if not texto:
        return b""

    if texto.startswith("data:image/") and "," in texto:
        try:
            cabecalho, conteudo = texto.split(",", 1)
            return base64.b64decode(conteudo) if ";base64" in cabecalho else urllib.parse.unquote_to_bytes(conteudo)
        except Exception:
            return b""

    if texto.lower().startswith(("http://", "https://")):
        try:
            resposta = requests.get(
                texto,
                timeout=20,
                allow_redirects=True,
                headers={"User-Agent": "FestManager/9.1 (+https://www.alphafest.com.br)"},
            )
            resposta.raise_for_status()
            tipo = str(resposta.headers.get("content-type", "")).lower()
            if tipo and not (tipo.startswith("image/") or "octet-stream" in tipo):
                return b""
            return resposta.content
        except Exception:
            return b""

    try:
        caminho = Path(texto)
        candidatos = [caminho]
        if not caminho.is_absolute():
            candidatos.extend([Path.cwd() / caminho, Path(__file__).resolve().parent / caminho])
        for candidato in candidatos:
            if candidato.exists() and candidato.is_file():
                return candidato.read_bytes()
    except Exception:
        pass
    return b""

def converter_imagem_para_png(origem):
    """Aceita imagem enviada ou caminho e devolve PNG em bytes, preservando o original."""
    if Image is None:
        raise RuntimeError("Pillow não está instalado.")
    bruto = _ler_bytes_midia(origem)
    if not bruto:
        raise ValueError("Não foi possível ler a imagem selecionada.")
    with Image.open(io.BytesIO(bruto)) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        saida = io.BytesIO()
        img.save(saida, format="PNG", optimize=True)
        return saida.getvalue()

def _fonte_segura(tamanho=42, negrito=False):
    if ImageFont is None:
        return None
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for caminho in candidatos:
        try:
            if Path(caminho).exists():
                return ImageFont.truetype(caminho, tamanho)
        except Exception:
            pass
    return ImageFont.load_default()

def _quebrar_texto(draw, texto, fonte, largura_max, limite_linhas=4):
    palavras = str(texto or "").split()
    linhas, atual = [], ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        try:
            largura = draw.textbbox((0, 0), teste, font=fonte)[2]
        except Exception:
            largura = len(teste) * 12
        if largura <= largura_max or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
            if len(linhas) >= limite_linhas:
                break
    if atual and len(linhas) < limite_linhas:
        linhas.append(atual)
    if len(linhas) == limite_linhas and len(" ".join(linhas)) < len(str(texto or "")):
        linhas[-1] = linhas[-1].rstrip(".,;:") + "…"
    return linhas

def _carregar_logo_alphafest(max_width=260):
    if Image is None:
        return None
    for caminho in (Path("logo.png"), Path("assets/logo.png")):
        try:
            if caminho.exists():
                logo = Image.open(caminho).convert("RGBA")
                logo.thumbnail((max_width, max_width), Image.Resampling.LANCZOS)
                return logo
        except Exception:
            continue
    return None

def gerar_arte_png(origem, canal, titulo, subtitulo="", preco="", cta="Chame no WhatsApp"):
    """Gera arte de campanha em PNG com identidade visual discreta da Alphafest."""
    if Image is None:
        raise RuntimeError("Pillow não está instalado.")
    config = CANAL_MIDIA_CONFIG.get(canal, CANAL_MIDIA_CONFIG["Instagram Feed"])
    largura, altura = config["size"]
    bruto = _ler_bytes_midia(origem)
    if not bruto:
        raise ValueError("Selecione uma imagem válida.")
    with Image.open(io.BytesIO(bruto)) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        fundo = ImageOps.fit(img, (largura, altura), method=Image.Resampling.LANCZOS)
        fundo = fundo.filter(ImageFilter.GaussianBlur(radius=24))
        fundo = Image.blend(fundo, Image.new("RGB", (largura, altura), "white"), 0.20)
        principal = ImageOps.contain(img, (int(largura * .92), int(altura * .68)), method=Image.Resampling.LANCZOS)
        canvas = fundo.copy().convert("RGBA")
        px = (largura - principal.width) // 2
        py = max(80, int(altura * .055))
        sombra = Image.new("RGBA", canvas.size, (0,0,0,0))
        sdraw = ImageDraw.Draw(sombra, "RGBA")
        sdraw.rounded_rectangle((px+12, py+18, px+principal.width+12, py+principal.height+18), radius=28, fill=(0,0,0,70))
        sombra = sombra.filter(ImageFilter.GaussianBlur(18))
        canvas.alpha_composite(sombra)
        canvas.paste(principal.convert("RGBA"), (px, py))
        draw = ImageDraw.Draw(canvas, "RGBA")

        # Identidade Alphafest no topo, discreta e sempre visível.
        logo = _carregar_logo_alphafest(max_width=max(150, int(largura*.20)))
        if logo is not None:
            box_w, box_h = logo.width + 34, logo.height + 24
            bx1, by1 = largura - box_w - 42, 34
            draw.rounded_rectangle((bx1, by1, bx1+box_w, by1+box_h), radius=20, fill=(255,255,255,220))
            canvas.alpha_composite(logo, (bx1+17, by1+12))
        else:
            f_brand = _fonte_segura(max(24, int(largura*.027)), True)
            marca = "ALPHAFEST"
            bbox = draw.textbbox((0,0), marca, font=f_brand)
            bx1 = largura-(bbox[2]-bbox[0])-84
            draw.rounded_rectangle((bx1-20, 38, largura-38, 96), radius=18, fill=(255,255,255,220))
            draw.text((bx1, 50), marca, font=f_brand, fill=(17,24,39,255))

        painel_y = int(altura * .72)
        draw.rounded_rectangle((38, painel_y, largura-38, altura-38), radius=38, fill=(255,255,255,244), outline=(255,255,255,255), width=2)
        f_titulo = _fonte_segura(max(34, int(largura*.050)), True)
        f_sub = _fonte_segura(max(24, int(largura*.030)), False)
        f_preco = _fonte_segura(max(34, int(largura*.046)), True)
        f_cta = _fonte_segura(max(23, int(largura*.028)), True)
        f_rodape = _fonte_segura(max(18, int(largura*.021)), False)
        x = 78; y = painel_y + 48
        for linha in _quebrar_texto(draw, titulo, f_titulo, largura-156, 2):
            draw.text((x,y), linha, font=f_titulo, fill=(17,24,39,255)); y += int(largura*.060)
        if subtitulo:
            for linha in _quebrar_texto(draw, subtitulo, f_sub, largura-156, 2):
                draw.text((x,y+6), linha, font=f_sub, fill=(75,85,99,255)); y += int(largura*.041)
        if preco:
            draw.text((x, altura-190), preco, font=f_preco, fill=(220,38,38,255))
        cta_box=(largura-500, altura-196, largura-78, altura-94)
        draw.rounded_rectangle(cta_box, radius=28, fill=(29,78,216,255))
        bbox=draw.textbbox((0,0), cta, font=f_cta)
        tx=cta_box[0]+(cta_box[2]-cta_box[0]-(bbox[2]-bbox[0]))//2
        ty=cta_box[1]+(cta_box[3]-cta_box[1]-(bbox[3]-bbox[1]))//2-3
        draw.text((tx,ty), cta, font=f_cta, fill="white")
        draw.text((78, altura-75), "Alphafest • Personalizados, Balões e Gráfica Rápida", font=f_rodape, fill=(55,65,81,230))
        saida=io.BytesIO(); canvas.convert("RGB").save(saida, format="PNG", optimize=True)
        return saida.getvalue()

def _openai_api_key():
    try:
        return str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    except Exception:
        return os.getenv("OPENAI_API_KEY", "").strip()

def _gerar_pacote_copy_ia(produto, objetivo, campanha, canais, observacoes, tom, imagem_png=None):
    """Gera todas as descrições em uma única chamada, com visão opcional da imagem."""
    api_key = _openai_api_key()
    if not api_key or OpenAI is None:
        return None, "Alpha local"
    nome = str(produto.get("Nome", "Produto personalizado")).strip()
    descricao = str(produto.get("Descricao", "")).strip()
    prompt = f"""Você é o copywriter comercial da Alphafest, empresa de personalizados, balões, lembranças e gráfica rápida em Itatiba-SP.\nCrie textos em português do Brasil com foco forte em gerar pedidos de orçamento, sem promessas falsas e sem linguagem apelativa.\nProduto identificado: {nome}\nDescrição confirmada: {descricao}\nObjetivo: {objetivo}\nLinha de venda: {tom}\nCampanha/data: {campanha or 'não informada'}\nOferta e detalhes obrigatórios: {observacoes or 'não informados'}\nCanais: {', '.join(canais)}\nDiferenciais obrigatórios quando fizer sentido: atendimento personalizado; fazemos conforme a necessidade; produzimos na quantidade necessária, sem quantidade mínima.\nEntregue SOMENTE um objeto JSON válido no formato {{"produto_identificado":"...","conteudos":{{"canal":"texto"}}}}. Cada texto deve ser específico para o canal, conter gancho, benefício, diferencial, urgência verdadeira quando informada e CTA para WhatsApp. Não invente preço, prazo, material ou promoção."""
    content = [{"type":"input_text", "text":prompt}]
    if imagem_png:
        data_url = "data:image/png;base64," + base64.b64encode(imagem_png).decode("ascii")
        content.append({"type":"input_image", "image_url":data_url, "detail":"low"})
    try:
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        response = client.responses.create(model=model, input=[{"role":"user", "content":content}])
        texto = str(response.output_text or "").strip()
        texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.I|re.S).strip()
        dados = json.loads(texto)
        conteudos = dados.get("conteudos", {}) if isinstance(dados, dict) else {}
        if not all(c in conteudos for c in canais):
            return None, "Alpha local"
        return {c: str(conteudos[c]) for c in canais}, f"IA OpenAI ({model})"
    except Exception:
        return None, "Alpha local"

def gerar_copy_comercial(produto, objetivo, campanha, canal, observacoes="", tom="Venda direta"):
    nome = str(produto.get("Nome", "Produto personalizado")).strip()
    descricao = re.sub(r"\s+", " ", str(produto.get("Descricao", "")).strip())
    campanha_txt = str(campanha or "").strip()
    obs = str(observacoes or "").strip()
    contexto = f" para {campanha_txt}" if campanha_txt else ""
    ganchos = {
        "Venda direta": f"🔥 Personalização que chama atenção: {nome}{contexto}.",
        "Emocional": f"✨ Transforme uma ocasião especial em uma lembrança única com {nome}{contexto}.",
        "Urgência": f"⏰ Sua data está chegando? Reserve agora o seu {nome}{contexto}.",
        "Premium": f"✨ Exclusividade em cada detalhe: conheça {nome}{contexto}.",
        "Corporativo": f"💼 Valorize sua marca e seu evento com {nome}{contexto}.",
        "Promoção": f"🔥 Condição especial para {nome}{contexto}.",
    }
    gancho = ganchos.get(tom, ganchos["Venda direta"])
    beneficio = descricao or "Personalização feita especialmente para a sua necessidade."
    diferencial = "Na Alphafest, fazemos conforme a sua necessidade e na quantidade que você precisa — sem quantidade mínima."
    oferta = f"\n\n🎯 {obs}" if obs else ""
    ctas = ["Chame agora no WhatsApp e solicite seu orçamento.", "Reserve sua data pelo WhatsApp.", "Fale com a Alphafest e transforme sua ideia em realidade."]
    cta = ctas[int(hashlib.md5((nome+canal+campanha_txt).encode()).hexdigest(),16) % len(ctas)]
    hashtags = "#AlphaFest #Personalizados #Itatiba #FeitoSobMedida #Orçamento #FestasPersonalizadas"
    if canal in ("Instagram Story", "Status WhatsApp"):
        return f"{gancho}\n\n✅ Atendimento personalizado\n✅ Sem quantidade mínima{oferta}\n\n📲 {cta}"
    if canal in ("Reel", "TikTok", "YouTube Shorts"):
        return f"GANCHO: {gancho}\nCENA 1: Mostre o produto em destaque.\nCENA 2: Aproxime nos detalhes da personalização.\nCENA 3: Mostre o resultado final.\nENCERRAMENTO: {cta}\n\nLegenda: {beneficio}{oferta}\n{hashtags}"
    if canal == "Facebook":
        return f"{gancho}\n\n{beneficio}\n\n{diferencial}{oferta}\n\n📲 {cta}"
    return f"{gancho}\n\n{beneficio}\n\n{diferencial}{oferta}\n\n📲 {cta}\n\n{hashtags}"

def carregar_marketing():
    dados = load_document("marketing_db", ARQUIVO_MARKETING, {"conteudos": [], "config": {}})
    if not isinstance(dados, dict): dados = {"conteudos": [], "config": {}}
    dados.setdefault("conteudos", [])
    dados.setdefault("config", {})
    return dados

def salvar_marketing(dados):
    save_document("marketing_db", dados, ARQUIVO_MARKETING)

def gerar_conteudo_marketing(produto, objetivo, campanha, canais, observacoes="", tom="Venda direta", imagem_png=None):
    pacote_ia, motor = _gerar_pacote_copy_ia(produto, objetivo, campanha, canais, observacoes, tom, imagem_png)
    if pacote_ia:
        return pacote_ia, motor
    return ({canal: gerar_copy_comercial(produto, objetivo, campanha, canal, observacoes, tom) for canal in canais}, motor)

def _icone_plataforma_data_uri(plataforma):
    caminho = Path(PLATFORM_ICON_FILES.get(plataforma, ""))
    try:
        bruto = caminho.read_bytes()
        return "data:image/svg+xml;base64," + base64.b64encode(bruto).decode("ascii")
    except Exception:
        return ""

def renderizar_cabecalho_canal(canal, aprovado=False, fila=False):
    cfg = CANAL_MIDIA_CONFIG.get(canal, {})
    uri = _icone_plataforma_data_uri(cfg.get("plataforma", ""))
    largura, altura = cfg.get("size", (0,0))
    status = "NA FILA" if fila else ("APROVADO" if aprovado else "REVISAR")
    status_cor = "#2563eb" if fila else ("#16a34a" if aprovado else "#d97706")
    logo_html = f'<img src="{uri}" style="width:36px;height:36px;object-fit:contain;">' if uri else ""
    st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 15px;border-radius:14px;background:#ffffff;border:1px solid #e5e7eb;border-left:6px solid {cfg.get('cor','#64748b')};margin-bottom:10px;box-shadow:0 2px 8px rgba(15,23,42,.05)"><div style="display:flex;align-items:center;gap:11px">{logo_html}<div><div style="font-size:1.08rem;font-weight:800;color:#111827">{html.escape(cfg.get('rotulo',canal))}</div><div style="font-size:.82rem;color:#6b7280">{largura} × {altura} • {cfg.get('arquivo','')}</div></div></div><span style="font-size:.72rem;font-weight:800;color:white;background:{status_cor};padding:6px 10px;border-radius:999px">{status}</span></div>""", unsafe_allow_html=True)

def _nome_arquivo_seguro(texto):
    limpo = re.sub(r"[^A-Za-z0-9_-]+", "_", str(texto or "campanha")).strip("_")
    return limpo[:80] or "campanha"


def _bytes_video_exportacao(referencia):
    """Lê o vídeo vinculado quando ele estiver disponível como arquivo local."""
    texto = str(referencia or "").strip()
    if not texto or texto.lower().startswith(("http://", "https://")):
        return b"", ""
    try:
        caminho = Path(texto)
        candidatos = [caminho]
        if not caminho.is_absolute():
            candidatos.extend([Path.cwd() / caminho, Path(__file__).resolve().parent / caminho])
        for candidato in candidatos:
            if candidato.exists() and candidato.is_file():
                return candidato.read_bytes(), candidato.suffix.lower() or ".mp4"
    except Exception:
        pass
    return b"", ""


def _checklist_publicacao(canal):
    cfg = CANAL_MIDIA_CONFIG.get(canal, {})
    largura, altura = cfg.get("size", (0, 0))
    tipo = cfg.get("tipo", "imagem")
    passos = [
        f"[ ] Conferir formato: {largura} x {altura}",
        "[ ] Revisar texto, preço, prazo e contato",
        "[ ] Conferir margens e legibilidade no celular",
        "[ ] Publicar manualmente no canal indicado",
    ]
    if tipo == "video":
        passos.extend([
            "[ ] Exportar em MP4 H.264, sem música",
            "[ ] Adicionar a música manualmente dentro da rede social",
            "[ ] Selecionar uma capa legível antes de publicar",
        ])
    else:
        passos.append("[ ] Usar o arquivo PNG da pasta deste canal")
    if canal.startswith("Instagram") or canal in ("Reel", "Carrossel"):
        passos.append("[ ] Confirmar se a replicação no Facebook está ativada na Meta")
    return "\n".join(passos) + "\n"


def gerar_zip_campanha(item):
    """Monta um kit offline organizado por canal para publicação manual."""
    pacote = io.BytesIO()
    nome_base = _nome_arquivo_seguro(item.get("produto") or item.get("id") or "campanha")
    campanha = item.get("campanha") or item.get("objetivo") or ""
    with zipfile.ZipFile(pacote, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifesto = [
            "ALPHAFEST MARKETING STUDIO",
            f"Campanha: {campanha}",
            f"Produto: {item.get('produto') or ''}",
            f"Criada em: {item.get('criado_em') or ''}",
            f"Motor de texto: {item.get('motor_copy') or 'Alpha local'}",
            "",
            "PUBLICAÇÃO MANUAL",
            "O Instagram é o canal principal. O Facebook recebe apenas a replicação configurada na Meta.",
            "Os vídeos são entregues sem música; adicione a trilha dentro da própria rede social.",
        ]
        zf.writestr("00_LEIA-ME.txt", "\n".join(manifesto))

        for indice, canal in enumerate(item.get("canais", []), start=1):
            cfg = CANAL_MIDIA_CONFIG.get(canal, {})
            slug = _nome_arquivo_seguro(canal)
            pasta = f"{indice:02d}_{slug}"
            largura, altura = cfg.get("size", (0, 0))
            especificacao = (
                f"Canal: {canal}\n"
                f"Formato: {largura} x {altura}\n"
                f"Tipo: {cfg.get('tipo', '')}\n"
                f"Arquivo recomendado: {cfg.get('arquivo', '')}\n"
                "Publicação: manual\n"
                "Música: adicionar manualmente na plataforma\n"
            )
            zf.writestr(f"{pasta}/01_ESPECIFICACOES.txt", especificacao)
            zf.writestr(f"{pasta}/02_CHECKLIST.txt", _checklist_publicacao(canal))

            arte_b64 = item.get("artes_png", {}).get(canal)
            if arte_b64:
                try:
                    zf.writestr(f"{pasta}/{nome_base}_{slug}.png", base64.b64decode(arte_b64))
                except Exception:
                    zf.writestr(f"{pasta}/ERRO_ARTE.txt", "A arte não pôde ser decodificada. Gere novamente este formato no Studio.")

            texto_canal = str(item.get("conteudos", {}).get(canal, "")).strip()
            if texto_canal:
                zf.writestr(f"{pasta}/03_TEXTO_PRONTO.txt", texto_canal)

        video_ref = str(item.get("video_original") or "").strip()
        if video_ref:
            video_bytes, extensao = _bytes_video_exportacao(video_ref)
            if video_bytes:
                zf.writestr(f"MIDIA_ORIGINAL/{nome_base}_video_original{extensao}", video_bytes)
            else:
                zf.writestr(
                    "MIDIA_ORIGINAL/REFERENCIA_VIDEO.txt",
                    "O vídeo está vinculado à campanha, mas não estava disponível como arquivo local durante a exportação.\n"
                    f"Referência registrada: {video_ref}\n",
                )

        zf.writestr(
            "99_FORMATOS_OFICIAIS.txt",
            "Instagram Feed: 1080x1350 PNG\n"
            "Instagram Story: 1080x1920 PNG\n"
            "Status WhatsApp: 1080x1920 PNG\n"
            "Instagram Reel: 1080x1920 MP4 H.264, sem música\n"
            "TikTok: 1080x1920 MP4 H.264, sem música\n"
            "YouTube Shorts: 1080x1920 MP4 H.264, sem música\n",
        )
    pacote.seek(0)
    return pacote.getvalue()


def renderizar_cartao_studio(titulo, descricao, icone):
    st.markdown(
        f"<div style='padding:16px;border:1px solid #dbeafe;border-radius:16px;background:#fff;min-height:115px;box-shadow:0 3px 12px rgba(15,23,42,.05)'>"
        f"<div style='font-size:1.55rem'>{icone}</div><div style='font-weight:800;color:#0f3f8c;margin-top:4px'>{html.escape(titulo)}</div>"
        f"<div style='font-size:.86rem;color:#64748b;margin-top:5px'>{html.escape(descricao)}</div></div>",
        unsafe_allow_html=True,
    )


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
        f"{produto} personalizado pela {carregar_config_empresa().get('nome', 'Alphafest')}, "
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

    termos = [produto, categoria, subcategoria, "personalizado", "festa", "presente", carregar_config_empresa().get("cidade", "")]
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

    tags_base = [produto, categoria, subcategoria, carregar_config_empresa().get("nome", "Alphafest"), "Personalizados", "Festa", carregar_config_empresa().get("cidade", "Itatiba")]
    hashtags_lista = []
    for item in tags_base:
        tag = hashtag(item)
        if tag and tag.lower() not in [x.lower() for x in hashtags_lista]:
            hashtags_lista.append(tag)
    hashtags = " ".join(hashtags_lista[:10])

    preco_txt = str(preco or "").strip()
    chamada_preco = f" Valor sugerido: R$ {preco_txt}." if preco_txt else ""
    whatsapp = carregar_config_empresa().get("celular", "")
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
    "integracao_instagram": False,
    "integracao_facebook": False,
    "meta_app_id": "",
    "meta_business_id": "",
    "meta_verify_token": "",
    "webhook_url": "",
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


def _telefone_chave(valor):
    """Normaliza telefone para cruzar atendimento, cliente e proposta."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    return digitos[-11:] if len(digitos) >= 11 else digitos


def estagio_funil_atendimento(item):
    status = str(item.get("status", "Novo contato"))
    mapa = {
        "Novo contato": "Novos leads",
        "Catálogo solicitado": "Em atendimento",
        "Catálogo enviado": "Em atendimento",
        "Orçamento solicitado": "Orçamento",
        "Orçamento em elaboração": "Orçamento",
        "Aguardando cliente": "Aguardando resposta",
        "Pedido aprovado": "Fechados",
        "Comprovante recebido": "Fechados",
        "Arte aprovada": "Fechados",
        "Em produção": "Fechados",
        "Pronto": "Fechados",
        "Entregue": "Fechados",
        "Pós-venda": "Fechados",
        "Arquivado": "Perdidos / arquivados",
    }
    return mapa.get(status, "Em atendimento")


def proxima_acao_crm(item):
    status = str(item.get("status", "Novo contato"))
    mapa = {
        "Novo contato": "Responder e entender a necessidade",
        "Catálogo solicitado": "Enviar o catálogo adequado",
        "Catálogo enviado": "Perguntar o que mais interessou",
        "Orçamento solicitado": "Preparar orçamento",
        "Orçamento em elaboração": "Finalizar e enviar orçamento",
        "Aguardando cliente": "Fazer acompanhamento",
        "Pedido aprovado": "Confirmar dados e enviar à produção",
        "Comprovante recebido": "Conferir pagamento",
        "Arte aprovada": "Iniciar produção",
        "Em produção": "Acompanhar prazo",
        "Pronto": "Avisar cliente",
        "Entregue": "Fazer pós-venda",
        "Pós-venda": "Registrar retorno e oportunidade futura",
        "Arquivado": "Sem ação",
    }
    return mapa.get(status, proxima_acao_atendimento(item))


def calcular_indice_alpha(item, historico=None, clientes=None):
    """Pontuação explicável de 0 a 100 para ordenar oportunidades."""
    historico = historico or []
    clientes = clientes or []
    status = str(item.get("status", "Novo contato"))
    mensagem = str(item.get("mensagem", "")).lower()
    prioridade = str(item.get("prioridade", "Normal"))
    pontos = {
        "Novo contato": 35, "Catálogo solicitado": 42, "Catálogo enviado": 48,
        "Orçamento solicitado": 72, "Orçamento em elaboração": 78,
        "Aguardando cliente": 58, "Pedido aprovado": 96,
        "Comprovante recebido": 98, "Arte aprovada": 95, "Em produção": 92,
        "Pronto": 90, "Entregue": 25, "Pós-venda": 30, "Arquivado": 5,
    }.get(status, 35)
    motivos = [f"Etapa: {status}"]

    bonus_prioridade = {"Urgente": 15, "Alta": 10, "Normal": 4, "Baixa": 0}.get(prioridade, 4)
    pontos += bonus_prioridade
    if bonus_prioridade:
        motivos.append(f"Prioridade {prioridade.lower()}")

    minutos = minutos_aguardando(item)
    if 0 <= minutos <= 15:
        pontos += 7
        motivos.append("Interação recente")
    elif minutos >= 60 and status not in ("Aguardando cliente", "Arquivado", "Entregue", "Pós-venda"):
        pontos += 5
        motivos.append("Resposta da equipe atrasada")
    elif status == "Aguardando cliente" and minutos >= 4320:
        pontos -= 8
        motivos.append("Cliente sem retorno há vários dias")

    palavras_quentes = ["orçamento", "orcamento", "fechar", "prazo", "urgente", "para hoje", "para amanhã", "valor", "quanto fica", "pode fazer"]
    qtd_quentes = sum(1 for termo in palavras_quentes if termo in mensagem)
    if qtd_quentes:
        pontos += min(14, qtd_quentes * 4)
        motivos.append("Mensagem com intenção de compra")

    tel = _telefone_chave(item.get("telefone"))
    nome = str(item.get("cliente", "")).strip().lower()
    cliente_existente = any(
        (tel and _telefone_chave(c.get("whatsapp") or c.get("telefone")) == tel)
        or (nome and str(c.get("nome", "")).strip().lower() == nome)
        for c in clientes
    )
    if cliente_existente:
        pontos += 8
        motivos.append("Cliente já cadastrado")

    compras = 0
    valor_historico = 0.0
    for proposta in historico:
        prop_tel = _telefone_chave(proposta.get("cliente_whatsapp") or proposta.get("whatsapp") or proposta.get("telefone"))
        prop_nome = str(proposta.get("cliente_nome", "")).strip().lower()
        if (tel and prop_tel == tel) or (nome and prop_nome == nome):
            if proposta.get("aprovado") or proposta.get("pago"):
                compras += 1
                try:
                    valor_historico += calcular_valores_proposta(proposta)[2]
                except Exception:
                    pass
    if compras:
        pontos += min(12, 5 + compras * 2)
        motivos.append(f"Cliente recorrente ({compras} pedido(s))")
    if valor_historico >= 1000:
        pontos += 5
        motivos.append("Histórico comercial relevante")

    return max(0, min(100, int(round(pontos)))), motivos[:4]


def temperatura_indice_alpha(indice):
    if indice >= 80:
        return "🔥 Quente"
    if indice >= 55:
        return "🟠 Morno"
    if indice >= 30:
        return "🟡 Em descoberta"
    return "🔵 Frio"

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


def registrar_evento_atendimento(item, descricao, usuario="Sistema"):
    """Registra uma linha do tempo simples dentro do próprio atendimento."""
    historico = item.get("historico") if isinstance(item.get("historico"), list) else []
    historico.append({
        "data": agora_local().strftime("%d/%m/%Y %H:%M"),
        "descricao": str(descricao or "Atualização").strip(),
        "usuario": str(usuario or "Sistema"),
    })
    item["historico"] = historico[-100:]


def sincronizar_atendimento_com_operacao(item, status_anterior=""):
    """Conecta a fila de atendimento com orçamento e fluxo de produção."""
    status = str(item.get("status", "Novo contato"))
    numero = str(item.get("numero_proposta", "")).strip()
    if not numero:
        return

    if status == "Pedido aprovado":
        tarefas = carregar_producao()
        alterou = False
        for tarefa in tarefas:
            if tarefa.get("numero_proposta") == numero and tarefa.get("ativa", True):
                atual = normalizar_status_fluxo(tarefa.get("status"))
                if atual in ["Pedido recebido", "Arte pendente"] and not tarefa.get("necessita_arte"):
                    tarefa["status"] = "Pronto para produzir"
                    tarefa["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                    alterou = True
        if alterou:
            salvar_producao(tarefas)
    elif status == "Arte aprovada":
        tarefas = carregar_producao()
        alterou = False
        for tarefa in tarefas:
            if tarefa.get("numero_proposta") == numero and tarefa.get("ativa", True):
                tarefa["status"] = "Arte aprovada"
                tarefa["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                alterou = True
        if alterou:
            salvar_producao(tarefas)
    elif status == "Em produção":
        tarefas = carregar_producao()
        alterou = False
        for tarefa in tarefas:
            if tarefa.get("numero_proposta") == numero and tarefa.get("ativa", True):
                tarefa["status"] = "Em produção"
                tarefa["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                alterou = True
        if alterou:
            salvar_producao(tarefas)
    elif status == "Pronto":
        tarefas = carregar_producao()
        alterou = False
        for tarefa in tarefas:
            if tarefa.get("numero_proposta") == numero and tarefa.get("ativa", True):
                tarefa["status"] = "Pronto"
                tarefa["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                alterou = True
        if alterou:
            salvar_producao(tarefas)
    elif status == "Entregue":
        alternar_status(numero, "entregue", True)


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


COMPONENTES_PADRAO = {
    "Materiais": [],
    "Cores": [],
    "Tamanhos": [],
    "Acabamentos": [],
    "Acessórios": [],
    "Formatos": [],
    "Técnicas": [],
    "Temas e personagens": [],
    "Outros": [],
}


def carregar_componentes():
    dados = load_document("componentes_db", ARQUIVO_COMPONENTES, COMPONENTES_PADRAO)
    resultado = {chave: [] for chave in COMPONENTES_PADRAO}
    if isinstance(dados, dict):
        for categoria, valores in dados.items():
            nome = str(categoria).strip()
            if not nome:
                continue
            if isinstance(valores, list):
                resultado[nome] = sorted({str(v).strip() for v in valores if str(v).strip()}, key=str.lower)
    return resultado


def salvar_componentes(dados):
    if not isinstance(dados, dict):
        raise ValueError("A biblioteca de componentes precisa ser um dicionário.")
    limpo = {}
    for categoria, valores in dados.items():
        nome = str(categoria).strip()
        if not nome:
            continue
        limpo[nome] = sorted({str(v).strip() for v in (valores or []) if str(v).strip()}, key=str.lower)
    save_document("componentes_db", limpo, ARQUIVO_COMPONENTES)


def componentes_do_projeto(projeto):
    dados = projeto.get("componentes", {})
    return dados if isinstance(dados, dict) else {}


def texto_componentes_projeto(projeto):
    partes = []
    for categoria, valores in componentes_do_projeto(projeto).items():
        partes.append(str(categoria))
        partes.extend(str(v) for v in (valores or []))
    return " ".join(partes)


def renderizar_base_conhecimento():
    st.header("🧠 Base de Conhecimento Alphafest")
    st.caption("Cadastre opções que agilizam o trabalho, sem limitar a criação. Qualquer novidade pode ser adicionada na hora.")

    tab_biblioteca, tab_vincular, tab_pesquisa = st.tabs([
        "🧩 Biblioteca de componentes", "🔗 Componentes dos projetos", "🔎 Pesquisa por características"
    ])

    with tab_biblioteca:
        componentes = carregar_componentes()
        c1, c2, c3 = st.columns([2, 3, 1])
        categorias = sorted(componentes.keys(), key=str.lower)
        categoria = c1.selectbox("Categoria", categorias, key="kb_categoria")
        novo = c2.text_input("Nova opção", placeholder="Ex.: Confete metalizado em formato de estrela", key="kb_nova_opcao")
        if c3.button("Adicionar", type="primary", use_container_width=True, key="kb_add"):
            if novo.strip():
                componentes.setdefault(categoria, [])
                if novo.strip().lower() not in {x.lower() for x in componentes[categoria]}:
                    componentes[categoria].append(novo.strip())
                    salvar_componentes(componentes)
                    st.success("Opção adicionada.")
                    st.rerun()
                else:
                    st.info("Essa opção já existe.")
        with st.expander("➕ Criar nova categoria"):
            nova_categoria = st.text_input("Nome da categoria", placeholder="Ex.: Tipos de confete", key="kb_nova_categoria")
            if st.button("Criar categoria", key="kb_criar_categoria"):
                if nova_categoria.strip() and nova_categoria.strip() not in componentes:
                    componentes[nova_categoria.strip()] = []
                    salvar_componentes(componentes)
                    st.success("Categoria criada.")
                    st.rerun()

        st.divider()
        for nome_cat in sorted(componentes.keys(), key=str.lower):
            valores = componentes.get(nome_cat, [])
            with st.expander(f"{nome_cat} ({len(valores)})", expanded=(nome_cat == categoria)):
                if not valores:
                    st.caption("Nenhuma opção cadastrada ainda.")
                for idx, valor in enumerate(valores):
                    a, b = st.columns([8, 1])
                    a.write(valor)
                    if b.button("🗑️", key=f"kb_del_{nome_cat}_{idx}", help="Remover da biblioteca; não altera projetos já salvos"):
                        componentes[nome_cat] = [v for v in valores if v != valor]
                        salvar_componentes(componentes)
                        st.rerun()

    with tab_vincular:
        projetos = carregar_projetos()
        if not projetos:
            st.info("Ainda não há projetos na Memória da Empresa.")
        else:
            opcoes = {
                f"{p.get('id')} — {p.get('cliente_nome') or 'Cliente'} — {p.get('tema') or ', '.join(p.get('produtos', []) or []) or 'Projeto'}": p
                for p in projetos
            }
            escolhido = st.selectbox("Projeto", list(opcoes.keys()), key="kb_projeto")
            projeto = dict(opcoes[escolhido])
            biblioteca = carregar_componentes()
            atuais = componentes_do_projeto(projeto)
            novos_componentes = {}
            st.caption("Marque apenas o que foi usado neste projeto. Você pode adicionar uma opção nova sem sair da tela.")
            for cat in sorted(biblioteca.keys(), key=str.lower):
                novos_componentes[cat] = st.multiselect(
                    cat,
                    biblioteca.get(cat, []),
                    default=[x for x in atuais.get(cat, []) if x in biblioteca.get(cat, [])],
                    key=f"kb_proj_{projeto.get('id')}_{cat}",
                )
            livres = st.text_area(
                "Características livres / ainda não cadastradas",
                value=str(projeto.get("caracteristicas_livres", "")),
                placeholder="Ex.: confete meia-lua perolado, mistura exclusiva de cores...",
                key=f"kb_livres_{projeto.get('id')}",
            )
            if st.button("💾 Salvar conhecimento do projeto", type="primary", use_container_width=True, key="kb_salvar_projeto"):
                projeto["componentes"] = {k: v for k, v in novos_componentes.items() if v}
                projeto["caracteristicas_livres"] = livres.strip()
                atualizar_projeto(projeto)
                st.success("Conhecimento do projeto salvo.")
                st.rerun()

    with tab_pesquisa:
        termo = st.text_input("Pesquisar", placeholder="Ex.: coração, fosco, dourado, LED, beach tennis", key="kb_busca").strip().lower()
        projetos = carregar_projetos()
        if termo:
            encontrados = []
            for projeto in projetos:
                base = " ".join([
                    texto_busca_projeto(projeto), texto_componentes_projeto(projeto),
                    str(projeto.get("caracteristicas_livres", "")), str(projeto.get("necessidade", "")),
                    str(projeto.get("detalhes", "")),
                ]).lower()
                if termo in base:
                    encontrados.append(projeto)
            st.caption(f"{len(encontrados)} projeto(s) encontrado(s)")
            for projeto in encontrados[:50]:
                with st.expander(f"{projeto.get('id')} — {projeto.get('cliente_nome') or 'Cliente'}"):
                    st.write(f"**Produtos:** {', '.join(projeto.get('produtos', []) or []) or 'Não informado'}")
                    st.write(f"**Tema:** {projeto.get('tema') or 'Não informado'}")
                    comps = componentes_do_projeto(projeto)
                    if comps:
                        for cat, valores in comps.items():
                            st.write(f"**{cat}:** {', '.join(valores)}")
                    if projeto.get("caracteristicas_livres"):
                        st.write(f"**Características livres:** {projeto.get('caracteristicas_livres')}")
        else:
            st.info("Digite uma característica para localizar produções semelhantes.")



# --- ALPHA ASSISTENTE COMERCIAL (6.1) ---
def _texto_sem_acentos(valor):
    import unicodedata
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def analisar_mensagem_alpha(mensagem):
    """Interpretação local e explicável do pedido, sem custo de API externa.

    A análise é propositalmente assistida: organiza o texto e sugere perguntas,
    mas a equipe confirma tudo antes de criar projeto ou orçamento.
    """
    original = str(mensagem or "").strip()
    texto = _texto_sem_acentos(original)
    familias = {
        "Bubble": ["bubble", "buble", "balao transparente"],
        "Topo de bolo": ["topo", "topper", "topo de bolo"],
        "Papel de arroz": ["papel de arroz", "papel arroz"],
        "Balões / decoração": ["balao", "baloes", "decoracao", "arco de baloes"],
        "Camiseta": ["camiseta", "camisa", "uniforme", "polo"],
        "Caneca": ["caneca", "copo", "squeeze"],
        "Chaveiro": ["chaveiro", "chaveiros"],
        "Medalha": ["medalha", "medalhas"],
        "Troféu": ["trofeu", "trofeus"],
        "Banner / faixa": ["banner", "faixa", "painel"],
        "Caixa / lembrancinha": ["caixa", "caixinha", "lembrancinha", "lembranca"],
        "Impressão 3D": ["3d", "impressao 3d", "peca 3d"],
    }
    detectados = []
    for familia, termos in familias.items():
        if any(t in texto for t in termos):
            detectados.append(familia)

    ocasioes = {
        "Aniversário": ["aniversario", "anos", "festa infantil"],
        "Casamento": ["casamento", "noivado", "bodas"],
        "Chá revelação / bebê": ["cha revelacao", "cha de bebe", "bebe"],
        "Empresa / evento corporativo": ["empresa", "corporativo", "sipat", "inauguracao"],
        "Escola": ["escola", "formatura", "volta as aulas", "professor"],
        "Esporte": ["campeonato", "torneio", "beach tennis", "futebol", "basquete", "volei", "tenis"],
        "Campanha": ["outubro rosa", "novembro azul", "campanha", "acao promocional"],
    }
    ocasiao = next((nome for nome, termos in ocasioes.items() if any(t in texto for t in termos)), "")

    cores_lista = ["rosa", "azul", "dourado", "prata", "vermelho", "verde", "amarelo", "lilas", "roxo", "preto", "branco", "laranja", "marrom", "bege", "colorido"]
    cores = [c for c in cores_lista if c in texto]

    idade = ""
    m = re.search(r"(?:idade\s*)?(\d{1,2})\s*(?:anos|ano)", texto)
    if m:
        idade = f"{m.group(1)} anos"

    quantidade = ""
    padroes_qtd = [r"(\d+)\s*(?:unidades|unidade|pecas|peca|camisas|camisetas|medalhas|chaveiros|pessoas|criancas|convidados)", r"quantidade\s*[:=-]?\s*(\d+)"]
    for padrao in padroes_qtd:
        mq = re.search(padrao, texto)
        if mq:
            quantidade = mq.group(0)
            break

    prazo = ""
    if "urgente" in texto or "para hoje" in texto:
        prazo = "Urgente / hoje"
    elif "amanha" in texto:
        prazo = "Amanhã"
    elif "sabado" in texto:
        prazo = "Sábado"
    elif "domingo" in texto:
        prazo = "Domingo"
    else:
        md = re.search(r"\b(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b", texto)
        if md:
            prazo = md.group(1)

    # Tema é uma sugestão, nunca uma confirmação automática.
    tema = ""
    padroes_tema = [
        r"tema\s+(?:do|da|de)?\s*([a-z0-9][a-z0-9 ]{1,35})",
        r"(?:do|da)\s+([a-z][a-z0-9 -]{2,25})\s+(?:para|com|de|,|\.)",
    ]
    for padrao in padroes_tema:
        mt = re.search(padrao, texto)
        if mt:
            candidato = mt.group(1).strip(" ,.-")
            candidato = re.split(r"\b(?:para|com|em|e|que|uma|um)\b", candidato)[0].strip()
            if candidato and candidato not in {"cliente", "menina", "menino", "empresa"}:
                tema = candidato.title()
                break

    detalhes_encontrados = []
    detalhes_termos = {
        "LED": ["led", "luz"], "Confete": ["confete"], "Metalizado": ["metalizado"],
        "Fosco": ["fosco"], "Coração": ["coracao"], "Estrela": ["estrela"],
        "Lua": ["lua"], "Pelúcia": ["pelucia"], "Glitter": ["glitter"],
        "Base de balões": ["base de baloes"], "Entrega": ["entrega", "entregar"],
        "Retirada": ["retirada", "retirar"],
    }
    for nome, termos in detalhes_termos.items():
        if any(t in texto for t in termos):
            detalhes_encontrados.append(nome)

    perguntas = []
    produto_principal = detectados[0] if detectados else ""
    if not produto_principal:
        perguntas.append("Qual produto ou solução o cliente imagina?")
    if not tema and produto_principal not in ("Empresa / evento corporativo",):
        perguntas.append("Qual é o tema, personagem ou identidade visual?")
    if not prazo:
        perguntas.append("Qual é a data ou o prazo de entrega?")
    if not quantidade:
        perguntas.append("Qual é a quantidade necessária?")
    if "Entrega" not in detalhes_encontrados and "Retirada" not in detalhes_encontrados:
        perguntas.append("Será retirada ou entrega?")

    especificas = {
        "Bubble": ["Qual tamanho do Bubble?", "Vai com LED?", "Qual tipo, formato e cor do confete?", "Terá base, laço, pelúcia ou outro acessório?"],
        "Topo de bolo": ["Qual nome e idade?", "Quantas camadas e qual acabamento?", "Tem preferência de cores ou materiais?"],
        "Papel de arroz": ["Qual tamanho e formato?", "O cliente enviará foto ou arte?"],
        "Camiseta": ["Qual modelo, cor e tamanhos?", "A arte ou logotipo já está pronto?", "Terá nomes ou numeração individual?"],
        "Medalha": ["Qual modalidade e tamanho?", "Qual texto ou gravação?", "Precisa de fita e embalagem?"],
        "Troféu": ["Qual modalidade, altura e material?", "Qual texto ou gravação?"],
        "Chaveiro": ["Qual material, formato e tamanho?", "Precisa de embalagem ou etiqueta?"],
    }
    for pergunta in especificas.get(produto_principal, []):
        termo_chave = _texto_sem_acentos(pergunta).split()[1:3]
        if not any(t in texto for t in termo_chave):
            perguntas.append(pergunta)

    return {
        "texto_original": original,
        "produtos": detectados,
        "produto_principal": produto_principal,
        "ocasiao": ocasiao,
        "tema": tema,
        "idade": idade,
        "cores": cores,
        "quantidade": quantidade,
        "prazo": prazo,
        "detalhes": detalhes_encontrados,
        "perguntas": list(dict.fromkeys(perguntas))[:8],
    }


def buscar_referencias_alpha(analise, limite=6):
    termos = []
    for valor in [analise.get("produto_principal"), analise.get("tema"), analise.get("ocasiao")]:
        if valor:
            termos.extend(_texto_sem_acentos(valor).split())
    termos.extend(_texto_sem_acentos(" ".join(analise.get("cores", []))).split())
    termos = [t for t in termos if len(t) >= 3]
    projetos = []
    for projeto in carregar_projetos():
        base = _texto_sem_acentos(" ".join(str(projeto.get(k, "")) for k in ["tema", "produtos", "necessidade", "detalhes", "caracteristicas_livres", "observacoes", "cliente_nome"]))
        pontos = sum(1 for t in termos if t in base)
        if pontos:
            projetos.append((pontos, projeto))
    produtos = []
    for produto in carregar_catalogo():
        base = _texto_sem_acentos(" ".join(str(produto.get(k, "")) for k in ["nome", "categoria", "descricao", "descricao_curta", "palavras_chave", "tema"]))
        pontos = sum(1 for t in termos if t in base)
        if pontos:
            produtos.append((pontos, produto))
    projetos.sort(key=lambda x: x[0], reverse=True)
    produtos.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in projetos[:limite]], [p for _, p in produtos[:limite]]


def resposta_assistida_alpha(analise):
    produto = analise.get("produto_principal") or "personalizado"
    abertura = f"Olá! 😊 Trabalhamos sim com {produto}."
    conhecidos = []
    if analise.get("tema"):
        conhecidos.append(f"tema {analise['tema']}")
    if analise.get("idade"):
        conhecidos.append(analise["idade"])
    if analise.get("cores"):
        conhecidos.append("cores " + ", ".join(analise["cores"]))
    meio = (" Entendi que você procura " + ", ".join(conhecidos) + ".") if conhecidos else ""
    perguntas = analise.get("perguntas", [])[:3]
    fim = " Para preparar o orçamento, poderia me informar: " + " ".join(f"• {p}" for p in perguntas) if perguntas else " Vou preparar as opções para você."
    return abertura + meio + fim


def preencher_jornada_com_alpha(analise, cliente="", whatsapp=""):
    st.session_state["jornada_cliente"] = str(cliente or "")
    st.session_state["jornada_whatsapp"] = str(whatsapp or "")
    st.session_state["jornada_necessidade"] = analise.get("texto_original", "")
    st.session_state["jornada_ocasiao"] = analise.get("ocasiao", "")
    st.session_state["jornada_tema"] = analise.get("tema", "")
    st.session_state["jornada_quantidade"] = analise.get("quantidade", "")
    st.session_state["jornada_prazo"] = analise.get("prazo", "")
    detalhes = ", ".join([*(analise.get("cores") or []), *(analise.get("detalhes") or [])])
    st.session_state["jornada_detalhes"] = detalhes
    st.session_state["jornada_observacoes"] = "Perguntas pendentes: " + " | ".join(analise.get("perguntas", []))


def renderizar_alpha_assistente_comercial():
    st.header("🤖 Alpha Assistente Comercial")
    st.caption("Cole a mensagem do cliente. O Alpha organiza o pedido, mostra o que falta perguntar e procura referências da própria Alphafest. Nada é enviado automaticamente.")

    dados = carregar_atendimentos()
    abertos = [x for x in dados.get("itens", []) if x.get("status") not in ("Entregue", "Pós-venda", "Arquivado")]
    opcoes = {f"{x.get('cliente') or 'Contato'} · {x.get('canal') or x.get('origem') or 'Canal'} · {str(x.get('mensagem') or '')[:55]}": x for x in abertos}
    origem = st.radio("Origem da análise", ["Mensagem livre", "Oportunidade da Central Multicanal"], horizontal=True)
    cliente = ""
    whatsapp = ""
    atendimento_id = ""
    mensagem = ""
    if origem == "Oportunidade da Central Multicanal" and opcoes:
        escolha = st.selectbox("Selecione a oportunidade", list(opcoes.keys()))
        item = opcoes[escolha]
        cliente = str(item.get("cliente") or "")
        whatsapp = str(item.get("telefone") or "")
        atendimento_id = str(item.get("id") or "")
        mensagem = st.text_area("Mensagem recebida", value=str(item.get("mensagem") or ""), height=120)
    else:
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente / identificação (opcional)", key="alpha_cliente")
        whatsapp = c2.text_input("WhatsApp (opcional)", key="alpha_whatsapp")
        mensagem = st.text_area("Digite ou cole exatamente como o cliente falou", key="alpha_mensagem", height=140, placeholder="Ex.: Quero um Bubble do Stitch para uma menina de 6 anos, rosa e dourado, para sábado.")

    if not mensagem.strip():
        st.info("Digite uma mensagem para o Alpha preparar o atendimento.")
        return

    relacionamento_alpha = localizar_relacionamento(cliente, whatsapp)
    restricao_alpha = resumo_restricao_relacionamento(relacionamento_alpha)
    if relacionamento_alpha:
        st.caption("Contato identificado no módulo Relacionamentos: " + ", ".join(papeis_relacionamento(relacionamento_alpha)))
    if restricao_alpha:
        nivel = restricao_alpha.get("nivel", "Atenção")
        motivo = restricao_alpha.get("motivo") or "Política comercial definida pela Alphafest."
        if nivel == "Bloqueado" or not restricao_alpha.get("permitir_resposta", True):
            st.error(f"🛑 Atendimento bloqueado: {motivo}")
        else:
            st.warning(f"🛡️ Atendimento {nivel}: {motivo}")
        if restricao_alpha.get("exigir_pagamento_antecipado"):
            st.info("💰 Este relacionamento exige pagamento antecipado.")
        if restricao_alpha.get("exigir_aprovacao_gestor"):
            st.info("👤 Este atendimento exige aprovação do gestor.")

    analise = analisar_mensagem_alpha(mensagem)
    projetos, produtos = buscar_referencias_alpha(analise)
    st.markdown("### Entendimento do pedido")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Produto principal", analise.get("produto_principal") or "A confirmar")
    c2.metric("Tema", analise.get("tema") or "A confirmar")
    c3.metric("Ocasião", analise.get("ocasiao") or "A confirmar")
    c4.metric("Prazo", analise.get("prazo") or "A confirmar")
    if analise.get("cores") or analise.get("idade") or analise.get("quantidade") or analise.get("detalhes"):
        st.write("**Detalhes identificados:**", " · ".join(filter(None, [analise.get("idade"), analise.get("quantidade"), ", ".join(analise.get("cores", [])), ", ".join(analise.get("detalhes", []))])))

    st.markdown("### Próximas perguntas sugeridas")
    if analise.get("perguntas"):
        for pergunta in analise["perguntas"]:
            st.checkbox(pergunta, key=f"alpha_pergunta_{abs(hash(pergunta))}")
    else:
        st.success("O pedido já possui as informações essenciais para iniciar o orçamento.")

    st.markdown("### Resposta assistida")
    resposta = st.text_area("Revise antes de enviar", value=resposta_assistida_alpha(analise), height=130, key=f"alpha_resposta_{abs(hash(mensagem))}")
    telefone = _telefone_chave(whatsapp)
    a1, a2, a3 = st.columns(3)
    bloqueado_alpha = bool(restricao_alpha and (restricao_alpha.get("nivel") == "Bloqueado" or not restricao_alpha.get("permitir_resposta", True)))
    if telefone and not bloqueado_alpha:
        numero = telefone if telefone.startswith("55") else "55" + telefone
        a1.link_button("📱 Abrir WhatsApp", f"https://wa.me/{numero}?text={quote(resposta)}", use_container_width=True)
    elif bloqueado_alpha:
        a1.button("🛑 Resposta bloqueada", disabled=True, use_container_width=True)
    else:
        a1.button("📱 Informe o WhatsApp", disabled=True, use_container_width=True)
    if a2.button("🚀 Levar para Jornada", type="primary", use_container_width=True, disabled=bool(restricao_alpha and not restricao_alpha.get("permitir_orcamento", True))):
        preencher_jornada_com_alpha(analise, cliente, whatsapp)
        if atendimento_id:
            st.session_state["alpha_atendimento_origem"] = atendimento_id
        st.success("Dados preparados. Abra a aba Jornada para continuar sem redigitar.")
    if a3.button("🧩 Preparar Projeto", use_container_width=True, disabled=bool(restricao_alpha and not restricao_alpha.get("permitir_orcamento", True))):
        st.session_state["_projeto_prefill"] = {"cliente": cliente, "whatsapp": whatsapp, "necessidade": mensagem, "origem": "Alpha Assistente Comercial", "atendimento_id": atendimento_id}
        st.success("Projeto preparado. Abra Projeto Personalizado.")

    st.markdown("### Referências encontradas na Alphafest")
    rp, rc = st.columns(2)
    with rp:
        st.write(f"**Projetos semelhantes ({len(projetos)})**")
        if not projetos:
            st.caption("Nenhum projeto semelhante encontrado ainda.")
        for projeto in projetos:
            with st.container(border=True):
                st.write(f"**{projeto.get('tema') or projeto.get('necessidade') or projeto.get('id', 'Projeto')}**")
                st.caption(" · ".join(str(x) for x in (projeto.get("produtos") or [])[:4]) if isinstance(projeto.get("produtos"), list) else str(projeto.get("produtos") or ""))
                if projeto.get("numero_proposta"):
                    st.caption(f"Proposta: {projeto.get('numero_proposta')}")
    with rc:
        st.write(f"**Produtos do catálogo ({len(produtos)})**")
        if not produtos:
            st.caption("Nenhum produto relacionado encontrado ainda.")
        for produto in produtos:
            with st.container(border=True):
                st.write(f"**{produto.get('nome', 'Produto')}**")
                preco = valor_float(produto.get("preco", produto.get("valor", 0)))
                if preco:
                    st.caption(f"Referência cadastrada: R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                st.caption(str(produto.get("categoria") or ""))

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


def registrar_evento_projeto(projeto, descricao, usuario="Sistema"):
    timeline = projeto.get("timeline") if isinstance(projeto.get("timeline"), list) else []
    timeline.append({
        "data": agora_local().strftime("%d/%m/%Y %H:%M"),
        "descricao": str(descricao or "Atualização").strip(),
        "usuario": str(usuario or "Sistema"),
    })
    projeto["timeline"] = timeline[-100:]
    projeto["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")


def proxima_acao_projeto(projeto):
    status = str(projeto.get("status", "Briefing"))
    if not str(projeto.get("numero_proposta", "")).strip():
        return "Revisar briefing e preparar orçamento"
    mapa = {
        "Briefing": "Preparar orçamento",
        "Orçamento preparado": "Revisar e salvar proposta",
        "Orçamento criado": "Aguardar aprovação do cliente",
        "Aprovado": "Enviar para produção",
        "Em produção": "Acompanhar fabricação",
        "Pronto": "Avisar cliente",
        "Entregue": "Registrar pós-venda",
    }
    return mapa.get(status, "Revisar andamento")


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
        " ".join(projeto.get("produtos", []) or []), texto_componentes_projeto(projeto),
        projeto.get("caracteristicas_livres", ""), projeto.get("necessidade", ""), projeto.get("detalhes", ""),
    ]
    for arq in projeto.get("arquivos", []) or []:
        partes.extend([arq.get("nome", ""), arq.get("categoria", ""), arq.get("descricao", ""), " ".join(arq.get("tags", []) or [])])
    return " ".join(str(x) for x in partes).lower()




def _texto_especificacoes_jornada(dados):
    partes = [
        f"Necessidade: {dados.get('necessidade', '').strip()}" if dados.get('necessidade', '').strip() else "",
        f"Ocasião: {dados.get('ocasiao', '').strip()}" if dados.get('ocasiao', '').strip() else "",
        f"Tema: {dados.get('tema', '').strip()}" if dados.get('tema', '').strip() else "",
        f"Quantidade/necessidade: {dados.get('quantidade_livre', '').strip()}" if dados.get('quantidade_livre', '').strip() else "",
        f"Prazo desejado: {dados.get('prazo_texto', '').strip()}" if dados.get('prazo_texto', '').strip() else "",
        f"Faixa de orçamento: {dados.get('limite_orcamento', '').strip()}" if dados.get('limite_orcamento', '').strip() else "",
        f"Detalhes: {dados.get('detalhes', '').strip()}" if dados.get('detalhes', '').strip() else "",
        f"Observações: {dados.get('observacoes', '').strip()}" if dados.get('observacoes', '').strip() else "",
    ]
    return " | ".join(x for x in partes if x)


def _salvar_rascunho_jornada(dados):
    projetos = carregar_projetos()
    pid = st.session_state.get("jornada_rascunho_id") or f"PRJ-{agora_local().strftime('%Y%m%d%H%M%S%f')}"
    existente = next((p for p in projetos if p.get("id") == pid), {})
    projeto = {
        **existente,
        "id": pid,
        "tipo": "jornada_atendimento",
        "origem": "Jornada de Atendimento",
        "numero_proposta": existente.get("numero_proposta", ""),
        "cliente_nome": dados.get("cliente", "").strip(),
        "whatsapp": dados.get("whatsapp", "").strip(),
        "ocasiao": dados.get("ocasiao", "").strip(),
        "tema": dados.get("tema", "").strip(),
        "necessidade": dados.get("necessidade", "").strip(),
        "quantidade_livre": dados.get("quantidade_livre", "").strip(),
        "prazo_texto": dados.get("prazo_texto", "").strip(),
        "limite_orcamento": dados.get("limite_orcamento", "").strip(),
        "produtos": [str(i.get("produto", "")).strip() for i in st.session_state.jornada_itens if str(i.get("produto", "")).strip()],
        "detalhes": dados.get("detalhes", "").strip(),
        "observacoes": dados.get("observacoes", "").strip(),
        "arquivos": existente.get("arquivos", []),
        "modelo": existente.get("modelo", False),
        "favorito": existente.get("favorito", False),
        "status": "Briefing",
        "timeline": existente.get("timeline", []) if isinstance(existente.get("timeline", []), list) else [],
        "criado_em": existente.get("criado_em", agora_local().strftime("%d/%m/%Y %H:%M")),
        "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
    }
    registrar_evento_projeto(projeto, "Rascunho da jornada salvo")
    atualizar_projeto(projeto)
    st.session_state.jornada_rascunho_id = pid
    return projeto


def renderizar_jornada_atendimento():
    """Fluxo único: necessidade -> itens -> proposta, sem trocar de módulo."""
    st.markdown("## 🚀 Jornada de Atendimento")
    st.caption("Registre a necessidade, monte a solução e gere a proposta na mesma tela. Nada precisa ser digitado duas vezes.")

    progresso = 0
    if st.session_state.get("jornada_cliente") or st.session_state.get("jornada_whatsapp"):
        progresso += 20
    if st.session_state.get("jornada_necessidade"):
        progresso += 30
    if st.session_state.jornada_itens:
        progresso += 30
    if st.session_state.get("jornada_entrega"):
        progresso += 20
    st.progress(min(progresso, 100) / 100, text=f"Progresso do atendimento: {min(progresso, 100)}%")

    st.markdown("### 1. Cliente e necessidade")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Cliente / identificação", key="jornada_cliente", placeholder="Ex.: Maria, Escola ABC, Arena Beach")
    whatsapp = c2.text_input("WhatsApp", key="jornada_whatsapp", placeholder="Ex.: 11999999999")
    necessidade = st.text_area(
        "O que o cliente precisa?",
        key="jornada_necessidade",
        placeholder="Digite como o cliente falou no WhatsApp.",
        height=110,
    )
    c3, c4, c5 = st.columns(3)
    ocasiao = c3.text_input("Ocasião", key="jornada_ocasiao", placeholder="Aniversário, empresa, escola...")
    tema = c4.text_input("Tema / personagem", key="jornada_tema", placeholder="Stitch, futebol, marca...")
    quantidade_livre = c5.text_input("Quantidade / necessidade", key="jornada_quantidade", placeholder="1 unidade, 30 pessoas...")
    c6, c7 = st.columns(2)
    prazo_texto = c6.text_input("Prazo desejado", key="jornada_prazo", placeholder="sábado, 15/08, urgente...")
    limite_orcamento = c7.text_input("Faixa de orçamento", key="jornada_limite", placeholder="até R$ 150...")
    detalhes = st.text_area("Materiais, cores, tamanhos, acabamentos e acessórios", key="jornada_detalhes", height=80)
    observacoes = st.text_area("Observações internas", key="jornada_observacoes", height=70)

    dados_jornada = {
        "cliente": cliente, "whatsapp": whatsapp, "necessidade": necessidade,
        "ocasiao": ocasiao, "tema": tema, "quantidade_livre": quantidade_livre,
        "prazo_texto": prazo_texto, "limite_orcamento": limite_orcamento,
        "detalhes": detalhes, "observacoes": observacoes,
    }

    salvar_col, limpar_col = st.columns([1, 1])
    if salvar_col.button("💾 Salvar rascunho", use_container_width=True):
        if not necessidade.strip():
            st.warning("Descreva o que o cliente precisa antes de salvar.")
        else:
            _salvar_rascunho_jornada(dados_jornada)
            st.success("Rascunho salvo na Memória da Empresa.")
    if limpar_col.button("🧹 Limpar jornada", use_container_width=True):
        for chave in [
            "jornada_cliente", "jornada_whatsapp", "jornada_necessidade", "jornada_ocasiao",
            "jornada_tema", "jornada_quantidade", "jornada_prazo", "jornada_limite",
            "jornada_detalhes", "jornada_observacoes", "jornada_entrega", "jornada_desconto",
            "jornada_prazo_prod", "jornada_frete", "jornada_validade",
        ]:
            st.session_state.pop(chave, None)
        st.session_state.jornada_itens = []
        st.session_state.jornada_rascunho_id = ""
        st.rerun()

    st.divider()
    st.markdown("### 2. Monte a solução")
    catalogo = carregar_catalogo()
    opcoes_catalogo = sorted({str(p.get("nome", "")).strip() for p in catalogo if str(p.get("nome", "")).strip()})
    i1, i2, i3 = st.columns([3, 1, 1])
    produto_item = i1.text_input("Produto / solução", key="jornada_produto", placeholder="Digite livremente ou escolha abaixo")
    quantidade_item = i2.number_input("Qtd.", min_value=1, value=1, key="jornada_qtd")
    valor_item = i3.number_input("Valor unitário", min_value=0.0, step=0.5, key="jornada_valor")
    escolha_catalogo = st.selectbox("Ou selecione do catálogo", [""] + opcoes_catalogo, key="jornada_catalogo")
    especificacao_item = st.text_area("Detalhes deste item", key="jornada_especificacao", height=70)
    if st.button("➕ Adicionar à solução", type="primary", use_container_width=True):
        nome_item = produto_item.strip() or escolha_catalogo.strip()
        if not nome_item:
            st.warning("Informe um produto ou solução.")
        else:
            preco = valor_item
            if preco <= 0 and escolha_catalogo:
                prod_cat = next((p for p in catalogo if str(p.get("nome", "")).strip() == escolha_catalogo), None)
                if prod_cat:
                    preco = valor_float(prod_cat.get("preco", prod_cat.get("valor", 0)))
            geral = _texto_especificacoes_jornada(dados_jornada)
            combinado = " | ".join(x for x in [geral, especificacao_item.strip()] if x)
            st.session_state.jornada_itens.append({
                "produto": nome_item,
                "especificacoes": combinado,
                "quantidade": quantidade_item,
                "valor_unitario": preco,
            })
            st.session_state.pop("jornada_produto", None)
            st.session_state.pop("jornada_catalogo", None)
            st.session_state.pop("jornada_especificacao", None)
            st.rerun()

    if st.session_state.jornada_itens:
        for idx, item in enumerate(st.session_state.jornada_itens):
            cinfo, crem = st.columns([8, 1])
            cinfo.write(f"**{idx + 1}. {item.get('produto')}** — {item.get('quantidade')} × R$ {valor_float(item.get('valor_unitario')):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            cinfo.caption(item.get("especificacoes", ""))
            if crem.button("🗑️", key=f"jornada_remover_{idx}"):
                st.session_state.jornada_itens.pop(idx)
                st.rerun()
    else:
        st.info("Adicione pelo menos um item para gerar a proposta.")

    st.divider()
    st.markdown("### 3. Finalize a proposta")
    f1, f2, f3 = st.columns(3)
    desconto = f1.number_input("Desconto (R$)", min_value=0.0, step=0.5, key="jornada_desconto")
    data_entrega = f2.date_input("Data de entrega", key="jornada_entrega")
    prazo_prod = f3.text_input("Prazo de produção", key="jornada_prazo_prod")
    f4, f5 = st.columns(2)
    frete = f4.text_input("Frete / entrega", key="jornada_frete")
    validade = f5.text_input("Validade da proposta", key="jornada_validade")

    subtotal = sum(valor_float(i.get("quantidade")) * valor_float(i.get("valor_unitario")) for i in st.session_state.jornada_itens)
    total = max(subtotal - desconto, 0.0)
    st.metric("Valor total", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    if st.button("🚀 Criar projeto e proposta", type="primary", use_container_width=True, disabled=not bool(st.session_state.jornada_itens)):
        if not necessidade.strip():
            st.warning("Descreva a necessidade do cliente.")
            return
        projeto = _salvar_rascunho_jornada(dados_jornada)
        numero = f"PROP-{agora_local().strftime('%Y%m%d%H%M%S')}"
        proposta = {
            "numero_proposta": numero,
            "data_geracao": agora_local().strftime("%d/%m/%Y"),
            "data_entrega": data_entrega.strftime("%d/%m/%Y"),
            "cliente_nome": cliente.strip(),
            "documento": "",
            "whatsapp": whatsapp.strip(),
            "cliente_cpf_cnpj": "",
            "cliente_wa": whatsapp.strip(),
            "itens": list(st.session_state.jornada_itens),
            "subtotal": subtotal,
            "desconto": desconto,
            "desconto_valor": desconto,
            "valor_total": total,
            "prazo_dias": prazo_prod,
            "frete_tipo": frete,
            "validade_dias": validade,
            "pago": False,
            "entregue": False,
            "aprovado": False,
            "timeline": [],
            "atendimento_id": "",
            "projeto_id": projeto.get("id", ""),
        }
        registrar_evento_proposta(proposta, "Proposta criada pela Jornada de Atendimento")
        historico = carregar_historico()
        historico.insert(0, proposta)
        salvar_historico_completo(historico)
        projeto["numero_proposta"] = numero
        projeto["status"] = "Orçamento criado"
        registrar_evento_projeto(projeto, f"Proposta {numero} criada na Jornada de Atendimento")
        atualizar_projeto(projeto)
        registrar_auditoria("Criar proposta", "Proposta", numero, {"origem": "Jornada de Atendimento", "cliente": cliente.strip()})
        st.success(f"Proposta {numero} criada com sucesso. O projeto e a linha do tempo foram vinculados.")
        st.session_state.alerta_proposta_numero = numero
        for chave in [
            "jornada_cliente", "jornada_whatsapp", "jornada_necessidade", "jornada_ocasiao",
            "jornada_tema", "jornada_quantidade", "jornada_prazo", "jornada_limite",
            "jornada_detalhes", "jornada_observacoes", "jornada_entrega", "jornada_desconto",
            "jornada_prazo_prod", "jornada_frete", "jornada_validade",
        ]:
            st.session_state.pop(chave, None)
        st.session_state.jornada_itens = []
        st.session_state.jornada_rascunho_id = ""


def renderizar_assistente_projeto_personalizado():
    """Cria um briefing livre, sem quantidade mínima e sem limitar combinações."""
    st.markdown("## 🧩 Projeto Personalizado")
    st.caption(
        "Comece pela necessidade do cliente. Os campos ajudam a organizar, mas não limitam o que a Alphafest pode criar."
    )

    prefill = st.session_state.pop("_projeto_prefill", {}) if isinstance(st.session_state.get("_projeto_prefill", {}), dict) else {}
    with st.form("form_projeto_personalizado", clear_on_submit=False):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente / identificação (opcional)", value=str(prefill.get("cliente", "")), placeholder="Ex.: Maria, Escola ABC, Arena Beach")
        whatsapp = c2.text_input("WhatsApp (opcional)", value=str(prefill.get("whatsapp", "")), placeholder="Ex.: 11999999999")

        necessidade = st.text_area(
            "O que o cliente precisa?",
            value=str(prefill.get("necessidade", "")),
            placeholder=(
                "Ex.: Um Bubble de 55 cm para aniversário de 6 anos, tema espaço, "
                "confete fosco em formato de lua e coração, tons azul e prata, com LED."
            ),
            height=130,
        )

        p1, p2, p3 = st.columns(3)
        ocasiao = p1.text_input("Ocasião (opcional)", placeholder="Aniversário, empresa, escola...")
        tema = p2.text_input("Tema / personagem (opcional)", placeholder="Stitch, futebol, marca da empresa...")
        quantidade_livre = p3.text_input(
            "Quantidade / necessidade (opcional)",
            placeholder="1 unidade, 30 pessoas, conforme necessário...",
        )

        p4, p5 = st.columns(2)
        prazo_texto = p4.text_input("Prazo ou data desejada (opcional)", placeholder="Ex.: sábado, 15/08, urgente")
        limite_orcamento = p5.text_input("Faixa de orçamento do cliente (opcional)", placeholder="Ex.: até R$ 150")

        catalogo_atual = carregar_catalogo()
        nomes_catalogo = sorted({str(x.get("nome", "")).strip() for x in catalogo_atual if str(x.get("nome", "")).strip()})
        bases = st.multiselect(
            "Produtos-base que podem ajudar (opcional)",
            nomes_catalogo,
            help="Use apenas como ponto de partida. Você poderá criar qualquer solução fora do catálogo.",
        )
        solucao_livre = st.text_input(
            "Outra solução / produto-base",
            placeholder="Digite algo novo que ainda não existe no catálogo",
        )
        detalhes = st.text_area(
            "Materiais, cores, tamanhos, acabamentos, acessórios e outros detalhes",
            placeholder="Escreva livremente. Ex.: confete metalizado dourado, estrela pequena, fita azul, base de balões...",
            height=110,
        )
        observacoes = st.text_area(
            "Observações internas",
            placeholder="Preferências do cliente, restrições, referências, dúvidas para confirmar...",
            height=80,
        )

        salvar, preparar = st.columns(2)
        botao_salvar = salvar.form_submit_button("💾 Salvar como projeto", use_container_width=True)
        botao_preparar = preparar.form_submit_button("➡️ Salvar e preparar orçamento", type="primary", use_container_width=True)

    if botao_salvar or botao_preparar:
        if not necessidade.strip():
            st.warning("Descreva o que o cliente precisa.")
            return

        produtos_base = list(bases)
        if solucao_livre.strip() and solucao_livre.strip() not in produtos_base:
            produtos_base.append(solucao_livre.strip())
        if not produtos_base:
            produtos_base = ["Solução personalizada"]

        projeto = {
            "id": f"PRJ-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
            "tipo": "necessidade_personalizada",
            "origem": prefill.get("origem", "Assistente de Projetos"),
            "atendimento_id": prefill.get("atendimento_id", ""),
            "numero_proposta": "",
            "cliente_nome": cliente.strip(),
            "whatsapp": whatsapp.strip(),
            "ocasiao": ocasiao.strip(),
            "tema": tema.strip(),
            "necessidade": necessidade.strip(),
            "quantidade_livre": quantidade_livre.strip(),
            "prazo_texto": prazo_texto.strip(),
            "limite_orcamento": limite_orcamento.strip(),
            "produtos": produtos_base,
            "detalhes": detalhes.strip(),
            "observacoes": observacoes.strip(),
            "arquivos": [],
            "modelo": False,
            "favorito": False,
            "status": "Briefing",
            "timeline": [],
            "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
            "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
        }
        registrar_evento_projeto(projeto, "Briefing do projeto criado")
        projetos = carregar_projetos()
        projetos.insert(0, projeto)
        salvar_projetos(projetos)

        if botao_preparar:
            st.session_state.form_cliente = cliente.strip()
            st.session_state.form_whatsapp = whatsapp.strip()
            especificacoes_partes = [
                f"Necessidade: {necessidade.strip()}",
                f"Ocasião: {ocasiao.strip()}" if ocasiao.strip() else "",
                f"Tema: {tema.strip()}" if tema.strip() else "",
                f"Quantidade/necessidade: {quantidade_livre.strip()}" if quantidade_livre.strip() else "",
                f"Prazo desejado: {prazo_texto.strip()}" if prazo_texto.strip() else "",
                f"Faixa de orçamento: {limite_orcamento.strip()}" if limite_orcamento.strip() else "",
                f"Detalhes: {detalhes.strip()}" if detalhes.strip() else "",
                f"Observações: {observacoes.strip()}" if observacoes.strip() else "",
            ]
            especificacoes = " | ".join(x for x in especificacoes_partes if x)
            for nome_produto in produtos_base:
                preco = 0.0
                produto_catalogo = next((x for x in catalogo_atual if str(x.get("nome", "")).strip() == nome_produto), None)
                if produto_catalogo:
                    preco = valor_float(produto_catalogo.get("preco", produto_catalogo.get("valor", 0)))
                st.session_state.temp_itens.append({
                    "produto": nome_produto,
                    "especificacoes": especificacoes,
                    "quantidade": 1,
                    "valor_unitario": preco,
                    "projeto_id": projeto["id"],
                })
            projeto["status"] = "Orçamento preparado"
            registrar_evento_projeto(projeto, "Dados enviados para preparação do orçamento")
            atualizar_projeto(projeto)
            st.session_state._projeto_origem_id = projeto["id"]
            st.session_state._atendimento_origem_id = projeto.get("atendimento_id", "") or st.session_state.get("_atendimento_origem_id", "")
            st.session_state._mensagem_sucesso_pendente = (
                "Projeto salvo e itens preparados. Abra a aba Novo Orçamento para revisar valores e finalizar."
            )
            st.rerun()
        else:
            st.success("Projeto personalizado salvo na Memória da Empresa.")
            st.rerun()


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


def pesquisar_global(termo, limite_por_tipo=8):
    """Pesquisa sob demanda em clientes, propostas, catálogo, atendimentos e projetos.

    A função só deve ser chamada quando o usuário digitar ao menos dois caracteres,
    evitando consultas desnecessárias ao Supabase durante os reruns do Streamlit.
    """
    termo = str(termo or "").strip().lower()
    resultado = {"clientes": [], "propostas": [], "produtos": [], "atendimentos": [], "projetos": [], "componentes": []}
    if len(termo) < 2:
        return resultado

    for cliente in carregar_clientes():
        base = " ".join(str(cliente.get(c, "")) for c in [
            "nome", "documento", "whatsapp", "email", "cidade", "observacoes",
            "segmentos", "interesses", "campanhas_interesse"
        ]).lower()
        if termo in base:
            resultado["clientes"].append(cliente)
            if len(resultado["clientes"]) >= limite_por_tipo:
                break

    for proposta in carregar_historico():
        if termo in normalizar_texto_busca(proposta):
            resultado["propostas"].append(proposta)
            if len(resultado["propostas"]) >= limite_por_tipo:
                break

    for indice, produto in enumerate(carregar_catalogo()):
        base = " ".join(str(produto.get(c, "")) for c in [
            "Nome", "Categoria", "Subcategoria", "CodigoInterno", "Descricao",
            "DescricaoCurta", "DescricaoCompleta", "PalavrasChave", "Tags"
        ]).lower()
        if termo in base:
            registro = dict(produto)
            registro["_indice_catalogo"] = indice
            resultado["produtos"].append(registro)
            if len(resultado["produtos"]) >= limite_por_tipo:
                break

    dados_at = carregar_atendimentos()
    for atendimento in dados_at.get("itens", []):
        base = " ".join(str(atendimento.get(c, "")) for c in [
            "cliente", "telefone", "mensagem", "status", "assunto", "responsavel"
        ]).lower()
        if termo in base:
            resultado["atendimentos"].append(atendimento)
            if len(resultado["atendimentos"]) >= limite_por_tipo:
                break

    for categoria, valores in carregar_componentes().items():
        for valor in valores:
            if termo in f"{categoria} {valor}".lower():
                resultado["componentes"].append({"categoria": categoria, "valor": valor})
                if len(resultado["componentes"]) >= limite_por_tipo:
                    break
        if len(resultado["componentes"]) >= limite_por_tipo:
            break

    for projeto in carregar_projetos():
        arquivos = projeto.get("arquivos", []) if isinstance(projeto.get("arquivos"), list) else []
        partes = [
            projeto.get("cliente", ""), projeto.get("tema", ""), projeto.get("produto", ""),
            projeto.get("numero_proposta", ""), projeto.get("observacoes", ""),
            texto_componentes_projeto(projeto), projeto.get("caracteristicas_livres", ""), projeto.get("necessidade", ""), projeto.get("detalhes", "")
        ]
        for arquivo in arquivos:
            partes.extend([arquivo.get("nome", ""), arquivo.get("descricao", ""), arquivo.get("tags", "")])
        if termo in " ".join(map(str, partes)).lower():
            resultado["projetos"].append(projeto)
            if len(resultado["projetos"]) >= limite_por_tipo:
                break
    return resultado


def montar_fila_operacional(historico, tarefas, atendimentos, limite=10):
    """Cria uma fila única de próximas ações, ordenada por urgência."""
    hoje = hoje_local()
    itens = []
    config_at = atendimentos.get("config", {}) if isinstance(atendimentos, dict) else {}
    for atendimento in atendimentos.get("itens", []) if isinstance(atendimentos, dict) else []:
        if atendimento.get("status") in ("Entregue", "Pós-venda", "Arquivado"):
            continue
        nivel = faixa_sla_atendimento(atendimento, config_at)[2]
        minutos = minutos_aguardando(atendimento)
        itens.append({
            "peso": 500 + nivel * 100 + min(minutos, 180),
            "tipo": "Atendimento",
            "titulo": atendimento.get("cliente", "Contato"),
            "detalhe": f"{atendimento.get('status', 'Novo contato')} · {tempo_aguardando_formatado(atendimento)}",
            "acao": proxima_acao_atendimento(atendimento),
            "referencia": atendimento.get("id", ""),
        })
    for proposta in historico:
        if proposta.get("entregue", False):
            continue
        entrega = data_entrega_segura(proposta.get("data_entrega"))
        if entrega:
            dias = (entrega - hoje).days
            if dias < 0:
                peso = 900 + min(abs(dias), 30)
                detalhe = f"Atrasado há {abs(dias)} dia(s)"
            elif dias == 0:
                peso = 800
                detalhe = "Entrega hoje"
            elif dias <= 2:
                peso = 650 - dias
                detalhe = f"Entrega em {dias} dia(s)"
            else:
                continue
            itens.append({
                "peso": peso,
                "tipo": "Pedido",
                "titulo": f"{proposta.get('numero_proposta', '—')} · {proposta.get('cliente_nome', 'Cliente')}",
                "detalhe": detalhe,
                "acao": "Revisar pedido e confirmar próxima etapa",
                "referencia": proposta.get("numero_proposta", ""),
            })
    for tarefa in tarefas:
        if not tarefa.get("ativa", True):
            continue
        status = normalizar_status_fluxo(tarefa.get("status"))
        mapa = {
            "Aguardando aprovação": (620, "Cobrar ou registrar aprovação da arte"),
            "Arte aprovada": (610, "Iniciar impressão/produção"),
            "Pronto para produzir": (600, "Iniciar produção"),
            "Em produção": (520, "Continuar produção"),
            "Montagem/acabamento": (540, "Concluir montagem e conferência"),
            "Pronto": (700, "Avisar cliente e organizar entrega"),
        }
        if status not in mapa:
            continue
        peso, acao = mapa[status]
        itens.append({
            "peso": peso,
            "tipo": "Produção",
            "titulo": f"{tarefa.get('numero_proposta', '—')} · {tarefa.get('cliente_nome', 'Cliente')}",
            "detalhe": status,
            "acao": acao,
            "referencia": tarefa.get("numero_proposta", ""),
        })
    itens.sort(key=lambda x: x.get("peso", 0), reverse=True)
    return itens[:limite]


def proxima_acao_proposta(proposta):
    """Retorna a ação operacional mais útil para uma proposta."""
    if proposta.get("entregue", False):
        return "Registrar pós-venda"
    if proposta.get("aprovado", False):
        if not proposta.get("pago", False):
            return "Confirmar pagamento e acompanhar produção"
        return "Acompanhar produção e entrega"
    if proposta.get("enviado", False):
        return "Aguardar ou registrar aprovação do cliente"
    return "Revisar e enviar orçamento"


def resumo_cliente_operacional(cliente, propostas):
    """Calcula um cartão operacional sem alterar nenhum dado do cliente."""
    propostas = propostas or []
    totais = [calcular_valores_proposta(p)[2] for p in propostas]
    total = sum(totais)
    ticket = total / len(totais) if totais else 0.0
    ordenadas = sorted(
        propostas,
        key=lambda p: data_entrega_segura(p.get("data_geracao")) or date.min,
        reverse=True,
    )
    ultima = ordenadas[0] if ordenadas else None
    produtos = {}
    temas = {}
    for proposta in propostas:
        for item in proposta.get("itens", []) if isinstance(proposta.get("itens"), list) else []:
            nome = str(item.get("produto") or item.get("nome") or item.get("descricao") or "").strip()
            if nome:
                produtos[nome] = produtos.get(nome, 0) + 1
            especificacoes = str(item.get("especificacoes") or "")
            tema = ""
            for trecho in especificacoes.replace("\n", ";").split(";"):
                if "tema" in trecho.lower() and ":" in trecho:
                    tema = trecho.split(":", 1)[1].strip()
                    break
            if tema:
                temas[tema] = temas.get(tema, 0) + 1
    favoritos_produtos = [k for k, _ in sorted(produtos.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:3]]
    favoritos_temas = [k for k, _ in sorted(temas.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:3]]
    return {
        "quantidade": len(propostas),
        "total": total,
        "ticket": ticket,
        "ultima_data": ultima.get("data_geracao", "—") if ultima else "—",
        "ultima_proposta": ultima.get("numero_proposta", "—") if ultima else "—",
        "produtos": favoritos_produtos,
        "temas": favoritos_temas,
    }


def montar_assistente_do_dia(fila, limite=5):
    """Transforma a fila operacional em recomendações curtas e objetivas."""
    recomendacoes = []
    for item in (fila or [])[:limite]:
        recomendacoes.append({
            "titulo": item.get("titulo", "Pendência"),
            "motivo": item.get("detalhe", "Requer atenção"),
            "acao": item.get("acao", "Verificar"),
            "tipo": item.get("tipo", "Operação"),
            "referencia": item.get("referencia", ""),
        })
    return recomendacoes


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



# --- NÚCLEO PROFISSIONAL: MIGRAÇÕES, AUDITORIA E LIXEIRA (4.2.0) ---
SYSTEM_META_PADRAO = {
    "schema_version": 1,
    "ultima_migracao_em": "",
    "migracoes_aplicadas": [],
}


def _usuario_auditoria():
    try:
        usuario = obter_usuario_atual()
        return str(usuario.get("nome") or usuario.get("email") or "Sistema")
    except Exception:
        return "Sistema"


def carregar_auditoria():
    dados = load_document("auditoria_db", ARQUIVO_AUDITORIA, [])
    return dados if isinstance(dados, list) else []


def registrar_auditoria(acao, entidade="Sistema", identificador="", detalhes=None, resultado="OK"):
    """Registra ações importantes sem impedir a operação caso a auditoria falhe."""
    try:
        registros = carregar_auditoria()
        registros.insert(0, {
            "id": agora_local().strftime("AUD%Y%m%d%H%M%S%f"),
            "data_hora": agora_local().isoformat(),
            "usuario": _usuario_auditoria(),
            "acao": str(acao),
            "entidade": str(entidade),
            "identificador": str(identificador or ""),
            "resultado": str(resultado),
            "detalhes": detalhes if isinstance(detalhes, dict) else ({"mensagem": str(detalhes)} if detalhes else {}),
        })
        # Limite operacional para evitar crescimento indefinido; backups preservam o histórico.
        save_document("auditoria_db", registros[:5000], ARQUIVO_AUDITORIA)
    except Exception:
        pass


def carregar_lixeira():
    dados = load_document("lixeira_db", ARQUIVO_LIXEIRA, [])
    return dados if isinstance(dados, list) else []


def enviar_para_lixeira(tipo, item, identificador=""):
    lixeira = carregar_lixeira()
    registro = {
        "id_lixeira": agora_local().strftime("LIX%Y%m%d%H%M%S%f"),
        "tipo": str(tipo),
        "identificador": str(identificador or ""),
        "excluido_em": agora_local().isoformat(),
        "excluido_por": _usuario_auditoria(),
        "item": item,
    }
    lixeira.insert(0, registro)
    save_document("lixeira_db", lixeira, ARQUIVO_LIXEIRA)
    registrar_auditoria("Mover para lixeira", tipo, identificador, {"id_lixeira": registro["id_lixeira"]})
    return registro


def remover_da_lixeira(id_lixeira):
    lixeira = carregar_lixeira()
    restante = [x for x in lixeira if x.get("id_lixeira") != id_lixeira]
    save_document("lixeira_db", restante, ARQUIVO_LIXEIRA)


def restaurar_item_lixeira(registro):
    tipo = registro.get("tipo")
    item = registro.get("item")
    if not isinstance(item, dict):
        raise ValueError("Item da lixeira inválido.")
    if tipo == "Proposta":
        dados = carregar_historico()
        chave, valor = "numero_proposta", item.get("numero_proposta")
        if not any(x.get(chave) == valor for x in dados): dados.append(item)
        salvar_historico_completo(dados)
    elif tipo == "Produto":
        dados = carregar_catalogo()
        # Produtos antigos podem não possuir ID; evita duplicidade por nome/categoria.
        assinatura = (str(item.get("Nome", "")).casefold(), str(item.get("Categoria", "")).casefold())
        if not any((str(x.get("Nome", "")).casefold(), str(x.get("Categoria", "")).casefold()) == assinatura for x in dados): dados.append(item)
        salvar_catalogo(dados)
    elif tipo == "Cliente":
        dados = carregar_clientes()
        if not any(x.get("id") == item.get("id") for x in dados): dados.append(item)
        salvar_clientes(dados)
    elif tipo == "Campanha":
        dados = carregar_campanhas()
        if not any(x.get("id") == item.get("id") for x in dados): dados.append(item)
        salvar_campanhas(dados)
    else:
        raise ValueError(f"Tipo de item ainda não restaurável: {tipo}")
    remover_da_lixeira(registro.get("id_lixeira"))
    registrar_auditoria("Restaurar da lixeira", tipo, registro.get("identificador", ""))


def executar_migracoes_seguras():
    """Acrescenta somente estruturas ausentes; nunca remove campos ou registros."""
    meta = load_document("system_meta", ARQUIVO_SYSTEM_META, SYSTEM_META_PADRAO)
    if not isinstance(meta, dict):
        meta = dict(SYSTEM_META_PADRAO)
    atual = int(meta.get("schema_version", 1) or 1)
    aplicadas = list(meta.get("migracoes_aplicadas", []) or [])
    if atual >= VERSAO_DADOS:
        return
    try:
        if atual < 2:
            alteracoes = {}
            clientes = carregar_clientes()
            mudou = 0
            defaults_cliente = {"segmentos": [], "interesses": [], "campanhas_interesse": [], "origem": "", "potencial": 0, "cidade": ""}
            for cliente in clientes:
                for campo, padrao in defaults_cliente.items():
                    if campo not in cliente:
                        cliente[campo] = list(padrao) if isinstance(padrao, list) else padrao
                        mudou += 1
            if mudou:
                salvar_clientes(clientes)
            alteracoes["clientes_campos_adicionados"] = mudou

            catalogo = carregar_catalogo()
            mudou = 0
            for produto in catalogo:
                for campo, padrao in {"ArquivosBiblioteca": [], "PalavrasChave": [], "PublicarSite": False}.items():
                    if campo not in produto:
                        produto[campo] = list(padrao) if isinstance(padrao, list) else padrao
                        mudou += 1
            if mudou:
                salvar_catalogo(catalogo)
            alteracoes["produtos_campos_adicionados"] = mudou
            if not isinstance(load_document("auditoria_db", ARQUIVO_AUDITORIA, []), list):
                save_document("auditoria_db", [], ARQUIVO_AUDITORIA)
            if not isinstance(load_document("lixeira_db", ARQUIVO_LIXEIRA, []), list):
                save_document("lixeira_db", [], ARQUIVO_LIXEIRA)
            aplicadas.append({"versao": 2, "aplicada_em": agora_local().isoformat(), "alteracoes": alteracoes})
            atual = 2
            registrar_auditoria("Migração de dados", "Banco", "v2", alteracoes)

        if atual < 3:
            componentes = load_document("componentes_db", ARQUIVO_COMPONENTES, COMPONENTES_PADRAO)
            if not isinstance(componentes, dict):
                componentes = dict(COMPONENTES_PADRAO)
                save_document("componentes_db", componentes, ARQUIVO_COMPONENTES)
            projetos = carregar_projetos()
            mudou = 0
            for projeto in projetos:
                if "componentes" not in projeto:
                    projeto["componentes"] = {}
                    mudou += 1
                if "caracteristicas_livres" not in projeto:
                    projeto["caracteristicas_livres"] = ""
                    mudou += 1
            if mudou:
                salvar_projetos(projetos)
            alteracoes_v3 = {"projetos_campos_adicionados": mudou, "biblioteca_componentes_inicializada": True}
            aplicadas.append({"versao": 3, "aplicada_em": agora_local().isoformat(), "alteracoes": alteracoes_v3})
            atual = 3
            registrar_auditoria("Migração de dados", "Banco", "v3", alteracoes_v3)

        if atual < 4:
            clientes = carregar_clientes()
            mudou = 0
            for cliente in clientes:
                defaults_v4 = {
                    "papeis": ["Cliente"],
                    "classificacao_relacionamento": "Não classificado",
                    "politica_atendimento": {
                        "nivel": "Normal", "motivo": "",
                        "permitir_resposta": True, "permitir_catalogo": True,
                        "permitir_orcamento": True, "permitir_campanhas": True,
                        "exigir_pagamento_antecipado": False,
                        "exigir_aprovacao_gestor": False,
                    },
                    "fornecedor": {
                        "materiais": "", "contato_comercial": "",
                        "prioridade": "Não definida", "prazo_medio": "",
                        "avaliacao": 0, "observacoes": "",
                    },
                }
                for campo, padrao in defaults_v4.items():
                    if campo not in cliente:
                        cliente[campo] = padrao.copy() if isinstance(padrao, dict) else list(padrao) if isinstance(padrao, list) else padrao
                        mudou += 1
            if mudou:
                salvar_clientes(clientes)
            alteracoes_v4 = {"relacionamentos_atualizados": len(clientes), "campos_adicionados": mudou}
            aplicadas.append({"versao": 4, "aplicada_em": agora_local().isoformat(), "alteracoes": alteracoes_v4})
            atual = 4
            registrar_auditoria("Migração de dados", "Banco", "v4", alteracoes_v4)

        if atual < 5:
            resultado_v5 = consolidar_vinculos_relacionamentos(salvar=True)
            marketing = load_document("marketing_db", ARQUIVO_MARKETING, {"conteudos": [], "config": {}})
            if not isinstance(marketing, dict):
                marketing = {"conteudos": [], "config": {}}
            marketing.setdefault("conteudos", [])
            marketing.setdefault("config", {})
            save_document("marketing_db", marketing, ARQUIVO_MARKETING)
            alteracoes_v5 = {"propostas_vinculadas": resultado_v5.get("vinculadas", 0), "casos_ambiguos": len(resultado_v5.get("ambiguas", [])), "central_marketing_inicializada": True}
            aplicadas.append({"versao": 5, "aplicada_em": agora_local().isoformat(), "alteracoes": alteracoes_v5})
            atual = 5
            registrar_auditoria("Migração de dados", "Banco", "v5", alteracoes_v5)

        meta.update({"schema_version": atual, "ultima_migracao_em": agora_local().isoformat(), "migracoes_aplicadas": aplicadas})
        save_document("system_meta", meta, ARQUIVO_SYSTEM_META)
    except Exception as exc:
        registrar_auditoria("Migração de dados", "Banco", f"v{atual + 1}", {"erro": str(exc)}, resultado="ERRO")
        st.session_state._erro_migracao = f"Migração pendente: {exc}"


def diagnostico_sistema():
    online, mensagem = connection_test()
    problemas, contagens = verificar_integridade_dados()
    cfg = carregar_config_backup()
    ultimo = str(cfg.get("ultimo_backup_em", "")).strip()
    backup_ok = False
    idade_horas = None
    if ultimo:
        try:
            dt = datetime.fromisoformat(ultimo)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=agora_local().tzinfo)
            idade_horas = max(0, (agora_local() - dt.astimezone(agora_local().tzinfo)).total_seconds() / 3600)
            backup_ok = idade_horas <= 48
        except Exception:
            pass
    meta = load_document("system_meta", ARQUIVO_SYSTEM_META, SYSTEM_META_PADRAO)
    return {
        "supabase_ok": online,
        "supabase_mensagem": mensagem,
        "integridade_ok": not problemas,
        "problemas": problemas,
        "contagens": contagens,
        "backup_ok": backup_ok,
        "backup_idade_horas": idade_horas,
        "schema_version": int(meta.get("schema_version", 1) or 1) if isinstance(meta, dict) else 1,
        "auditorias": len(carregar_auditoria()),
        "lixeira": len(carregar_lixeira()),
    }



# --- PROTEÇÃO DE DADOS E BACKUP AUTOMÁTICO (4.0.1) ---
BACKUP_CONFIG_PADRAO = {
    "ativo": True,
    "horario": "22:00",
    "retencao_automatica": 30,
    "ultimo_backup_em": "",
    "versao_dados": VERSAO_DADOS,
}

DOCUMENTOS_BACKUP = [
    ("historico_orcamentos", ARQUIVO_HISTORICO, []),
    ("catalogo_db", ARQUIVO_CATALOGO, []),
    ("clientes_db", ARQUIVO_CLIENTES, []),
    ("producao_db", ARQUIVO_PRODUCAO, []),
    ("config_empresa", ARQUIVO_EMPRESA, CONFIG_EMPRESA_PADRAO),
    ("projetos_db", ARQUIVO_PROJETOS, []),
    ("campanhas_db", ARQUIVO_CAMPANHAS, []),
    ("integracoes_db", ARQUIVO_INTEGRACOES, {}),
    ("alpha_intelligence_db", ARQUIVO_INTELIGENCIA, {}),
    ("atendimentos_db", ARQUIVO_ATENDIMENTOS, {"config": {}, "itens": []}),
    ("segmentos_db", ARQUIVO_SEGMENTOS, []),
    ("auditoria_db", ARQUIVO_AUDITORIA, []),
    ("lixeira_db", ARQUIVO_LIXEIRA, []),
    ("system_meta", ARQUIVO_SYSTEM_META, SYSTEM_META_PADRAO),
    ("componentes_db", ARQUIVO_COMPONENTES, COMPONENTES_PADRAO),
    ("marketing_db", ARQUIVO_MARKETING, {"conteudos": [], "config": {}}),
]

def carregar_config_backup():
    dados = load_document("backup_config", ARQUIVO_BACKUP_CONFIG, BACKUP_CONFIG_PADRAO)
    config = dict(BACKUP_CONFIG_PADRAO)
    if isinstance(dados, dict):
        config.update(dados)
    return config

def salvar_config_backup(config):
    dados = dict(BACKUP_CONFIG_PADRAO)
    if isinstance(config, dict):
        dados.update(config)
    save_document("backup_config", dados, ARQUIVO_BACKUP_CONFIG)

def coletar_dados_backup():
    documentos = {}
    contagens = {}
    for chave, caminho, padrao in DOCUMENTOS_BACKUP:
        valor = load_document(chave, caminho, padrao)
        documentos[chave] = valor
        if isinstance(valor, list):
            contagens[chave] = len(valor)
        elif isinstance(valor, dict) and isinstance(valor.get("itens"), list):
            contagens[chave] = len(valor["itens"])
        elif isinstance(valor, dict):
            contagens[chave] = len(valor)
        else:
            contagens[chave] = 0
    return documentos, contagens

def carregar_indice_backups():
    dados = load_document("backups_index", "backups_index.json", [])
    return dados if isinstance(dados, list) else []

def salvar_indice_backups(indice):
    save_document("backups_index", indice, "backups_index.json")

def criar_backup_completo(tipo="manual", protegido=False, motivo=""):
    documentos, contagens = coletar_dados_backup()
    instante = agora_local()
    backup_id = instante.strftime("%Y%m%d_%H%M%S_%f")
    payload = {
        "backup_id": backup_id,
        "criado_em": instante.isoformat(),
        "tipo": tipo,
        "protegido": bool(protegido),
        "motivo": str(motivo or ""),
        "versao_app": VERSAO_APP,
        "versao_dados": VERSAO_DADOS,
        "contagens": contagens,
        "documentos": documentos,
    }
    serializado = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    payload["sha256"] = hashlib.sha256(serializado).hexdigest()
    save_document(f"backup_{backup_id}", payload, f"backup_{backup_id}.json")
    indice = carregar_indice_backups()
    indice.insert(0, {k: payload[k] for k in ["backup_id", "criado_em", "tipo", "protegido", "motivo", "versao_app", "versao_dados", "contagens", "sha256"]})
    config = carregar_config_backup()
    limite = max(1, int(config.get("retencao_automatica", 30) or 30))
    automaticos = 0
    novo_indice = []
    for item in indice:
        if item.get("tipo") == "automatico" and not item.get("protegido"):
            automaticos += 1
            if automaticos > limite:
                continue
        novo_indice.append(item)
    salvar_indice_backups(novo_indice)
    config["ultimo_backup_em"] = instante.isoformat()
    salvar_config_backup(config)
    registrar_auditoria("Criar backup", "Backup", backup_id, {"tipo": tipo, "contagens": contagens})
    return payload

def carregar_backup_por_id(backup_id):
    return load_document(f"backup_{backup_id}", f"backup_{backup_id}.json", {})

def backup_para_zip_bytes(payload):
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
        arquivo_zip.writestr("backup_manifest.json", json.dumps({k: v for k, v in payload.items() if k != "documentos"}, ensure_ascii=False, indent=2, default=str))
        for chave, valor in (payload.get("documentos") or {}).items():
            arquivo_zip.writestr(f"dados/{chave}.json", json.dumps(valor, ensure_ascii=False, indent=2, default=str))
    return memoria.getvalue()

def verificar_integridade_dados():
    documentos, contagens = coletar_dados_backup()
    problemas = []
    # componentes_db é uma biblioteca categorizada e, por definição, usa objeto/dicionário.
    esperados_lista = {"historico_orcamentos", "catalogo_db", "clientes_db", "producao_db", "projetos_db", "campanhas_db", "segmentos_db"}
    for chave in esperados_lista:
        if not isinstance(documentos.get(chave), list):
            problemas.append(f"{chave}: estrutura inválida (esperada lista).")
    if not isinstance(documentos.get("componentes_db"), dict):
        problemas.append("componentes_db: estrutura inválida (esperado objeto categorizado).")
    if not isinstance(documentos.get("atendimentos_db"), dict):
        problemas.append("atendimentos_db: estrutura inválida (esperado objeto).")
    if not isinstance(documentos.get("config_empresa"), dict):
        problemas.append("config_empresa: estrutura inválida (esperado objeto).")
    return problemas, contagens

def restaurar_backup_payload(payload):
    documentos = payload.get("documentos") if isinstance(payload, dict) else None
    if not isinstance(documentos, dict):
        raise ValueError("Backup inválido ou incompleto.")
    criar_backup_completo(tipo="antes_restauracao", protegido=True, motivo="Cópia automática antes da restauração")
    mapa = {chave: caminho for chave, caminho, _ in DOCUMENTOS_BACKUP}
    restaurados = []
    for chave, valor in documentos.items():
        if chave in mapa:
            save_document(chave, valor, mapa[chave])
            restaurados.append(chave)
    registrar_auditoria("Restaurar backup", "Backup", payload.get("backup_id", ""), {"documentos": restaurados})
    return restaurados

def executar_backup_automatico_se_necessario():
    if st.session_state.get("backup_auto_verificado"):
        return
    st.session_state.backup_auto_verificado = True
    config = carregar_config_backup()
    if not config.get("ativo", True):
        return
    agora = agora_local()
    try:
        hora, minuto = [int(x) for x in str(config.get("horario", "22:00")).split(":", 1)]
    except Exception:
        hora, minuto = 22, 0
    horario_alvo = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    ultimo = None
    try:
        ultimo = datetime.fromisoformat(str(config.get("ultimo_backup_em", "")))
        if ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=agora.tzinfo)
    except Exception:
        ultimo = None
    deve_fazer = agora >= horario_alvo and (ultimo is None or ultimo.date() < agora.date())
    if deve_fazer:
        try:
            criar_backup_completo(tipo="automatico", motivo="Rotina diária automática")
            st.session_state._mensagem_sucesso_pendente = "Backup automático diário concluído com sucesso."
        except Exception as exc:
            st.session_state._erro_backup_automatico = f"Não foi possível concluir o backup automático: {exc}"

# Manutenções isoladas: se uma delas falhar, a tela continua disponível.
if not st.session_state.get("_manutencao_boot_1424_concluida"):
    executar_etapa_segura("Migrações seguras", executar_migracoes_seguras)
    executar_etapa_segura("Backup automático", executar_backup_automatico_se_necessario)
    st.session_state["_manutencao_boot_1424_concluida"] = True

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
        st.caption("Ambiente personalizado conforme as permissões do usuário")

    _usuario_sidebar_atual = obter_usuario_atual()

    # Health Monitor 14.2.5: imediatamente visível para Jorge, sem consultas extras.
    if pode_executar_acoes_tecnicas(_usuario_sidebar_atual):
        registros_monitor = diagnostico_boot_1424()
        total_monitor = len(registros_monitor)
        falhas_monitor = sum(1 for item in registros_monitor.values() if str(item.get("status", "ok")) not in {"ok", "contingencia", "isolado"})
        contingencias_monitor = sum(1 for item in registros_monitor.values() if str(item.get("status", "ok")) in {"contingencia", "isolado"})
        tempo_monitor = sum(float(item.get("duracao", 0.0) or 0.0) for item in registros_monitor.values())
        status_geral_monitor = "🟢 Estável" if falhas_monitor == 0 else "🔴 Atenção"
        banco_monitor = "🟢 Online" if conectado else "🟡 Contingência"
        st.markdown("**🩺 Health Monitor 14.2.5**")
        cmon1, cmon2 = st.columns(2)
        cmon1.caption(f"Sistema\n\n{status_geral_monitor}")
        cmon2.caption(f"Banco\n\n{banco_monitor}")
        st.caption(f"Boot: {total_monitor - falhas_monitor}/{total_monitor} etapas • {tempo_monitor:.2f}s")
        if contingencias_monitor:
            st.caption(f"🟡 {contingencias_monitor} módulo(s) em contingência controlada")
        st.divider()

    if usuario_em_operacao_protegida(_usuario_sidebar_atual):
        st.success("🛡️ Modo Operação Protegida ativo")
        st.caption("Atendimento, orçamentos, histórico e pedidos continuam isolados das atualizações técnicas.")

    st.divider()
    st.markdown("**🔎 Pesquisa global**")
    termo_global_sidebar = st.text_input(
        "Cliente, telefone, produto, pedido, tema ou arquivo",
        key="pesquisa_global_sidebar",
        placeholder="Digite pelo menos 2 caracteres",
        label_visibility="collapsed",
    ).strip()
    if len(termo_global_sidebar) >= 2:
        resultados_globais = pesquisar_global(termo_global_sidebar, limite_por_tipo=5)
        total_global = sum(len(v) for v in resultados_globais.values())
        st.caption(f"{total_global} resultado(s) encontrado(s)")
        with st.expander("Ver resultados", expanded=True):
            for cliente in resultados_globais["clientes"]:
                st.write(f"👤 **{cliente.get('nome', 'Cliente')}** · {cliente.get('whatsapp') or 'sem WhatsApp'}")
                a, b = st.columns(2)
                if a.button("Orçamento", key=f"gcli_orc_{cliente.get('id')}", use_container_width=True):
                    carregar_cliente_no_orcamento(cliente)
                    st.success("Cliente preparado. Abra Novo Orçamento.")
                telefone = re.sub(r"\D", "", str(cliente.get("whatsapp", "")))
                numero = telefone if telefone.startswith("55") else f"55{telefone}"
                if telefone:
                    b.link_button("WhatsApp", f"https://wa.me/{numero}", use_container_width=True)
            for proposta in resultados_globais["propostas"]:
                st.write(f"📄 **{proposta.get('numero_proposta', '—')}** · {proposta.get('cliente_nome', 'Cliente')}")
                if st.button("Selecionar proposta", key=f"gprop_{proposta.get('numero_proposta')}", use_container_width=True):
                    st.session_state.alerta_proposta_numero = proposta.get("numero_proposta")
                    st.success("Proposta selecionada. Abra Histórico.")
            for produto in resultados_globais["produtos"]:
                st.write(f"📦 **{produto.get('Nome', 'Produto')}** · {produto.get('Categoria', 'Sem categoria')}")
                if st.button("Filtrar no catálogo", key=f"gprod_{produto.get('_indice_catalogo')}", use_container_width=True):
                    st.session_state["pesquisa_catalogo"] = produto.get("Nome", "")
                    st.success("Filtro preparado. Abra Catálogo → Produtos cadastrados.")
            for atendimento in resultados_globais["atendimentos"]:
                st.write(f"📥 **{atendimento.get('cliente', 'Contato')}** · {atendimento.get('status', 'Novo contato')}")
            for projeto in resultados_globais["projetos"]:
                st.write(f"🧠 **{projeto.get('tema') or projeto.get('produto') or 'Projeto'}** · {projeto.get('cliente', 'Cliente')}")

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
        a1, a2, a3, a4 = st.columns(4)
        if a1.button("✏️ Editar proposta", key=f"editar_alerta_{prefixo}_{proposta_alerta.get('numero_proposta')}", use_container_width=True):
            carregar_proposta_no_formulario(proposta_alerta, duplicar=False)
            st.session_state.alerta_proposta_numero = None
            st.rerun()
        numero_alerta = re.sub(r"\D", "", str(proposta_alerta.get("whatsapp") or proposta_alerta.get("cliente_wa") or ""))
        if numero_alerta and not numero_alerta.startswith("55"):
            numero_alerta = "55" + numero_alerta
        link_alerta = f"https://wa.me/{numero_alerta}?text={quote(formatar_msg_whatsapp(proposta_alerta))}" if numero_alerta else f"https://wa.me/?text={quote(formatar_msg_whatsapp(proposta_alerta))}"
        a2.link_button("📱 Enviar WhatsApp", link_alerta, use_container_width=True)
        a3.download_button(
            "📄 Baixar HTML",
            gerar_html(proposta_alerta),
            file_name=f"{proposta_alerta.get('numero_proposta', 'proposta')}.html",
            mime="text/html",
            key=f"html_alerta_{prefixo}_{proposta_alerta.get('numero_proposta')}",
            use_container_width=True,
        )
        if a4.button("Fechar", key=f"fechar_alerta_{prefixo}_{proposta_alerta.get('numero_proposta')}", use_container_width=True):
            st.session_state.alerta_proposta_numero = None
            st.rerun()

mensagem_sucesso = st.session_state.pop("_mensagem_sucesso_pendente", None)
if mensagem_sucesso:
    st.success(mensagem_sucesso)
erro_backup_auto = st.session_state.pop("_erro_backup_automatico", None)
if erro_backup_auto:
    st.warning(erro_backup_auto)
erro_migracao = st.session_state.pop("_erro_migracao", None)
if erro_migracao:
    st.warning(erro_migracao)

_dados_atendimento_badge = carregar_atendimentos()
_qtd_atendimento_badge = sum(1 for _a in _dados_atendimento_badge.get("itens", []) if _a.get("status") not in ("Entregue", "Pós-venda", "Arquivado"))
_rotulo_atendimento = f"📥 Atendimento ({_qtd_atendimento_badge})" if _qtd_atendimento_badge else "📥 Multicanal"


# -----------------------------------------------------------------------------
# ANNA WORKSPACE 12.0.10 — fluxo isolado, rápido e com janelas operacionais
# -----------------------------------------------------------------------------
def _anna_fmt_moeda(valor):
    return f"R$ {valor_float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _anna_numero_whatsapp(valor):
    numero = re.sub(r"\D", "", str(valor or ""))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    return numero


def _anna_salvar_proposta(dados, numero_original=None):
    """Salva e confirma no Supabase antes de liberar o fechamento do modal."""
    import time

    dados = dict(dados or {})
    # Para novas propostas, o número é sempre gerado aqui com microssegundos.
    # Isso evita colisões quando a Anna salva dois orçamentos rapidamente.
    numero = numero_original or f"PROP-{agora_local().strftime('%Y%m%d%H%M%S%f')}"
    dados["numero_proposta"] = numero
    dados["cliente_nome"] = str(dados.get("cliente_nome") or dados.get("cliente") or "").strip()
    dados["cliente"] = dados["cliente_nome"]
    registrar_evento_proposta(
        dados,
        "Proposta atualizada" if numero_original else "Proposta criada",
        usuario="Anna",
    )

    historico = carregar_historico()
    if not isinstance(historico, list):
        historico = []

    if numero_original:
        encontrado = False
        for indice, proposta_existente in enumerate(historico):
            if proposta_existente.get("numero_proposta") == numero_original:
                historico[indice] = dados
                encontrado = True
                break
        if not encontrado:
            return False, f"A proposta {numero_original} não foi encontrada para atualização."
    else:
        # Não remove uma proposta válida por engano. Como o número é único, basta inserir.
        historico.insert(0, dados)

    salvou_online = salvar_historico_completo(historico)
    if not salvou_online:
        return False, (
            "O banco online não confirmou o salvamento. Os dados continuam na janela. "
            "Verifique a conexão e clique em Salvar novamente."
        )

    # Confirma o conteúdo gravado, não apenas a existência do número.
    confirmado = False
    for _ in range(4):
        time.sleep(0.25)
        historico_confirmacao = carregar_historico()
        for proposta_confirmada in historico_confirmacao if isinstance(historico_confirmacao, list) else []:
            if proposta_confirmada.get("numero_proposta") != numero:
                continue
            nome_confirmado = str(
                proposta_confirmada.get("cliente_nome")
                or proposta_confirmada.get("cliente")
                or ""
            ).strip()
            if nome_confirmado == dados["cliente_nome"] and proposta_confirmada.get("itens"):
                confirmado = True
                break
        if confirmado:
            break

    if not confirmado:
        return False, (
            f"O banco recebeu a solicitação, mas ainda não confirmou a proposta de "
            f"{dados['cliente_nome'] or 'cliente não informado'}. A janela foi mantida aberta."
        )

    st.session_state["_ultima_proposta_salva_anna"] = dict(dados)
    st.session_state["_mensagem_sucesso_pendente"] = (
        f"Proposta {numero} de {dados['cliente_nome']} salva com sucesso."
    )
    return True, numero


@st.dialog("📄 ORÇAMENTOS ALPHAFEST", width="large")
def dialog_orcamento_anna(proposta=None):
    """Orçamento da Anna em modal, preservando o mesmo layout do formulário principal."""
    registrar_atividade(obter_usuario_atual(), "Corrigindo um orçamento" if proposta else "Digitando novo orçamento", "Orçamentos")
    proposta = dict(proposta or {})
    numero_original = proposta.get("numero_proposta")

    # Inicializa o formulário somente uma vez por proposta/modal.
    chave_modal = f"anna_modal_iniciado_{numero_original or 'novo'}"
    mostrar_orientacao_thu(
        "atualizar_orcamento" if numero_original else "novo_orcamento",
        token=chave_modal,
    )
    if not st.session_state.get(chave_modal):
        st.session_state[chave_modal] = True
        st.session_state["anna_modal_cliente"] = str(proposta.get("cliente_nome", proposta.get("cliente", "")))
        st.session_state["anna_modal_documento"] = str(proposta.get("documento", proposta.get("cliente_cpf_cnpj", "")))
        st.session_state["anna_modal_whatsapp"] = str(proposta.get("whatsapp", proposta.get("cliente_wa", "")))
        st.session_state["anna_modal_itens"] = [dict(x) for x in proposta.get("itens", []) or []]
        st.session_state["anna_modal_item_key"] = int(st.session_state.get("anna_modal_item_key", 0)) + 1
        st.session_state["anna_modal_desconto"] = float(valor_float(proposta.get("desconto", proposta.get("desconto_valor", 0))))
        try:
            st.session_state["anna_modal_entrega"] = datetime.strptime(str(proposta.get("data_entrega", "")), "%d/%m/%Y").date()
        except Exception:
            st.session_state["anna_modal_entrega"] = hoje_local()
        st.session_state["anna_modal_prazo"] = str(proposta.get("prazo_dias", "10"))
        st.session_state["anna_modal_frete"] = str(proposta.get("frete_tipo", "Retirada em Itatiba"))
        st.session_state["anna_modal_validade"] = str(proposta.get("validade_dias", "5"))

    logo_b64, _ = encontrar_logo_base64()
    if logo_b64:
        le, lc, ld = st.columns([1, 1, 1])
        with lc:
            try:
                st.image(base64.b64decode(logo_b64), use_container_width=True)
            except Exception:
                pass
    st.markdown(
        "<p style='text-align:center; margin-top:-8px; color:#6b7280;'>"
        "Personalizados • Impressão 3D • Papelaria</p>",
        unsafe_allow_html=True,
    )

    if numero_original:
        st.info(f"✏️ Editando a proposta {numero_original}")

    ultima = st.session_state.get("_ultima_proposta_salva_anna")
    if ultima:
        with st.container(border=True):
            st.success(f"Proposta {ultima.get('numero_proposta', '')} salva com sucesso.")
            a1, a2, a3 = st.columns([2, 2, 1])
            destino = re.sub(r"\D", "", str(ultima.get("whatsapp") or ultima.get("cliente_wa") or ""))
            if destino and not destino.startswith("55"):
                destino = "55" + destino
            link = f"https://wa.me/{destino}?text={quote(formatar_msg_whatsapp(ultima))}" if destino else f"https://wa.me/?text={quote(formatar_msg_whatsapp(ultima))}"
            a1.link_button("📱 Enviar orçamento por WhatsApp", link, use_container_width=True)
            a2.download_button("📄 Gerar HTML", gerar_html(ultima), file_name=f"{ultima.get('numero_proposta','orcamento')}.html", mime="text/html", use_container_width=True, key=f"anna_html_salvo_{ultima.get('numero_proposta','orcamento')}")
            if a3.button("✖ Fechar", key="anna_modal_fechar_sucesso", use_container_width=True):
                st.session_state.pop("_ultima_proposta_salva_anna", None)
                st.rerun()

    # Mesmo desenho do orçamento principal: cliente + um item por vez.
    with st.form(key=f"anna_modal_item_{st.session_state.get('anna_modal_item_key', 0)}", clear_on_submit=False):
        nome = st.text_input("Nome / Razão Social", key="anna_modal_cliente")
        c1, c2 = st.columns(2)
        doc = c1.text_input("CPF / CNPJ", key="anna_modal_documento")
        wa = c2.text_input("WhatsApp", key="anna_modal_whatsapp")

        prod = st.text_input("Produto", key=f"anna_modal_prod_{st.session_state.get('anna_modal_item_key', 0)}")
        with st.expander("🎨 Personalização & Especificações", expanded=True):
            e1, e2 = st.columns(2)
            tema = e1.text_input("Tema / Ocasião", key=f"anna_modal_tema_{st.session_state.get('anna_modal_item_key', 0)}")
            nome_item = e1.text_input("Nome(s) Personalizado(s)", key=f"anna_modal_nome_item_{st.session_state.get('anna_modal_item_key', 0)}")
            cor = e1.text_input("Cor / Material", key=f"anna_modal_cor_{st.session_state.get('anna_modal_item_key', 0)}")
            idade = e2.text_input("Idade / Data do Evento", key=f"anna_modal_idade_{st.session_state.get('anna_modal_item_key', 0)}")
            obs = e2.text_input("Outros Detalhes", key=f"anna_modal_obs_{st.session_state.get('anna_modal_item_key', 0)}")
        q = st.number_input("Qtd", min_value=1, value=1, key=f"anna_modal_qtd_{st.session_state.get('anna_modal_item_key', 0)}")
        v = st.number_input("Valor Unitário (R$)", min_value=0.0, value=0.0, step=0.5, key=f"anna_modal_valor_{st.session_state.get('anna_modal_item_key', 0)}")
        adicionar = st.form_submit_button("➕ Adicionar Item", use_container_width=True)

    if adicionar:
        registrar_atividade(obter_usuario_atual(), "Adicionando item ao orçamento", "Orçamentos")
        if not prod.strip():
            st.warning("Informe o produto antes de adicionar.")
        else:
            detalhes = f"Tema: {tema} | Nome: {nome_item} | Idade: {idade} | Cor: {cor} | Obs: {obs}"
            st.session_state["anna_modal_itens"].append({"produto": prod.strip(), "especificacoes": detalhes, "quantidade": q, "valor_unitario": v})
            st.session_state["anna_modal_item_key"] += 1
            # Não executar rerun global dentro do diálogo: isso fecha o popup e apaga a experiência visual.
            # A lista abaixo já usa o session_state atualizado e mostra o item imediatamente.

    itens = st.session_state.get("anna_modal_itens", [])
    if itens:
        st.write("📋 **Itens da proposta:**")
        for idx, item in enumerate(itens):
            ci, cr = st.columns([8, 1])
            ci.write(f"**{idx + 1}. {item.get('produto')}** — Qtd: {item.get('quantidade')} — R$ {valor_float(item.get('valor_unitario')):,.2f}")
            ci.caption(item.get("especificacoes", ""))
            if cr.button("🗑️", key=f"anna_modal_remover_{idx}", help="Remover item"):
                itens.pop(idx)
                try:
                    st.rerun(scope="fragment")
                except Exception:
                    pass

        st.divider()
        d1, d2, d3 = st.columns(3)
        desconto = d1.number_input("Desconto (R$)", min_value=0.0, step=0.5, key="anna_modal_desconto")
        entrega = d2.date_input("📅 Data Entrega", key="anna_modal_entrega")
        prazo = d3.text_input("Prazo de Produção (dias úteis)", key="anna_modal_prazo")
        f1, f2 = st.columns(2)
        frete = f1.text_input("Frete/Entrega", key="anna_modal_frete")
        validade = f2.text_input("Validade (dias corridos)", key="anna_modal_validade")
        subtotal = sum(valor_float(i.get("quantidade")) * valor_float(i.get("valor_unitario")) for i in itens)
        total = max(subtotal - desconto, 0.0)
        st.metric("Valor total", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        salvar_rotulo = "💾 SALVAR ALTERAÇÕES" if numero_original else "🚀 SALVAR PROPOSTA"
        if st.button(salvar_rotulo, type="primary", use_container_width=True, key="anna_modal_salvar_orcamento"):
            if not nome.strip():
                st.error("Informe o nome do cliente.")
                return
            numero = numero_original or ""
            dados = {
                **proposta,
                "numero_proposta": numero,
                "data_geracao": proposta.get("data_geracao", agora_local().strftime("%d/%m/%Y")),
                "data_entrega": entrega.strftime("%d/%m/%Y"),
                "cliente_nome": nome.strip(), "documento": doc.strip(), "whatsapp": wa.strip(),
                "cliente_cpf_cnpj": doc.strip(), "cliente_wa": wa.strip(),
                "itens": list(itens), "subtotal": subtotal, "desconto": desconto, "desconto_valor": desconto,
                "valor_total": total, "prazo_dias": prazo, "frete_tipo": frete, "validade_dias": validade,
                "pago": proposta.get("pago", False), "entregue": proposta.get("entregue", False),
                "aprovado": proposta.get("aprovado", False),
                "timeline": proposta.get("timeline", []) if isinstance(proposta.get("timeline", []), list) else [],
                "atendimento_id": proposta.get("atendimento_id") or st.session_state.get("_atendimento_origem_id", ""),
                "projeto_id": proposta.get("projeto_id") or st.session_state.get("_projeto_origem_id", ""),
            }
            ok_salvar, retorno_salvar = _anna_salvar_proposta(dados, numero_original)
            if ok_salvar:
                registrar_atividade(obter_usuario_atual(), "Orçamento salvo", "Orçamentos", detalhe=str(retorno_salvar), evento=True)
                st.session_state["anna_modal_itens"] = []
                st.session_state[chave_modal] = False
                st.rerun()
            else:
                st.error(retorno_salvar)
    else:
        st.info("Adicione pelo menos um item para concluir o orçamento.")


@st.dialog("💬 Novo atendimento", width="large")
def dialog_atendimento_anna():
    registrar_atividade(obter_usuario_atual(), "Cadastrando novo atendimento", "Atendimento")
    with st.form("anna_novo_atendimento", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente")
        telefone = c2.text_input("Telefone/WhatsApp")
        origem = st.selectbox("Canal de origem", ["WhatsApp", "Instagram", "Facebook", "TikTok", "YouTube", "Site", "Manual"])
        mensagem = st.text_area("Mensagem ou solicitação")
        prioridade = st.selectbox("Prioridade", ["Normal", "Alta", "Urgente"])
        salvar = st.form_submit_button("Salvar atendimento", type="primary", use_container_width=True)
    if salvar:
        dados = carregar_atendimentos()
        dados["itens"].insert(0, {
            "id": f"AT-{agora_local().strftime('%Y%m%d%H%M%S%f')}", "cliente": cliente.strip() or "Contato",
            "telefone": telefone.strip(), "mensagem": mensagem.strip(), "canal": origem, "origem": origem,
            "canal_origem": origem, "canal_atendimento": "WhatsApp", "status": "Novo contato",
            "responsavel": "Anna", "prioridade": prioridade, "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
            "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M"), "historico": [],
        })
        salvar_atendimentos(dados)
        st.session_state["_mensagem_sucesso_pendente"] = "Atendimento criado."
        st.rerun()


@st.dialog("👤 Cadastro rápido de cliente", width="large")
def dialog_cliente_anna():
    registrar_atividade(obter_usuario_atual(), "Cadastrando novo cliente", "Clientes")
    with st.form("anna_novo_cliente", clear_on_submit=True):
        nome = st.text_input("Nome")
        c1, c2 = st.columns(2)
        whatsapp = c1.text_input("WhatsApp")
        documento = c2.text_input("CPF/CNPJ")
        cidade = st.text_input("Cidade")
        observacoes = st.text_area("Observações")
        salvar = st.form_submit_button("Salvar cliente", type="primary", use_container_width=True)
    if salvar:
        clientes = carregar_clientes()
        chave = chave_cliente(nome, documento, whatsapp)
        existente = next((x for x in clientes if chave_cliente(x.get("nome", ""), x.get("documento", ""), x.get("whatsapp", "")) == chave), None)
        dados = {"id": (existente or {}).get("id", f"CLI-{agora_local().strftime('%Y%m%d%H%M%S%f')}"), "nome": nome.strip(), "whatsapp": whatsapp.strip(), "documento": documento.strip(), "cidade": cidade.strip(), "observacoes": observacoes.strip(), "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")}
        if existente:
            existente.update(dados)
        else:
            clientes.insert(0, dados)
        salvar_clientes(clientes)
        st.session_state["_mensagem_sucesso_pendente"] = "Cliente salvo."
        st.rerun()


def salvar_andamento_proposta(numero, aprovado, pago, entregue):
    """Atualiza os três status, confirma a gravação e preserva todos os demais campos."""
    historico = carregar_historico()
    proposta = next((p for p in historico if p.get("numero_proposta") == numero), None)
    if proposta is None:
        return False, "Proposta não encontrada no histórico."

    anteriores = {
        "aprovado": valor_bool(proposta.get("aprovado", False)),
        "pago": valor_bool(proposta.get("pago", False)),
        "entregue": valor_bool(proposta.get("entregue", False)),
    }
    novos = {"aprovado": valor_bool(aprovado), "pago": valor_bool(pago), "entregue": valor_bool(entregue)}
    proposta.update(novos)
    agora_status = agora_local().strftime("%d/%m/%Y %H:%M")
    for campo, campo_data in (("aprovado", "aprovado_em"), ("pago", "pago_em"), ("entregue", "entregue_em")):
        if novos[campo] and not anteriores[campo] and not proposta.get(campo_data):
            proposta[campo_data] = agora_status
        elif not novos[campo] and anteriores[campo]:
            proposta.pop(campo_data, None)

    rotulos = {
        "aprovado": "Orçamento aprovado",
        "pago": "Pagamento confirmado",
        "entregue": "Entrega concluída",
    }
    for campo, valor in novos.items():
        if anteriores[campo] != valor:
            texto = rotulos[campo] if valor else f"{rotulos[campo]} desmarcado"
            registrar_evento_proposta(proposta, texto, usuario="Anna")

    salvar_historico_completo(historico)

    # Confirma a persistência antes de informar sucesso.
    confirmado = next((p for p in carregar_historico() if p.get("numero_proposta") == numero), None)
    if confirmado is None:
        return False, "A proposta não foi localizada após a gravação."
    if any(valor_bool(confirmado.get(campo, False)) != valor for campo, valor in novos.items()):
        return False, "O banco não confirmou a atualização. Tente novamente."

    if novos["aprovado"] and not anteriores["aprovado"]:
        sincronizar_producao_com_propostas()
    if proposta_concluida(confirmado):
        if not proposta_concluida({**confirmado, **anteriores}):
            # Registra uma única vez a conclusão operacional.
            historico_final = carregar_historico()
            alvo = next((p for p in historico_final if p.get("numero_proposta") == numero), None)
            if alvo is not None:
                registrar_evento_proposta(alvo, "Aprovado, pago e entregue — proposta movida para o Histórico", usuario="Sistema")
                salvar_historico_completo(historico_final)
        return True, f"{numero} concluída e movida para o Histórico."
    return True, f"Andamento de {numero} atualizado."


@st.dialog("📦 Fluxo de pedidos", width="large")
def dialog_fluxo_anna():
    registrar_atividade(obter_usuario_atual(), "Atualizando fluxo de pedidos", "Fluxo de Pedidos")
    historico = carregar_historico()
    if not historico:
        st.info("Nenhuma proposta cadastrada.")
        return

    c_busca, c_status = st.columns([2, 1])
    busca = c_busca.text_input(
        "Pesquisar",
        placeholder="Cliente, proposta ou telefone",
        key="dlg_fluxo_busca",
    ).strip().lower()
    status = c_status.selectbox(
        "Mostrar",
        ["Todas", "Ativas", "Aguardando aprovação", "Aprovadas", "Pagas", "Entregues"],
        key="dlg_fluxo_status",
    )

    def atende_filtro(prop):
        texto = " ".join([
            str(prop.get("numero_proposta", "")),
            str(prop.get("cliente_nome", prop.get("cliente", ""))),
            str(prop.get("whatsapp", prop.get("cliente_wa", ""))),
        ]).lower()
        if busca and busca not in texto:
            return False
        aprovado = valor_bool(prop.get("aprovado", False))
        pago = valor_bool(prop.get("pago", False))
        entregue = valor_bool(prop.get("entregue", False))
        ativa = proposta_ativa_operacional(prop)
        return {
            "Todas": ativa,
            "Ativas": ativa,
            "Aguardando aprovação": ativa and not aprovado,
            "Aprovadas": ativa and aprovado,
            "Pagas": ativa and pago,
            "Entregues": ativa and entregue,
        }[status]

    propostas = [p for p in historico if atende_filtro(p)]
    st.caption(f"{len(propostas)} de {len(historico)} proposta(s) exibida(s)")
    if not propostas:
        st.warning("Nenhuma proposta encontrada com esse filtro.")
        return

    propostas.sort(key=lambda p: str(p.get("data_entrega", "")), reverse=False)
    for prop in propostas:
        numero = str(prop.get("numero_proposta", "")).strip()
        if not numero:
            continue
        chave_segura = "".join(ch if ch.isalnum() else "_" for ch in numero)
        with st.container(border=True):
            st.write(f"**{numero} — {prop.get('cliente_nome', prop.get('cliente', 'Cliente'))}**")
            st.caption(
                f"Entrega: {prop.get('data_entrega', '—')} · "
                f"{_anna_fmt_moeda(prop.get('valor_total', prop.get('total', 0)))}"
            )
            with st.form(f"dlg_fluxo_form_{chave_segura}"):
                c1, c2, c3 = st.columns(3)
                aprovado = c1.checkbox("Aprovado", value=valor_bool(prop.get("aprovado", False)))
                pago = c2.checkbox("Pago", value=valor_bool(prop.get("pago", False)))
                entregue = c3.checkbox("Entregue", value=valor_bool(prop.get("entregue", False)))
                salvar = st.form_submit_button("💾 Salvar andamento", use_container_width=True)
            if salvar:
                ok, mensagem = salvar_andamento_proposta(numero, aprovado, pago, entregue)
                if ok:
                    st.session_state["_mensagem_sucesso_pendente"] = mensagem
                    st.rerun()
                else:
                    st.error(mensagem)


@st.dialog("➕ Cadastrar produto no catálogo", width="large")
def dialog_catalogo_cadastro_anna(produto_indice=None):
    registrar_atividade(obter_usuario_atual(), "Atualizando produto" if produto_indice is not None else "Cadastrando produto no catálogo", "Catálogo")
    mostrar_orientacao_thu(
        "atualizar_catalogo" if produto_indice is not None else "cadastrar_produto",
        token=f"catalogo_{produto_indice if produto_indice is not None else 'novo'}",
    )
    catalogo = carregar_catalogo()
    produto = dict(catalogo[produto_indice]) if produto_indice is not None and 0 <= produto_indice < len(catalogo) else {}
    chave = f"anna_cat_{produto_indice if produto_indice is not None else 'novo'}"
    with st.form(chave, clear_on_submit=False):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do produto", value=str(produto.get("Nome", "")))
        categoria = c2.text_input("Grupo / categoria", value=str(produto.get("Categoria", "")))
        c3, c4 = st.columns(2)
        subcategoria = c3.text_input("Subcategoria", value=str(produto.get("Subcategoria", "")))
        preco = c4.text_input("Valor", value=str(produto.get("Preco", "")), placeholder="Ex.: 25,00")
        descricao = st.text_area("Descrição para o catálogo", value=str(produto.get("DescricaoCurta", produto.get("Descricao", ""))), height=110)
        imagens_urls = st.text_area("URLs das imagens (uma por linha)", value="\n".join([x for x in (produto.get("Imagens", []) or []) if str(x).startswith("http")]), height=90)
        fotos = st.file_uploader("Adicionar fotos", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)
        c5, c6 = st.columns(2)
        ativo = c5.checkbox("Produto ativo", value=bool(produto.get("Ativo", True)))
        destaque = c6.checkbox("Produto em destaque", value=bool(produto.get("Destaque", False)))
        salvar = st.form_submit_button("💾 Salvar produto", type="primary", use_container_width=True)
    if salvar:
        if not nome.strip() or not categoria.strip():
            st.error("Informe o nome e o grupo/categoria.")
            return
        imagens = [u.strip() for u in imagens_urls.splitlines() if u.strip()]
        imagens.extend([x for x in (produto.get("Imagens", []) or []) if not str(x).startswith("http")])
        for foto in fotos or []:
            caminho = salvar_upload_catalogo(foto)
            if caminho:
                imagens.insert(0, caminho)
        registro = dict(produto)
        registro.update({
            "Nome": nome.strip(), "Categoria": categoria.strip(), "Subcategoria": subcategoria.strip(),
            "Preco": preco.strip(), "Descricao": descricao.strip(), "DescricaoCurta": descricao.strip(),
            "Imagens": list(dict.fromkeys(imagens)), "Ativo": bool(ativo), "Destaque": bool(destaque),
            "AtualizadoEm": agora_local().isoformat(timespec="seconds"),
        })
        if produto_indice is None:
            registro.setdefault("CriadoEm", agora_local().isoformat(timespec="seconds"))
            catalogo.insert(0, registro)
        else:
            catalogo[produto_indice] = registro
        salvar_catalogo(catalogo)
        confirmado = any(str(x.get("Nome", "")).strip() == nome.strip() for x in carregar_catalogo())
        if confirmado:
            st.session_state["_mensagem_sucesso_pendente"] = f"Produto {nome.strip()} salvo no catálogo."
            st.rerun()
        else:
            st.error("Não foi possível confirmar o salvamento do produto.")


@st.dialog("📋 Visualizar e editar catálogo", width="large")
def dialog_catalogo_visualizar_anna():
    registrar_atividade(obter_usuario_atual(), "Consultando e corrigindo o catálogo", "Catálogo")
    mostrar_orientacao_thu("atualizar_catalogo", token="catalogo_visualizar")
    catalogo = carregar_catalogo()
    busca = st.text_input("Pesquisar produto ou grupo", key="anna_catalogo_busca_modal")
    termo = busca.strip().casefold()
    filtrados = [
        (i, p) for i, p in enumerate(catalogo)
        if not termo or termo in f"{p.get('Nome','')} {p.get('Categoria','')} {p.get('Subcategoria','')}".casefold()
    ]
    st.caption(f"{len(filtrados)} produto(s) encontrado(s)")

    for i, produto in filtrados[:100]:
        imagens_atuais = [str(x).strip() for x in (produto.get("Imagens", []) or []) if str(x).strip()]
        with st.container(border=True):
            topo_img, topo_info = st.columns([1.35, 4.65], vertical_alignment="center")
            with topo_img:
                if imagens_atuais:
                    try:
                        st.image(imagens_atuais[0], use_container_width=True)
                    except Exception:
                        st.caption("Imagem indisponível")
                else:
                    st.info("Sem foto")
            with topo_info:
                st.markdown(f"**{produto.get('Nome','Produto')}**")
                st.caption(
                    f"{produto.get('Categoria','Sem categoria')}"
                    f" · {produto.get('Subcategoria','Sem subcategoria')}"
                    f" · {formatar_preco_catalogo(produto.get('Preco'))}"
                    f" · {len(imagens_atuais)} foto(s)"
                )

            with st.expander("✏️ Abrir campos, visualizar fotos e adicionar imagens", expanded=False):
                if imagens_atuais:
                    st.markdown("**Fotos cadastradas**")
                    cols = st.columns(3)
                    for pos, imagem in enumerate(imagens_atuais):
                        with cols[pos % 3]:
                            try:
                                st.image(imagem, use_container_width=True)
                            except Exception:
                                st.caption(Path(imagem).name or "Imagem indisponível")

                form_key = f"anna_cat_inline_{i}"
                with st.form(form_key, clear_on_submit=False):
                    c1, c2 = st.columns(2)
                    nome = c1.text_input("Nome do produto", value=str(produto.get("Nome", "")), key=f"{form_key}_nome")
                    categoria = c2.text_input("Grupo / categoria", value=str(produto.get("Categoria", "")), key=f"{form_key}_cat")
                    c3, c4 = st.columns(2)
                    subcategoria = c3.text_input("Subcategoria", value=str(produto.get("Subcategoria", "")), key=f"{form_key}_sub")
                    preco = c4.text_input("Valor", value=str(produto.get("Preco", "")), key=f"{form_key}_preco")
                    descricao = st.text_area(
                        "Descrição para o catálogo",
                        value=str(produto.get("DescricaoCurta", produto.get("Descricao", ""))),
                        height=100,
                        key=f"{form_key}_desc",
                    )
                    urls_existentes = [x for x in imagens_atuais if x.startswith(("http://", "https://"))]
                    imagens_urls = st.text_area(
                        "URLs das imagens (uma por linha)",
                        value="\n".join(urls_existentes),
                        height=80,
                        key=f"{form_key}_urls",
                    )
                    novas_fotos = st.file_uploader(
                        "Adicionar mais fotos deste produto",
                        type=["png", "jpg", "jpeg", "webp"],
                        accept_multiple_files=True,
                        key=f"{form_key}_fotos",
                    )
                    manter_fotos = st.checkbox(
                        "Manter todas as fotos já cadastradas",
                        value=True,
                        key=f"{form_key}_manter",
                    )
                    c5, c6 = st.columns(2)
                    ativo = c5.checkbox("Produto ativo", value=bool(produto.get("Ativo", True)), key=f"{form_key}_ativo")
                    destaque = c6.checkbox("Produto em destaque", value=bool(produto.get("Destaque", False)), key=f"{form_key}_dest")
                    salvar = st.form_submit_button("💾 Salvar alterações e fotos", type="primary", use_container_width=True)

                if salvar:
                    if not nome.strip() or not categoria.strip():
                        st.error("Informe o nome e o grupo/categoria.")
                    else:
                        imagens = list(imagens_atuais) if manter_fotos else []
                        imagens = [x for x in imagens if not x.startswith(("http://", "https://"))]
                        imagens.extend([u.strip() for u in imagens_urls.splitlines() if u.strip()])
                        for foto in novas_fotos or []:
                            caminho = salvar_upload_catalogo(foto)
                            if caminho:
                                imagens.insert(0, caminho)
                        registro = dict(produto)
                        registro.update({
                            "Nome": nome.strip(),
                            "Categoria": categoria.strip(),
                            "Subcategoria": subcategoria.strip(),
                            "Preco": preco.strip(),
                            "Descricao": descricao.strip(),
                            "DescricaoCurta": descricao.strip(),
                            "Imagens": list(dict.fromkeys(imagens)),
                            "Ativo": bool(ativo),
                            "Destaque": bool(destaque),
                            "AtualizadoEm": agora_local().isoformat(timespec="seconds"),
                        })
                        catalogo[i] = registro
                        salvar_catalogo(catalogo)
                        confirmado = carregar_catalogo()
                        ok = i < len(confirmado) and str(confirmado[i].get("Nome", "")).strip() == nome.strip()
                        if ok:
                            st.session_state["_mensagem_sucesso_pendente"] = f"Produto {nome.strip()} e suas fotos foram atualizados."
                            st.rerun()
                        else:
                            st.error("Não foi possível confirmar a atualização do produto.")

                if st.button("🗑️ Excluir este produto", key=f"anna_cat_del_{i}", use_container_width=True):
                    catalogo.pop(i)
                    salvar_catalogo(catalogo)
                    st.session_state["_mensagem_sucesso_pendente"] = "Produto excluído do catálogo."
                    st.rerun()


@st.dialog("📤 Gerar catálogos", width="large")
def dialog_catalogo_gerar_anna():
    registrar_atividade(obter_usuario_atual(), "Gerando catálogo para divulgação", "Catálogo")
    catalogo = [p for p in carregar_catalogo() if p.get("Ativo", True)]
    grupos = sorted({str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria" for p in catalogo})
    escolhidos = st.multiselect("Grupos incluídos", grupos, default=grupos)
    produtos = [p for p in catalogo if (str(p.get("Categoria", "Sem categoria")).strip() or "Sem categoria") in escolhidos]
    st.info(f"Serão incluídos {len(produtos)} produto(s), organizados por seus respectivos grupos.")
    html_interno = gerar_html_catalogo(produtos, titulo="Catálogo Geral Alphafest", mostrar_precos=True)
    html_cliente = gerar_html_catalogo(produtos, titulo="Catálogo Alphafest", mostrar_precos=False)
    c1,c2 = st.columns(2)
    c1.download_button("💰 Catálogo geral com valores", html_interno, file_name="catalogo_geral_com_valores.html", mime="text/html", use_container_width=True)
    c2.download_button("👥 Catálogo do cliente sem valores", html_cliente, file_name="catalogo_cliente_sem_valores.html", mime="text/html", use_container_width=True)



def _proposta_eh_de_hoje(prop):
    return any(
        registro_eh_de_hoje(prop.get(campo))
        for campo in ("data_geracao", "data", "criado_em", "created_at")
    )


def _ordenar_propostas_recentes(propostas):
    def chave(prop):
        texto = str(prop.get("data_geracao") or prop.get("criado_em") or prop.get("created_at") or prop.get("data") or "")
        for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, formato)
            except (ValueError, TypeError):
                continue
        return datetime.min
    return sorted(propostas, key=chave, reverse=True)


def _renderizar_linha_proposta_anna(prop, prefixo):
    numero = str(prop.get("numero_proposta", ""))
    _, _, total = calcular_valores_proposta(prop)
    c1, c2, c3, c4 = st.columns([4, 1.4, 1.4, 1.2])
    c1.write(f"**{numero} — {prop.get('cliente_nome','Cliente')}** · {_anna_fmt_moeda(total)}")
    if c2.button("✏️ Atualizar", key=f"{prefixo}_edit_{numero}", use_container_width=True):
        dialog_orcamento_anna(prop)
    numero_wa = _anna_numero_whatsapp(prop.get("whatsapp") or prop.get("cliente_wa"))
    link = f"https://wa.me/{numero_wa}?text={quote(formatar_msg_whatsapp(prop))}" if numero_wa else f"https://wa.me/?text={quote(formatar_msg_whatsapp(prop))}"
    c3.link_button("📱 WhatsApp", link, use_container_width=True)
    c4.download_button("📄 HTML", gerar_html(prop), file_name=f"{numero}.html", mime="text/html", key=f"{prefixo}_html_{numero}", use_container_width=True)
    with st.expander("✅ Atualizar aprovação, pagamento e entrega", expanded=False):
        with st.form(f"{prefixo}_status_form_{numero}"):
            s1, s2, s3 = st.columns(3)
            aprovado = s1.checkbox("✅ Aprovado", value=valor_bool(prop.get("aprovado")))
            pago = s2.checkbox("💰 Pago", value=valor_bool(prop.get("pago")))
            entregue = s3.checkbox("📦 Entregue", value=valor_bool(prop.get("entregue")))
            salvar_status = st.form_submit_button("💾 Salvar andamento", type="primary", use_container_width=True)
        if salvar_status:
            ok, mensagem = salvar_andamento_proposta(numero, aprovado, pago, entregue)
            if ok:
                st.session_state["_mensagem_sucesso_pendente"] = mensagem
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
                st.rerun()
            else:
                st.error(mensagem)


@st.dialog("📦 Entregas de hoje", width="large")
def dialog_entregas_hoje_anna(propostas):
    entregas = [
        p for p in propostas
        if not valor_bool(p.get("entregue"))
        and data_entrega_segura(p.get("data_entrega")) == hoje_local()
    ]
    entregas = _ordenar_propostas_recentes(entregas)
    if not entregas:
        st.success("Não há entregas pendentes para hoje.")
        return
    st.info(f"{len(entregas)} entrega(s) prevista(s) para hoje.")
    for idx, prop in enumerate(entregas):
        numero = str(prop.get("numero_proposta", ""))
        itens = prop.get("itens", []) or []
        principal = itens[0].get("produto", "Produto não informado") if itens else "Produto não informado"
        _, _, total = calcular_valores_proposta(prop)
        with st.container(border=True):
            st.markdown(f"### {prop.get('cliente_nome', 'Cliente')}")
            st.caption(f"{numero} · {principal}")
            d1, d2, d3 = st.columns(3)
            d1.metric("Valor", _anna_fmt_moeda(total))
            d2.metric("Pagamento", "Pago" if valor_bool(prop.get("pago")) else "Pendente")
            d3.metric("Situação", "Entregue" if valor_bool(prop.get("entregue")) else "Entrega hoje")
            _renderizar_linha_proposta_anna(prop, f"entrega_hoje_{idx}")


@st.dialog("🗓️ Orçamentos lançados hoje", width="large")
def dialog_propostas_hoje_anna(propostas):
    hoje = _ordenar_propostas_recentes([p for p in propostas if proposta_ativa_operacional(p) and _proposta_eh_de_hoje(p)])
    if not hoje:
        st.info("Nenhum orçamento lançado hoje foi localizado.")
        return
    st.success(f"{len(hoje)} orçamento(s) lançado(s) hoje.")
    for idx, prop in enumerate(hoje):
        _renderizar_linha_proposta_anna(prop, f"orc_hoje_dialog_{idx}")

def renderizar_workspace_anna_isolado():
    registrar_atividade(obter_usuario_atual(), "Na Central Operacional", "Central da Anna")
    usuario = obter_usuario_atual()

    # Os indicadores são carregados uma única vez e também alimentam a recepção.
    atendimentos = carregar_atendimentos()
    fila = [x for x in atendimentos.get("itens", []) if x.get("status") not in ("Arquivado", "Entregue", "Pós-venda") and str(x.get("responsavel", "")).strip() in ("", "Anna")]
    historico = carregar_historico()
    ativos = [p for p in historico if proposta_ativa_operacional(p)]
    qtd_novos = len([x for x in fila if x.get("status") == "Novo contato"])
    qtd_aguardando = len([x for x in fila if x.get("status") == "Aguardando cliente"])
    qtd_entregas = len([p for p in ativos if data_entrega_segura(p.get("data_entrega")) == hoje_local()])
    resumo = f"Hoje: {qtd_novos} novo(s) atendimento(s), {qtd_aguardando} aguardando cliente, {len(ativos)} pedido(s) ativo(s) e {qtd_entregas} entrega(s)."
    renderizar_boas_vindas_anna(resumo)

    st.markdown("## 🚀 Central Operacional da Anna")
    st.caption("Atendimento, orçamento, clientes e pedidos em janelas rápidas — sem sair desta tela.")

    msg = st.session_state.pop("_mensagem_sucesso_pendente", None)
    if msg:
        st.success(msg)

    ultima = st.session_state.get("_ultima_proposta_salva_anna")
    if ultima:
        with st.container(border=True):
            st.success(f"Proposta {ultima.get('numero_proposta', '')} salva.")
            c1, c2, c3, c4 = st.columns([2,2,1,1])
            numero = _anna_numero_whatsapp(ultima.get("whatsapp") or ultima.get("cliente_wa"))
            link = f"https://wa.me/{numero}?text={quote(formatar_msg_whatsapp(ultima))}" if numero else f"https://wa.me/?text={quote(formatar_msg_whatsapp(ultima))}"
            c1.link_button("📱 Enviar por WhatsApp", link, use_container_width=True)
            c2.download_button("📄 Gerar HTML", gerar_html(ultima), file_name=f"{ultima.get('numero_proposta','orcamento')}.html", mime="text/html", use_container_width=True, key=f"html_ultima_{ultima.get('numero_proposta','orcamento')}")
            if c3.button("➕ Outro", use_container_width=True):
                st.session_state.pop("_ultima_proposta_salva_anna", None)
                dialog_orcamento_anna()
            if c4.button("Fechar", use_container_width=True):
                st.session_state.pop("_ultima_proposta_salva_anna", None)
                st.rerun()

    a1, a2, a3, a4 = st.columns(4)
    if a1.button("💬 Novo atendimento", use_container_width=True): dialog_atendimento_anna()
    if a2.button("➕ Novo orçamento", type="primary", use_container_width=True): dialog_orcamento_anna()
    if a3.button("👤 Novo cliente", use_container_width=True): dialog_cliente_anna()
    if a4.button("📦 Fluxo de pedidos", use_container_width=True): dialog_fluxo_anna()

    st.markdown("### 📚 Catálogo")
    k1, k2, k3 = st.columns(3)
    if k1.button("➕ Cadastrar produto", use_container_width=True): dialog_catalogo_cadastro_anna()
    if k2.button("📋 Visualizar produtos", use_container_width=True): dialog_catalogo_visualizar_anna()
    if k3.button("📤 Gerar catálogos", use_container_width=True): dialog_catalogo_gerar_anna()

    entregas_hoje = [p for p in ativos if data_entrega_segura(p.get("data_entrega")) == hoje_local()]
    propostas_hoje = _ordenar_propostas_recentes([p for p in historico if proposta_ativa_operacional(p) and _proposta_eh_de_hoje(p)])

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Para atender", len([x for x in fila if x.get("status") == "Novo contato"]))
    m2.metric("Aguardando cliente", len([x for x in fila if x.get("status") == "Aguardando cliente"]))
    m3.metric("Pedidos ativos", len(ativos))
    m4.metric("Entregas hoje", len(entregas_hoje))
    if entregas_hoje:
        if m4.button("🔎 Ver quais são", key="anna_ver_entregas_hoje", use_container_width=True):
            dialog_entregas_hoje_anna(historico)

    st.markdown("### 🗓️ Orçamentos lançados hoje")
    if propostas_hoje:
        st.caption(f"{len(propostas_hoje)} orçamento(s) encontrado(s) hoje. Os mais recentes ficam sempre no topo.")
        for idx, prop in enumerate(propostas_hoje[:5]):
            _renderizar_linha_proposta_anna(prop, f"anna_hoje_{idx}")
        if len(propostas_hoje) > 5 and st.button(f"Ver todos os {len(propostas_hoje)} orçamentos de hoje", key="anna_ver_todos_hoje", use_container_width=True):
            dialog_propostas_hoje_anna(historico)
    else:
        st.info("Nenhum orçamento lançado hoje foi localizado. Use Atualizar dados para consultar o banco novamente.")

    st.markdown("### 📄 Todas as propostas e pedidos")
    busca = st.text_input("Pesquisar", placeholder="Cliente, proposta ou telefone", key="anna_busca_rapida")
    termo = busca.strip().lower()
    lista = _ordenar_propostas_recentes([p for p in historico if proposta_ativa_operacional(p) and (not termo or termo in normalizar_texto_busca(p))])
    for idx, prop in enumerate(lista[:20]):
        _renderizar_linha_proposta_anna(prop, f"anna_lista_{idx}")


# O conjunto de abas continua estável no código; a exibição é personalizada por usuário.
if usuario_em_operacao_protegida(obter_usuario_atual()):
    renderizar_workspace_anna_isolado()
    st.stop()

aplicar_visibilidade_abas(obter_usuario_atual())

# Navegação executiva leve: somente o módulo escolhido é renderizado.
# Isso elimina o custo do st.tabs, que executava todos os 20 módulos a cada clique.
GRUPOS_NAVEGACAO = {
    "🏠 Central": ["central"],
    "📋 Operação": ["novo_orcamento", "historico", "fluxo", "catalogo", "projeto", "jornada"],
    "👥 Clientes": ["atendimento", "crm", "clientes_360", "relacionamentos"],
    "🧠 Inteligência": ["alpha", "intelligence", "memoria", "conhecimento"],
    "📈 Gestão": ["executivo", "relatorios"],
    "📢 Marketing": ["crescimento", "calendario"],
    "⚙️ Administração": ["configuracoes"],
}
ROTULOS_ABAS = dict(ABAS_SISTEMA)
permitidas_exec = set(obter_perfil_configurado(obter_usuario_atual()).get("abas", []))
pagina_pendente = st.session_state.get("_pagina_principal", "central")
if pagina_pendente not in permitidas_exec:
    pagina_pendente = "central"

# Descobre o grupo atual e oferece dois controles compactos, sem a antiga fila de abas.
grupo_atual = next((g for g, itens in GRUPOS_NAVEGACAO.items() if pagina_pendente in itens), "🏠 Central")
grupos_disponiveis = [g for g, itens in GRUPOS_NAVEGACAO.items() if any(x in permitidas_exec for x in itens)]
if grupo_atual not in grupos_disponiveis:
    grupo_atual = grupos_disponiveis[0]

nav_col1, nav_col2 = st.columns([1.15, 2.15])
grupo_escolhido = nav_col1.selectbox(
    "Área", grupos_disponiveis,
    index=grupos_disponiveis.index(grupo_atual),
    key="nav_grupo_executivo",
    label_visibility="collapsed",
)
opcoes_modulo = [x for x in GRUPOS_NAVEGACAO[grupo_escolhido] if x in permitidas_exec]
modulo_padrao = pagina_pendente if pagina_pendente in opcoes_modulo else opcoes_modulo[0]
pagina_atual = nav_col2.selectbox(
    "Módulo", opcoes_modulo,
    index=opcoes_modulo.index(modulo_padrao),
    format_func=lambda chave: ROTULOS_ABAS.get(chave, chave),
    key=f"nav_modulo_{grupo_escolhido}",
    label_visibility="collapsed",
)
if pagina_atual != st.session_state.get("_pagina_principal"):
    st.session_state["_pagina_principal"] = pagina_atual
    # Interrompe este ciclo imediatamente: evita que o módulo anterior continue
    # processando abaixo enquanto o usuário já selecionou outro módulo.
    st.rerun()

st.caption(f"📍 {grupo_escolhido} › {ROTULOS_ABAS.get(pagina_atual, pagina_atual)}")


# A Central da Anna já foi encerrada acima com st.stop(); nenhuma alteração visual nela.

executar_navegacao_aba_pendente()

if pagina_atual == "central":
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

    perfil_central = obter_perfil_configurado(usuario_atual)
    if str(usuario_atual.get("nome", "")).casefold() == "anna":
        st.info("👩‍💼 **Central Operacional da Anna** — Atendimento multicanal, orçamentos, artes/projetos, controle de pedidos, entregas, pagamentos e catálogo. O canal de origem permanece identificado em cada atendimento.")
    else:
        st.info("👨‍💼 **Central de Gestão do Jorge** — visão completa da operação, inteligência, conexões, marketing, indicadores e configurações.")
        renderizar_alpha_live_auto()
    favoritos_central = perfil_central.get("favoritos", []) or []
    if favoritos_central:
        if str(usuario_atual.get("nome", "")).casefold() == "anna":
            mapa_favoritos_anna = {
                "atendimento": "📥 Multicanal",
                "novo_orcamento": "➕ Novo Orçamento",
                "catalogo": "📦 Catálogo",
            }
            favoritos_validos = [(ch, mapa_favoritos_anna[ch]) for ch in favoritos_central if ch in mapa_favoritos_anna]
            if favoritos_validos:
                st.caption("⭐ Favoritos")
                cols_fav = st.columns(len(favoritos_validos))
                for col_fav, (chave_fav, rotulo_fav) in zip(cols_fav, favoritos_validos):
                    if col_fav.button(rotulo_fav, key=f"fav_anna_{chave_fav}", use_container_width=True):
                        solicitar_navegacao_aba(indice_aba(chave_fav))
        else:
            favoritos_validos = [(ch, dict(ABAS_SISTEMA).get(ch, ch)) for ch in favoritos_central if ch in dict(ABAS_SISTEMA)]
            if favoritos_validos:
                st.caption("⭐ Favoritos")
                cols_fav = st.columns(len(favoritos_validos))
                for col_fav, (chave_fav, rotulo_fav) in zip(cols_fav, favoritos_validos):
                    if col_fav.button(rotulo_fav, key=f"fav_jorge_{chave_fav}", use_container_width=True):
                        solicitar_navegacao_aba(indice_aba(chave_fav))

    # Anna Workspace: área operacional leve e direta, sem alterar o modelo da mensagem de orçamento.
    if str(usuario_atual.get("nome", "")).casefold() == "anna":
        st.markdown("### 🚀 Modo Trabalho")
        st.caption("Atendimento, orçamento, andamento e catálogo em poucos cliques. Relatórios e integrações permanecem fora deste fluxo para manter a tela rápida.")
        modo_trabalho_anna = st.toggle("Ativar ambiente compacto", value=True, key="modo_trabalho_anna")
        if modo_trabalho_anna:
            dados_ws = carregar_atendimentos()
            itens_ws = [
                x for x in dados_ws.get("itens", [])
                if x.get("status") not in ("Arquivado", "Entregue", "Pós-venda")
                and str(x.get("responsavel", "")).strip() in ("", "Anna")
            ]
            itens_ws = sorted(itens_ws, key=lambda x: (-faixa_sla_atendimento(x, dados_ws.get("config", {}))[2], -minutos_aguardando(x)))
            historico_ws = carregar_historico()
            orc_ws = [p for p in historico_ws if proposta_ativa_operacional(p)]
            aguardando_ws = [x for x in itens_ws if x.get("status") == "Aguardando cliente"]
            solicitados_ws = [x for x in itens_ws if x.get("status") in ("Orçamento solicitado", "Orçamento em elaboração")]

            w1, w2, w3, w4 = st.columns(4)
            w1.metric("💬 Para atender", len([x for x in itens_ws if x.get("status") in ("Novo contato", "Catálogo solicitado")]))
            w2.metric("📄 Orçamentos", len(solicitados_ws))
            w3.metric("⏳ Aguardando cliente", len(aguardando_ws))
            w4.metric("📦 Pedidos ativos", len(orc_ws))

            area_ws = st.radio(
                "Área de trabalho",
                ["💬 Atendimento", "📄 Orçamentos", "📚 Catálogo rápido"],
                horizontal=True,
                key="area_trabalho_anna",
                label_visibility="collapsed",
            )

            if area_ws == "💬 Atendimento":
                st.markdown("#### Próximos atendimentos")
                if not itens_ws:
                    st.success("Nenhum atendimento pendente para a Anna.")
                for item_ws in itens_ws[:8]:
                    icone_ws, rotulo_ws, _ = faixa_sla_atendimento(item_ws, dados_ws.get("config", {}))
                    with st.expander(f"{icone_ws} {item_ws.get('cliente', 'Contato')} · {item_ws.get('status', 'Novo contato')} · {tempo_aguardando_formatado(item_ws)}"):
                        st.caption(f"{item_ws.get('origem', 'WhatsApp')} · {rotulo_ws} · {item_ws.get('telefone') or 'Telefone não informado'}")
                        st.write(item_ws.get("mensagem") or "Sem mensagem registrada.")
                        ra1, ra2, ra3, ra4 = st.columns(4)
                        telefone_ws = re.sub(r"\D", "", str(item_ws.get("telefone", "")))
                        numero_ws = telefone_ws if telefone_ws.startswith("55") else f"55{telefone_ws}"
                        if telefone_ws:
                            ra1.link_button("📱 Abrir WhatsApp", f"https://wa.me/{numero_ws}", use_container_width=True)
                        if ra2.button("➕ Orçamento", key=f"ws_orc_{item_ws.get('id')}", use_container_width=True):
                            st.session_state.form_cliente = item_ws.get("cliente", "")
                            st.session_state.form_whatsapp = item_ws.get("telefone", "")
                            st.session_state.form_observacoes = item_ws.get("mensagem", "")
                            st.session_state._atendimento_origem_id = item_ws.get("id")
                            item_ws["status"] = "Orçamento em elaboração"
                            item_ws["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                            registrar_evento_atendimento(item_ws, "Orçamento iniciado pelo Modo Trabalho da Anna")
                            salvar_atendimentos(dados_ws)
                            st.session_state["_mensagem_sucesso_pendente"] = "Cliente e conversa preparados. Abra Novo Orçamento; a mensagem padrão permanece intacta."
                            st.rerun()
                        if ra3.button("✅ Respondido", key=f"ws_resp_{item_ws.get('id')}", use_container_width=True):
                            status_ant = item_ws.get("status", "Novo contato")
                            item_ws["status"] = "Aguardando cliente"
                            item_ws["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                            registrar_evento_atendimento(item_ws, f"Status alterado de {status_ant} para Aguardando cliente")
                            salvar_atendimentos(dados_ws)
                            st.rerun()
                        if ra4.button("📦 Arquivar", key=f"ws_arq_{item_ws.get('id')}", use_container_width=True):
                            item_ws["status"] = "Arquivado"
                            item_ws["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                            registrar_evento_atendimento(item_ws, "Atendimento arquivado no Modo Trabalho")
                            salvar_atendimentos(dados_ws)
                            st.rerun()

            elif area_ws == "📄 Orçamentos":
                st.markdown("#### Orçamentos e pedidos em andamento")
                lista_ws = sorted(orc_ws, key=lambda p: data_entrega_segura(p.get("data_entrega")) or date.max)[:10]
                if not lista_ws:
                    st.success("Nenhum orçamento ou pedido pendente.")
                for p_ws in lista_ws:
                    _, _, total_ws = calcular_valores_proposta(p_ws)
                    cws1, cws2 = st.columns([7, 2])
                    cws1.write(f"**{p_ws.get('numero_proposta', '—')} — {p_ws.get('cliente_nome', 'Cliente')}** · Entrega: {p_ws.get('data_entrega', 'A combinar')} · R$ {total_ws:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    if cws2.button("Abrir", key=f"ws_abrir_prop_{p_ws.get('numero_proposta')}", use_container_width=True):
                        st.session_state.alerta_proposta_numero = p_ws.get("numero_proposta")
                        st.rerun()

            else:
                st.markdown("#### Catálogo rápido")
                st.caption("Pesquisa e atualização de preço/atividade sem carregar o editor completo.")
                catalogo_ws = carregar_catalogo()
                busca_ws = st.text_input("Pesquisar produto", key="busca_catalogo_workspace", placeholder="Digite nome ou categoria...")
                termo_ws = busca_ws.strip().casefold()
                encontrados_ws = [
                    (i, prod) for i, prod in enumerate(catalogo_ws)
                    if not termo_ws or termo_ws in str(prod.get("Nome", "")).casefold() or termo_ws in str(prod.get("Categoria", "")).casefold()
                ][:10]
                if not encontrados_ws:
                    st.info("Nenhum produto encontrado.")
                for idx_ws, prod_ws in encontrados_ws:
                    with st.container(border=True):
                        cp1, cp2, cp3, cp4 = st.columns([4, 2, 2, 1])
                        cp1.markdown(f"**{prod_ws.get('Nome', 'Produto')}**")
                        cp1.caption(prod_ws.get("Categoria", "Sem categoria"))
                        preco_ws = cp2.text_input("Preço", value=str(prod_ws.get("Preco", "")), key=f"ws_preco_{idx_ws}")
                        ativo_atual_ws = bool(prod_ws.get("Ativo", True))
                        ativo_ws = cp3.checkbox("Ativo", value=ativo_atual_ws, key=f"ws_ativo_{idx_ws}")
                        if cp4.button("Salvar", key=f"ws_salvar_cat_{idx_ws}", use_container_width=True):
                            catalogo_ws[idx_ws]["Preco"] = preco_ws.strip()
                            catalogo_ws[idx_ws]["Ativo"] = bool(ativo_ws)
                            catalogo_ws[idx_ws]["AtualizadoEm"] = agora_local().strftime("%d/%m/%Y %H:%M")
                            salvar_catalogo(catalogo_ws)
                            st.session_state["_mensagem_sucesso_pendente"] = f"Produto {prod_ws.get('Nome', '')} atualizado."
                            st.rerun()
        st.divider()

    st.markdown("#### ⚡ Ações rápidas")
    ac1, ac2, ac3, ac4, ac5 = st.columns(5)
    if ac1.button("📥 Novo atendimento", key="acao_rapida_atendimento", use_container_width=True):
        st.session_state["foco_novo_atendimento"] = True
        solicitar_navegacao_aba(indice_aba("atendimento"))
    if ac2.button("➕ Novo orçamento", key="acao_rapida_orcamento", use_container_width=True):
        st.session_state["form_cliente"] = ""
        st.session_state["form_whatsapp"] = ""
        solicitar_navegacao_aba(indice_aba("novo_orcamento"))
    if ac3.button("🧩 Novo projeto", key="acao_rapida_projeto", use_container_width=True):
        solicitar_navegacao_aba(indice_aba("projeto"))
    if ac4.button("👤 Novo cliente", key="acao_rapida_cliente", use_container_width=True):
        st.session_state["cliente_edicao_id"] = None
        solicitar_navegacao_aba(indice_aba("relacionamentos"))
    if ac5.button("📦 Fluxo de pedidos", key="acao_rapida_fluxo", use_container_width=True):
        solicitar_navegacao_aba(indice_aba("fluxo"))

    historico_central = carregar_historico()
    tarefas_central = sincronizar_producao_com_propostas()
    tarefas_ativas_central = [t for t in tarefas_central if t.get("ativa", True)]

    propostas_operacionais_central = [p for p in historico_central if not proposta_encerrada(p)]
    propostas_aprovadas_abertas_central = [
        p for p in propostas_operacionais_central
        if valor_bool(p.get("aprovado")) and not valor_bool(p.get("entregue"))
    ]
    entregas_hoje_central = [
        p for p in propostas_aprovadas_abertas_central
        if data_entrega_segura(p.get("data_entrega")) == hoje_central
    ]
    pedidos_atrasados_central = [
        p for p in propostas_aprovadas_abertas_central
        if (data_entrega_segura(p.get("data_entrega")) or date.max) < hoje_central
    ]
    aguardando_aprovacao_central = [
        p for p in propostas_operacionais_central
        if not valor_bool(p.get("aprovado")) and not valor_bool(p.get("entregue"))
    ]
    em_producao_central = [t for t in tarefas_ativas_central if normalizar_status_fluxo(t.get("status")) in ["Pedido recebido", "Arte pendente", "Aguardando aprovação", "Pronto para produzir", "Em produção"]]
    prontos_central = [t for t in tarefas_ativas_central if normalizar_status_fluxo(t.get("status")) == "Pronto"]
    pendentes_pagamento_central = [p for p in propostas_aprovadas_abertas_central if not valor_bool(p.get("pago"))]
    valor_previsto_hoje = sum(calcular_valores_proposta(p)[2] for p in entregas_hoje_central)

    dados_atendimento_central = carregar_atendimentos()
    atendimentos_abertos_central = [a for a in dados_atendimento_central.get("itens", []) if a.get("status") not in ("Entregue", "Pós-venda", "Arquivado")]
    orcamentos_whatsapp_central = [a for a in atendimentos_abertos_central if a.get("status") in ("Orçamento solicitado", "Orçamento em elaboração")]
    catalogos_whatsapp_central = [a for a in atendimentos_abertos_central if a.get("status") == "Catálogo solicitado"]
    aguardando_resposta_central = [a for a in atendimentos_abertos_central if minutos_aguardando(a) >= 30]

    indicadores_unificados_central = calcular_indicadores_unificados(
        historico_central,
        dados_atendimento_central.get("itens", []),
        tarefas_ativas_central,
        hoje_central,
    )

    if str(usuario_atual.get("nome", "")).strip().casefold() == "jorge":
        briefing_thu_central = calcular_briefing(
            historico_central,
            indicadores_unificados_central,
            hoje_central,
            calcular_valores_proposta,
        )
        renderizar_briefing_thu(str(usuario_atual.get("nome") or "Jorge"), briefing_thu_central)
        snapshot_alpha_core = calcular_alpha_core(
            historico_central,
            dados_atendimento_central.get("itens", []),
            hoje_central,
            calcular_valores_proposta,
        )
        renderizar_centro_executivo(snapshot_alpha_core, indicadores_unificados_central)


    nome_usuario_central = str(usuario_atual.get("nome", "")).strip()
    minha_fila_central = [
        a for a in atendimentos_abertos_central
        if str(a.get("responsavel", "")).strip() in ("", nome_usuario_central)
    ]
    minha_fila_central = sorted(
        minha_fila_central,
        key=lambda a: (
            -faixa_sla_atendimento(a, dados_atendimento_central.get("config", {}))[2],
            -minutos_aguardando(a),
        ),
    )

    propostas_criadas_hoje = [
        p for p in historico_central
        if registro_eh_de_hoje(p.get("data_geracao") or p.get("data") or p.get("criado_em"))
    ]
    pedidos_aprovados_hoje = [
        p for p in historico_central
        if valor_bool(p.get("aprovado")) and registro_eh_de_hoje(p.get("atualizado_em") or p.get("data_geracao") or p.get("data"))
    ]
    entregues_hoje_resumo = [
        p for p in historico_central
        if valor_bool(p.get("entregue")) and registro_eh_de_hoje(p.get("entregue_em") or p.get("atualizado_em"))
    ]

    if str(usuario_atual.get("nome", "")).strip().casefold() == "anna":
        st.markdown("### 🌻 Painel da Anna")
        st.caption("Tudo que precisa de atenção hoje, reunido em um só lugar.")

        canais_anna = {"WhatsApp": 0, "Instagram": 0, "Facebook": 0, "Site / Catálogo": 0, "Outro": 0}
        for item_anna in minha_fila_central:
            canal_anna = str(item_anna.get("canal_atendimento") or item_anna.get("canal") or item_anna.get("canal_origem") or "Outro").strip()
            if canal_anna not in canais_anna:
                canal_anna = "Outro"
            canais_anna[canal_anna] += 1

        pa1, pa2, pa3, pa4 = st.columns(4)
        pa1.metric("💬 Atendimentos", len(minha_fila_central), help="Fila atribuída à Anna ou ainda sem responsável.")
        pa2.metric("📋 Orçamentos", len(orcamentos_whatsapp_central), help="Solicitados ou em elaboração.")
        pa3.metric("🎨 Artes / projetos", len(aguardando_aprovacao_central), help="Aguardando aprovação do cliente.")
        pa4.metric("📚 Catálogos", len(catalogos_whatsapp_central), help="Solicitações de catálogo ainda abertas.")

        pb1, pb2, pb3, pb4 = st.columns(4)
        pb1.metric("🚚 Entregas hoje", len(entregas_hoje_central))
        pb2.metric("💰 Pagamentos pendentes", len(pendentes_pagamento_central))
        pb3.metric("⚠️ Aguardando +30 min", len(aguardando_resposta_central))
        pb4.metric("📦 Em produção", len(em_producao_central))

        st.markdown("#### 📲 De onde estão vindo os atendimentos")
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("🟢 WhatsApp", canais_anna.get("WhatsApp", 0))
        pc2.metric("📸 Instagram", canais_anna.get("Instagram", 0))
        pc3.metric("📘 Facebook", canais_anna.get("Facebook", 0))
        pc4.metric("🌐 Site / catálogo", canais_anna.get("Site / Catálogo", 0))

        total_prioridades_anna = len(minha_fila_central) + len(entregas_hoje_central) + len(pendentes_pagamento_central)
        if total_prioridades_anna:
            st.success(f"🎯 **Missão do dia:** organizar {len(minha_fila_central)} atendimento(s), acompanhar {len(entregas_hoje_central)} entrega(s) e confirmar {len(pendentes_pagamento_central)} pagamento(s) pendente(s).")
        else:
            st.success("🎉 Sua fila está organizada. Aproveite para revisar catálogos, artes e retornos de clientes.")
        st.divider()

    st.markdown("#### 📊 Resumo de hoje")
    rs1, rs2, rs3, rs4 = st.columns(4)
    rs1.metric("Orçamentos criados", indicadores_unificados_central["propostas_hoje"])
    rs2.metric("Pedidos aprovados", indicadores_unificados_central["aprovadas_hoje"])
    rs3.metric("Entregas concluídas", indicadores_unificados_central["entregues_hoje"])
    rs4.metric("Minha fila", len(minha_fila_central))
    st.caption("Indicadores calculados pela fonte única da Central, CRM e THU.")

    if minha_fila_central:
        with st.expander(f"👤 Minha fila — {nome_usuario_central} ({len(minha_fila_central)})", expanded=False):
            for item_minha_fila in minha_fila_central[:8]:
                nivel = faixa_sla_atendimento(item_minha_fila, dados_atendimento_central.get("config", {}))[2]
                icone = "🔴" if nivel >= 3 else "🟡" if nivel >= 2 else "🟢"
                st.write(
                    f"{icone} **{item_minha_fila.get('cliente', 'Contato')}** · "
                    f"{item_minha_fila.get('status', 'Novo contato')} · "
                    f"{tempo_aguardando_formatado(item_minha_fila)}"
                )
            if len(minha_fila_central) > 8:
                st.caption(f"Mais {len(minha_fila_central) - 8} item(ns) na aba Atendimento.")

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
    c1.metric("🚨 Atrasados", indicadores_unificados_central["atrasados_operacionais"], help="Pedidos aprovados, ainda não entregues e com data de entrega vencida.")
    c2.metric("📦 Entregas hoje", indicadores_unificados_central["entregas_hoje_abertas"], help="Pedidos aprovados e ainda não entregues com entrega marcada para hoje.")
    c3.metric("🟡 Aprovação", indicadores_unificados_central["aguardando_aprovacao"], help="Orçamentos abertos que ainda não foram aprovados nem encerrados.")
    c4.metric("🔵 Em produção", indicadores_unificados_central["em_producao_operacional"], help="Pedidos aprovados e ativos que ainda não estão prontos ou entregues.")
    c5.metric("✅ Prontos", indicadores_unificados_central["prontos_operacionais"], help="Pedidos aprovados cujos itens estão marcados como Pronto.")
    c6.metric("💰 Previsto hoje", f"R$ {valor_previsto_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), help="Soma dos pedidos aprovados, ainda não entregues, previstos para hoje.")
    st.caption("Atrasados, entregas e valor previsto consideram somente pedidos aprovados. Aprovação considera orçamentos ainda abertos.")

    st.divider()
    st.subheader("🎯 O que fazer agora")
    prioridade = None
    prioridade_atendimento = None
    motivo = ""
    atendimentos_urgentes = sorted(
        [a for a in atendimentos_abertos_central if faixa_sla_atendimento(a, dados_atendimento_central.get("config", {}))[2] >= 2],
        key=minutos_aguardando,
        reverse=True,
    )
    if atendimentos_urgentes:
        prioridade_atendimento = atendimentos_urgentes[0]
        motivo = f"Atendimento aguardando há {tempo_aguardando_formatado(prioridade_atendimento)}"
    elif pedidos_atrasados_central:
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

    if prioridade_atendimento:
        with st.container(border=True):
            st.markdown(f"### 📥 {html.escape(str(prioridade_atendimento.get('cliente', 'Contato')))}")
            st.write(f"**Situação:** {prioridade_atendimento.get('status', 'Novo contato')}")
            st.write(f"**Motivo:** {motivo}")
            st.write(f"**Próxima ação:** {proxima_acao_atendimento(prioridade_atendimento)}")
            st.caption("Abra a aba Atendimento para responder ou criar o orçamento.")
    elif prioridade:
        _, _, total_prioridade = calcular_valores_proposta(prioridade)
        with st.container(border=True):
            st.markdown(f"### {html.escape(str(prioridade.get('cliente_nome', 'Cliente')))}")
            st.write(f"**Pedido:** {prioridade.get('numero_proposta', '—')}  •  **Entrega:** {prioridade.get('data_entrega', 'A combinar')}")
            st.write(f"**Motivo:** {motivo}")
            st.write(f"**Valor:** R$ {total_prioridade:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            if st.button("📋 Abrir e atualizar agora", key="central_abrir_prioridade", type="primary"):
                st.session_state.alerta_proposta_numero = prioridade.get("numero_proposta")
                st.rerun()
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
        for idx_alerta, (icone, numero, cliente, texto) in enumerate(alertas_central[:10]):
            al1, al2 = st.columns([7, 2])
            al1.write(f"{icone} **{numero} — {cliente}** · {texto}")
            if al2.button("Abrir e atualizar", key=f"central_alerta_abrir_{idx_alerta}_{numero}", use_container_width=True):
                st.session_state.alerta_proposta_numero = numero
                st.rerun()
    else:
        st.info("Nenhum alerta importante agora.")

    # Editor operacional rápido: permite à Anna dar andamento sem procurar a proposta em outra aba.
    numero_central_selecionado = st.session_state.get("alerta_proposta_numero")
    if numero_central_selecionado:
        proposta_central_selecionada = next(
            (p for p in carregar_historico() if str(p.get("numero_proposta")) == str(numero_central_selecionado)),
            None,
        )
        if proposta_central_selecionada:
            _, _, total_central_sel = calcular_valores_proposta(proposta_central_selecionada)
            with st.container(border=True):
                st.markdown(f"### 📋 {html.escape(str(proposta_central_selecionada.get('numero_proposta', 'Proposta')))} — {html.escape(str(proposta_central_selecionada.get('cliente_nome', 'Cliente')))}")
                det1, det2, det3 = st.columns(3)
                det1.metric("Entrega", proposta_central_selecionada.get("data_entrega", "A combinar"))
                det2.metric("Valor", f"R$ {total_central_sel:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                det3.metric("WhatsApp", proposta_central_selecionada.get("whatsapp") or proposta_central_selecionada.get("cliente_wa") or "Não informado")

                st.write("**Itens do pedido**")
                for item_central_sel in proposta_central_selecionada.get("itens", []) or []:
                    st.write(f"• {item_central_sel.get('produto', 'Produto')} · Qtd.: {item_central_sel.get('quantidade', 0)}")

                st.markdown("**Atualização rápida**")
                up1, up2, up3 = st.columns(3)
                aprovado_central = up1.checkbox("✅ Aprovado", value=valor_bool(proposta_central_selecionada.get("aprovado")), key=f"central_aprov_{numero_central_selecionado}")
                pago_central = up2.checkbox("💰 Pago", value=valor_bool(proposta_central_selecionada.get("pago")), key=f"central_pago_{numero_central_selecionado}")
                entregue_central = up3.checkbox("📦 Entregue", value=valor_bool(proposta_central_selecionada.get("entregue")), key=f"central_entregue_{numero_central_selecionado}")
                observacao_central = st.text_area(
                    "Observação operacional",
                    value=str(proposta_central_selecionada.get("observacao_operacional", "")),
                    key=f"central_obs_{numero_central_selecionado}",
                    placeholder="Ex.: cliente confirmou retirada às 16h; falta comprovante; arte enviada...",
                    height=80,
                )
                op1, op2, op3 = st.columns(3)
                if op1.button("💾 Salvar andamento", key=f"central_salvar_{numero_central_selecionado}", type="primary", use_container_width=True):
                    ok_andamento, msg_andamento = salvar_andamento_proposta(
                        numero_central_selecionado, aprovado_central, pago_central, entregue_central
                    )
                    if not ok_andamento:
                        st.error(msg_andamento)
                        st.stop()
                    historico_atual_central = carregar_historico()
                    for proposta_atualizar in historico_atual_central:
                        if str(proposta_atualizar.get("numero_proposta")) == str(numero_central_selecionado):
                            proposta_atualizar["observacao_operacional"] = observacao_central.strip()
                            proposta_atualizar["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                            break
                    salvar_historico_completo(historico_atual_central)

                    # Limpa somente o estado do editor salvo. Isso força a Central do Dia
                    # a reconstruir todos os resumos, alertas e filas com os dados novos,
                    # sem reaproveitar checkboxes ou campos da proposta anterior.
                    for chave_editor in (
                        f"central_aprov_{numero_central_selecionado}",
                        f"central_pago_{numero_central_selecionado}",
                        f"central_entregue_{numero_central_selecionado}",
                        f"central_obs_{numero_central_selecionado}",
                    ):
                        st.session_state.pop(chave_editor, None)

                    st.session_state.alerta_proposta_numero = None
                    st.session_state["_central_atualizada_em"] = agora_local().isoformat()
                    st.session_state["_mensagem_sucesso_pendente"] = msg_andamento

                    # Limpa caches de leitura eventualmente usados por outros módulos e
                    # executa novamente o aplicativo inteiro, não apenas o formulário.
                    try:
                        st.cache_data.clear()
                    except Exception:
                        pass
                    try:
                        st.cache_resource.clear()
                    except Exception:
                        pass
                    st.rerun()
                if op2.button("✏️ Editar proposta completa", key=f"central_editar_{numero_central_selecionado}", use_container_width=True):
                    carregar_proposta_no_formulario(proposta_central_selecionada, duplicar=False)
                    st.session_state.alerta_proposta_numero = None
                    rerun_na_aba("novo_orcamento", "Proposta carregada para edição.")
                if op3.button("✖ Fechar", key=f"central_fechar_{numero_central_selecionado}", use_container_width=True):
                    st.session_state.alerta_proposta_numero = None
                    st.rerun()
        else:
            st.session_state.alerta_proposta_numero = None

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
    fila_operacional = montar_fila_operacional(
        historico_central,
        tarefas_ativas_central,
        dados_atendimento_central,
        limite=10,
    )
    st.subheader("🧭 Assistente operacional")
    recomendacoes_dia = montar_assistente_do_dia(fila_operacional, limite=5)
    if recomendacoes_dia:
        st.caption("As prioridades abaixo são ordenadas automaticamente por SLA, prazo e etapa da operação.")
        for indice_rec, rec in enumerate(recomendacoes_dia, start=1):
            icone_rec = "📥" if rec["tipo"] == "Atendimento" else "📦" if rec["tipo"] == "Pedido" else "⚙️"
            with st.container(border=True):
                rc1, rc2 = st.columns([5, 2])
                rc1.markdown(f"**{indice_rec}. {icone_rec} {html.escape(str(rec['titulo']))}**")
                rc1.caption(f"{rec['motivo']} · Próxima ação: {rec['acao']}")
                if rec["tipo"] == "Atendimento":
                    atendimento_rec = next((a for a in dados_atendimento_central.get("itens", []) if a.get("id") == rec.get("referencia")), None)
                    telefone_rec = str((atendimento_rec or {}).get("telefone", "")).strip()
                    if telefone_rec:
                        numero_rec = re.sub(r"\D", "", telefone_rec)
                        if numero_rec and not numero_rec.startswith("55"):
                            numero_rec = "55" + numero_rec
                        rc2.link_button("📱 Abrir WhatsApp", f"https://wa.me/{numero_rec}", use_container_width=True)
                    else:
                        rc2.info(rec["acao"])
                else:
                    rc2.info(rec["acao"])
    else:
        st.success("Nenhuma prioridade crítica no momento.")

    st.divider()
    st.subheader("📌 Fila operacional")
    if fila_operacional:
        for posicao, item_fila in enumerate(fila_operacional, start=1):
            icone = "📥" if item_fila["tipo"] == "Atendimento" else "📦" if item_fila["tipo"] == "Pedido" else "⚙️"
            with st.container(border=True):
                fc1, fc2 = st.columns([5, 2])
                fc1.markdown(f"**{posicao}. {icone} {html.escape(str(item_fila['titulo']))}**")
                fc1.caption(f"{item_fila['tipo']} · {item_fila['detalhe']}")
                fc2.info(item_fila["acao"])
    else:
        st.success("Fila operacional vazia. Nenhuma ação pendente encontrada.")

    st.divider()
    st.subheader("🔎 Pesquisa global")
    busca_central = st.text_input(
        "Cliente, telefone, pedido, produto, tema ou arquivo",
        key="busca_central_dia",
        placeholder="Digite pelo menos 2 caracteres",
    ).strip()
    if len(busca_central) >= 2:
        resultados = pesquisar_global(busca_central, limite_por_tipo=10)
        total_resultados = sum(len(v) for v in resultados.values())
        st.caption(f"{total_resultados} resultado(s) em todos os módulos")
        rg1, rg2 = st.columns(2)
        with rg1:
            if resultados["clientes"]:
                st.markdown("#### 👥 Clientes")
                for cli in resultados["clientes"]:
                    st.write(f"• **{cli.get('nome', 'Cliente')}** · {cli.get('whatsapp') or 'sem WhatsApp'}")
            if resultados["produtos"]:
                st.markdown("#### 📦 Produtos")
                for prod in resultados["produtos"]:
                    st.write(f"• **{prod.get('Nome', 'Produto')}** · {prod.get('Categoria', 'Sem categoria')}")
            if resultados["projetos"]:
                st.markdown("#### 🧠 Projetos e arquivos")
                for proj in resultados["projetos"]:
                    st.write(f"• **{proj.get('tema') or proj.get('produto') or 'Projeto'}** · {proj.get('cliente', 'Cliente')}")
        with rg2:
            if resultados["propostas"]:
                st.markdown("#### 📋 Propostas")
                for prop in resultados["propostas"]:
                    _, _, total_resultado = calcular_valores_proposta(prop)
                    st.write(f"• **{prop.get('numero_proposta', '—')} — {prop.get('cliente_nome', 'Cliente')}** · R$ {total_resultado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            if resultados["atendimentos"]:
                st.markdown("#### 📥 Atendimentos")
                for at in resultados["atendimentos"]:
                    st.write(f"• **{at.get('cliente', 'Contato')}** · {at.get('status', 'Novo contato')}")
        if not total_resultados:
            st.info("Nenhum resultado encontrado.")

if pagina_atual == "atendimento":
    st.header("📥 Central Multicanal")
    st.caption("Reúna oportunidades do WhatsApp, Instagram, Facebook, site e atendimento manual em uma única fila.")
    dados_at = carregar_atendimentos()
    config_at = dados_at["config"]
    itens_at = dados_at["itens"]

    tab_oportunidades, tab_fila, tab_novo, tab_config, tab_integracoes = st.tabs(["🎯 Oportunidades", "📋 Caixa unificada", "➕ Registrar oportunidade", "⚙️ Modos e automações", "🔌 Integrações Meta"])

    with tab_oportunidades:
        if render_central_oportunidades is None:
            st.warning("A Central de Oportunidades está temporariamente isolada para não interromper o atendimento.")
            if CENTRAL_OPORTUNIDADES_IMPORT_ERROR:
                st.caption(CENTRAL_OPORTUNIDADES_IMPORT_ERROR)
        else:
            try:
                render_central_oportunidades(
                    dados_at=dados_at,
                    salvar_atendimentos=salvar_atendimentos,
                    historico=carregar_historico(),
                    now_fn=agora_local,
                )
            except Exception as exc:
                st.error("A Central de Oportunidades encontrou um erro, mas a Caixa Unificada e o restante da operação continuam disponíveis.")
                st.caption(str(exc))

    with tab_fila:
        f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
        busca_at = f1.text_input("Pesquisar cliente, telefone ou mensagem", key="busca_atendimento").strip().lower()
        status_filtro = f2.selectbox("Status", ["Todos"] + STATUS_ATENDIMENTO, key="filtro_status_at")
        prioridade_filtro = f3.selectbox("Prioridade", ["Todas", "Urgente", "Alta", "Normal", "Baixa"], key="filtro_prior_at")
        responsavel_filtro = f4.selectbox("Responsável", ["Todos", "Anna", "Jorge", "Sem responsável"], key="filtro_resp_at")
        canal_filtro = f5.selectbox("Canal", ["Todos"] + CANAIS_ATENDIMENTO, key="filtro_canal_at")
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
            if canal_filtro != "Todos" and str(item.get("canal") or item.get("origem") or "Outro") != canal_filtro:
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
                relacionamento_item = localizar_relacionamento(item.get("cliente", ""), item.get("telefone", ""))
                restricao_item = resumo_restricao_relacionamento(relacionamento_item)
                if relacionamento_item:
                    st.caption("🌐 Papéis: " + ", ".join(papeis_relacionamento(relacionamento_item)))
                if restricao_item:
                    motivo_item = restricao_item.get("motivo") or "Política comercial definida pela Alphafest."
                    if restricao_item.get("nivel") == "Bloqueado" or not restricao_item.get("permitir_resposta", True):
                        st.error(f"🛑 Atendimento bloqueado — {motivo_item}")
                    else:
                        st.warning(f"🛡️ Atendimento {restricao_item.get('nivel')} — {motivo_item}")
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
                    modos_permitidos = ["Manual"] if restricao_item and restricao_item.get("nivel") in ("Somente manual", "Atenção", "Monitorado", "Bloqueado") else ["Manual", "Assistido", "Automático"]
                    modo_atual_item = item.get("modo", config_at.get("modo", "Manual"))
                    if modo_atual_item not in modos_permitidos:
                        modo_atual_item = "Manual"
                    modo_conversa = st.selectbox("Modo desta conversa", modos_permitidos, index=modos_permitidos.index(modo_atual_item), key=f"modo_at_{item.get('id')}")

                historico_item = item.get("historico") if isinstance(item.get("historico"), list) else []
                if historico_item:
                    with st.expander("🕒 Linha do tempo do atendimento"):
                        for evento in reversed(historico_item[-20:]):
                            st.write(f"**{evento.get('data', '—')}** · {evento.get('descricao', 'Atualização')}")
                if item.get("numero_proposta"):
                    st.info(f"📄 Atendimento vinculado à proposta **{item.get('numero_proposta')}**")

                b1, b2, b3, b4 = st.columns(4)
                if b1.button("💾 Salvar", key=f"salvar_at_{item.get('id')}", use_container_width=True):
                    status_anterior = item.get("status", "Novo contato")
                    item.update({"status": novo_status, "prioridade": nova_prioridade, "responsavel": "" if novo_responsavel == "Sem responsável" else novo_responsavel, "modo": modo_conversa, "resposta_rascunho": resposta, "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    if status_anterior != novo_status:
                        registrar_evento_atendimento(item, f"Status alterado de {status_anterior} para {novo_status}")
                        sincronizar_atendimento_com_operacao(item, status_anterior)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                telefone_limpo = re.sub(r"\D", "", str(item.get("telefone", "")))
                numero_wa = telefone_limpo if telefone_limpo.startswith("55") else f"55{telefone_limpo}"
                link_wa = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(resposta)}" if telefone_limpo else ""
                bloqueado_item = bool(restricao_item and (restricao_item.get("nivel") == "Bloqueado" or not restricao_item.get("permitir_resposta", True)))
                orcamento_bloqueado_item = bool(restricao_item and not restricao_item.get("permitir_orcamento", True))
                if link_wa and not bloqueado_item:
                    b2.link_button("📱 Responder", link_wa, use_container_width=True)
                elif bloqueado_item:
                    b2.button("🛑 Bloqueado", disabled=True, use_container_width=True)
                if b3.button("🧩 Criar projeto", key=f"proj_at_{item.get('id')}", use_container_width=True, disabled=orcamento_bloqueado_item):
                    st.session_state._projeto_prefill = {
                        "cliente": item.get("cliente", ""),
                        "whatsapp": item.get("telefone", ""),
                        "necessidade": item.get("mensagem", ""),
                        "atendimento_id": item.get("id", ""),
                        "origem": "Atendimento",
                    }
                    status_antigo = item.get("status", "Novo contato")
                    item["status"] = "Orçamento em elaboração"
                    item["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                    registrar_evento_atendimento(item, "Dados enviados para criação de projeto personalizado")
                    salvar_atendimentos(dados_at)
                    st.success("Projeto preparado. Abra a aba Projeto Personalizado para revisar e salvar.")
                if b4.button("➕ Criar orçamento", key=f"orc_at_{item.get('id')}", use_container_width=True, disabled=orcamento_bloqueado_item):
                    st.session_state.form_cliente = item.get("cliente", "")
                    st.session_state.form_whatsapp = item.get("telefone", "")
                    st.session_state.form_observacoes = item.get("mensagem", "")
                    st.session_state._atendimento_origem_id = item.get("id")
                    status_antigo = item.get("status", "Novo contato")
                    item["status"] = "Orçamento em elaboração"
                    item["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                    registrar_evento_atendimento(item, f"Status alterado de {status_antigo} para Orçamento em elaboração")
                    salvar_atendimentos(dados_at)
                    st.success("Dados preparados. Abra a aba Novo Orçamento.")

                q1, q2, q3, q4 = st.columns(4)
                if q1.button("✅ Atendido", key=f"atendido_{item.get('id')}", use_container_width=True):
                    status_anterior = item.get("status", "Novo contato")
                    item.update({"status": "Aguardando cliente", "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    registrar_evento_atendimento(item, f"Status alterado de {status_anterior} para Aguardando cliente")
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if q2.button("⏳ Aguardar cliente", key=f"aguardar_{item.get('id')}", use_container_width=True):
                    status_anterior = item.get("status", "Novo contato")
                    item.update({"status": "Aguardando cliente", "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    registrar_evento_atendimento(item, f"Status alterado de {status_anterior} para Aguardando cliente")
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if q3.button("🏁 Concluir", key=f"concluir_{item.get('id')}", use_container_width=True):
                    status_anterior = item.get("status", "Novo contato")
                    item.update({"status": "Pós-venda", "concluido_em": agora_local().strftime("%d/%m/%Y %H:%M"), "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    registrar_evento_atendimento(item, f"Atendimento concluído a partir do status {status_anterior}")
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if q4.button("📦 Arquivar", key=f"arquivar_{item.get('id')}", use_container_width=True):
                    status_anterior = item.get("status", "Novo contato")
                    item.update({"status": "Arquivado", "atualizado_em": agora_local().strftime("%d/%m/%Y %H:%M")})
                    registrar_evento_atendimento(item, f"Atendimento arquivado a partir do status {status_anterior}")
                    salvar_atendimentos(dados_at)
                    st.rerun()

    with tab_novo:
        st.subheader("Registrar mensagem ou contato")
        n1, n2, ncanal = st.columns([2, 2, 1])
        nome_at = n1.text_input("Nome / identificação", key="novo_at_nome")
        telefone_at = n2.text_input("Telefone / WhatsApp (opcional)", key="novo_at_telefone")
        canal_at = ncanal.selectbox("Canal", CANAIS_ATENDIMENTO, key="novo_at_canal")
        mensagem_at = st.text_area("Mensagem recebida", key="novo_at_mensagem", placeholder="Ex.: Gostaria do catálogo de topos e um orçamento para sábado")
        sugestao_status = sugerir_tipo_atendimento(mensagem_at)
        n3, n4, n5 = st.columns(3)
        status_at = n3.selectbox("Classificação", STATUS_ATENDIMENTO, index=STATUS_ATENDIMENTO.index(sugestao_status), key="novo_at_status")
        prioridade_at = n4.selectbox("Prioridade", ["Urgente", "Alta", "Normal", "Baixa"], index=2, key="novo_at_prioridade")
        responsavel_at = n5.selectbox("Responsável", ["Sem responsável", "Anna", "Jorge"], key="novo_at_responsavel")
        with st.expander("🎯 Fonte do contato / conteúdo que gerou o interesse", expanded=canal_at not in ("WhatsApp", "Telefone", "Balcão")):
            fc1, fc2 = st.columns(2)
            tipo_conteudo_at = fc1.selectbox("Tipo de conteúdo", ["Reel", "Story", "Post", "Comentário", "Short", "Vídeo", "Página do site", "Catálogo", "Anúncio", "Pesquisa Google", "Indicação", "Outro"], key="novo_at_tipo_conteudo")
            motivo_contato_at = fc2.selectbox("Motivo do contato", ["Pedido de orçamento", "Pedido de catálogo", "Dúvida", "Solicitação de arte", "Balões", "Topo de bolo", "Lembrancinhas", "Locação", "Pós-venda", "Indicação", "Outro"], key="novo_at_motivo")
            conteudo_titulo_at = st.text_input("Nome do post, Reel, vídeo ou página", key="novo_at_conteudo_titulo")
            fc3, fc4 = st.columns(2)
            campanha_at = fc3.text_input("Campanha", key="novo_at_campanha")
            produto_interesse_at = fc4.text_input("Produto relacionado", key="novo_at_produto")
            conteudo_url_at = st.text_input("Link do conteúdo (opcional)", key="novo_at_conteudo_url")
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
                    "origem": canal_at,
                    "canal": canal_at,
                    "canal_origem": canal_at,
                    "canal_atendimento": "WhatsApp" if canal_at == "WhatsApp" else canal_at,
                    "etapa_captacao": "Nova captação" if canal_at not in ("WhatsApp", "Telefone", "Balcão") else "Em atendimento no WhatsApp",
                    "tipo_conteudo": tipo_conteudo_at,
                    "motivo_contato": motivo_contato_at,
                    "conteudo_titulo": conteudo_titulo_at.strip(),
                    "conteudo_url": conteudo_url_at.strip(),
                    "campanha": campanha_at.strip(),
                    "produto_interesse": produto_interesse_at.strip(),
                    "perfil_externo": "",
                    "id_mensagem_externa": "",
                    "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
                    "historico": [{"data": agora_local().strftime("%d/%m/%Y %H:%M"), "descricao": "Atendimento registrado", "usuario": "Sistema"}],
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
        st.info("Os modos abaixo valem para todos os canais. Respostas automáticas só serão enviadas depois que a integração oficial correspondente estiver ativa.")
        if st.button("💾 Salvar modos de atendimento", type="primary"):
            config_at.update({"modo": modo_geral, "sla_atencao_min": int(sla_atencao), "sla_urgente_min": int(sla_urgente), **regras})
            salvar_atendimentos(dados_at)
            st.success("Configurações salvas.")
            st.rerun()


    with tab_integracoes:
        st.subheader("Conexões oficiais da Meta")
        st.caption("As credenciais vêm do Alpha Connect. Aqui você acompanha separadamente se o webhook já está recebendo eventos reais.")
        cfg = dados_at["config"]

        def _segredo_local(nome):
            try:
                valor = st.secrets.get(nome, "")
                return str(valor or "").strip()
            except Exception:
                return ""

        meta_app_secret = _segredo_local("META_APP_ID")
        meta_app_id_suspeito = bool(meta_app_secret and ("googleusercontent.com" in meta_app_secret.lower() or ".apps.google" in meta_app_secret.lower()))
        meta_token_ok = bool(_segredo_app("META_ACCESS_TOKEN"))
        meta_page_ok = bool(_segredo_app("META_PAGE_ID"))
        instagram_id_ok = bool(_segredo_app("INSTAGRAM_ACCOUNT_ID"))
        whatsapp_phone_ok = bool(_segredo_local("WHATSAPP_PHONE_NUMBER_ID"))
        whatsapp_business_ok = bool(_segredo_local("WHATSAPP_BUSINESS_ACCOUNT_ID"))

        cred_fb = bool(meta_app_secret and not meta_app_id_suspeito and meta_token_ok and meta_page_ok)
        cred_ig = bool(meta_token_ok and instagram_id_ok)
        cred_wa = bool(meta_token_ok and whatsapp_phone_ok and whatsapp_business_ok)

        def _rotulo_conexao(credenciais, webhook_ativo):
            if credenciais and webhook_ativo:
                return "🟢 Conectado"
            if credenciais:
                return "🟡 Credenciais OK · webhook pendente"
            return "⚪ Credenciais incompletas"

        c1, c2, c3 = st.columns(3)
        c1.metric("WhatsApp", _rotulo_conexao(cred_wa, bool(cfg.get("integracao_whatsapp"))))
        c2.metric("Instagram", _rotulo_conexao(cred_ig, bool(cfg.get("integracao_instagram"))))
        c3.metric("Facebook", _rotulo_conexao(cred_fb, bool(cfg.get("integracao_facebook"))))

        st.info("🟡 Credenciais configuradas permitem testar a API. O estado verde exige também o webhook publicado, cadastrado na Meta e validado com entrada real.")
        if meta_app_id_suspeito:
            st.error("⚠️ O valor salvo em META_APP_ID parece ser um Client ID do Google (`apps.googleusercontent.com`). Substitua pelo **ID numérico do aplicativo Meta** em Streamlit Secrets. Isso impede a conexão real com Facebook, Instagram e WhatsApp.")

        supabase_url_meta = _segredo_local("SUPABASE_URL").rstrip("/")
        webhook_sugerido = f"{supabase_url_meta}/functions/v1/meta-webhook" if supabase_url_meta else ""
        i1, i2 = st.columns(2)
        meta_app_id = i1.text_input("Meta App ID", value=str(cfg.get("meta_app_id") or meta_app_secret or ""), help="Identificador do aplicativo criado no Meta for Developers.")
        meta_business_id = i2.text_input("Business Manager ID", value=str(cfg.get("meta_business_id", "")))
        webhook_url = st.text_input("URL pública do webhook", value=str(cfg.get("webhook_url") or webhook_sugerido or ""), placeholder="https://SEU-PROJETO.supabase.co/functions/v1/meta-webhook")
        token_atual = str(cfg.get("meta_verify_token", ""))
        if not token_atual:
            token_atual = "alphafest-" + secrets.token_urlsafe(18)
        verify_token = st.text_input("Token de verificação do webhook", value=token_atual, type="password")
        a1, a2, a3 = st.columns(3)
        int_wa = a1.toggle("Webhook WhatsApp validado", value=bool(cfg.get("integracao_whatsapp")), disabled=not cred_wa)
        int_ig = a2.toggle("Webhook Instagram validado", value=bool(cfg.get("integracao_instagram")), disabled=not cred_ig)
        int_fb = a3.toggle("Webhook Facebook validado", value=bool(cfg.get("integracao_facebook")), disabled=not cred_fb)
        teste_webhook_col, salvar_webhook_col = st.columns([1, 2])
        if teste_webhook_col.button("🧪 Testar endpoint", use_container_width=True, disabled=not bool(webhook_url.strip() and verify_token.strip())):
            try:
                desafio = "ALPHAFEST_OK"
                resposta_webhook = requests.get(
                    webhook_url.strip(),
                    params={"hub.mode": "subscribe", "hub.verify_token": verify_token.strip(), "hub.challenge": desafio},
                    timeout=12,
                )
                if resposta_webhook.status_code == 200 and resposta_webhook.text.strip() == desafio:
                    cfg["webhook_ultimo_teste"] = agora_local().strftime("%d/%m/%Y %H:%M")
                    cfg["webhook_endpoint_ok"] = True
                    salvar_atendimentos(dados_at)
                    st.success("Endpoint publicado e token de verificação confirmados. Agora cadastre esta URL nos Webhooks da Meta e envie uma mensagem real.")
                else:
                    cfg["webhook_endpoint_ok"] = False
                    salvar_atendimentos(dados_at)
                    st.error(f"Endpoint respondeu {resposta_webhook.status_code}, mas não confirmou o desafio da Meta.")
            except Exception as erro_teste_webhook:
                cfg["webhook_endpoint_ok"] = False
                salvar_atendimentos(dados_at)
                st.error(f"Não foi possível alcançar o endpoint: {erro_teste_webhook.__class__.__name__}")

        if salvar_webhook_col.button("💾 Salvar configuração das integrações", type="primary", use_container_width=True):
            cfg.update({
                "meta_app_id": meta_app_id.strip(),
                "meta_business_id": meta_business_id.strip(),
                "webhook_url": webhook_url.strip(),
                "meta_verify_token": verify_token.strip(),
                "integracao_whatsapp": bool(int_wa),
                "integracao_instagram": bool(int_ig),
                "integracao_facebook": bool(int_fb),
            })
            salvar_atendimentos(dados_at)
            st.success("Configuração salva. O canal fica verde somente depois da validação real do webhook.")
            st.rerun()

        if cfg.get("webhook_endpoint_ok"):
            st.success(f"🌐 Endpoint do webhook acessível · último teste: {cfg.get('webhook_ultimo_teste', 'agora')}")
        elif webhook_url.strip():
            st.caption("🌐 URL informada, mas o endpoint ainda não foi validado por este painel.")

        st.markdown("#### Teste de entrada multicanal")
        st.caption("Use este teste antes da conexão oficial para confirmar que uma oportunidade entra corretamente na caixa unificada.")
        t1, t2 = st.columns(2)
        teste_canal = t1.selectbox("Canal do teste", ["WhatsApp", "Instagram", "Facebook", "Site / Catálogo"], key="teste_canal_meta")
        teste_nome = t2.text_input("Nome ou perfil", key="teste_nome_meta", placeholder="@cliente ou Maria")
        teste_msg = st.text_area("Mensagem de teste", key="teste_msg_meta", placeholder="Vocês fazem medalhas personalizadas? Gostaria de orçamento.")
        if st.button("📥 Inserir oportunidade de teste", use_container_width=True):
            if not teste_msg.strip():
                st.warning("Digite a mensagem de teste.")
            else:
                novo = {
                    "id": f"AT-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                    "cliente": teste_nome.strip() or f"Contato do {teste_canal}",
                    "telefone": "",
                    "mensagem": teste_msg.strip(),
                    "status": sugerir_tipo_atendimento(teste_msg),
                    "prioridade": "Normal",
                    "responsavel": "",
                    "modo": cfg.get("modo", "Manual"),
                    "origem": teste_canal,
                    "canal": teste_canal,
                    "perfil_externo": teste_nome.strip(),
                    "id_mensagem_externa": f"TESTE-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                    "criado_em": agora_local().strftime("%d/%m/%Y %H:%M"),
                    "historico": [{"data": agora_local().strftime("%d/%m/%Y %H:%M"), "descricao": f"Oportunidade recebida pelo canal {teste_canal} (teste)", "usuario": "Sistema"}],
                }
                itens_at.append(novo)
                salvar_atendimentos(dados_at)
                st.success("Oportunidade incluída na caixa unificada.")
                st.rerun()

        with st.expander("Checklist para ativar WhatsApp, Instagram e Facebook"):
            st.markdown("""
1. Criar ou usar um aplicativo no **Meta for Developers**.
2. Vincular a conta empresarial, a Página do Facebook e o Instagram profissional.
3. Publicar a função `supabase/functions/meta-webhook/index.ts`.
4. Configurar os segredos `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e `META_VERIFY_TOKEN`.
5. Informar a URL da função e o mesmo token no painel de Webhooks da Meta.
6. Assinar os eventos de mensagens dos canais utilizados.
7. Enviar uma mensagem real, conferir a entrada na Caixa unificada e só então marcar o canal como conectado.
            """)


if pagina_atual == "crm":
    st.header("🎯 CRM Inteligente")
    st.caption("Priorize oportunidades, acompanhe o funil e evite que clientes interessados sejam esquecidos.")

    dados_crm = carregar_atendimentos()
    itens_crm = dados_crm.get("itens", [])
    historico_crm = carregar_historico()
    clientes_crm = carregar_clientes()
    tarefas_crm = sincronizar_producao_com_propostas()
    indicadores_unificados_crm = calcular_indicadores_unificados(
        historico_crm, itens_crm, tarefas_crm, agora_local().date()
    )

    oportunidades = []
    for item in itens_crm:
        indice, motivos = calcular_indice_alpha(item, historico_crm, clientes_crm)
        enriquecido = dict(item)
        enriquecido["indice_alpha"] = indice
        enriquecido["motivos_alpha"] = motivos
        enriquecido["temperatura"] = temperatura_indice_alpha(indice)
        enriquecido["estagio_funil"] = estagio_funil_atendimento(item)
        oportunidades.append(enriquecido)

    estagios = ["Novos leads", "Em atendimento", "Orçamento", "Aguardando resposta", "Fechados", "Perdidos / arquivados"]
    contagem_funil = {e: indicadores_unificados_crm["funil"].get(e, 0) for e in estagios}
    abertas_crm = [o for o in oportunidades if o.get("status") not in ("Entregue", "Pós-venda", "Arquivado")]
    quentes_crm = [o for o in abertas_crm if o["indice_alpha"] >= 80]
    sem_retorno_crm = [o for o in abertas_crm if o.get("status") == "Aguardando cliente" and minutos_aguardando(o) >= 1440]
    media_indice = sum(o["indice_alpha"] for o in abertas_crm) / len(abertas_crm) if abertas_crm else 0

    st.markdown("#### Visão geral comercial — mesma fonte da Central")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orçamentos criados hoje", indicadores_unificados_crm["propostas_hoje"])
    c2.metric("Pedidos aprovados hoje", indicadores_unificados_crm["aprovadas_hoje"])
    c3.metric("Entregas concluídas hoje", indicadores_unificados_crm["entregues_hoje"])
    c4.metric("Oportunidades abertas", indicadores_unificados_crm["atendimentos_abertos"])

    d1, d2, d3 = st.columns(3)
    d1.metric("🔥 Quentes", len(quentes_crm))
    d2.metric("Sem retorno +24h", len(sem_retorno_crm))
    d3.metric("Índice Alpha médio", f"{media_indice:.0f}/100")
    st.caption("Central, CRM e THU utilizam o mesmo cálculo e a mesma data de referência.")

    st.markdown("#### Funil comercial unificado")
    cols_funil = st.columns(len(estagios))
    icones_funil = ["🆕", "💬", "📝", "⏳", "✅", "⚫"]
    for col, estagio, icone in zip(cols_funil, estagios, icones_funil):
        col.metric(f"{icone} {estagio}", contagem_funil[estagio])

    st.divider()
    fcrm1, fcrm2, fcrm3, fcrm4 = st.columns([2, 1, 1, 1])
    busca_crm = fcrm1.text_input("Pesquisar cliente, telefone ou mensagem", key="crm_busca").strip().lower()
    filtro_temp = fcrm2.selectbox("Temperatura", ["Todas", "🔥 Quente", "🟠 Morno", "🟡 Em descoberta", "🔵 Frio"], key="crm_temp")
    filtro_estagio = fcrm3.selectbox("Etapa", ["Todas"] + estagios, key="crm_estagio")
    filtro_canal_crm = fcrm4.selectbox("Canal", ["Todos"] + CANAIS_ATENDIMENTO, key="crm_canal")

    lista_crm = []
    for op in oportunidades:
        base = " ".join(str(op.get(k, "")) for k in ("cliente", "telefone", "mensagem", "status", "canal", "origem")).lower()
        if busca_crm and busca_crm not in base:
            continue
        if filtro_temp != "Todas" and op["temperatura"] != filtro_temp:
            continue
        if filtro_estagio != "Todas" and op["estagio_funil"] != filtro_estagio:
            continue
        canal_op = str(op.get("canal") or op.get("origem") or "Outro")
        if filtro_canal_crm != "Todos" and canal_op != filtro_canal_crm:
            continue
        lista_crm.append(op)
    lista_crm.sort(key=lambda x: (-x["indice_alpha"], -minutos_aguardando(x)))

    st.markdown("#### Quem precisa de atenção")
    if not lista_crm:
        st.info("Nenhuma oportunidade encontrada com os filtros selecionados.")
    for op in lista_crm[:50]:
        op_id = op.get("id")
        canal_op = str(op.get("canal") or op.get("origem") or "Outro")
        with st.container(border=True):
            a, b, c = st.columns([4, 1.2, 1.5])
            a.markdown(f"**{html.escape(str(op.get('cliente') or 'Contato sem nome'))}** · {html.escape(canal_op)}")
            a.caption(f"{op.get('status', 'Novo contato')} · {tempo_aguardando_formatado(op)} · Próxima ação: {proxima_acao_crm(op)}")
            if op.get("mensagem"):
                a.write(str(op.get("mensagem"))[:280])
            b.metric("Índice Alpha", f"{op['indice_alpha']}/100")
            b.caption(op["temperatura"])
            c.write("**Por que está aqui**")
            for motivo in op.get("motivos_alpha", []):
                c.caption(f"• {motivo}")

            ac1, ac2, ac3, ac4 = st.columns([1.3, 1.4, 1.5, 1.2])
            telefone_op = _telefone_chave(op.get("telefone"))
            if telefone_op:
                numero_op = telefone_op
                if not numero_op.startswith("55"):
                    numero_op = "55" + numero_op
                ac1.link_button("📱 WhatsApp", f"https://wa.me/{numero_op}", use_container_width=True)
            else:
                ac1.button("📱 Sem telefone", disabled=True, use_container_width=True, key=f"crm_sem_tel_{op_id}")
            novo_status_crm = ac2.selectbox(
                "Etapa / status", STATUS_ATENDIMENTO,
                index=STATUS_ATENDIMENTO.index(op.get("status")) if op.get("status") in STATUS_ATENDIMENTO else 0,
                key=f"crm_status_{op_id}", label_visibility="collapsed",
            )
            novo_resp_crm = ac3.selectbox(
                "Responsável", ["Sem responsável", "Anna", "Jorge"],
                index=["Sem responsável", "Anna", "Jorge"].index(str(op.get("responsavel") or "Sem responsável")) if str(op.get("responsavel") or "Sem responsável") in ["Sem responsável", "Anna", "Jorge"] else 0,
                key=f"crm_resp_{op_id}", label_visibility="collapsed",
            )
            if ac4.button("💾 Atualizar", key=f"crm_salvar_{op_id}", use_container_width=True):
                for original in dados_crm.get("itens", []):
                    if original.get("id") == op_id:
                        original["status"] = novo_status_crm
                        original["responsavel"] = "" if novo_resp_crm == "Sem responsável" else novo_resp_crm
                        original["atualizado_em"] = agora_local().isoformat()
                        adicionar_evento_timeline(original, f"CRM atualizado: {novo_status_crm}", obter_usuario_atual().get("nome", "Equipe"))
                        break
                salvar_atendimentos(dados_crm)
                st.success("Oportunidade atualizada.")
                st.rerun()

if pagina_atual == "alpha":
    renderizar_alpha_assistente_comercial()


if pagina_atual == "intelligence":
    st.header("🧠 Alpha Intelligence")
    if usuario_em_operacao_protegida():
        st.info("🛡️ Este módulo está em modo protegido durante o atendimento da Anna. Os módulos operacionais continuam disponíveis normalmente.")
    elif render_alpha_intelligence is None:
        st.warning("O módulo Intelligence foi isolado porque não pôde ser carregado. O atendimento e os demais módulos continuam funcionando.")
        if ALPHA_INTELLIGENCE_IMPORT_ERROR:
            st.caption("Diagnóstico técnico disponível para o administrador.")
    else:
        def _salvar_snapshot_inteligencia(snapshot):
            save_document("alpha_intelligence_db", snapshot, ARQUIVO_INTELIGENCIA)
        try:
            render_alpha_intelligence(
                carregar_clientes(), carregar_historico(), carregar_catalogo(), carregar_producao(),
                save_snapshot=_salvar_snapshot_inteligencia, today=hoje_local(),
            )
        except Exception as _alpha_runtime_exc:
            st.warning("O Intelligence encontrou uma falha e foi isolado. Atendimento, orçamentos e pedidos não foram interrompidos.")
            st.caption("O administrador pode consultar os logs para o diagnóstico técnico.")


if pagina_atual == "clientes_360":
    clientes_360 = sincronizar_clientes_do_historico()
    renderizar_inteligencia_clientes(
        clientes=clientes_360,
        propostas_por_cliente=propostas_do_cliente,
        calcular_total=lambda proposta: calcular_valores_proposta(proposta)[2],
        hoje=hoje_local(),
    )


if pagina_atual == "crescimento":
    if not feature_enabled("marketing_studio", True):
        st.warning("Alpha Marketing Studio temporariamente desativado pela chave de segurança.")
        st.stop()
    st.header("📸 Alpha Marketing Studio")
    st.caption("Crie, organize e exporte campanhas prontas para publicação manual. A Central da Anna permanece intacta.")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1: renderizar_cartao_studio("Nova campanha", "Artes, textos e roteiros por canal.", "➕")
    with sc2: renderizar_cartao_studio("Biblioteca", "Campanhas salvas e reutilizáveis.", "📚")
    with sc3: renderizar_cartao_studio("Banco de mídia", "Fotos, vídeos, logos e fundos.", "🖼️")
    with sc4: renderizar_cartao_studio("Exportação", "Kit ZIP pronto para postar.", "📦")
    marketing = carregar_marketing()
    conteudos = marketing.get("conteudos", [])
    config_marketing = marketing.setdefault("config", {})

    with st.container(border=True):
        st.markdown("#### 🧰 Modo de trabalho")
        ig_conectado = bool(_segredo_app("META_ACCESS_TOKEN") and _segredo_app("INSTAGRAM_ACCOUNT_ID"))
        page_conectada = bool(_segredo_app("META_ACCESS_TOKEN") and _segredo_app("META_PAGE_ID"))
        c_status1, c_status2, c_status3 = st.columns(3)
        c_status1.metric("Criação offline", "🟢 Ativa")
        c_status2.metric("Publicação", "Manual")
        c_status3.metric("Canal principal", "Instagram")
        replicar_facebook = st.toggle(
            "Replicação automática no Facebook pela Meta",
            value=bool(config_marketing.get("replicar_facebook", True)),
            help="O Alpha Marketing prepara e registra o Instagram como publicação oficial. A Meta pode replicar o conteúdo na Página vinculada.",
            key="mkt_replica_facebook",
        )
        incluir_whatsapp = st.toggle(
            "Preparar também uma versão para Status do WhatsApp",
            value=bool(config_marketing.get("incluir_whatsapp", True)),
            key="mkt_incluir_whatsapp",
        )
        mudou_config = (
            config_marketing.get("replicar_facebook", True) != replicar_facebook
            or config_marketing.get("incluir_whatsapp", True) != incluir_whatsapp
            or config_marketing.get("canal_principal") != "Instagram"
        )
        if mudou_config:
            config_marketing.update({"canal_principal": "Instagram", "replicar_facebook": replicar_facebook, "incluir_whatsapp": incluir_whatsapp})
            marketing["config"] = config_marketing
            salvar_marketing(marketing)
        st.info("Nesta fase, o Studio gera e salva os arquivos no formato correto. A postagem é manual e a música é adicionada dentro de cada rede social.")

    t1, t2, t3, t4 = st.tabs(["🎨 Nova campanha", "📚 Biblioteca", "🖼️ Banco de mídia", "📦 Exportações"])

    with t1:
        catalogo_mkt = carregar_catalogo()
        fonte_imagem = st.radio(
            "Origem do trabalho",
            ["Upload livre", "Produto do catálogo"],
            horizontal=True,
            key="mkt_modo_origem",
            help="No Upload livre nenhum dado do catálogo é reaproveitado.",
        )
        upload_mkt = None
        imagem_ref = ""
        produto_mkt = {"Nome": "", "Descricao": "", "Categoria": ""}
        video_upload = None

        if fonte_imagem == "Upload livre":
            st.info("🔒 Modo independente: produto, descrição e preço do catálogo são ignorados.")
            upload_mkt = st.file_uploader(
                "Imagem desta campanha",
                type=["png","jpg","jpeg","webp","bmp","tif","tiff"],
                key="mkt_upload_livre_imagem",
            )
            video_upload = st.file_uploader(
                "Vídeo curto (opcional — preservado para Reels, TikTok e Shorts)",
                type=["mp4","mov","m4v","avi","mkv","webm"],
                key="mkt_upload_livre_video",
            )
            nome_livre = st.text_input("Nome do produto / serviço da foto", placeholder="Ex.: Copos térmicos personalizados", key="mkt_nome_livre")
            descricao_livre = st.text_area("O que aparece na imagem e quais benefícios destacar", placeholder="Ex.: Dois copos térmicos com nomes personalizados, ótima opção para presente...", key="mkt_descricao_livre")
            produto_mkt = {"Nome": nome_livre.strip(), "Descricao": descricao_livre.strip(), "Categoria": "Upload livre"}
            if upload_mkt:
                st.image(upload_mkt, width=420, caption="Imagem livre — nenhuma descrição do catálogo será utilizada")
            if video_upload:
                st.video(video_upload)
        else:
            if not catalogo_mkt:
                st.warning("Cadastre produtos no Catálogo ou use o modo Upload livre.")
            else:
                nomes = [p.get("Nome", "Produto") for p in catalogo_mkt]
                escolhido = st.selectbox("Produto / trabalho", nomes, key="mkt_produto_catalogo")
                produto_mkt = catalogo_mkt[nomes.index(escolhido)]
                imagens_mkt = produto_mkt.get("Imagens", []) or []
                if imagens_mkt:
                    imagem_ref = st.selectbox("Imagem do catálogo", imagens_mkt, format_func=lambda x: Path(str(x)).name or "Imagem")
                    try: st.image(imagem_ref, width=420)
                    except Exception: st.warning("Não foi possível abrir esta imagem do catálogo.")
                else:
                    st.warning("Este produto ainda não possui imagem no catálogo.")

        c1, c2, c3 = st.columns(3)
        objetivo = c1.selectbox("Objetivo", ["Vender", "Promoção", "Lançamento", "Engajar"], key="mkt_objetivo")
        tom = c2.selectbox("Linha de venda", ["Venda direta", "Emocional", "Urgência", "Premium", "Corporativo", "Promoção"], key="mkt_tom")
        campanha = c3.text_input("Campanha / data", placeholder="Ex.: Dia dos Pais", key="mkt_campanha")
        canais_instagram = ["Instagram Feed", "Instagram Story", "Carrossel", "Reel", "TikTok", "YouTube Shorts", "YouTube Horizontal"]
        opcoes_canais = canais_instagram + (["Status WhatsApp"] if incluir_whatsapp else [])
        canais_padrao = ["Instagram Feed", "Instagram Story"] + (["Status WhatsApp"] if incluir_whatsapp else [])
        canais = st.multiselect(
            "Canais e formatos que deseja preparar",
            opcoes_canais,
            default=[c for c in canais_padrao if c in opcoes_canais],
            key="mkt_canais_instagram",
            help="O Facebook não é gerado como publicação separada: a Meta replica o post do Instagram quando essa opção está ativa na conta.",
        )
        observacoes = st.text_area("Oferta e detalhes obrigatórios", placeholder="Ex.: Até sexta, R$ 90, entrega em Itatiba...", key="mkt_obs")
        p1,p2,p3 = st.columns(3)
        preco_arte = p1.text_input("Preço na arte (opcional)", placeholder="R$ 90,00")
        subtitulo_arte = p2.text_input("Chamada curta na arte", value="Personalizado do seu jeito")
        cta_arte = p3.text_input("Botão / CTA", value="Chame no WhatsApp")

        # Sprint 14.2.6 — Preview ao vivo isolado e exclusivo da Central do Jorge.
        preview_liberado = (
            feature_enabled("marketing_preview", False)
            and str(obter_usuario_atual().get("nome", "")).casefold() == "jorge"
        )
        if preview_liberado:
            st.markdown("### 👁️ Preview em tempo real")
            st.caption("Pré-visualização local. Nenhum arquivo é salvo e nenhuma postagem é realizada nesta etapa.")

            origem_preview = upload_mkt if fonte_imagem == "Upload livre" else imagem_ref
            campos_preview = {
                "Imagem": bool(origem_preview),
                "Produto": bool(str(produto_mkt.get("Nome", "")).strip()),
                "Descrição": bool(str(produto_mkt.get("Descricao", "")).strip()),
                "Oferta": bool(str(observacoes).strip() or str(preco_arte).strip()),
                "Chamada": bool(str(subtitulo_arte).strip()),
                "CTA": bool(str(cta_arte).strip()),
                "Canal": bool(canais),
            }
            pontos = sum(1 for ok in campos_preview.values() if ok)
            qualidade = round((pontos / len(campos_preview)) * 100) if campos_preview else 0
            q1, q2 = st.columns([1, 2])
            q1.metric("Qualidade da campanha", f"{qualidade}%")
            q2.progress(qualidade / 100)
            pendencias = [nome for nome, ok in campos_preview.items() if not ok]
            if pendencias:
                st.caption("Para melhorar: " + ", ".join(pendencias) + ".")
            else:
                st.success("Campanha pronta para geração.")

            canais_preview = [c for c in canais if CANAL_MIDIA_CONFIG.get(c, {}).get("tipo") == "imagem"]
            if origem_preview and canais_preview and produto_mkt.get("Nome"):
                canal_preview = st.selectbox(
                    "Formato do preview",
                    canais_preview,
                    key="mkt_preview_canal_1426",
                )
                try:
                    arte_preview = gerar_arte_png(
                        origem_preview,
                        canal_preview,
                        produto_mkt.get("Nome", "Produto"),
                        subtitulo_arte,
                        preco_arte,
                        cta_arte,
                    )
                    pv1, pv2 = st.columns([1.08, 0.92])
                    with pv1:
                        st.image(arte_preview, use_container_width=True, caption=f"Prévia — {canal_preview}")
                    with pv2:
                        st.markdown("#### Texto de apoio")
                        st.markdown(f"**{produto_mkt.get('Nome', 'Produto')}**")
                        if campanha:
                            st.caption(campanha)
                        if produto_mkt.get("Descricao"):
                            st.write(produto_mkt.get("Descricao"))
                        if observacoes:
                            st.info(observacoes)
                        st.markdown(f"**{cta_arte or 'Chame no WhatsApp'}**")
                        st.caption("A música será adicionada manualmente na rede social.")
                except Exception as exc:
                    st.warning(f"O preview foi isolado e não pôde ser exibido: {exc}")
            elif not origem_preview:
                st.info("Envie ou selecione uma imagem para visualizar a campanha.")
            elif not canais_preview:
                st.info("Selecione ao menos um formato de imagem para visualizar a campanha.")
            elif not produto_mkt.get("Nome"):
                st.info("Informe o nome do produto ou serviço para montar o preview.")

        if st.button("🚀 Gerar campanha profissional", type="primary", use_container_width=True):
            origem = upload_mkt if fonte_imagem == "Upload livre" else imagem_ref
            faltas = []
            if not canais: faltas.append("selecione pelo menos um canal")
            if not origem: faltas.append("envie ou selecione uma imagem")
            if not produto_mkt.get("Nome"): faltas.append("informe o nome do produto/serviço")
            if fonte_imagem == "Upload livre" and not produto_mkt.get("Descricao"): faltas.append("descreva o que aparece na imagem")
            if faltas:
                st.warning("Para continuar, " + "; ".join(faltas) + ".")
            else:
                try:
                    imagem_original_salva = ""
                    video_original_salvo = ""
                    if upload_mkt is not None:
                        imagem_original_salva = upload_library_file(upload_mkt, produto_nome=produto_mkt.get("Nome", "produto"), local_upload_dir="marketing_originais")
                    if video_upload is not None:
                        video_original_salvo = upload_library_file(video_upload, produto_nome=produto_mkt.get("Nome", "produto"), local_upload_dir="marketing_videos_originais")
                    png_original = converter_imagem_para_png(origem)
                    saidas, motor_copy = gerar_conteudo_marketing(produto_mkt, objetivo, campanha, canais, observacoes, tom, png_original)
                    artes = {}
                    for canal in canais:
                        config_canal = CANAL_MIDIA_CONFIG[canal]
                        if config_canal["tipo"] == "imagem":
                            artes[canal] = base64.b64encode(gerar_arte_png(origem, canal, produto_mkt.get("Nome", "Produto"), subtitulo_arte, preco_arte, cta_arte)).decode("ascii")
                    registro = {
                        "id": f"MKT-{agora_local().strftime('%Y%m%d%H%M%S%f')}",
                        "criado_em": agora_local().isoformat(),
                        "modo_origem": fonte_imagem,
                        "produto": produto_mkt.get("Nome", ""),
                        "descricao_confirmada": produto_mkt.get("Descricao", ""),
                        "categoria": produto_mkt.get("Categoria", ""),
                        "imagem_original": imagem_original_salva or imagem_ref,
                        "video_original": video_original_salvo,
                        "imagem_png_base64": base64.b64encode(png_original).decode("ascii"),
                        "objetivo": objetivo, "tom": tom, "campanha": campanha, "canais": canais,
                        "conteudos": saidas, "motor_copy": motor_copy,
                        "artes_png": artes, "aprovacoes": {canal: False for canal in canais},
                        "fila_publicacao": {}, "status": "Em revisão",
                    }
                    conteudos.insert(0, registro); marketing["conteudos"] = conteudos; salvar_marketing(marketing)
                    registrar_auditoria("Gerar campanha", "Marketing", registro["id"], {"produto": registro["produto"], "canais": canais, "modo": fonte_imagem, "motor": motor_copy})
                    st.session_state.mkt_ultimo_id = registro["id"]
                    st.success(f"Campanha criada com {motor_copy}. Revise os formatos e baixe o kit para publicação manual.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível gerar a campanha: {exc}")

        ultimo_id = st.session_state.get("mkt_ultimo_id")
        ultimo = next((x for x in conteudos if x.get("id") == ultimo_id), None)
        if ultimo:
            aprovados_total = sum(bool(ultimo.get("aprovacoes", {}).get(c)) for c in ultimo.get("canais", []))
            st.markdown(f"### Preview por formato • {aprovados_total}/{len(ultimo.get('canais', []))} aprovados")
            st.caption(f"Produto confirmado: {ultimo.get('produto')} • Origem: {ultimo.get('modo_origem')} • Texto: {ultimo.get('motor_copy','Alpha local')}")
            alterou = False
            for canal in ultimo.get("canais", []):
                aprovado_atual = bool(ultimo.get("aprovacoes", {}).get(canal))
                fila_atual = bool(ultimo.get("fila_publicacao", {}).get(canal))
                with st.container(border=True):
                    renderizar_cabecalho_canal(canal, aprovado_atual, fila_atual)
                    cols = st.columns([1.05, 1])
                    with cols[0]:
                        arte_b64 = ultimo.get("artes_png", {}).get(canal)
                        if arte_b64:
                            arte_bytes = base64.b64decode(arte_b64)
                            st.image(arte_bytes, use_container_width=True)
                            st.download_button("⬇️ Baixar PNG", arte_bytes, file_name=f"{re.sub(r'[^A-Za-z0-9_-]','_',ultimo.get('produto','campanha'))}_{re.sub(r'[^A-Za-z0-9_-]','_',canal)}.png", mime="image/png", key=f"baixar_{ultimo_id}_{canal}", use_container_width=True)
                        elif ultimo.get("video_original"):
                            st.video(ultimo.get("video_original"))
                            st.info("O vídeo original foi preservado. O roteiro abaixo está pronto para o canal; a edição MP4 automática será habilitada no Video Studio.")
                        else:
                            st.info("Canal de vídeo: foi gerado o roteiro comercial. Envie um vídeo no modo Upload livre para anexá-lo à campanha.")
                    with cols[1]:
                        texto = st.text_area("Descrição / roteiro comercial", value=ultimo.get("conteudos", {}).get(canal, ""), height=270, key=f"texto_{ultimo_id}_{canal}")
                        if texto != ultimo.get("conteudos", {}).get(canal, ""):
                            ultimo.setdefault("conteudos", {})[canal] = texto; alterou = True
                        aprovado = st.checkbox("✅ Aprovar este canal", value=aprovado_atual, key=f"aprovar_{ultimo_id}_{canal}")
                        if aprovado != aprovado_atual:
                            ultimo.setdefault("aprovacoes", {})[canal] = aprovado; alterou = True
                        st.caption("Ao aprovar, este formato entra no mesmo lote do Instagram.")
            if alterou:
                ultimo["status"] = "Aprovado" if all(ultimo.get("aprovacoes", {}).get(c) for c in ultimo.get("canais", [])) else "Em revisão"
                salvar_marketing(marketing)
            b1, b2 = st.columns([1, 1])
            if b1.button("💾 Salvar textos e aprovações", use_container_width=True):
                salvar_marketing(marketing); st.success("Revisão salva.")
            aprovados = [c for c in ultimo.get("canais", []) if ultimo.get("aprovacoes", {}).get(c)]
            kit_bytes = gerar_zip_campanha(ultimo)
            b2.download_button(
                f"📦 Baixar kit com {len(ultimo.get('canais', []))} formato(s)",
                kit_bytes,
                file_name=f"Campanha_{_nome_arquivo_seguro(ultimo.get('produto'))}_{_nome_arquivo_seguro(ultimo.get('campanha') or ultimo.get('objetivo'))}.zip",
                mime="application/zip",
                use_container_width=True,
                key=f"kit_ultimo_{ultimo_id}",
            )
            if False:
                momento = agora_local().isoformat()
                ultimo.setdefault("fila_publicacao", {})
                for canal in aprovados:
                    ultimo["fila_publicacao"][canal] = {"status": "Na fila", "adicionado_em": momento}
                ultimo["status"] = "Na fila de publicação"
                ultimo["lote_publicacao_em"] = momento
                salvar_marketing(marketing)
                registrar_auditoria("Publicação em lote", "Marketing", ultimo.get("id"), {"canais": aprovados})
                st.success("Os formatos aprovados foram enviados para a fila do Instagram. A publicação automática dependerá das credenciais oficiais da Meta; a replicação no Facebook seguirá a configuração da própria conta.")
                st.rerun()

    with t2:
        a,b,c = st.columns(3)
        a.metric("Campanhas", len(conteudos))
        b.metric("Em revisão", sum(1 for x in conteudos if x.get("status") == "Em revisão"))
        c.metric("Na fila/publicadas", sum(1 for x in conteudos if x.get("status") in ("Aprovado","Na fila de publicação","Publicado")))
        if not conteudos: st.info("A fila será preenchida quando você gerar a primeira campanha.")
        for item in conteudos[:50]:
            aprovados = sum(1 for canal in item.get("canais", []) if item.get("aprovacoes", {}).get(canal))
            with st.expander(f"{item.get('produto','Produto')} • {item.get('campanha') or item.get('objetivo')} • {item.get('status','Em revisão')} ({aprovados}/{len(item.get('canais',[]))} canais)"):
                st.caption(f"Origem: {item.get('modo_origem','Legado')} • Motor de texto: {item.get('motor_copy','Alpha local')}")
                st.download_button(
                    "📦 Baixar kit completo",
                    gerar_zip_campanha(item),
                    file_name=f"Campanha_{_nome_arquivo_seguro(item.get('produto'))}_{_nome_arquivo_seguro(item.get('campanha') or item.get('objetivo'))}.zip",
                    mime="application/zip",
                    key=f"kit_biblioteca_{item.get('id')}",
                    use_container_width=True,
                )
                for canal in item.get("canais", []):
                    renderizar_cabecalho_canal(canal, bool(item.get("aprovacoes",{}).get(canal)), bool(item.get("fila_publicacao",{}).get(canal)))
                    arte_b64=item.get("artes_png",{}).get(canal)
                    if arte_b64:
                        arte_bytes=base64.b64decode(arte_b64); st.image(arte_bytes, width=280)
                        st.download_button(f"Baixar {canal} PNG", arte_bytes, file_name=f"{item.get('id')}_{re.sub(r'[^A-Za-z0-9_-]','_',canal)}.png", mime="image/png", key=f"fila_dl_{item.get('id')}_{canal}")
                    st.code(item.get("conteudos",{}).get(canal,""), language=None)
                x1,x2=st.columns(2)
                if x1.button("✅ Marcar lote como publicado", key=f"mkt_pub_{item.get('id')}", use_container_width=True):
                    item["status"]="Publicado"; item["publicado_em"]=agora_local().isoformat()
                    for canal in item.get("canais", []):
                        if item.get("aprovacoes",{}).get(canal):
                            item.setdefault("fila_publicacao", {})[canal] = {"status":"Publicado", "publicado_em":item["publicado_em"]}
                    salvar_marketing(marketing); st.rerun()
                if x2.button("🗑️ Remover", key=f"mkt_del_{item.get('id')}", use_container_width=True):
                    marketing["conteudos"]=[x for x in conteudos if x.get("id") != item.get("id")]; salvar_marketing(marketing); st.rerun()

    with t3:
        st.subheader("🖼️ Banco de mídia AlphaFest")
        st.caption("Cadastre referências por produto. Nesta primeira etapa, os arquivos permanecem ligados às campanhas e ao catálogo já existente.")
        mid1, mid2, mid3 = st.columns(3)
        mid1.metric("Fotos nas campanhas", sum(1 for x in conteudos if x.get("imagem_original") or x.get("imagem_png_base64")))
        mid2.metric("Vídeos vinculados", sum(1 for x in conteudos if x.get("video_original")))
        mid3.metric("Templates oficiais", 1)
        with st.container(border=True):
            st.markdown("#### 🎨 Template Oficial 001")
            st.write("**Papel Arroz Institucional**")
            st.caption("Azul e branco, logo AlphaFest, título forte, aplicações do produto, benefícios e WhatsApp no rodapé.")
            st.success("Padrão visual aprovado e ativo para a evolução do motor de campanhas.")
        st.info("A próxima etapa permitirá cadastrar fundos, logos, fotos e vídeos em pastas por categoria sem afetar o catálogo operacional da Anna.")

    with t4:
        st.subheader("📦 Central de exportações")
        st.caption("Baixe kits completos para publicar manualmente no Instagram, TikTok, YouTube e WhatsApp.")
        if not conteudos:
            st.info("Gere uma campanha para habilitar as exportações.")
        for item in conteudos[:30]:
            with st.container(border=True):
                ex1, ex2 = st.columns([3, 1])
                ex1.markdown(f"**{item.get('produto','Campanha')}**")
                ex1.caption(f"{item.get('campanha') or item.get('objetivo')} • {len(item.get('canais', []))} formato(s)")
                ex2.download_button(
                    "⬇️ Baixar ZIP",
                    gerar_zip_campanha(item),
                    file_name=f"Campanha_{_nome_arquivo_seguro(item.get('produto'))}_{_nome_arquivo_seguro(item.get('campanha') or item.get('objetivo'))}.zip",
                    mime="application/zip",
                    key=f"export_zip_{item.get('id')}",
                    use_container_width=True,
                )


if pagina_atual == "jornada":
    renderizar_jornada_atendimento()

if pagina_atual == "projeto":
    renderizar_assistente_projeto_personalizado()


if pagina_atual == "novo_orcamento":
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

    ultima_salva = st.session_state.get("_ultima_proposta_salva")
    if ultima_salva:
        with st.container(border=True):
            st.success(f"Proposta {ultima_salva.get('numero_proposta', '')} salva com sucesso.")
            ac1, ac2, ac3 = st.columns([2, 2, 1])
            numero_destino = re.sub(r"\D", "", str(ultima_salva.get("whatsapp") or ultima_salva.get("cliente_wa") or ""))
            if numero_destino and not numero_destino.startswith("55"):
                numero_destino = "55" + numero_destino
            link_whatsapp = f"https://wa.me/{numero_destino}?text={quote(formatar_msg_whatsapp(ultima_salva))}" if numero_destino else f"https://wa.me/?text={quote(formatar_msg_whatsapp(ultima_salva))}"
            ac1.link_button("📱 Enviar orçamento por WhatsApp", link_whatsapp, use_container_width=True)
            ac2.download_button(
                "📄 Gerar HTML",
                gerar_html(ultima_salva),
                file_name=f"{ultima_salva.get('numero_proposta', 'orcamento')}.html",
                mime="text/html",
                use_container_width=True,
                key=f"html_pos_salvar_{ultima_salva.get('numero_proposta', 'orcamento')}",
            )
            if ac3.button("✖ Fechar", key="fechar_acoes_ultima_proposta", use_container_width=True):
                st.session_state.pop("_ultima_proposta_salva", None)
                st.rerun()

    # O formulário evita reruns enquanto a Anna digita. O processamento ocorre
    # somente ao clicar em Adicionar Item, deixando a digitação muito mais ágil.
    with st.form(key=f"form_item_orcamento_{st.session_state.form_key}", clear_on_submit=False):
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
        adicionar_item = st.form_submit_button("➕ Adicionar Item", use_container_width=True)

    if adicionar_item:
        if not prod.strip():
            st.warning("Informe o produto antes de adicionar.")
        else:
            detalhes = f"Tema: {et} | Nome: {en} | Idade: {ei} | Cor: {ec} | Obs: {eg}"
            st.session_state.temp_itens.append({"produto": prod, "especificacoes": detalhes, "quantidade": q, "valor_unitario": v})
            st.session_state.form_key += 1
            rerun_na_aba("novo_orcamento")

    if st.session_state.temp_itens:
        st.write("📋 **Itens da proposta:**")
        for idx, item in enumerate(st.session_state.temp_itens):
            col_info, col_remover = st.columns([8, 1])
            col_info.write(f"**{idx + 1}. {item.get('produto')}** — Qtd: {item.get('quantidade')} — R$ {valor_float(item.get('valor_unitario')):,.2f}")
            col_info.caption(item.get("especificacoes", ""))
            if col_remover.button("🗑️", key=f"remover_item_{idx}", help="Remover item"):
                remover_item_temp(idx, "novo_orcamento")

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
                "aprovado": antigo.get("aprovado", False),
                "timeline": antigo.get("timeline", []) if isinstance(antigo.get("timeline", []), list) else [],
                "atendimento_id": antigo.get("atendimento_id") or st.session_state.get("_atendimento_origem_id", ""),
                "projeto_id": antigo.get("projeto_id") or st.session_state.get("_projeto_origem_id", ""),
            }

            registrar_evento_proposta(dados, "Proposta atualizada" if st.session_state.editar_numero else "Proposta criada")
            if st.session_state.editar_numero:
                atualizar_proposta(numero, dados)
            else:
                h = carregar_historico()
                h.insert(0, dados)
                salvar_historico_completo(h)

            projeto_origem_id = st.session_state.pop("_projeto_origem_id", None) or dados.get("projeto_id")
            if projeto_origem_id:
                projetos_link = carregar_projetos()
                for projeto_link in projetos_link:
                    if projeto_link.get("id") == projeto_origem_id:
                        projeto_link["numero_proposta"] = numero
                        projeto_link["status"] = "Orçamento criado"
                        registrar_evento_projeto(projeto_link, f"Proposta {numero} criada")
                        break
                salvar_projetos(projetos_link)

            atendimento_origem_id = st.session_state.pop("_atendimento_origem_id", None) or dados.get("atendimento_id")
            if atendimento_origem_id:
                dados_at_link = carregar_atendimentos()
                for atendimento_link in dados_at_link.get("itens", []):
                    if atendimento_link.get("id") == atendimento_origem_id:
                        status_anterior = atendimento_link.get("status", "Novo contato")
                        atendimento_link["numero_proposta"] = numero
                        atendimento_link["status"] = "Aguardando cliente"
                        atendimento_link["atualizado_em"] = agora_local().strftime("%d/%m/%Y %H:%M")
                        registrar_evento_atendimento(atendimento_link, f"Proposta {numero} criada e enviada para acompanhamento")
                        break
                salvar_atendimentos(dados_at_link)

            # Mantém uma cópia somente para exibir as ações imediatas após salvar.
            # A mensagem e o layout padrão permanecem exatamente os mesmos.
            st.session_state["_ultima_proposta_salva"] = dict(dados)
            agendar_limpeza_formulario()
            rerun_na_aba("novo_orcamento", "Proposta salva com sucesso e operação atualizada.")

if pagina_atual == "historico":
    renderizar_painel_alertas("historico")

    historico = carregar_historico()
    busca = st.text_input("🔎 Pesquisar por cliente, proposta, telefone ou produto")
    if busca.strip():
        termo = busca.strip().lower()
        historico = [p for p in historico if termo in normalizar_texto_busca(p)]
    st.caption(f"{len(historico)} proposta(s) encontrada(s)")

    for prop in historico:
        prop_atual, relacionamento_atual = proposta_com_dados_atuais(prop)
        num_p = prop.get("numero_proposta", "SEM-NÚMERO")
        cliente_p = prop_atual.get("cliente_nome", "Cliente não informado")
        subtotal_p, desconto_p, total_p = calcular_valores_proposta(prop)
        pago_p = bool(prop.get("pago", False))
        entregue_p = bool(prop.get("entregue", False))
        aprovado_p = bool(prop.get("aprovado", False))
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
            whatsapp_hist = prop_atual.get("whatsapp", prop_atual.get("cliente_wa", "")) or "Não informado"
            documento_hist = prop_atual.get("documento", prop_atual.get("cliente_cpf_cnpj", "")) or "Não informado"
            st.write(f"📱 **WhatsApp:** {whatsapp_hist}")
            st.write(f"🪪 **CPF/CNPJ:** {documento_hist}")
            if relacionamento_atual:
                st.caption("🌐 Dados pessoais atuais do módulo Relacionamentos. Itens, valores e datas permanecem históricos.")
            for item in prop.get('itens', []):
                st.write(f"• {item.get('produto', '')} (Qtd: {item.get('quantidade', 0)})")

            c1, c2 = st.columns(2)
            c1.link_button("📱 Enviar WhatsApp", f"https://wa.me/?text={quote(formatar_msg_whatsapp(prop_atual))}", use_container_width=True)
            c2.download_button("📄 Gerar HTML", gerar_html(prop_atual), file_name=f"{num_p}.html", mime="text/html", use_container_width=True, key=f"html_historico_{num_p}")

            c3, c4, c5 = st.columns(3)
            if c3.button("✏️ Editar", key=f"editar_{num_p}", use_container_width=True):
                carregar_proposta_no_formulario(prop, duplicar=False)
                rerun_na_aba("novo_orcamento", "Proposta carregada para correção.")
            if c4.button("📋 Duplicar pedido", key=f"duplicar_{num_p}", use_container_width=True):
                carregar_proposta_no_formulario(prop_atual, duplicar=True)
                rerun_na_aba("novo_orcamento", "Cópia carregada como novo orçamento.")
            if c5.button("🗑️ Excluir", key=f"del_{num_p}", use_container_width=True):
                excluir_proposta(num_p)

            s1, s2, s3 = st.columns(3)
            s1.checkbox("Aprovado", value=prop.get("aprovado", False), key=f"a_{num_p}", on_change=alternar_status, args=(num_p, "aprovado", not prop.get("aprovado", False)))
            s2.checkbox("Pago", value=prop.get("pago", False), key=f"p_{num_p}", on_change=alternar_status, args=(num_p, "pago", not prop.get("pago", False)))
            s3.checkbox("Entregue", value=prop.get("entregue", False), key=f"e_{num_p}", on_change=alternar_status, args=(num_p, "entregue", not prop.get("entregue", False)))

            if entregue_p:
                proxima_acao = "Registrar pós-venda"
            elif not aprovado_p:
                proxima_acao = "Aguardar ou registrar aprovação do cliente"
            elif not pago_p:
                proxima_acao = "Confirmar pagamento e acompanhar produção"
            else:
                proxima_acao = "Concluir produção e entregar"
            st.info(f"🎯 **Próxima ação:** {proxima_acao}")
            timeline_prop = prop.get("timeline", []) if isinstance(prop.get("timeline"), list) else []
            if timeline_prop:
                with st.expander("🕒 Linha do tempo da proposta"):
                    for evento in reversed(timeline_prop[-20:]):
                        st.write(f"**{evento.get('data', '—')}** · {evento.get('descricao', 'Atualização')}")

            st.divider()
            renderizar_caixa_projeto(prop, prefixo="hist")


if pagina_atual == "fluxo":
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


if pagina_atual == "relatorios":
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



if pagina_atual == "executivo":
    st.markdown("<h2 style='text-align:center;'>📈 Painel Executivo</h2>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#6b7280;'>Visão rápida da operação, vendas e atendimento da Alphafest.</p>",
        unsafe_allow_html=True,
    )

    def _moeda_exec(valor):
        try:
            return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "R$ 0,00"

    def _data_exec(valor):
        if not valor:
            return None
        texto = str(valor).strip()
        formatos = (
            "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
        )
        for formato in formatos:
            try:
                return datetime.strptime(texto, formato).date()
            except (ValueError, TypeError):
                pass
        try:
            return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return None

    hoje_exec = hoje_local()
    inicio_mes_exec = hoje_exec.replace(day=1)
    historico_exec = carregar_historico()
    clientes_exec = carregar_clientes()
    atendimentos_exec = carregar_atendimentos()
    tarefas_exec = [t for t in sincronizar_producao_com_propostas() if t.get("ativa", True)]

    propostas_mes = []
    propostas_hoje = []
    for proposta in historico_exec:
        d = _data_exec(proposta.get("data_geracao") or proposta.get("data") or proposta.get("criado_em"))
        if d == hoje_exec:
            propostas_hoje.append(proposta)
        if d and inicio_mes_exec <= d <= hoje_exec:
            propostas_mes.append(proposta)

    orcado_hoje = sum(calcular_valores_proposta(p)[2] for p in propostas_hoje)
    confirmado_hoje = sum(calcular_valores_proposta(p)[2] for p in propostas_hoje if p.get("aprovado", False))
    recebido_hoje = sum(calcular_valores_proposta(p)[2] for p in historico_exec if p.get("pago", False) and registro_eh_de_hoje(p.get("atualizado_em") or p.get("pago_em") or p.get("data_geracao")))
    a_receber_total = sum(calcular_valores_proposta(p)[2] for p in historico_exec if p.get("aprovado", False) and not p.get("pago", False))

    total_mes = sum(calcular_valores_proposta(p)[2] for p in propostas_mes)
    aprovadas_mes = [p for p in propostas_mes if p.get("aprovado", False)]
    confirmado_mes = sum(calcular_valores_proposta(p)[2] for p in aprovadas_mes)
    conversao_mes = (len(aprovadas_mes) / len(propostas_mes) * 100) if propostas_mes else 0
    ticket_aprovado = (confirmado_mes / len(aprovadas_mes)) if aprovadas_mes else 0

    st.markdown("#### 💰 Comercial e financeiro")
    ef1, ef2, ef3, ef4 = st.columns(4)
    ef1.metric("Orçado hoje", _moeda_exec(orcado_hoje))
    ef2.metric("Confirmado hoje", _moeda_exec(confirmado_hoje))
    ef3.metric("Recebido hoje", _moeda_exec(recebido_hoje))
    ef4.metric("A receber", _moeda_exec(a_receber_total))

    em_atraso_exec = [t for t in tarefas_exec if classe_prazo_producao(t.get("data_entrega"), t.get("status")) == "Atrasado"]
    urgentes_exec = [t for t in tarefas_exec if str(t.get("prioridade", "")).lower() == "urgente"]
    em_producao_exec = [t for t in tarefas_exec if normalizar_status_fluxo(t.get("status")) in ("Arte aprovada", "Pronto para produzir", "Em produção", "Montagem/acabamento")]
    prontos_exec = [t for t in tarefas_exec if normalizar_status_fluxo(t.get("status")) == "Pronto"]

    abertos_exec = [a for a in atendimentos_exec.get("itens", []) if a.get("status") not in ("Entregue", "Pós-venda", "Arquivado")]
    aguardando_30_exec = [a for a in abertos_exec if minutos_aguardando(a) >= 30]
    atendimentos_hoje_exec = [a for a in atendimentos_exec.get("itens", []) if registro_eh_de_hoje(a.get("criado_em") or a.get("data") or a.get("atualizado_em"))]

    st.markdown("#### ⚙️ Operação de hoje")
    eo1, eo2, eo3, eo4, eo5 = st.columns(5)
    eo1.metric("Pedidos ativos", len(tarefas_exec))
    eo2.metric("Atrasados", len(em_atraso_exec))
    eo3.metric("Urgentes", len(urgentes_exec))
    eo4.metric("Em produção", len(em_producao_exec))
    eo5.metric("Prontos", len(prontos_exec))

    st.markdown("#### 📱 Atendimento e vendas do mês")
    ea1, ea2, ea3, ea4, ea5 = st.columns(5)
    ea1.metric("Atendimentos hoje", len(atendimentos_hoje_exec))
    ea2.metric("Aguardando +30 min", len(aguardando_30_exec))
    ea3.metric("Propostas no mês", len(propostas_mes))
    ea4.metric("Conversão", f"{conversao_mes:.1f}%".replace(".", ","))
    ea5.metric("Ticket aprovado", _moeda_exec(ticket_aprovado))

    st.divider()
    st.markdown("#### 🚦 Saúde da empresa")
    saude_atendimento = "🔴 Atenção" if aguardando_30_exec else "🟢 Em dia"
    saude_producao = "🔴 Atenção" if em_atraso_exec else ("🟡 Acompanhar" if urgentes_exec else "🟢 Em dia")
    saude_financeiro = "🟡 A receber" if a_receber_total > 0 else "🟢 Em dia"
    cfg_backup_exec = carregar_config_backup()
    ultimo_backup_exec = str(cfg_backup_exec.get("ultimo_backup_em", "")).strip()
    idade_backup_exec = None
    if ultimo_backup_exec:
        try:
            dt_backup_exec = datetime.fromisoformat(ultimo_backup_exec)
            if dt_backup_exec.tzinfo is None:
                dt_backup_exec = dt_backup_exec.replace(tzinfo=agora_local().tzinfo)
            idade_backup_exec = max(0, (agora_local() - dt_backup_exec.astimezone(agora_local().tzinfo)).total_seconds() / 3600)
        except Exception:
            idade_backup_exec = None
    saude_backup = "🔴 Sem backup" if idade_backup_exec is None else ("🔴 Atrasado" if idade_backup_exec > 30 else "🟢 Atual")
    sh1, sh2, sh3, sh4 = st.columns(4)
    sh1.metric("Atendimento", saude_atendimento)
    sh2.metric("Produção", saude_producao)
    sh3.metric("Financeiro", saude_financeiro)
    sh4.metric("Backup", saude_backup)

    st.divider()
    col_graf1, col_graf2 = st.columns(2)
    linhas_mes = []
    produtos_mes = {}
    for p in propostas_mes:
        d = _data_exec(p.get("data_geracao") or p.get("data") or p.get("criado_em"))
        if d:
            linhas_mes.append({"Dia": d.strftime("%d/%m"), "Valor": calcular_valores_proposta(p)[2]})
        for item in p.get("itens", []) or []:
            nome = str(item.get("produto", "Não informado")).strip() or "Não informado"
            qtd = valor_float(item.get("quantidade"))
            produtos_mes[nome] = produtos_mes.get(nome, 0) + qtd

    with col_graf1:
        st.markdown("##### Orçamentos no mês")
        if linhas_mes:
            df_mes_exec = pd.DataFrame(linhas_mes).groupby("Dia", as_index=False)["Valor"].sum()
            chart_mes = alt.Chart(df_mes_exec).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X("Dia:N", sort=None, title=None),
                y=alt.Y("Valor:Q", title="Valor orçado"),
                tooltip=[alt.Tooltip("Dia:N"), alt.Tooltip("Valor:Q", format=",.2f")],
            ).properties(height=280)
            st.altair_chart(chart_mes, use_container_width=True)
            st.caption(f"Total do mês: {_moeda_exec(total_mes)}")
        else:
            st.info("Ainda não há propostas neste mês.")

    with col_graf2:
        st.markdown("##### Produtos mais solicitados no mês")
        if produtos_mes:
            df_prod_exec = pd.DataFrame([
                {"Produto": nome, "Quantidade": qtd} for nome, qtd in produtos_mes.items()
            ]).sort_values("Quantidade", ascending=False).head(8)
            chart_prod = alt.Chart(df_prod_exec).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X("Quantidade:Q", title=None),
                y=alt.Y("Produto:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("Produto:N"), alt.Tooltip("Quantidade:Q", format=",.1f")],
            ).properties(height=280)
            st.altair_chart(chart_prod, use_container_width=True)
        else:
            st.info("Ainda não há itens suficientes para o ranking.")

    st.divider()
    st.markdown("#### 🎯 Atenções do gestor")
    alertas_exec = []
    if em_atraso_exec:
        alertas_exec.append(f"{len(em_atraso_exec)} pedido(s) atrasado(s) precisam de revisão.")
    if aguardando_30_exec:
        alertas_exec.append(f"{len(aguardando_30_exec)} cliente(s) aguardam resposta há mais de 30 minutos.")
    if a_receber_total > 0:
        alertas_exec.append(f"Há {_moeda_exec(a_receber_total)} em pedidos aprovados ainda não pagos.")
    if conversao_mes < 30 and len(propostas_mes) >= 3:
        alertas_exec.append(f"A conversão do mês está em {conversao_mes:.1f}%; vale revisar os orçamentos pendentes.")
    if not alertas_exec:
        st.success("Nenhuma atenção crítica identificada neste momento.")
    else:
        for alerta in alertas_exec:
            st.warning(alerta)


if pagina_atual == "catalogo":
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
                    if cacoes.button("🗑️ Mover para lixeira", key=f"cat_excluir_{i}", use_container_width=True):
                        removido = catalogo.pop(i)
                        enviar_para_lixeira("Produto", removido, removido.get("Nome", ""))
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

if pagina_atual == "relacionamentos":
    st.header("🌐 Relacionamentos")
    st.caption("Um único cadastro para clientes, fornecedores, parceiros e contatos que exigem regras especiais de atendimento.")

    clientes = sincronizar_clientes_do_historico()
    with st.expander("🧬 Cadastro Mestre e integridade dos vínculos", expanded=False):
        st.caption("Relacionamentos são a fonte oficial dos dados pessoais. Orçamentos, projetos, produção, atendimentos e campanhas guardam o vínculo pelo ID permanente.")
        ids_ok = sum(1 for c in clientes if str(c.get("id", "")).strip())
        hist_atual = carregar_historico()
        hist_vinc = sum(1 for p in hist_atual if str(p.get("relacionamento_id", "")).strip())
        c1, c2, c3 = st.columns(3)
        c1.metric("Relacionamentos com ID", f"{ids_ok}/{len(clientes)}")
        c2.metric("Orçamentos vinculados", f"{hist_vinc}/{len(hist_atual)}")
        c3.metric("Fonte oficial", "Relacionamentos")
        if st.button("🔄 Sincronizar Cadastro Mestre agora", type="primary", use_container_width=True):
            with st.spinner("Consolidando IDs e vínculos sem apagar históricos..."):
                resumo_master = sincronizar_cadastro_mestre(salvar=True)
            st.success(f"Sincronização concluída: {resumo_master['alteracoes']} vínculo(s) criado(s) e {resumo_master['duplicidades_consolidadas']} duplicidade(s) segura(s) consolidada(s).")
            if resumo_master["sem_vinculo"]:
                st.warning(f"{resumo_master['sem_vinculo']} registro(s) ainda precisam de identificação manual.")
            st.session_state["ultimo_resumo_master"] = resumo_master
            st.rerun()
    if "cliente_edit_id" not in st.session_state:
        st.session_state.cliente_edit_id = None

    aba_cli_lista, aba_cli_cadastro = st.tabs(["🔎 Consultar relacionamentos", "➕ Cadastrar / Editar"])

    with aba_cli_lista:
        termo_cli = st.text_input(
            "Pesquisar por nome, papel, CPF/CNPJ, WhatsApp, e-mail ou observação",
            key="pesquisa_clientes_v31",
        ).strip().lower()

        filtrados_cli = []
        for cli in clientes:
            base = " ".join(str(cli.get(c, "")) for c in ["nome", "documento", "whatsapp", "email", "observacoes", "cidade", "origem_cliente", "segmentos", "interesses", "campanhas_interesse", "papeis", "classificacao_relacionamento", "politica_atendimento", "fornecedor"]).lower()
            if not termo_cli or termo_cli in base:
                filtrados_cli.append(cli)

        total_clientes = len(clientes)
        clientes_com_pedidos = sum(1 for cli in clientes if propostas_do_cliente(cli))
        total_propostas_clientes = sum(len(propostas_do_cliente(cli)) for cli in clientes)
        m1, m2, m3 = st.columns(3)
        m1.metric("Relacionamentos cadastrados", total_clientes)
        m2.metric("Clientes com propostas", clientes_com_pedidos)
        m3.metric("Propostas vinculadas", total_propostas_clientes)

        st.write(f"**{len(filtrados_cli)} relacionamento(s) encontrado(s)**")
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
                    st.write("**Papéis:** " + ", ".join(papeis_relacionamento(cli)))
                    st.write(f"**Classificação:** {cli.get('classificacao_relacionamento') or 'Não classificado'}")
                    pol_cli = politica_atendimento(cli)
                    if pol_cli.get("nivel") != "Normal":
                        st.warning(f"🛡️ Atendimento: {pol_cli.get('nivel')}" + (f" — {pol_cli.get('motivo')}" if pol_cli.get('motivo') else ""))
                    if "Fornecedor" in papeis_relacionamento(cli):
                        forn = cli.get("fornecedor", {}) or {}
                        st.info(f"🏭 Fornecedor {forn.get('prioridade') or 'sem prioridade definida'}" + (f" — {forn.get('materiais')}" if forn.get('materiais') else ""))
                    if cli.get("segmentos"):
                        st.write("**Perfis:** " + ", ".join(cli.get("segmentos", [])))
                    if cli.get("interesses"):
                        st.write("**Interesses:** " + ", ".join(cli.get("interesses", [])))
                    st.write(f"**Potencial comercial:** {'⭐' * int(cli.get('potencial', 0) or 0) or 'Não avaliado'}")
                    if cli.get("observacoes"):
                        st.write(f"**Observações:** {cli.get('observacoes')}")
                with cstats:
                    resumo_cli = resumo_cliente_operacional(cli, propostas_cli)
                    st.metric("Total orçado", f"R$ {total_orcado_cli:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.metric("Total recebido", f"R$ {total_pago_cli:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.metric("Ticket médio", f"R$ {resumo_cli['ticket']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.caption(f"Última proposta: {resumo_cli['ultima_proposta']} · {resumo_cli['ultima_data']}")
                    if resumo_cli["produtos"]:
                        st.write("**Mais solicitados:** " + ", ".join(resumo_cli["produtos"]))
                    if resumo_cli["temas"]:
                        st.write("**Temas recorrentes:** " + ", ".join(resumo_cli["temas"]))
                    if propostas_cli:
                        st.info(f"🎯 Próxima ação sugerida: {proxima_acao_proposta(sorted(propostas_cli, key=lambda p: data_entrega_segura(p.get('data_geracao')) or date.min, reverse=True)[0])}")
                    else:
                        st.info("🎯 Próxima ação sugerida: iniciar relacionamento ou registrar primeiro orçamento")

                b1, b2, b3 = st.columns(3)
                pol_acao_cli = politica_atendimento(cli)
                if b1.button("➕ Novo orçamento", key=f"cli_orc_{cli.get('id')}", use_container_width=True, disabled=not pol_acao_cli.get("permitir_orcamento", True)):
                    carregar_cliente_no_orcamento(cli)
                    st.rerun()
                if b2.button("✏️ Editar cliente", key=f"cli_edit_{cli.get('id')}", use_container_width=True):
                    st.session_state.cliente_edit_id = cli.get("id")
                    st.rerun()
                if b3.button("🗑️ Mover para lixeira", key=f"cli_del_{cli.get('id')}", use_container_width=True):
                    enviar_para_lixeira("Cliente", cli, cli.get("id") or cli.get("nome", ""))
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
        st.subheader("✏️ Editar relacionamento" if cliente_edicao else "➕ Novo relacionamento")
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

        st.markdown("#### 🌐 Papéis e política de relacionamento")
        cli_papeis = st.multiselect("Papéis (pode marcar vários)", PAPEIS_RELACIONAMENTO, default=papeis_relacionamento(cliente_edicao) if cliente_edicao else ["Cliente"], key=f"cli_papeis_{edit_id}")
        classificacao_atual = cliente_edicao.get("classificacao_relacionamento", "Não classificado") if cliente_edicao else "Não classificado"
        if classificacao_atual not in CLASSIFICACOES_RELACIONAMENTO:
            classificacao_atual = "Não classificado"
        cli_classificacao = st.selectbox("Classificação do relacionamento", CLASSIFICACOES_RELACIONAMENTO, index=CLASSIFICACOES_RELACIONAMENTO.index(classificacao_atual), key=f"cli_classificacao_{edit_id}")
        politica_atual = politica_atendimento(cliente_edicao or {})
        p1, p2 = st.columns(2)
        cli_nivel_atendimento = p1.selectbox("Nível de atendimento", NIVEIS_ATENDIMENTO, index=NIVEIS_ATENDIMENTO.index(politica_atual.get("nivel", "Normal")) if politica_atual.get("nivel", "Normal") in NIVEIS_ATENDIMENTO else 0, key=f"cli_nivel_atendimento_{edit_id}")
        cli_motivo_restricao = p2.text_input("Motivo interno / alerta", value=politica_atual.get("motivo", ""), key=f"cli_motivo_restricao_{edit_id}", placeholder="Ex.: inadimplência, concorrente, alterações frequentes")
        pp1, pp2, pp3 = st.columns(3)
        cli_permitir_resposta = pp1.checkbox("Pode receber resposta", value=politica_atual.get("permitir_resposta", True), key=f"cli_permitir_resposta_{edit_id}")
        cli_permitir_catalogo = pp1.checkbox("Pode receber catálogo", value=politica_atual.get("permitir_catalogo", True), key=f"cli_permitir_catalogo_{edit_id}")
        cli_permitir_orcamento = pp2.checkbox("Pode solicitar orçamento", value=politica_atual.get("permitir_orcamento", True), key=f"cli_permitir_orcamento_{edit_id}")
        cli_permitir_campanhas = pp2.checkbox("Pode receber campanhas", value=politica_atual.get("permitir_campanhas", True), key=f"cli_permitir_campanhas_{edit_id}")
        cli_pagamento_antecipado = pp3.checkbox("Exigir pagamento antecipado", value=politica_atual.get("exigir_pagamento_antecipado", False), key=f"cli_pagamento_antecipado_{edit_id}")
        cli_aprovacao_gestor = pp3.checkbox("Exigir aprovação do gestor", value=politica_atual.get("exigir_aprovacao_gestor", False), key=f"cli_aprovacao_gestor_{edit_id}")

        fornecedor_atual = (cliente_edicao or {}).get("fornecedor", {}) or {}
        if "Fornecedor" in cli_papeis:
            st.markdown("#### 🏭 Dados de fornecedor")
            f1, f2 = st.columns(2)
            cli_forn_materiais = f1.text_area("Materiais / serviços fornecidos", value=fornecedor_atual.get("materiais", ""), key=f"cli_forn_materiais_{edit_id}")
            cli_forn_contato = f2.text_input("Contato comercial", value=fornecedor_atual.get("contato_comercial", ""), key=f"cli_forn_contato_{edit_id}")
            prioridade_atual = fornecedor_atual.get("prioridade", "Não definida")
            if prioridade_atual not in PRIORIDADES_FORNECEDOR:
                prioridade_atual = "Não definida"
            ff1, ff2, ff3 = st.columns(3)
            cli_forn_prioridade = ff1.selectbox("Prioridade", PRIORIDADES_FORNECEDOR, index=PRIORIDADES_FORNECEDOR.index(prioridade_atual), key=f"cli_forn_prioridade_{edit_id}")
            cli_forn_prazo = ff2.text_input("Prazo médio", value=fornecedor_atual.get("prazo_medio", ""), key=f"cli_forn_prazo_{edit_id}", placeholder="Ex.: 3 dias")
            cli_forn_avaliacao = ff3.slider("Avaliação interna", 0, 5, int(fornecedor_atual.get("avaliacao", 0) or 0), key=f"cli_forn_avaliacao_{edit_id}")
            cli_forn_obs = st.text_area("Observações de fornecedor", value=fornecedor_atual.get("observacoes", ""), key=f"cli_forn_obs_{edit_id}")
        else:
            cli_forn_materiais = fornecedor_atual.get("materiais", "")
            cli_forn_contato = fornecedor_atual.get("contato_comercial", "")
            cli_forn_prioridade = fornecedor_atual.get("prioridade", "Não definida")
            cli_forn_prazo = fornecedor_atual.get("prazo_medio", "")
            cli_forn_avaliacao = int(fornecedor_atual.get("avaliacao", 0) or 0)
            cli_forn_obs = fornecedor_atual.get("observacoes", "")

        cli_potencial = st.slider("Potencial comercial (opcional)", 0, 5, int(cliente_edicao.get("potencial", 0) or 0) if cliente_edicao else 0, help="0 = ainda não avaliado; 5 = alto potencial")
        opcoes_origem = ["Não informado", "WhatsApp", "Instagram", "Facebook", "TikTok", "Google", "Indicação", "Mercado Livre", "Shopee", "Loja", "Outro"]
        origem_atual = cliente_edicao.get("origem_cliente", "Não informado") if cliente_edicao else "Não informado"
        if origem_atual not in opcoes_origem:
            origem_atual = "Não informado"
        cli_origem = st.selectbox("Origem do cliente (opcional)", opcoes_origem, index=opcoes_origem.index(origem_atual), key=f"cli_origem_cliente_{edit_id}")
        cli_obs = st.text_area("Observações internas (opcional)", value=cliente_edicao.get("observacoes", "") if cliente_edicao else "", key=f"cli_obs_{edit_id}")
        st.caption("Somente o nome/identificação é necessário. Papéis, políticas e dados de fornecedor podem ser completados aos poucos.")
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
        if ac1.button("💾 Salvar relacionamento", type="primary", use_container_width=True):
            if not cli_nome.strip():
                st.warning("Informe o nome ou a identificação do relacionamento.")
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
                    "papeis": cli_papeis or ["Cliente"],
                    "classificacao_relacionamento": cli_classificacao,
                    "politica_atendimento": {
                        "nivel": cli_nivel_atendimento,
                        "motivo": cli_motivo_restricao.strip(),
                        "permitir_resposta": cli_permitir_resposta,
                        "permitir_catalogo": cli_permitir_catalogo,
                        "permitir_orcamento": cli_permitir_orcamento,
                        "permitir_campanhas": cli_permitir_campanhas,
                        "exigir_pagamento_antecipado": cli_pagamento_antecipado,
                        "exigir_aprovacao_gestor": cli_aprovacao_gestor,
                    },
                    "fornecedor": {
                        "materiais": cli_forn_materiais.strip(),
                        "contato_comercial": cli_forn_contato.strip(),
                        "prioridade": cli_forn_prioridade,
                        "prazo_medio": cli_forn_prazo.strip(),
                        "avaliacao": cli_forn_avaliacao,
                        "observacoes": cli_forn_obs.strip(),
                    },
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
                st.success("Relacionamento salvo.")
                st.rerun()
        if cliente_edicao and ac2.button("Cancelar edição", use_container_width=True):
            st.session_state.cliente_edit_id = None
            st.rerun()



if pagina_atual == "memoria":
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
            st.info(f"🎯 **Próxima ação:** {proxima_acao_projeto(projeto)}")
            timeline_projeto = projeto.get("timeline", []) if isinstance(projeto.get("timeline"), list) else []
            if timeline_projeto:
                with st.expander("🕒 Linha do tempo do projeto"):
                    for evento in reversed(timeline_projeto[-20:]):
                        st.write(f"**{evento.get('data', '—')}** · {evento.get('descricao', 'Atualização')}")
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



if pagina_atual == "conhecimento":
    renderizar_base_conhecimento()


if pagina_atual == "calendario":
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
                if x3.button("🗑️ Mover para lixeira", key=f"camp_del_{campanha.get('id')}", use_container_width=True):
                    enviar_para_lixeira("Campanha", campanha, campanha.get("id") or campanha.get("nome", ""))
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




def _secret_valor(nome):
    try:
        valor = st.secrets.get(nome, "")
    except Exception:
        valor = os.getenv(nome, "")
    return str(valor or "").strip()


def _secret_configurado(nome):
    return bool(_secret_valor(nome))


def carregar_status_integracoes():
    dados = load_document("integracoes_db", ARQUIVO_INTEGRACOES, {})
    return dados if isinstance(dados, dict) else {}


def salvar_status_integracoes(dados):
    save_document("integracoes_db", dados if isinstance(dados, dict) else {}, ARQUIVO_INTEGRACOES)


def _status_integracao(chave, nome, obrigatorios, observacao="", opcionais=None):
    presentes = [campo for campo in obrigatorios if _secret_configurado(campo)]
    opcionais = opcionais or []
    total = len(obrigatorios)
    if total and len(presentes) == total:
        status, icone = "Configurado", "🟢"
    elif presentes:
        status, icone = "Incompleto", "🟡"
    else:
        status, icone = "Não configurado", "⚪"
    return {
        "chave": chave, "nome": nome, "status": status, "icone": icone,
        "detalhe": observacao, "faltando": [c for c in obrigatorios if c not in presentes],
        "opcionais_faltando": [c for c in opcionais if not _secret_configurado(c)],
    }


def _testar_integracao(chave):
    """Executa um teste leve, sem publicar, enviar mensagens ou alterar dados externos."""
    try:
        if chave == "openai":
            if OpenAI is None:
                return False, "Biblioteca OpenAI não instalada."
            client = OpenAI(api_key=_secret_valor("OPENAI_API_KEY"))
            modelos = client.models.list()
            return True, f"Conexão confirmada. {len(list(modelos.data))} modelo(s) acessível(is)."
        if chave == "meta":
            page_id, token = _secret_valor("META_PAGE_ID"), _secret_valor("META_ACCESS_TOKEN")
            r = requests.get(f"https://graph.facebook.com/v21.0/{page_id}", params={"fields":"id,name", "access_token":token}, timeout=15)
            r.raise_for_status(); data=r.json()
            return True, f"Página conectada: {data.get('name', data.get('id','Meta'))}."
        if chave == "instagram":
            account, token = _secret_valor("INSTAGRAM_ACCOUNT_ID"), _secret_valor("META_ACCESS_TOKEN")
            r = requests.get(f"https://graph.facebook.com/v21.0/{account}", params={"fields":"id,username,name", "access_token":token}, timeout=15)
            r.raise_for_status(); data=r.json()
            return True, f"Instagram conectado: @{data.get('username','conta profissional')}."
        if chave == "whatsapp":
            phone_id, token = _secret_valor("WHATSAPP_PHONE_NUMBER_ID"), _secret_valor("META_ACCESS_TOKEN")
            r = requests.get(f"https://graph.facebook.com/v21.0/{phone_id}", params={"fields":"display_phone_number,verified_name", "access_token":token}, timeout=15)
            r.raise_for_status(); data=r.json()
            return True, f"WhatsApp conectado: {data.get('verified_name','')} {data.get('display_phone_number','')}.".strip()
        if chave == "youtube":
            if not _secret_configurado("YOUTUBE_REFRESH_TOKEN"):
                return False, "Cliente OAuth criado, mas ainda falta autorizar o canal e salvar YOUTUBE_REFRESH_TOKEN."
            payload = {"client_id":_secret_valor("YOUTUBE_CLIENT_ID"), "client_secret":_secret_valor("YOUTUBE_CLIENT_SECRET"), "refresh_token":_secret_valor("YOUTUBE_REFRESH_TOKEN"), "grant_type":"refresh_token"}
            r = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=15)
            r.raise_for_status()
            return True, "OAuth do YouTube renovado com sucesso."
        if chave == "tiktok":
            return False, "Credenciais básicas presentes; teste completo ficará disponível após a revisão do aplicativo TikTok."
        return False, "Integração desconhecida."
    except Exception as exc:
        mensagem = str(exc)
        if len(mensagem) > 240:
            mensagem = mensagem[:237] + "..."
        return False, mensagem


def renderizar_alpha_connect():
    st.subheader("🔗 Alpha Connect Pro")
    st.caption("Diagnóstico seguro das integrações. Nenhuma chave secreta é exibida e os testes não publicam conteúdo.")
    integracoes = [
        _status_integracao("openai", "OpenAI", ["OPENAI_API_KEY"], "Textos comerciais e análise visual.", ["OPENAI_MODEL"]),
        _status_integracao("meta", "Meta / Facebook", ["META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_PAGE_ID"], "Página e publicação pela Meta Graph API."),
        _status_integracao("instagram", "Instagram", ["META_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"], "Conta profissional vinculada à Página."),
        _status_integracao("whatsapp", "WhatsApp Business", ["META_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_BUSINESS_ACCOUNT_ID"], "Mensagens pela plataforma oficial."),
        _status_integracao("youtube", "YouTube", ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"], "OAuth do canal para vídeos e Shorts.", ["YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CHANNEL_ID"]),
        _status_integracao("tiktok", "TikTok", ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"], "Pendente até concluir a revisão do aplicativo."),
    ]
    historico = carregar_status_integracoes()
    cols = st.columns(2)
    for indice, item in enumerate(integracoes):
        with cols[indice % 2].container(border=True):
            st.markdown(f"### {item['icone']} {item['nome']}")
            st.write(f"**Status:** {item['status']}")
            st.caption(item["detalhe"])
            if item["faltando"]:
                st.caption("Faltando: " + ", ".join(item["faltando"]))
            ultimo = historico.get(item["chave"], {}) if isinstance(historico, dict) else {}
            if ultimo:
                selo = "✅" if ultimo.get("ok") else "⚠️"
                st.caption(f"{selo} Último teste: {ultimo.get('quando','—')} — {ultimo.get('mensagem','')}")
            pode_testar = item["status"] == "Configurado" and pode_executar_acoes_tecnicas()
            if usuario_em_operacao_protegida():
                st.caption("🛡️ Testes técnicos bloqueados no modo de atendimento.")
            if st.button("🧪 Testar conexão", key=f"teste_connect_{item['chave']}", use_container_width=True, disabled=not pode_testar):
                with st.spinner(f"Testando {item['nome']}..."):
                    ok, mensagem = _testar_integracao(item["chave"])
                historico[item["chave"]] = {"ok": ok, "mensagem": mensagem, "quando": agora_local().strftime("%d/%m/%Y %H:%M"), "usuario": obter_usuario_atual().get("nome", "Equipe")}
                salvar_status_integracoes(historico)
                (st.success if ok else st.warning)(mensagem)
                st.rerun()
    st.info("Credencial configurada não significa permissão de publicação. A publicação será habilitada somente após OAuth, permissões e teste específico do canal.")


if pagina_atual == "configuracoes":
    st.header("⚙️ Configurações e Integrações")
    aba_cfg_empresa, aba_cfg_connect, aba_cfg_usuarios, aba_cfg_thu = st.tabs(["🏢 Empresa", "🔗 Alpha Connect", "👥 Usuários e permissões", "🎓 Orientações do THU"])
    with aba_cfg_connect:
        renderizar_alpha_connect()
    with aba_cfg_thu:
        renderizar_configuracoes_orientacoes_thu()
    with aba_cfg_usuarios:
        if not pode_executar_acoes_tecnicas():
            st.warning("Somente o Jorge pode alterar usuários e permissões.")
        else:
            st.subheader("👥 Ambiente de trabalho por usuário")
            st.caption("O perfil define o ponto de partida. Você pode acrescentar ou retirar abas e ações sem apagar dados nem alterar o sistema da outra pessoa.")
            dados_usuarios = carregar_config_usuarios()
            usuarios_cfg = dados_usuarios.setdefault("usuarios", {})
            opcoes_email = list(usuarios_cfg.keys())
            email_edicao = st.selectbox(
                "Usuário",
                opcoes_email,
                format_func=lambda e: f"{usuarios_cfg[e].get('nome', e)} — {e}",
                key="permissoes_usuario_email",
            )
            cfg_usuario = usuarios_cfg[email_edicao]
            p1, p2 = st.columns(2)
            nome_perfil = p1.text_input("Nome", value=str(cfg_usuario.get("nome", "")), key="permissoes_nome")
            perfil_nome = p2.selectbox("Perfil base", ["Operacional", "Administrador", "Produção", "Financeiro", "Personalizado"], index=["Operacional", "Administrador", "Produção", "Financeiro", "Personalizado"].index(cfg_usuario.get("perfil", "Personalizado")) if cfg_usuario.get("perfil") in ["Operacional", "Administrador", "Produção", "Financeiro", "Personalizado"] else 4, key="permissoes_perfil")

            st.markdown("#### Abas visíveis")
            abas_atuais = set(cfg_usuario.get("abas", []))
            selecionadas = []
            cols = st.columns(3)
            for idx, (chave, rotulo) in enumerate(ABAS_SISTEMA):
                if cols[idx % 3].checkbox(rotulo, value=chave in abas_atuais, key=f"perm_aba_{email_edicao}_{chave}"):
                    selecionadas.append(chave)

            st.markdown("#### Favoritos da tela inicial")
            favoritos = st.multiselect(
                "Aparecem em destaque no painel do usuário",
                options=selecionadas,
                default=[x for x in cfg_usuario.get("favoritos", []) if x in selecionadas],
                format_func=lambda ch: dict(ABAS_SISTEMA).get(ch, ch),
                key=f"perm_favoritos_{email_edicao}",
            )

            st.markdown("#### Ações permitidas por aba")
            st.caption("Visualizar é o mínimo. Para acesso somente de acompanhamento, marque apenas Visualizar.")
            acoes_novas = {}
            for chave in selecionadas:
                with st.expander(dict(ABAS_SISTEMA).get(chave, chave), expanded=chave in ("atendimento", "novo_orcamento", "catalogo")):
                    atuais = set((cfg_usuario.get("acoes") or {}).get(chave, []))
                    escolhidas = st.multiselect(
                        "Permissões",
                        options=ACOES_PADRAO,
                        default=[a for a in ACOES_PADRAO if a in atuais] or ["visualizar"],
                        key=f"perm_acoes_{email_edicao}_{chave}",
                    )
                    acoes_novas[chave] = escolhidas

            if st.button("💾 Salvar ambiente deste usuário", type="primary", use_container_width=True, key="salvar_permissoes_usuario"):
                cfg_usuario.update({"nome": nome_perfil.strip() or cfg_usuario.get("nome", "Usuário"), "perfil": perfil_nome, "abas": selecionadas, "acoes": acoes_novas, "favoritos": favoritos})
                usuarios_cfg[email_edicao] = cfg_usuario
                salvar_config_usuarios(dados_usuarios)
                st.success("Permissões salvas. O menu será atualizado no próximo acesso ou após recarregar a página.")
                st.rerun()

            st.divider()
            st.markdown("#### Adicionar outro colaborador")
            n1, n2 = st.columns(2)
            novo_email = n1.text_input("E-mail do novo usuário", key="novo_usuario_email").strip().lower()
            novo_nome = n2.text_input("Nome do novo usuário", key="novo_usuario_nome").strip()
            if st.button("➕ Criar usuário operacional", use_container_width=True, key="criar_novo_usuario"):
                if not novo_email or "@" not in novo_email:
                    st.warning("Informe um e-mail válido.")
                elif novo_email in usuarios_cfg:
                    st.warning("Esse e-mail já está cadastrado.")
                else:
                    usuarios_cfg[novo_email] = {
                        "nome": novo_nome or novo_email.split("@")[0].title(),
                        "perfil": "Operacional",
                        "abas": sorted(PERMISSOES_PADRAO_ANNA),
                        "acoes": {ch: ["visualizar", "criar", "editar"] for ch in PERMISSOES_PADRAO_ANNA},
                        "favoritos": ["atendimento", "novo_orcamento"],
                    }
                    salvar_config_usuarios(dados_usuarios)
                    st.success("Usuário criado. Depois configure o login/OIDC para esse e-mail.")
                    st.rerun()
    with aba_cfg_empresa:
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

        st.divider()
        st.header("🛡️ Proteção de Dados")
        st.caption("Atualizações trocam o código, mas não substituem os dados salvos. O backup automático cria pontos de recuperação sem depender da memória da equipe.")
        cfg_backup = carregar_config_backup()
        with st.form("form_config_backup"):
            b1, b2, b3 = st.columns(3)
            backup_ativo = b1.checkbox("Backup automático ativo", value=bool(cfg_backup.get("ativo", True)))
            horario_backup = b2.text_input("Horário diário", value=str(cfg_backup.get("horario", "22:00")), help="Formato HH:MM. Se o sistema estiver fechado, o backup será feito no primeiro acesso após esse horário.")
            retencao_backup = b3.number_input("Backups automáticos mantidos", min_value=1, max_value=365, value=int(cfg_backup.get("retencao_automatica", 30) or 30))
            salvar_backup_cfg = st.form_submit_button("💾 Salvar rotina de backup", use_container_width=True)
        if salvar_backup_cfg:
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", horario_backup.strip()):
                st.warning("Informe o horário no formato HH:MM, por exemplo 22:00.")
            else:
                cfg_backup.update({"ativo": backup_ativo, "horario": horario_backup.strip(), "retencao_automatica": int(retencao_backup), "versao_dados": VERSAO_DADOS})
                salvar_config_backup(cfg_backup)
                st.success("Rotina de backup salva.")

        ultimo_backup = str(cfg_backup.get("ultimo_backup_em", "")).strip()
        if ultimo_backup:
            try:
                ultimo_fmt = datetime.fromisoformat(ultimo_backup).astimezone(agora_local().tzinfo).strftime("%d/%m/%Y às %H:%M")
            except Exception:
                ultimo_fmt = ultimo_backup
            st.success(f"🟢 Proteção ativa — último backup: {ultimo_fmt}")
        else:
            st.warning("Ainda não existe backup completo registrado. Faça o primeiro backup agora.")

        problemas_integridade, contagens_integridade = verificar_integridade_dados()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Propostas", contagens_integridade.get("historico_orcamentos", 0))
        c2.metric("Clientes", contagens_integridade.get("clientes_db", 0))
        c3.metric("Produtos", contagens_integridade.get("catalogo_db", 0))
        c4.metric("Atendimentos", contagens_integridade.get("atendimentos_db", 0))
        ac1, ac2 = st.columns(2)
        if ac1.button("🛡️ Fazer backup completo agora", type="primary", use_container_width=True):
            try:
                novo_backup = criar_backup_completo(tipo="manual", protegido=True, motivo="Backup manual solicitado pela equipe")
                st.session_state._backup_download_id = novo_backup["backup_id"]
                st.success("Backup completo criado e protegido.")
            except Exception as exc:
                st.error(f"Falha ao criar backup: {exc}")
        if ac2.button("🔎 Verificar integridade dos dados", use_container_width=True):
            if problemas_integridade:
                for problema in problemas_integridade:
                    st.error(problema)
            else:
                st.success("Integridade verificada: todas as estruturas principais estão válidas.")

        indice_backups = carregar_indice_backups()
        if indice_backups:
            st.subheader("Histórico de backups")
            opcoes_backup = {f"{item.get('criado_em','')} — {item.get('tipo','')} — {'🔒 protegido' if item.get('protegido') else 'normal'}": item.get("backup_id") for item in indice_backups[:100]}
            escolha_backup = st.selectbox("Selecione um backup", list(opcoes_backup.keys()), key="backup_historico_select")
            backup_selecionado = carregar_backup_por_id(opcoes_backup[escolha_backup])
            if backup_selecionado:
                st.json({k: v for k, v in backup_selecionado.items() if k != "documentos"}, expanded=False)
                d1, d2 = st.columns(2)
                d1.download_button("⬇️ Baixar cópia ZIP", data=backup_para_zip_bytes(backup_selecionado), file_name=f"festmanager_backup_{backup_selecionado.get('backup_id','')}.zip", mime="application/zip", use_container_width=True)
                confirmacao = d2.text_input("Para restaurar, digite RESTAURAR", key=f"confirmar_restauracao_{backup_selecionado.get('backup_id')}")
                if st.button("♻️ Restaurar backup selecionado", disabled=confirmacao.strip().upper() != "RESTAURAR", use_container_width=True):
                    try:
                        restaurados = restaurar_backup_payload(backup_selecionado)
                        st.success(f"Restauração concluída. Documentos restaurados: {len(restaurados)}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Falha na restauração: {exc}")
        else:
            st.info("O histórico aparecerá depois do primeiro backup.")



        st.divider()
        st.header("🏭 Núcleo Profissional")
        st.caption("Migrações seguras, auditoria, lixeira e diagnóstico para manter o FestManager em produção sem perder dados.")
        tab_diag, tab_boot, tab_audit, tab_lix, tab_update = st.tabs(["🩺 Saúde do sistema", "🚦 Boot Manager", "🧾 Auditoria", "🗑️ Lixeira", "🔄 Atualização segura"])

        with tab_diag:
            diag = diagnostico_sistema()
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Supabase", "🟢 Online" if diag["supabase_ok"] else "🟡 Contingência")
            d2.metric("Integridade", "🟢 OK" if diag["integridade_ok"] else "🔴 Atenção")
            d3.metric("Backup", "🟢 Atual" if diag["backup_ok"] else "🟡 Verificar")
            d4.metric("Estrutura de dados", f"v{diag['schema_version']}")
            st.caption(diag["supabase_mensagem"])
            if diag["backup_idade_horas"] is not None:
                st.caption(f"Último backup há aproximadamente {diag['backup_idade_horas']:.1f} hora(s).")
            if diag["problemas"]:
                for problema in diag["problemas"]:
                    st.error(problema)
            else:
                st.success("Estruturas principais válidas.")
            st.write(f"Registros de auditoria: **{diag['auditorias']}** • Itens recuperáveis na lixeira: **{diag['lixeira']}**")
            if st.button("🔄 Executar diagnóstico novamente", key="health_refresh", use_container_width=True):
                st.rerun()

        with tab_boot:
            st.subheader("🚦 Boot Manager 14.2.5")
            st.caption("Diagnóstico exclusivo da Central do Jorge. Nenhuma configuração da Central da Anna é alterada.")
            registros_boot = diagnostico_boot_1424()
            linhas_boot = []
            for nome_etapa, info_etapa in registros_boot.items():
                status_etapa = str(info_etapa.get("status", "ok"))
                icone = "🟢" if status_etapa == "ok" else ("🟡" if status_etapa in {"contingencia", "isolado"} else "🔴")
                linhas_boot.append({
                    "Etapa": nome_etapa,
                    "Estado": f"{icone} {status_etapa}",
                    "Tempo (s)": round(float(info_etapa.get("duracao", 0.0) or 0.0), 3),
                    "Detalhe": str(info_etapa.get("detalhe", "")),
                })
            st.dataframe(pd.DataFrame(linhas_boot), use_container_width=True, hide_index=True)
            flags_boot = feature_flags()
            st.markdown("#### Chaves de segurança")
            st.json(flags_boot, expanded=False)
            st.info("Preview, IA e Campanha Mestre permanecem desligados até homologação na Central do Jorge.")
            if st.button("🔄 Atualizar diagnóstico do boot", key="boot1424_refresh", use_container_width=True):
                st.rerun()

        with tab_audit:
            auditoria = carregar_auditoria()
            if not auditoria:
                st.info("A auditoria começará a registrar backups, migrações, exclusões e restaurações.")
            else:
                filtro_acao = st.text_input("Filtrar auditoria", placeholder="Usuário, ação, entidade ou identificador", key="audit_filter").strip().casefold()
                exibidos = []
                for reg in auditoria:
                    texto = " ".join(str(reg.get(k, "")) for k in ["usuario", "acao", "entidade", "identificador", "resultado"]).casefold()
                    if not filtro_acao or filtro_acao in texto:
                        exibidos.append(reg)
                linhas = []
                for reg in exibidos[:500]:
                    try:
                        data_fmt = datetime.fromisoformat(reg.get("data_hora", "")).astimezone(agora_local().tzinfo).strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        data_fmt = reg.get("data_hora", "")
                    linhas.append({"Data": data_fmt, "Usuário": reg.get("usuario"), "Ação": reg.get("acao"), "Entidade": reg.get("entidade"), "Identificador": reg.get("identificador"), "Resultado": reg.get("resultado")})
                st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
                st.download_button("⬇️ Exportar auditoria JSON", json.dumps(auditoria, ensure_ascii=False, indent=2), file_name=f"auditoria_festmanager_{hoje_local().isoformat()}.json", mime="application/json", use_container_width=True)

        with tab_lix:
            lixeira = carregar_lixeira()
            if not lixeira:
                st.success("A lixeira está vazia.")
            else:
                st.warning(f"{len(lixeira)} item(ns) podem ser restaurados. A remoção definitiva exige confirmação.")
                for reg in lixeira[:200]:
                    try:
                        dt_fmt = datetime.fromisoformat(reg.get("excluido_em", "")).astimezone(agora_local().tzinfo).strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        dt_fmt = reg.get("excluido_em", "")
                    with st.expander(f"{reg.get('tipo')} — {reg.get('identificador') or 'sem identificação'} — {dt_fmt}"):
                        st.caption(f"Movido por: {reg.get('excluido_por', 'Não informado')}")
                        st.json(reg.get("item", {}), expanded=False)
                        r1, r2 = st.columns(2)
                        if r1.button("♻️ Restaurar", key=f"lix_restore_{reg.get('id_lixeira')}", use_container_width=True):
                            try:
                                restaurar_item_lixeira(reg)
                                st.success("Item restaurado.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Não foi possível restaurar: {exc}")
                        confirm = r2.checkbox("Confirmar remoção definitiva", key=f"lix_confirm_{reg.get('id_lixeira')}")
                        if st.button("❌ Remover definitivamente", key=f"lix_purge_{reg.get('id_lixeira')}", disabled=not confirm, use_container_width=True):
                            remover_da_lixeira(reg.get("id_lixeira"))
                            registrar_auditoria("Remover definitivamente", reg.get("tipo", "Item"), reg.get("identificador", ""))
                            st.rerun()

        with tab_update:
            st.info("Antes de publicar uma nova versão, gere um ponto de restauração e anote as contagens. O pacote de atualização deve conter somente código e migrações, nunca os dados da empresa.")
            diag_pre = diagnostico_sistema()
            st.json({
                "versao_app": VERSAO_APP,
                "versao_dados": VERSAO_DADOS,
                "contagens_antes_atualizacao": diag_pre["contagens"],
                "supabase": diag_pre["supabase_mensagem"],
                "integridade": "OK" if diag_pre["integridade_ok"] else diag_pre["problemas"],
            }, expanded=False)
            if st.button("🛡️ Preparar atualização segura", type="primary", key="preparar_update_seguro", use_container_width=True):
                try:
                    bk = criar_backup_completo(tipo="antes_atualizacao", protegido=True, motivo=f"Ponto de restauração antes de atualizar a partir da versão {VERSAO_APP}")
                    registrar_auditoria("Preparar atualização", "Sistema", VERSAO_APP, {"backup_id": bk.get("backup_id"), "contagens": bk.get("contagens")})
                    st.success(f"Atualização preparada. Backup protegido: {bk.get('backup_id')}")
                    st.download_button("⬇️ Baixar ponto de restauração", data=backup_para_zip_bytes(bk), file_name=f"antes_atualizacao_{bk.get('backup_id')}.zip", mime="application/zip", use_container_width=True)
                except Exception as exc:
                    st.error(f"Falha ao preparar atualização: {exc}")


        st.caption(f"Versão do aplicativo: {VERSAO_APP} • Versão dos dados: {VERSAO_DADOS}")
