"""Presença operacional leve e compartilhada do AlphaFest Center Innovation.

Registra somente contexto de trabalho (tela/ação), nunca o conteúdo digitado.
Os dados são compartilhados pelo mesmo documento do Supabase usado pelo app.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import secrets

import streamlit as st

try:
    from cloud_db import load_document, save_document
except Exception:  # fallback resiliente
    load_document = save_document = None

DOC_KEY = "alpha_live_operacao"
LOCAL_PATH = str(Path(__file__).with_name("alpha_live_operacao.json"))
DEFAULT = {"usuarios": {}, "eventos": []}


def _agora() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


def _carregar() -> dict[str, Any]:
    if load_document is None:
        return dict(DEFAULT)
    dados = load_document(DOC_KEY, LOCAL_PATH, DEFAULT)
    if not isinstance(dados, dict):
        dados = dict(DEFAULT)
    dados.setdefault("usuarios", {})
    dados.setdefault("eventos", [])
    return dados


def _salvar(dados: dict[str, Any]) -> None:
    if save_document is not None:
        save_document(DOC_KEY, dados, LOCAL_PATH)


def session_id() -> str:
    if "_alpha_live_session_id" not in st.session_state:
        st.session_state["_alpha_live_session_id"] = secrets.token_hex(6)
    return str(st.session_state["_alpha_live_session_id"])


def registrar_atividade(usuario: dict[str, Any] | str, acao: str, modulo: str = "", detalhe: str = "", evento: bool = False) -> None:
    """Atualiza presença e, opcionalmente, registra um evento concluído."""
    if isinstance(usuario, dict):
        nome = str(usuario.get("nome") or "Usuário")
        email = str(usuario.get("email") or nome).lower()
    else:
        nome = str(usuario or "Usuário")
        email = nome.lower()

    agora = _agora()
    dados = _carregar()
    chave = f"{email}:{session_id()}"
    dados["usuarios"][chave] = {
        "nome": nome,
        "email": email,
        "sessao": session_id(),
        "acao": str(acao),
        "modulo": str(modulo),
        "detalhe": str(detalhe),
        "atualizado_em": agora.isoformat(),
    }
    if evento:
        dados["eventos"].insert(0, {
            "nome": nome,
            "acao": str(acao),
            "modulo": str(modulo),
            "detalhe": str(detalhe),
            "em": agora.isoformat(),
        })
        dados["eventos"] = dados["eventos"][:80]

    # Remove sessões abandonadas há mais de 24h para o documento não crescer.
    limite = agora - timedelta(hours=24)
    ativos = {}
    for k, item in dados["usuarios"].items():
        try:
            dt = datetime.fromisoformat(str(item.get("atualizado_em", "")))
            if dt.tzinfo is None and agora.tzinfo is not None:
                dt = dt.replace(tzinfo=agora.tzinfo)
            if dt >= limite:
                ativos[k] = item
        except Exception:
            pass
    dados["usuarios"] = ativos
    _salvar(dados)


def obter_operacao_online(expira_segundos: int = 150) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dados = _carregar()
    agora = _agora()
    limite = agora - timedelta(seconds=max(30, int(expira_segundos)))
    online = []
    for item in dados.get("usuarios", {}).values():
        try:
            dt = datetime.fromisoformat(str(item.get("atualizado_em", "")))
            if dt.tzinfo is None and agora.tzinfo is not None:
                dt = dt.replace(tzinfo=agora.tzinfo)
            if dt >= limite:
                copia = dict(item)
                copia["segundos"] = max(0, int((agora - dt).total_seconds()))
                online.append(copia)
        except Exception:
            continue
    online.sort(key=lambda x: (str(x.get("nome")), int(x.get("segundos", 0))))
    eventos = list(dados.get("eventos", []))[:20]
    return online, eventos
