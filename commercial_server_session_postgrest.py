"""HF65.24.53 — contrato servidor-only para sessões na API de HOMOLOGAÇÃO.

Ainda NÃO integrado ao login Streamlit nem ao Manager, não valida OIDC/JWT.
Chamadores devem autenticar criptograficamente, aplicar ACL e guardar o handle
somente no backend. Nunca aceitar handle da URL, formulário ou navegador.
Nenhuma chamada de rede ocorre sem callbacks injetados pelo servidor.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any
from urllib.parse import urlsplit

from commercial_operator_policy import VerifiedOperator

HOST = "hvaptsdhaxrdxgqqpicu.supabase.co"
TABLE = "hf53_server_sessions"
MAX_TTL = 3600


class SessionHttpDenied(PermissionError):
    pass


def _endpoint(base_url: str, headers: Mapping[str, str]) -> str:
    try:
        p = urlsplit(base_url)
        if (p.scheme != "https" or p.hostname != HOST or p.port not in (None, 443)
            or p.username is not None or p.password is not None
            or p.path not in ("", "/") or p.query or p.fragment):
            raise ValueError()
        if (not isinstance(headers, Mapping)
            or not isinstance(headers.get("apikey"), str) or not headers["apikey"]
            or not isinstance(headers.get("Authorization"), str)
            or not headers["Authorization"].startswith("Bearer ")):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise SessionHttpDenied("Credencial privada ou endpoint de homologação inválido.") from None
    return "https://" + HOST + "/rest/v1/" + TABLE


def _identity(principal: Any) -> VerifiedOperator:
    if not isinstance(principal, VerifiedOperator) or any(
        not isinstance(x, str) or not x or x != x.strip() or len(x) > 256
        for x in (principal.subject, principal.issuer, principal.audience)
    ):
        raise SessionHttpDenied("Identidade autenticada no servidor obrigatória.")
    return principal


def _time(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise SessionHttpDenied("Relógio do servidor inválido.")
    return now.astimezone(timezone.utc)


def _digest(handle: str) -> str:
    if not isinstance(handle, str) or not 40 <= len(handle) <= 128:
        raise SessionHttpDenied("Sessão não reconhecida.")
    try:
        return sha256(handle.encode("ascii")).hexdigest()
    except UnicodeEncodeError:
        raise SessionHttpDenied("Sessão não reconhecida.") from None


def _request(callback: Callable[..., Any], endpoint: str, **kwargs: Any) -> Any:
    if not callable(callback):
        raise SessionHttpDenied("Cliente HTTP de servidor indisponível.")
    try:
        result = callback(endpoint, timeout=10, allow_redirects=False, **kwargs)
        result.raise_for_status()
        if type(result.status_code) is not int or not 200 <= result.status_code < 300:
            raise ValueError()
        rows = result.json()
    except Exception:
        raise SessionHttpDenied("Operação privada não confirmada.") from None
    if not isinstance(rows, list):
        raise SessionHttpDenied("Resposta privada inesperada.")
    return rows


def issue_staging_session(
    *, post: Callable[..., Any], base_url: str, headers: Mapping[str, str],
    principal: VerifiedOperator, now: datetime, ttl_seconds: int = 900,
) -> str:
    """Emitir somente quando principal foi validado por autenticador real no backend."""
    endpoint = _endpoint(base_url, headers)
    principal = _identity(principal)
    stamp = _time(now)
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_TTL:
        raise SessionHttpDenied("Duração inválida.")
    handle = token_urlsafe(32)
    payload = {
        "handle_sha256": _digest(handle),
        "subject": principal.subject, "issuer": principal.issuer,
        "audience": principal.audience, "created_at": stamp.isoformat(),
        "expires_at": (stamp + timedelta(seconds=ttl_seconds)).isoformat(),
    }
    request_headers = {**headers, "Prefer": "return=representation"}
    rows = _request(post, endpoint, headers=request_headers, json=payload,
                    params={"select":"handle_sha256"},)
    if (len(rows) != 1 or not isinstance(rows[0], dict)
        or rows[0].get("handle_sha256") != payload["handle_sha256"]):
        raise SessionHttpDenied("Emissão não confirmada.")
    return handle


def active_staging_session(
    *, get: Callable[..., Any], base_url: str, headers: Mapping[str, str],
    principal: VerifiedOperator, handle: str, now: datetime,
) -> bool:
    """Fail-closed: estado consultado remotamente em TODA operação privada."""
    try:
        endpoint = _endpoint(base_url, headers)
        principal = _identity(principal)
        stamp = _time(now)
        digest = _digest(handle)
        rows = _request(get, endpoint, headers=dict(headers), params={
            "select": "handle_sha256,subject,issuer,audience,expires_at,revoked_at",
            "handle_sha256": "eq." + digest, "limit": "2",
        })
        if len(rows) != 1 or not isinstance(rows[0], dict):
            return False
        row = rows[0]
        if (row.get("handle_sha256") != digest
            or row.get("subject") != principal.subject
            or row.get("issuer") != principal.issuer
            or row.get("audience") != principal.audience
            or row.get("revoked_at") is not None):
            return False
        expiry = datetime.fromisoformat(row["expires_at"])
        return expiry.tzinfo is not None and expiry.astimezone(timezone.utc) > stamp
    except Exception:
        return False


def revoke_staging_session(
    *, patch: Callable[..., Any], base_url: str, headers: Mapping[str, str],
    principal: VerifiedOperator, handle: str, now: datetime,
) -> bool:
    """Revoga atomicamente só a sessão pertencente ao operador autenticado."""
    endpoint = _endpoint(base_url, headers)
    principal = _identity(principal)
    stamp = _time(now)
    digest = _digest(handle)
    request_headers = {**headers, "Prefer": "return=representation"}
    rows = _request(patch, endpoint, headers=request_headers, params={
        "handle_sha256": "eq." + digest,
        "subject": "eq." + principal.subject,
        "issuer": "eq." + principal.issuer,
        "audience": "eq." + principal.audience,
        "revoked_at": "is.null",
        "select": "handle_sha256",
    }, json={"revoked_at": stamp.isoformat()})
    if len(rows) == 0:
        return False
    if (len(rows) != 1 or not isinstance(rows[0], dict)
        or rows[0].get("handle_sha256") != digest):
        raise SessionHttpDenied("Revogação não confirmada.")
    return True
