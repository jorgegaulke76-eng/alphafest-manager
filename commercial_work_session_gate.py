"""HF65.24.53 — gate servidor de sessão revogável + ACL, SEM relatório.

O Streamlit gerencia o login Google; um handle efêmero pode ficar apenas no
session_state do backend do app de HOMOLOGAÇÃO, mas nunca constitui prova de
identidade por si. Para cada acesso o gate reconstrói o principal com st.user,
consulta o estado remoto e aplica permissão explícita. Um falso/erro nega.
Ainda não é importado pelo Manager nem libera dados comerciais.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from commercial_operator_policy import OperatorPolicy, VerifiedOperator
from commercial_server_session_postgrest import active_staging_session
from hf65_24_53_oidc_bound_probe import authenticated_principal
from hf65_24_53_http_diagnostic import STAGING_URL

HANDLE_KEY = "_hf53_server_side_work_handle"


def _backend(st: Any) -> tuple[str, dict[str, str]]:
    try:
        url = st.secrets["HF53_STAGING_SUPABASE_URL"]
        key = st.secrets["HF53_STAGING_SERVICE_KEY"]
        if url != STAGING_URL or not isinstance(key, str) or not key.strip():
            raise ValueError()
        headers = {"apikey": key}
        if not key.startswith("sb_secret_"):
            headers["Authorization"] = "Bearer " + key
        return url, headers
    except Exception:
        raise PermissionError("Backend de homologação indisponível.") from None


def authorized_work_session(
    st: Any, *, policy: OperatorPolicy, action: str,
    get: Callable[..., Any], now: datetime | None = None,
) -> VerifiedOperator | None:
    """Somente a prova conjunta de OIDC, sessão remota e ACL autoriza."""
    try:
        if st.secrets.get("HF53_WORK_SESSION_GATE_ENABLED") is not True:
            return None
        if not isinstance(policy, OperatorPolicy):
            return None
        principal = authenticated_principal(st, now=now, require_diagnostic_access=False)
        if policy.permitted(principal, action) is not True:
            return None
        handle = st.session_state.get(HANDLE_KEY)
        if not isinstance(handle, str):
            return None
        url, headers = _backend(st)
        if not active_staging_session(
            get=get, base_url=url, headers=headers, principal=principal,
            handle=handle, now=now or datetime.now(timezone.utc),
        ):
            return None
        return principal
    except Exception:
        return None


def revoke_local_work_session(
    st: Any, *, patch: Callable[..., Any],
    now: datetime | None = None,
) -> bool:
    """Revoga primeiro no backend, descarta handle depois. Nunca autentica."""
    from commercial_server_session_postgrest import revoke_staging_session
    try:
        principal = authenticated_principal(st, now=now, require_diagnostic_access=False)
        handle = st.session_state.get(HANDLE_KEY)
        url, headers = _backend(st)
        if not isinstance(handle, str):
            return False
        return revoke_staging_session(
            patch=patch, base_url=url, headers=headers,
            principal=principal, handle=handle,
            now=now or datetime.now(timezone.utc),
        )
    except Exception:
        return False
    finally:
        try:
            st.session_state.pop(HANDLE_KEY, None)
        except Exception:
            pass
