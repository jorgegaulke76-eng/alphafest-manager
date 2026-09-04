"""Publicação assistida do site AlphaFest no Cloudflare Worker (HF44).

A integração usa a API oficial de Direct Upload de Static Assets. Credenciais
são recebidas em memória e nunca são persistidas por este módulo.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import mimetypes
import os
import re
import zipfile
from datetime import date
from pathlib import PurePosixPath
from typing import Any, Dict, Mapping, Optional, Tuple

import requests

API_BASE = "https://api.cloudflare.com/client/v4"
WORKER_PADRAO = "alphafest-novo"
DOMINIO_PADRAO = "alphafest.com.br"
ARQUIVOS_PUBLICOS_PERMITIDOS = {
    "index.html",
    "404.html",
    "robots.txt",
    "sitemap.xml",
}
MODULOS_STATIC_ASSETS = {"_headers", "_redirects"}


class CloudflarePublishError(RuntimeError):
    """Falha segura e legível na publicação Cloudflare."""


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _validar_account_id(account_id: str) -> str:
    valor = _texto(account_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", valor):
        raise CloudflarePublishError("Account ID da Cloudflare ausente ou inválido.")
    return valor


def _validar_token(api_token: str) -> str:
    valor = _texto(api_token)
    if len(valor) < 20 or any(ch.isspace() for ch in valor):
        raise CloudflarePublishError("API Token da Cloudflare ausente ou inválido.")
    return valor


def _validar_worker(worker_name: str) -> str:
    valor = _texto(worker_name) or WORKER_PADRAO
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", valor):
        raise CloudflarePublishError("Nome do Worker inválido.")
    return valor


def credenciais_ambiente() -> Dict[str, str]:
    """Lê integração opcional do ambiente sem expor o token."""
    return {
        "account_id": _texto(os.getenv("CLOUDFLARE_ACCOUNT_ID")),
        "api_token": _texto(os.getenv("CLOUDFLARE_API_TOKEN")),
        "worker_name": _texto(os.getenv("CLOUDFLARE_WORKER_NAME")) or WORKER_PADRAO,
    }


def extrair_pacote_publico(pacote_zip: bytes) -> Tuple[Dict[str, bytes], Dict[str, bytes]]:
    """Extrai somente assets públicos e módulos especiais (_headers/_redirects).

    README e STATUS do pacote continuam disponíveis no ZIP para auditoria, mas
    não são publicados como arquivos web pela integração HF44.
    """
    bruto = bytes(pacote_zip or b"")
    if not bruto:
        raise CloudflarePublishError("Pacote de produção vazio.")
    try:
        with zipfile.ZipFile(io.BytesIO(bruto), "r") as zf:
            nomes = {n for n in zf.namelist() if not n.endswith("/")}
            if "index.html" not in nomes:
                raise CloudflarePublishError("Pacote de produção sem index.html.")
            assets: Dict[str, bytes] = {}
            modulos: Dict[str, bytes] = {}
            for nome in sorted(nomes):
                seguro = str(PurePosixPath(nome))
                if seguro.startswith("../") or seguro.startswith("/"):
                    continue
                if seguro in MODULOS_STATIC_ASSETS:
                    modulos[seguro] = zf.read(nome)
                elif seguro in ARQUIVOS_PUBLICOS_PERMITIDOS:
                    assets[f"/{seguro}"] = zf.read(nome)
            if "/index.html" not in assets:
                raise CloudflarePublishError("index.html não pôde ser extraído do pacote.")
            return assets, modulos
    except zipfile.BadZipFile as exc:
        raise CloudflarePublishError("Pacote de produção inválido ou corrompido.") from exc


def _hash_asset(path: str, conteudo: bytes) -> str:
    extensao = PurePosixPath(path).suffix.lstrip(".")
    base64_texto = base64.b64encode(conteudo).decode("ascii")
    return hashlib.sha256((base64_texto + extensao).encode("utf-8")).hexdigest()[:32]


def criar_manifesto(assets: Mapping[str, bytes]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    manifesto: Dict[str, Dict[str, Any]] = {}
    hash_para_path: Dict[str, str] = {}
    for path, conteudo in sorted(assets.items()):
        h = _hash_asset(path, bytes(conteudo))
        manifesto[path] = {"hash": h, "size": len(conteudo)}
        # Dois caminhos podem compartilhar o mesmo conteúdo/hash (ex.: index.html e 404.html).
        # A Cloudflare faz o upload do blob uma vez e o manifesto o referencia em ambos.
        hash_para_path.setdefault(h, path)
    return manifesto, hash_para_path


def fingerprint_pacote(pacote_zip: bytes) -> str:
    assets, modulos = extrair_pacote_publico(pacote_zip)
    h = hashlib.sha256()
    for nome, conteudo in sorted({**assets, **modulos}.items()):
        h.update(nome.encode("utf-8"))
        h.update(b"\0")
        h.update(conteudo)
        h.update(b"\0")
    return h.hexdigest()[:16]


def _json_resposta(response: Any, etapa: str) -> Dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        status = getattr(response, "status_code", "?")
        raise CloudflarePublishError(f"Cloudflare respondeu sem JSON na etapa {etapa} (HTTP {status}).") from exc

    if not getattr(response, "ok", False) or not payload.get("success", False):
        erros = payload.get("errors") or []
        mensagens = []
        for erro in erros[:3]:
            if isinstance(erro, dict):
                codigo = erro.get("code")
                msg = _texto(erro.get("message"))
                mensagens.append(f"{codigo}: {msg}" if codigo else msg)
        detalhe = "; ".join(x for x in mensagens if x) or f"HTTP {getattr(response, 'status_code', '?')}"
        raise CloudflarePublishError(f"Falha na Cloudflare ({etapa}): {detalhe}")
    return payload


def testar_conexao(
    *,
    account_id: str,
    api_token: str,
    worker_name: str = WORKER_PADRAO,
    timeout: int = 20,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    """Confere se a credencial enxerga o Worker, sem modificar nada."""
    account_id = _validar_account_id(account_id)
    api_token = _validar_token(api_token)
    worker_name = _validar_worker(worker_name)
    http = session or requests.Session()
    url = f"{API_BASE}/accounts/{account_id}/workers/workers/{worker_name}"
    response = http.get(url, headers={"Authorization": f"Bearer {api_token}"}, timeout=timeout)
    payload = _json_resposta(response, "teste de conexão")
    result = payload.get("result") or {}
    return {
        "ok": True,
        "worker_name": _texto(result.get("name")) or worker_name,
        "worker_id": _texto(result.get("id")),
    }


def _mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def publicar_pacote(
    pacote_zip: bytes,
    *,
    account_id: str,
    api_token: str,
    worker_name: str = WORKER_PADRAO,
    versao_manager: str = "20.4.9-I8.13.5-HF44",
    timeout: int = 45,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    """Publica o snapshot aprovado no Worker existente e o coloca em 100% do tráfego.

    Não cria/altera DNS, Custom Domains, MX, webmail ou Redirect Rules.
    """
    account_id = _validar_account_id(account_id)
    api_token = _validar_token(api_token)
    worker_name = _validar_worker(worker_name)
    assets, modulos_especiais = extrair_pacote_publico(pacote_zip)
    manifesto, hash_para_path = criar_manifesto(assets)
    http = session or requests.Session()
    token_headers = {"Authorization": f"Bearer {api_token}"}

    # 1. Registrar manifesto e receber JWT temporário de upload.
    session_url = f"{API_BASE}/accounts/{account_id}/workers/scripts/{worker_name}/assets-upload-session"
    response = http.post(
        session_url,
        headers={**token_headers, "Content-Type": "application/json"},
        json={"manifest": manifesto},
        timeout=timeout,
    )
    payload = _json_resposta(response, "registro do manifesto")
    result = payload.get("result") or {}
    upload_jwt = _texto(result.get("jwt"))
    buckets = result.get("buckets")
    if not upload_jwt or not isinstance(buckets, list):
        raise CloudflarePublishError("Cloudflare não retornou sessão de upload válida.")

    completion_jwt = upload_jwt
    uploads_realizados = 0

    # 2. Enviar somente arquivos que a Cloudflare informou como novos/alterados.
    for bucket in buckets:
        if not isinstance(bucket, list) or not bucket:
            continue
        files: Dict[str, Tuple[str, str, str]] = {}
        for asset_hash in bucket:
            path = hash_para_path.get(str(asset_hash))
            if not path:
                raise CloudflarePublishError("A Cloudflare solicitou um asset ausente do manifesto local.")
            conteudo = assets[path]
            files[str(asset_hash)] = (
                PurePosixPath(path).name,
                base64.b64encode(conteudo).decode("ascii"),
                _mime(path),
            )
        upload_url = f"{API_BASE}/accounts/{account_id}/workers/assets/upload?base64=true"
        up_response = http.post(
            upload_url,
            headers={"Authorization": f"Bearer {upload_jwt}"},
            files=files,
            timeout=timeout,
        )
        up_payload = _json_resposta(up_response, "upload dos arquivos")
        up_result = up_payload.get("result") or {}
        novo_jwt = _texto(up_result.get("jwt"))
        if novo_jwt:
            completion_jwt = novo_jwt
        uploads_realizados += len(files)

    if not completion_jwt:
        raise CloudflarePublishError("Upload concluído sem token final de publicação.")

    # 3. Criar nova versão do Worker e já enviar 100% do tráfego para ela.
    script = (
        "export default { async fetch(request, env) { "
        "return env.ASSETS.fetch(request); } };"
    ).encode("utf-8")
    modules = [
        {
            "name": "main.js",
            "content_type": "application/javascript+module",
            "content_base64": base64.b64encode(script).decode("ascii"),
        }
    ]
    for nome in ("_headers", "_redirects"):
        if nome in modulos_especiais:
            modules.append({
                "name": nome,
                "content_type": "text/plain",
                "content_base64": base64.b64encode(modulos_especiais[nome]).decode("ascii"),
            })

    version_body = {
        "main_module": "main.js",
        "compatibility_date": date.today().isoformat(),
        "bindings": [{"type": "assets", "name": "ASSETS"}],
        "assets": {
            "jwt": completion_jwt,
            "config": {
                "html_handling": "auto-trailing-slash",
                "not_found_handling": "404-page",
            },
        },
        "modules": modules,
        "annotations": {
            "workers/message": f"AlphaFest Manager {versao_manager}: publicação assistida do Catálogo",
            "workers/tag": versao_manager[-32:],
            "workers/triggered_by": "upload",
        },
    }
    version_url = f"{API_BASE}/accounts/{account_id}/workers/workers/{worker_name}/versions?deploy=true"
    ver_response = http.post(
        version_url,
        headers={**token_headers, "Content-Type": "application/json"},
        json=version_body,
        timeout=timeout,
    )
    ver_payload = _json_resposta(ver_response, "criação/deploy da versão")
    ver_result = ver_payload.get("result") or {}
    version_id = _texto(ver_result.get("id"))
    if not version_id:
        raise CloudflarePublishError("Versão criada sem identificador de confirmação.")

    return {
        "ok": True,
        "worker_name": worker_name,
        "version_id": version_id,
        "version_number": ver_result.get("number"),
        "assets_total": len(assets),
        "assets_enviados": uploads_realizados,
        "fingerprint": fingerprint_pacote(pacote_zip),
        "dominio": DOMINIO_PADRAO,
    }
