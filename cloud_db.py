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
    "credential_mode",
    "connection_test",
    "load_document",
    "save_document",
    "mutate_document",
    "mutate_list_record",
    "append_list_record",
    "upload_catalog_image",
    "upload_library_file",
    "upload_private_3d_file",
    "read_private_3d_file",
    "delete_private_3d_file",
    "catalog_public_url",
    "catalog_render_url",
    "catalog_render_available",
    "publish_catalog_html",
]


def _secret_or_env(name: str) -> str:
    value = ""
    try:
        value = str(st.secrets.get(name, "") or "").strip()
    except Exception:
        pass
    return value or os.getenv(name, "").strip()


def _config() -> tuple[str, str]:
    """Retorna URL e credencial de servidor.

    I8.13.3: quando disponível, ``SUPABASE_SERVICE_KEY`` tem prioridade sobre
    a chave anônima. O Manager roda no servidor do Streamlit, portanto a chave
    de serviço permanece em Secrets e nunca é enviada ao navegador. Isso permite
    fechar escrita anônima no Supabase sem custo adicional.
    """
    url = _secret_or_env("SUPABASE_URL")
    service_key = _secret_or_env("SUPABASE_SERVICE_KEY")
    anon_key = _secret_or_env("SUPABASE_KEY")
    return url.rstrip("/"), service_key or anon_key


def credential_mode() -> str:
    if _secret_or_env("SUPABASE_SERVICE_KEY"):
        return "service"
    if _secret_or_env("SUPABASE_KEY"):
        return "anon"
    return "none"


