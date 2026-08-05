"""Persistência gratuita no Supabase com fallback automático para JSON local.

A aplicação usa uma única tabela ``app_data`` para guardar documentos JSON.
Isso preserva a estrutura atual do sistema e facilita a migração dos arquivos
historico_orcamentos.json e catalogo_db.json sem perda de campos.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import streamlit as st

# Hotfix 14.2.3a: falha rápida e contingência local.
# O timeout separado limita conexão e leitura sem deixar a interface em branco.
TIMEOUT = (2, 3)
CIRCUIT_BREAKER_SECONDS = 120
_SESSION = requests.Session()
_ONLINE_SUSPENDED_UNTIL = 0.0
_LAST_ONLINE_ERROR = ""


def _online_temporariamente_suspenso() -> bool:
    return time.monotonic() < _ONLINE_SUSPENDED_UNTIL


def _suspender_online(exc: Exception | None = None) -> None:
    global _ONLINE_SUSPENDED_UNTIL, _LAST_ONLINE_ERROR
    _ONLINE_SUSPENDED_UNTIL = time.monotonic() + CIRCUIT_BREAKER_SECONDS
    _LAST_ONLINE_ERROR = type(exc).__name__ if exc is not None else "Falha de conexão"


def _reativar_online() -> None:
    global _ONLINE_SUSPENDED_UNTIL, _LAST_ONLINE_ERROR
    _ONLINE_SUSPENDED_UNTIL = 0.0
    _LAST_ONLINE_ERROR = ""


__all__ = [
    "online_configured",
    "connection_test",
    "load_document",
    "save_document",
    "upload_catalog_image",
    "upload_library_file",
]


def _config() -> tuple[str, str]:
    url = ""
    key = ""
    try:
        url = str(st.secrets.get("SUPABASE_URL", "")).strip()
        key = str(st.secrets.get("SUPABASE_KEY", "")).strip()
    except Exception:
        pass
    url = url or os.getenv("SUPABASE_URL", "").strip()
    key = key or os.getenv("SUPABASE_KEY", "").strip()
    return url.rstrip("/"), key


def online_configured() -> bool:
    url, key = _config()
    return bool(url and key)


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    _, key = _config()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _read_local(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _write_local(path: str, value: Any) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=4)


def load_document(document_key: str, local_path: str, default: Any) -> Any:
    """Carrega do Supabase; se vazio, importa automaticamente o JSON local."""
    if not online_configured() or _online_temporariamente_suspenso():
        return _read_local(local_path, default)

    url, _ = _config()
    try:
        response = _SESSION.get(
            f"{url}/rest/v1/app_data",
            headers=_headers(),
            params={"select": "value", "key": f"eq.{document_key}", "limit": "1"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        _reativar_online()
        rows = response.json()
        if rows:
            value = rows[0].get("value", default)
            return value if value is not None else default

        local_value = _read_local(local_path, default)
        save_document(document_key, local_value, local_path)
        return local_value
    except (requests.RequestException, ValueError, TypeError) as exc:
        _suspender_online(exc)
        return _read_local(local_path, default)


def save_document(document_key: str, value: Any, local_path: str) -> bool:
    """Salva online e mantém uma cópia JSON local como contingência."""
    try:
        _write_local(local_path, value)
    except OSError:
        pass

    if not online_configured() or _online_temporariamente_suspenso():
        return False

    url, _ = _config()
    payload = {
        "key": document_key,
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        response = _SESSION.post(
            f"{url}/rest/v1/app_data",
            headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
            params={"on_conflict": "key"},
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        _reativar_online()
        return True
    except requests.RequestException as exc:
        _suspender_online(exc)
        return False


def connection_test() -> tuple[bool, str]:
    if not online_configured():
        return False, "Supabase não configurado — usando arquivos JSON locais."
    if _online_temporariamente_suspenso():
        detalhe = _LAST_ONLINE_ERROR or "falha recente"
        return False, f"Modo local protegido ativo ({detalhe}). Nova tentativa automática em instantes."
    url, _ = _config()
    try:
        response = _SESSION.get(
            f"{url}/rest/v1/app_data",
            headers=_headers(),
            params={"select": "key", "limit": "1"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        _reativar_online()
        return True, "Banco online conectado."
    except requests.RequestException as exc:
        _suspender_online(exc)
        return False, f"Modo local protegido ativo ({exc.__class__.__name__}). Os dados locais continuam disponíveis."


def upload_catalog_image(upload: Any, local_upload_dir: str = "uploads") -> str:
    """Envia imagem ao bucket público ``catalogo``; usa arquivo local como fallback."""
    if upload is None:
        return ""

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", str(upload.name))
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    content = bytes(upload.getbuffer())
    content_type = getattr(upload, "type", None) or "application/octet-stream"

    if online_configured() and not _online_temporariamente_suspenso():
        url, _ = _config()
        encoded_name = quote(unique_name, safe="")
        try:
            response = _SESSION.post(
                f"{url}/storage/v1/object/catalogo/{encoded_name}",
                headers={
                    **_headers(),
                    "Content-Type": content_type,
                    "x-upsert": "false",
                },
                data=content,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            return f"{url}/storage/v1/object/public/catalogo/{encoded_name}"
        except requests.RequestException as exc:
            _suspender_online(exc)

    Path(local_upload_dir).mkdir(parents=True, exist_ok=True)
    local_path = Path(local_upload_dir) / unique_name
    local_path.write_bytes(content)
    return str(local_path).replace("\\", "/")


def upload_library_file(upload: Any, produto_nome: str = "produto", local_upload_dir: str = "biblioteca_uploads") -> str:
    """Envia qualquer arquivo da memória do produto ao bucket público ``catalogo``.

    Usa uma subpasta ``biblioteca/<produto>`` e mantém fallback local.
    """
    if upload is None:
        return ""

    produto_seguro = re.sub(r"[^A-Za-z0-9._-]", "_", str(produto_nome).strip()) or "produto"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", str(upload.name))
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    object_path = f"biblioteca/{produto_seguro}/{unique_name}"
    content = bytes(upload.getbuffer())
    content_type = getattr(upload, "type", None) or "application/octet-stream"

    if online_configured() and not _online_temporariamente_suspenso():
        url, _ = _config()
        encoded_path = quote(object_path, safe="/")
        try:
            response = _SESSION.post(
                f"{url}/storage/v1/object/catalogo/{encoded_path}",
                headers={
                    **_headers(),
                    "Content-Type": content_type,
                    "x-upsert": "false",
                },
                data=content,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            return f"{url}/storage/v1/object/public/catalogo/{encoded_path}"
        except requests.RequestException as exc:
            _suspender_online(exc)

    local_dir = Path(local_upload_dir) / produto_seguro
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / unique_name
    local_path.write_bytes(content)
    return str(local_path).replace("\\", "/")
