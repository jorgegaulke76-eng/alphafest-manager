"""HF65.24.53 — validação de sessão ANTES do acesso comercial.

Contrato de servidor para sessão já autenticada pelo provedor. Não é um
verificador OIDC/JWT; o integrador deverá injetar verificação criptográfica
de token, assinatura, expiração, issuer/audience e sessão ativa/revogada.
Nenhum segredo, token ou identificador pessoal é registrado em logs.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from math import isfinite
from typing import Any

from commercial_operator_policy import VerifiedOperator


class SessionRejected(PermissionError):
    pass


def verify_authenticated_session(
    session: Any, *,
    verify_provider: Callable[[Any], Mapping[str, Any] | None],
    is_session_active: Callable[[str, str], bool],
    expected_issuer: str,
    expected_audience: str,
    now: datetime | None = None,
) -> VerifiedOperator:
    """Exige atestado do backend + tempo válido + sessão não revogada.

    O atestado passado por verify_provider NÃO pode originar-se de parâmetros
    HTTP/Streamlit editáveis. O backend deve validar assinatura/algoritmo,
    chave, issuer, audience, nonce/PKCE quando aplicável e atualização de sessão.
    """
    if not callable(verify_provider) or not callable(is_session_active):
        raise SessionRejected("Validação da sessão indisponível.")
    if (not isinstance(expected_issuer, str) or not expected_issuer.strip()
            or expected_issuer != expected_issuer.strip()
            or not isinstance(expected_audience, str) or not expected_audience.strip()
            or expected_audience != expected_audience.strip()):
        raise SessionRejected("Emissor/público do aplicativo não configurados.")
    try:
        claims = verify_provider(session)
    except Exception:
        raise SessionRejected("Não foi possível verificar a sessão.") from None
    if not isinstance(claims, Mapping) or claims.get("verified") is not True:
        raise SessionRejected("Sessão não verificada.")
    subject = claims.get("sub")
    issuer = claims.get("iss")
    audience = claims.get("aud")
    session_id = claims.get("sid")
    issued_at = claims.get("iat")
    expires_at = claims.get("exp")
    if (
        not isinstance(subject, str) or not subject.strip() or subject != subject.strip()
        or len(subject) > 256
        or issuer != expected_issuer or audience != expected_audience
        or not isinstance(session_id, str) or not session_id.strip()
        or session_id != session_id.strip() or len(session_id) > 256
        or isinstance(issued_at, bool) or not isinstance(issued_at, (int, float))
        or isinstance(expires_at, bool) or not isinstance(expires_at, (int, float))
        or not isfinite(issued_at) or not isfinite(expires_at)
    ):
        raise SessionRejected("Identidade de sessão inválida.")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise SessionRejected("Relógio do servidor sem fuso.")
    ts = current.timestamp()
    if not isfinite(ts):
        raise SessionRejected("Relógio do servidor inválido.")
    # Valida limites temporais com tolerância mínima de clock skew.
    if expires_at <= ts or issued_at > ts + 60 or issued_at >= expires_at:
        raise SessionRejected("Sessão expirada ou inconsistente.")
    try:
        if is_session_active(subject, session_id) is not True:
            raise SessionRejected("Sessão revogada ou não reconhecida.")
    except SessionRejected:
        raise
    except Exception:
        raise SessionRejected("Não foi possível verificar a validade da sessão.") from None
    return VerifiedOperator(subject=subject, issuer=issuer, audience=audience)
