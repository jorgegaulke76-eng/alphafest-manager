"""HF53: ensaio de sessao revogavel vinculada ao login Google real.

SOMENTE app isolado de homologacao, nao gateway/Manager produtivo.
A identidade vem exclusivamente de st.user autenticado pelo Streamlit OIDC;
email permitido e claims sao validados novamente no servidor. O sujeito
persistido e HMAC nao reversivel; nenhuma credencial ou claim vai ao navegador.
O teste emite, verifica e revoga IMEDIATAMENTE, sem autorizar relatorios.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from hashlib import sha256
from hmac import new as hmac_new
from math import isfinite
from typing import Any

from commercial_operator_policy import VerifiedOperator
from commercial_server_session_postgrest import (
    issue_staging_session, active_staging_session, revoke_staging_session
)
from hf65_24_53_http_diagnostic import _eligible, STAGING_URL

SUCCESS = "Sessao vinculada ao login Google e revogada no Supabase de homologacao."


def authenticated_principal(
    st: Any, *, now: datetime | None = None,
    require_diagnostic_access: bool = True,
) -> VerifiedOperator:
    """Identidade Google no servidor; autorizacao comercial e verificada na ACL.

    O modo padrao preserva o bloqueio do diagnostico; o gate comercial usa
    require_diagnostic_access=False, mas exige login OIDC e email verificado
    independentemente do email/flag dos diagnósticos.
    """
    if require_diagnostic_access:
        allowed, _ = _eligible(st)
        if not allowed:
            raise PermissionError("Identidade do probe indisponivel.")
    else:
        try:
            if (st.user.is_logged_in is not True
                or st.user.to_dict().get("email_verified") is not True):
                raise ValueError()
        except Exception:
            raise PermissionError("Login Google verificado obrigatorio.") from None
    try:
        user = st.user
        c = user.to_dict()
        auth = st.secrets["auth"]
        sub = c["sub"]
        iss = c["iss"]
        aud = c["aud"]
        issued = c["iat"]
        expires = c["exp"]
        client_id = auth["client_id"]
        pepper = auth["cookie_secret"]
        t = (now or datetime.now(timezone.utc)).timestamp()
        if (not isinstance(sub, str) or not sub or sub != sub.strip() or len(sub) > 256
            or iss != "https://accounts.google.com"
            or not isinstance(client_id, str) or not client_id
            or aud != client_id
            or isinstance(issued, bool) or not isinstance(issued, (float, int))
            or isinstance(expires, bool) or not isinstance(expires, (float, int))
            or not isfinite(issued) or not isfinite(expires) or not isfinite(t)
            or issued > t + 60 or expires <= t or issued >= expires
            or not isinstance(pepper, str) or len(pepper) < 32):
            raise ValueError()
        # O ID do Google nao e enviado para o banco; apenas um sujeito opaco
        # por app/issuer derivado de segredo exclusivo do backend.
        message = (iss + "\x00" + aud + "\x00" + sub).encode("utf-8")
        pseudonym = hmac_new(pepper.encode("utf-8"), message, sha256).hexdigest()
        return VerifiedOperator(pseudonym, iss, aud)
    except Exception:
        raise PermissionError("Identidade OIDC do probe invalida.") from None


def run_bound_session_probe(
    st: Any, *, http: Any = None, now: datetime | None = None
) -> str:
    """Sem criar sessao permanente: POST, GET, PATCH e GET em uma acao."""
    if st.secrets.get("HF53_OIDC_BOUND_DIAG_ENABLED") is not True:
        raise PermissionError("Ensaio nao habilitado.")
    principal = authenticated_principal(st, now=now)
    target = st.secrets["HF53_STAGING_SUPABASE_URL"]
    if target != STAGING_URL:
        raise PermissionError("Projeto de homologacao obrigatorio.")
    key = st.secrets["HF53_STAGING_SERVICE_KEY"]
    if not isinstance(key, str) or not key.strip():
        raise PermissionError("Credencial indisponivel.")
    if http is None:
        import requests
        http = requests.Session()
    headers = {"apikey": key}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    stamp = now or datetime.now(timezone.utc)
    handle = issue_staging_session(
        post=http.post, base_url=target, headers=headers,
        principal=principal, now=stamp, ttl_seconds=60
    )
    verified = False
    try:
        verified = active_staging_session(
            get=http.get, base_url=target, headers=headers,
            principal=principal, handle=handle, now=stamp
        )
    finally:
        # Revoga mesmo se o GET falhar. Se PATCH falhar, falha fechado.
        revoked = revoke_staging_session(
            patch=http.patch, base_url=target, headers=headers,
            principal=principal, handle=handle, now=datetime.now(timezone.utc)
        )
    if (not verified or not revoked or active_staging_session(
        get=http.get, base_url=target, headers=headers,
        principal=principal, handle=handle, now=datetime.now(timezone.utc)
    )):
        raise RuntimeError("Revogacao vinculada ao OIDC nao confirmada.")
    return SUCCESS


def render_bound_session_diagnostic(st: Any, *, runner: Any = None) -> None:
    st.subheader("Google OIDC + revogacao real — teste isolado")
    allowed, _ = _eligible(st)
    if not allowed or st.secrets.get("HF53_OIDC_BOUND_DIAG_ENABLED") is not True:
        st.caption("Ensaio OIDC vinculado desativado ou nao autorizado.")
        return
    st.caption(
        "Usa sua identidade Google autenticada para testar uma sessao "
        "pseudonimizada de 60 segundos, revogada imediatamente. "
        "Nao concede acesso ao Manager ou ao relatorio."
    )
    if not st.button("Validar sessao Google e revogacao no banco"):
        return
    try:
        result = (runner or run_bound_session_probe)(st)
        if result != SUCCESS:
            raise RuntimeError()
    except Exception:
        st.error("Sessao Google/revogacao nao confirmadas. Relatorio permanece bloqueado.")
        return
    st.success("Google vinculado ao registro de teste e revogacao HTTP confirmada.")