def online_configured() -> bool:
    url, key = _config()
    return bool(url and key)


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Monta cabeçalhos compatíveis com chaves novas e legadas do Supabase.

    I8.13.3-HF1:
    - ``sb_secret_...`` / ``sb_publishable_...`` são chaves opacas e devem ser
      enviadas em ``apikey``; NÃO podem ser usadas como ``Bearer``.
    - chaves legadas ``anon`` / ``service_role`` são JWTs e continuam usando
      também ``Authorization: Bearer ...`` para compatibilidade.
    """
    _, key = _config()
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }

    # As novas chaves do Supabase (sb_*) não são JWTs. Enviá-las como Bearer
    # provoca HTTP 401 / Invalid JWT. Para chaves legadas JWT, mantemos Bearer.
    if key and not key.startswith(("sb_secret_", "sb_publishable_")):
        headers["Authorization"] = f"Bearer {key}"

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
    """Persiste com confirmação online antes de atualizar a contingência local.

    I8.13.3 — regra de integridade: quando o Supabase está configurado, uma
    falha online NÃO grava primeiro uma versão local mais nova. Isso evita o
    efeito "salvou na tela, mas voltou depois" causado por duas verdades
    diferentes (cache/local x banco). A cópia local só acompanha um write que
    o banco confirmou.

    Sem configuração online, a cópia local ainda é escrita para diagnóstico e
    uso local, porém o retorno permanece ``False`` porque não houve confirmação
    no banco oficial.
    """
    if not online_configured():
        try:
            _write_local(local_path, value)
        except OSError:
            pass
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
    except requests.RequestException:
        return False

    try:
        _write_local(local_path, value)
    except OSError:
        pass
    return True




def mutate_document(document_key: str, local_path: str, default: Any, updater, retries: int = 4):
    """Atualiza um documento inteiro com leitura fresca + compare-and-swap.

    I8.13.4-HF3 — usado para reconciliações determinísticas (como o espelho
    Histórico -> Fluxo) sem sobrescrever silenciosamente uma gravação feita
    por outra sessão entre a leitura e o salvamento. O ``updater`` recebe uma
    cópia do valor mais novo e deve devolver o documento completo reconciliado.

    Retorna ``(ok, documento_atualizado, motivo)``.
    """
    if not callable(updater):
        return False, None, "updater inválido"

    def aplicar(base):
        copia = json.loads(json.dumps(base, ensure_ascii=False))
        novo = updater(copia)
        return copia if novo is None else novo

    if not online_configured():
        atual = _read_local(local_path, default)
        try:
            novo_doc = aplicar(atual)
            _write_local(local_path, novo_doc)
        except (OSError, ValueError, TypeError):
            return False, atual, "falha ao reconciliar contingência local"
        # Sem banco online não há confirmação oficial.
        return False, novo_doc, "contingência local sem confirmação online"

    url, _ = _config()
    ultimo_erro = "conflito de concorrência"
    for _ in range(max(1, int(retries or 1))):
        try:
            leitura = _SESSION.get(
                f"{url}/rest/v1/app_data",
                headers=_headers(),
                params={"select": "value,updated_at", "key": f"eq.{document_key}", "limit": "1"},
                timeout=TIMEOUT,
            )
            leitura.raise_for_status()
            rows = leitura.json()
            if not rows:
                base = _read_local(local_path, default)
                if not save_document(document_key, base, local_path):
                    return False, base, "documento não encontrado"
                continue

            row = rows[0]
            atual = row.get("value", default)
            updated_at = row.get("updated_at")
            novo_doc = aplicar(atual)
            novo_updated_at = datetime.now(timezone.utc).isoformat()
            params = {"key": f"eq.{document_key}", "select": "key"}
            if updated_at:
                params["updated_at"] = f"eq.{updated_at}"
            resposta = _SESSION.patch(
                f"{url}/rest/v1/app_data",
                headers=_headers({"Prefer": "return=representation"}),
                params=params,
                json={"value": novo_doc, "updated_at": novo_updated_at},
                timeout=TIMEOUT,
            )
            resposta.raise_for_status()
            confirmacao = resposta.json()
            if confirmacao:
                try:
                    _write_local(local_path, novo_doc)
                except OSError:
                    pass
                return True, novo_doc, "online"
            ultimo_erro = "conflito detectado; nova tentativa realizada"
        except (requests.RequestException, ValueError, TypeError) as exc:
            ultimo_erro = f"{exc.__class__.__name__}"
    return False, None, ultimo_erro

def append_list_record(document_key: str, local_path: str, default: Any, record: Any, max_items: int = 5000, retries: int = 4):
    """Acrescenta um registro a um documento-lista com compare-and-swap.

    I8.13.4: usado pela auditoria oficial para que duas sessões não percam
    eventos quando Jorge e Anna gravam quase ao mesmo tempo. O registro entra
    no início da lista e o documento é limitado a ``max_items``.

    Retorna ``(ok, documento_atualizado, motivo)``.
    """
    if not isinstance(default, list):
        default = []
    limite = max(1, int(max_items or 1))

    def montar(base):
        atual = base if isinstance(base, list) else []
        copia = json.loads(json.dumps(atual, ensure_ascii=False))
        novo = json.loads(json.dumps(record, ensure_ascii=False))
        return [novo] + copia[: max(0, limite - 1)]

    if not online_configured():
        atual = _read_local(local_path, default)
        novo_doc = montar(atual)
        try:
            _write_local(local_path, novo_doc)
            return True, novo_doc, "local"
        except OSError:
            return False, atual, "falha ao gravar contingência local"

    url, _ = _config()
    ultimo_erro = "conflito de concorrência"
    for _ in range(max(1, int(retries or 1))):
        try:
            leitura = _SESSION.get(
                f"{url}/rest/v1/app_data",
                headers=_headers(),
                params={"select": "value,updated_at", "key": f"eq.{document_key}", "limit": "1"},
                timeout=TIMEOUT,
            )
            leitura.raise_for_status()
            rows = leitura.json()
            if not rows:
                base = _read_local(local_path, default)
                if not save_document(document_key, base, local_path):
                    return False, base, "documento não encontrado"
                continue

            row = rows[0]
            atual = row.get("value", default)
            updated_at = row.get("updated_at")
            novo_doc = montar(atual)
            novo_updated_at = datetime.now(timezone.utc).isoformat()
            params = {"key": f"eq.{document_key}", "select": "key"}
            if updated_at:
                params["updated_at"] = f"eq.{updated_at}"
            resposta = _SESSION.patch(
                f"{url}/rest/v1/app_data",
                headers=_headers({"Prefer": "return=representation"}),
                params=params,
                json={"value": novo_doc, "updated_at": novo_updated_at},
                timeout=TIMEOUT,
            )
            resposta.raise_for_status()
            confirmacao = resposta.json()
            if confirmacao:
                try:
                    _write_local(local_path, novo_doc)
                except OSError:
                    pass
                return True, novo_doc, "online"
            ultimo_erro = "conflito detectado; nova tentativa realizada"
        except (requests.RequestException, ValueError, TypeError) as exc:
            ultimo_erro = f"{exc.__class__.__name__}"
    return False, None, ultimo_erro


def mutate_list_record(document_key: str, local_path: str, default: Any, identity_field: str, identity_value: Any, updater, retries: int = 3):
    """Atualiza um registro dentro de uma lista com leitura fresca e CAS no Supabase.

    Evita que duas sessões (ex.: Jorge e Anna) sobrescrevam silenciosamente o
    documento inteiro a partir de caches diferentes. Em caso de conflito, lê a
    versão mais nova e reaplica somente a alteração do registro-alvo.

    Retorna ``(ok, registro_atualizado, documento_atualizado, motivo)``.
    """
    if not callable(updater):
        return False, None, None, "updater inválido"

    def aplicar(lista):
        if not isinstance(lista, list):
            return None, None
        copia = json.loads(json.dumps(lista, ensure_ascii=False))
        for idx, item in enumerate(copia):
            if isinstance(item, dict) and str(item.get(identity_field)) == str(identity_value):
                alvo = item
                resultado = updater(alvo)
                if isinstance(resultado, dict) and resultado is not alvo:
                    copia[idx] = resultado
                    alvo = resultado
                return copia, alvo
        return None, None

    if not online_configured():
        atual = _read_local(local_path, default)
        novo_doc, alvo = aplicar(atual)
        if novo_doc is None:
            return False, None, atual, "registro não encontrado"
        try:
            _write_local(local_path, novo_doc)
            return True, alvo, novo_doc, "local"
        except OSError:
            return False, None, atual, "falha ao gravar contingência local"

    url, _ = _config()
    ultimo_erro = "conflito de concorrência"
    for _ in range(max(1, int(retries or 1))):
        try:
            leitura = _SESSION.get(
                f"{url}/rest/v1/app_data",
                headers=_headers(),
                params={"select": "value,updated_at", "key": f"eq.{document_key}", "limit": "1"},
                timeout=TIMEOUT,
            )
            leitura.raise_for_status()
            rows = leitura.json()
            if not rows:
                # Mantém compatibilidade com bases ainda não importadas.
                base = _read_local(local_path, default)
                if not save_document(document_key, base, local_path):
                    return False, None, base, "documento não encontrado"
                continue
            row = rows[0]
            atual = row.get("value", default)
            updated_at = row.get("updated_at")
            novo_doc, alvo = aplicar(atual)
            if novo_doc is None:
                return False, None, atual, "registro não encontrado"

            novo_updated_at = datetime.now(timezone.utc).isoformat()
            params = {"key": f"eq.{document_key}", "select": "key"}
            if updated_at:
                params["updated_at"] = f"eq.{updated_at}"
            resposta = _SESSION.patch(
                f"{url}/rest/v1/app_data",
                headers=_headers({"Prefer": "return=representation"}),
                params=params,
                json={"value": novo_doc, "updated_at": novo_updated_at},
                timeout=TIMEOUT,
            )
            resposta.raise_for_status()
            confirmacao = resposta.json()
            if confirmacao:
                try:
                    _write_local(local_path, novo_doc)
                except OSError:
                    pass
                return True, alvo, novo_doc, "online"
            ultimo_erro = "conflito detectado; nova tentativa realizada"
        except (requests.RequestException, ValueError, TypeError) as exc:
            ultimo_erro = f"{exc.__class__.__name__}"
            break

    # Compatibilidade: se PATCH condicional não estiver disponível na política
    # atual do projeto, faz uma última leitura fresca + gravação. Ainda reduz a
    # janela de conflito em relação ao comportamento antigo baseado em cache.
    try:
        atual = load_document(document_key, local_path, default)
        novo_doc, alvo = aplicar(atual)
        if novo_doc is not None and save_document(document_key, novo_doc, local_path):
            return True, alvo, novo_doc, "fallback-fresh"
    except Exception:
        pass
    return False, None, None, ultimo_erro

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



BIBLIOTECA_3D_BUCKET = "biblioteca3d"


def _ensure_private_3d_bucket() -> bool:
    """Garante o bucket privado da Biblioteca 3D.

    O bucket é criado sob demanda. A operação exige a credencial de servidor
    já usada pelo Manager; se ela não tiver permissão, a gravação é abortada
    em vez de cair para disco efêmero.
    """
    if not online_configured():
        return False
    url, _ = _config()
    try:
        response = _SESSION.get(
            f"{url}/storage/v1/bucket/{BIBLIOTECA_3D_BUCKET}",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if response.ok:
            return True
        if response.status_code not in (400, 404):
            return False
        create = _SESSION.post(
            f"{url}/storage/v1/bucket",
            headers=_headers(),
            json={
                "id": BIBLIOTECA_3D_BUCKET,
                "name": BIBLIOTECA_3D_BUCKET,
                "public": False,
            },
            timeout=TIMEOUT,
        )
        return bool(create.ok or create.status_code in (200, 201, 409))
    except requests.RequestException:
        return False


def upload_private_3d_file(upload: Any, folder: str = "modelos") -> str:
    """Salva arquivo da Biblioteca 3D em bucket privado e retorna object path.

    Não existe fallback local: o objetivo desta biblioteca é preservar o
    arquivo. Se a nuvem não confirmar a gravação, retorna vazio e o cadastro
    não deve ser concluído.
    """
    if upload is None or not _ensure_private_3d_bucket():
        return ""

    pasta = re.sub(r"[^A-Za-z0-9._/-]", "_", str(folder or "modelos").strip()).strip("/") or "modelos"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", str(getattr(upload, "name", "arquivo.bin")))
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    object_path = f"{pasta}/{unique_name}"
    content = bytes(upload.getbuffer())
    if not content:
        return ""
    content_type = getattr(upload, "type", None) or "application/octet-stream"
    url, _ = _config()
    encoded_path = quote(object_path, safe="/")
    try:
        response = _SESSION.post(
            f"{url}/storage/v1/object/{BIBLIOTECA_3D_BUCKET}/{encoded_path}",
            headers={**_headers(), "Content-Type": content_type, "x-upsert": "false"},
            data=content,
            timeout=max(TIMEOUT, 45),
        )
        response.raise_for_status()
        return object_path
    except requests.RequestException:
        return ""


def read_private_3d_file(object_path: str) -> bytes | None:
    """Lê um objeto privado da Biblioteca 3D usando a credencial do servidor."""
    caminho = str(object_path or "").strip().lstrip("/")
    if not caminho or not online_configured():
        return None
    url, _ = _config()
    encoded_path = quote(caminho, safe="/")
    try:
        response = _SESSION.get(
            f"{url}/storage/v1/object/{BIBLIOTECA_3D_BUCKET}/{encoded_path}",
            headers=_headers(),
            timeout=max(TIMEOUT, 45),
        )
        response.raise_for_status()
        return bytes(response.content)
    except requests.RequestException:
        return None


def delete_private_3d_file(object_path: str) -> bool:
    """Remove um objeto privado; usado para limpar uploads incompletos."""
    caminho = str(object_path or "").strip().lstrip("/")
    if not caminho or not online_configured():
        return False
    url, _ = _config()
    encoded_path = quote(caminho, safe="/")
    try:
        response = _SESSION.delete(
            f"{url}/storage/v1/object/{BIBLIOTECA_3D_BUCKET}/{encoded_path}",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        return bool(response.ok)
    except requests.RequestException:
        return False

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
