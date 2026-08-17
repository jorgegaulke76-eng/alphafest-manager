"""Persistência gratuita no Supabase com fallback automático para JSON local.

A aplicação usa uma única tabela ``app_data`` para guardar documentos JSON.
Isso preserva a estrutura atual do sistema e facilita a migração dos arquivos
historico_orcamentos.json e catalogo_db.json sem perda de campos.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import streamlit as st

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

TIMEOUT = 10
_SESSION = requests.Session()

# 20.4.9-I8.9.2.1 — hotfix da URL real do Supabase no visualizador público.
# Pode ser sobrescrito por st.secrets/env sem alterar o código.
DEFAULT_CATALOG_VIEWER_URL = "https://jorgegaulke76-eng.github.io/alphafest-catalogos/"

__all__ = [
    "online_configured",
    "connection_test",
    "load_document",
    "save_document",
    "upload_catalog_image",
    "upload_library_file",
    "catalog_public_url",
    "catalog_render_url",
    "catalog_render_available",
    "publish_catalog_html",
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
    if not online_configured():
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
        response = _SESSION.post(
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
        response = _SESSION.get(
            f"{url}/rest/v1/app_data",
            headers=_headers(),
            params={"select": "key", "limit": "1"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return True, "Banco online conectado."
    except requests.RequestException as exc:
        return False, f"Sem conexão com o banco online ({exc.__class__.__name__}). Usando cópia local."


def _catalog_image_data_url(content: bytes, content_type: str = "image/jpeg") -> str:
    """Cria uma representação persistente e compacta para fallback do catálogo.

    O filesystem do Streamlit Cloud é efêmero. Se o Storage do Supabase não
    estiver disponível, guardar apenas um caminho local faz a foto desaparecer
    no próximo restart/deploy. Este fallback grava a imagem dentro do documento
    JSON do catálogo como data URL, reduzindo resolução/peso quando Pillow está
    disponível.
    """
    raw = bytes(content or b"")
    if not raw:
        return ""

    if Image is not None:
        try:
            with Image.open(io.BytesIO(raw)) as img:
                if ImageOps is not None:
                    img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")
                img.thumbnail((1600, 1600))
                out = io.BytesIO()
                img.save(out, format="WEBP", quality=82, method=6)
                raw = out.getvalue()
                content_type = "image/webp"
        except Exception:
            pass

    mime = str(content_type or "image/jpeg").split(";", 1)[0].strip().lower()
    if not mime.startswith("image/"):
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


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
        except requests.RequestException:
            pass

    # IMPORTANTE: não usar caminho local como persistência final no Streamlit
    # Cloud. O disco é efêmero e o cadastro sobreviveria sem a foto.
    return _catalog_image_data_url(content, content_type)


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

    if online_configured():
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
        except requests.RequestException:
            pass

    local_dir = Path(local_upload_dir) / produto_seguro
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / unique_name
    local_path.write_bytes(content)
    return str(local_path).replace("\\", "/")


def catalog_public_url(object_path: str) -> str:
    """Retorna a URL pública determinística de um catálogo no bucket `catalogo`."""
    if not online_configured():
        return ""
    url, _ = _config()
    caminho = str(object_path or "").strip().lstrip("/")
    if not caminho:
        return ""
    return f"{url}/storage/v1/object/public/catalogo/{quote(caminho, safe='/')}"


def _catalog_viewer_url() -> str:
    """Retorna o visualizador público do catálogo.

    O HTML permanece armazenado no Supabase. O GitHub Pages atua somente
    como camada de apresentação, recebendo ``?path=...`` e buscando o objeto
    público do bucket ``catalogo``.
    """
    viewer = ""
    try:
        viewer = str(st.secrets.get("CATALOG_VIEWER_URL", "")).strip()
    except Exception:
        pass
    viewer = viewer or os.getenv("CATALOG_VIEWER_URL", "").strip() or DEFAULT_CATALOG_VIEWER_URL
    return viewer.rstrip("/") + "/" if viewer else ""


def catalog_render_url(object_path: str) -> str:
    """URL que o cliente abre no GitHub Pages (I8.9.2.1).

    Publicações antigas continuam compatíveis porque a URL é reconstruída
    a partir do ``object_path`` já persistido na Central.
    """
    caminho = str(object_path or "").strip().lstrip("/")
    if not caminho:
        return ""
    # Mesma blindagem do visualizador publicado no GitHub Pages: nunca gerar
    # um link para objetos fora da árvore oficial de catálogos públicos.
    if not re.fullmatch(r"catalogos-publicos/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.html", caminho):
        return ""
    viewer = _catalog_viewer_url()
    if not viewer:
        return ""
    # I8.9.2.1: a URL real do Supabase acompanha o link. O visualizador
    # deixa de depender de um project-ref hardcoded e continua validando
    # que a origem pertence ao domínio oficial supabase.co.
    supabase_url, _ = _config()
    if not supabase_url:
        return ""
    return (
        f"{viewer}?path={quote(caminho, safe='')}"
        f"&base={quote(supabase_url.rstrip('/'), safe='')}"
    )


@st.cache_data(ttl=300, show_spinner=False)
def catalog_render_available() -> bool:
    """Indica se o visualizador GitHub Pages I8.9.2.1 está configurado.

    A publicação não fica dependente de um teste de rede a cada rerun do
    Streamlit. O endereço padrão já foi homologado e pode ser substituído por
    ``CATALOG_VIEWER_URL`` em secrets/env se a AlphaFest trocar de domínio.
    """
    viewer = _catalog_viewer_url()
    return bool(viewer and viewer.startswith("https://"))


def publish_catalog_html(content: str | bytes, object_path: str) -> str:
    """Guarda o HTML imutável no Storage e retorna a URL técnica do objeto.

    A URL técnica não deve ser enviada ao cliente, pois o Supabase Storage
    serve HTML como texto puro. Use :func:`catalog_render_url` para a URL de apresentação
    via GitHub Pages que deve ser enviada ao cliente.
    """
    if not online_configured():
        return ""
    caminho = str(object_path or "").strip().lstrip("/")
    if not caminho:
        return ""
    bruto = content.encode("utf-8") if isinstance(content, str) else bytes(content or b"")
    if not bruto:
        return ""
    url, _ = _config()
    encoded_path = quote(caminho, safe="/")
    try:
        response = _SESSION.post(
            f"{url}/storage/v1/object/catalogo/{encoded_path}",
            headers={
                **_headers(),
                "Content-Type": "text/html; charset=utf-8",
                "x-upsert": "false",
            },
            data=bruto,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return catalog_public_url(caminho)
    except requests.RequestException:
        return ""
