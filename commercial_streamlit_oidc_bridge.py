"""HF65.24.53 — ponte experimental para login OIDC nativo Streamlit.

Não ativa login, não chama st.login e NÃO está importada no app principal.
Somente um st.user fornecido pelo runtime com OIDC configurado em Secrets
pode ser usado. Claims de um formulário ou de st.session_state NÃO servem.
Sem sid de provedor e sem checagem externa da sessão ativa: acesso negado.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from commercial_session_guard import verify_authenticated_session, SessionRejected
from commercial_operator_policy import VerifiedOperator


def authenticate_streamlit_oidc_user(
    st: Any, *,
    expected_issuer: str,
    expected_audience: str,
    is_session_active: Callable[[str, str], bool],
    now: datetime | None = None,
) -> VerifiedOperator:
    """Adapta exclusivamente st.user autenticado pelo Streamlit.

    Não verifica assinatura JWT diretamente; depende de OIDC nativo realmente
    configurado no host e da integridade do runtime. Claims exp/iat e sid
    continuam obrigatórias; sem sid/revogação habilitada, negar.
    """
    try:
        user = st.user
        if user.is_logged_in is not True:
            raise SessionRejected("É necessário login OIDC.")
        claims = user.to_dict()
        if not isinstance(claims, Mapping):
            raise SessionRejected("Claims OIDC indisponíveis.")
    except SessionRejected:
        raise
    except Exception:
        raise SessionRejected("Login OIDC não configurado ou indisponível.") from None

    # Nenhum token, segredo ou claim é registrado no log da aplicação.
    # Não aceitar um campo 'verified' vindo do objeto mapeado. Esta afirmação
    # existe SOMENTE no callback interno após checar st.user.is_logged_in.
    verified_claims = {
        key: claims.get(key)
        for key in ("sub", "iss", "aud", "sid", "iat", "exp")
    }
    verified_claims["verified"] = True
    return verify_authenticated_session(
        session=user,
        verify_provider=lambda _user: verified_claims,
        is_session_active=is_session_active,
        expected_issuer=expected_issuer,
        expected_audience=expected_audience,
        now=now,
    )
