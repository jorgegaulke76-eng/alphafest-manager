"""HF65.24.53 — contrato HTTP PostgREST de bootstrap privado (desligado).

Não importa cloud_db nem acessa rede por si: get/post e headers entram do
servidor após autenticação real. Distinge ausência de documento de falha HTTP.
Inserção condicional usa ignore-duplicates, nunca merge-duplicates.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

from commercial_private_document_adapter import DOCUMENT_KEY, _valid_document


STAGING_HOST = "hvaptsdhaxrdxgqqpicu.supabase.co"


class PrivateBootstrapHttpError(RuntimeError):
    pass


def _validate_args(url: str, headers: Mapping[str, str], key: str) -> str:
    if key != DOCUMENT_KEY:
        raise PrivateBootstrapHttpError("Chave de diário não autorizada.")
    if not isinstance(url, str):
        raise PrivateBootstrapHttpError("Endpoint HTTPS obrigatório.")
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise PrivateBootstrapHttpError("Endpoint do banco inválido.") from None
    # HF53 é um experimento exclusivamente de homologação: nunca enviar
    # chave privada para outro projeto, inclusive AlphaFest em produção.
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https" or host != STAGING_HOST
        or parsed.username is not None or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.path not in ("", "/") or parsed.query or parsed.fragment
    ):
        raise PrivateBootstrapHttpError("Endpoint Supabase seguro obrigatório.")
    if not isinstance(headers, Mapping) or not isinstance(headers.get("apikey"), str) or not headers["apikey"]:
        raise PrivateBootstrapHttpError("Credencial do servidor ausente.")
    return url.rstrip("/") + "/rest/v1/app_data"


def read_bootstrap_document_optional(
    *, get: Callable[..., Any], base_url: str,
    headers: Mapping[str, str], document_key: str = DOCUMENT_KEY,
    timeout: int = 10,
) -> dict[str, Any] | None:
    """Retorna None APENAS quando GET HTTP 2xx confirmar [] no banco."""
    endpoint = _validate_args(base_url, headers, document_key)
    if not callable(get):
        raise PrivateBootstrapHttpError("Cliente de leitura não configurado.")
    try:
        response = get(
            endpoint, headers=dict(headers),
            params={"select": "key,value", "key": "eq." + document_key, "limit": "2"},
            timeout=timeout, allow_redirects=False,
        )
        response.raise_for_status()
        if not isinstance(response.status_code, int) or not 200 <= response.status_code < 300:
            raise PrivateBootstrapHttpError("Status remoto não confirmado.")
        rows = response.json()
    except Exception:
        raise PrivateBootstrapHttpError("Leitura remota não confirmada.") from None
    if not isinstance(rows, list) or len(rows) > 1:
        raise PrivateBootstrapHttpError("Resposta de leitura inválida.")
    if not rows:
        return None
    row = rows[0]
    if not isinstance(row, dict) or set(row) != {"key", "value"} or row["key"] != document_key:
        raise PrivateBootstrapHttpError("Documento retornado não corresponde à chave.")
    try:
        return _valid_document(row["value"])
    except (ValueError, RuntimeError):
        raise PrivateBootstrapHttpError("Histórico privado inválido.") from None


def insert_bootstrap_document_if_absent(
    *, post: Callable[..., Any], base_url: str,
    headers: Mapping[str, str], document_key: str,
    document: dict[str, Any], timeout: int = 10,
) -> bool:
    """Exige resposta de linha inserida; [] significa conflito preservado."""
    endpoint = _validate_args(base_url, headers, document_key)
    if not callable(post) or document != {"events": []}:
        raise PrivateBootstrapHttpError("Solicitação de inicialização inválida.")
    request_headers = dict(headers)
    request_headers["Prefer"] = "resolution=ignore-duplicates,return=representation"
    try:
        response = post(
            endpoint, headers=request_headers,
            params={"on_conflict": "key", "select": "key,value"},
            json={"key": document_key, "value": {"events": []}},
            timeout=timeout, allow_redirects=False,
        )
        response.raise_for_status()
        if not isinstance(response.status_code, int) or not 200 <= response.status_code < 300:
            raise PrivateBootstrapHttpError("Status remoto não confirmado.")
        rows = response.json()
    except Exception:
        raise PrivateBootstrapHttpError("Inserção não confirmada pelo banco.") from None
    if rows == []:
        return False
    if (
        isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict)
        and rows[0].get("key") == document_key
        and rows[0].get("value") == {"events": []}
    ):
        return True
    raise PrivateBootstrapHttpError("Confirmação de inserção inválida.")
