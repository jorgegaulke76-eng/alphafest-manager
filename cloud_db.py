"""Persistência gratuita no Supabase com fallback automático para JSON local.

A aplicação usa uma única tabela ``app_data`` para guardar documentos JSON.
Isso preserva a estrutura atual do sistema e facilita a migração dos arquivos
historico_orcamentos.json e catalogo_db.json sem perda de campos.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import streamlit as st

TIMEOUT = 20


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
    if not online_configured():
        return _read_local(local_path, default)

    url, _ = _config()
    try:
        response = requests.get(
            f"{url}/rest/v1/app_data",
            headers=_headers(),
            params={"select": "value", "key": f"eq.{document_key}", "limit": "1"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json()
        if rows:
            value = rows[0].get("value", default)
            return value if value is not None else default

        local_value = _read_local(local_path, default)
        save_document(document_key, local_value, local_path)
        return local_value
    except (requests.RequestException, ValueError, TypeError):
        return _read_local(local_path, default)


def save_document(document_key: str, value: Any, local_path: str) -> bool:
    """Salva online e mantém uma cópia JSON local como contingência."""
    try:
        _write_local(local_path, value)
    except OSError:
        pass

    if not online_configured():
        return False

    url, _ = _config()
    payload = {
        "key": document_key,
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        response = requests.post(
            f"{url}/rest/v1/app_data",
            headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
            params={"on_conflict": "key"},
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def connection_test() -> tuple[bool, str]:
    if not online_configured():
        return False, "Supabase não configurado — usando arquivos JSON locais."
    url, _ = _config()
    try:
        response = requests.get(
            f"{url}/rest/v1/app_data",
            headers=_headers(),
            params={"select": "key", "limit": "1"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return True, "Banco online conectado."
    except requests.RequestException as exc:
        return False, f"Sem conexão com o banco online ({exc.__class__.__name__}). Usando cópia local."


def upload_catalog_image(upload: Any, local_upload_dir: str = "uploads") -> str:
    """Envia imagem ao bucket público ``catalogo``; usa arquivo local como fallback."""
    if upload is None:
        return ""

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", str(upload.name))
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    content = bytes(upload.getbuffer())
    content_type = getattr(upload, "type", None) or "application/octet-stream"

    if online_configured():
        url, _ = _config()
        encoded_name = quote(unique_name, safe="")
        try:
            response = requests.post(
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
        except requests.RequestException:
            pass

    Path(local_upload_dir).mkdir(parents=True, exist_ok=True)
    local_path = Path(local_upload_dir) / unique_name
    local_path.write_bytes(content)
    return str(local_path).replace("\\", "/")
