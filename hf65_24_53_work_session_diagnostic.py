"""HF65.24.53: sessão de trabalho duradoura no app ISOLADO de homologação.

Exercita login Google + sessão PostgREST + permissão do diagnóstico.
NÃO habilita relatório nem utiliza pedidos. Permissão é a allowlist exclusiva
do diagnóstico, NÃO substitui ACL independente do Manager.
O handle permanece somente em st.session_state, nunca em URL ou widget.
Observação: refresh completo/nova aba reinicia session_state do Streamlit;
o registro remoto expira após 15 minutos se não for revogado.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from commercial_operator_policy import OperatorPolicy, READ
from commercial_server_session_postgrest import issue_staging_session
from commercial_work_session_gate import (
    HANDLE_KEY, _backend, authorized_work_session, revoke_local_work_session,
)
from hf65_24_53_http_diagnostic import _eligible
from hf65_24_53_oidc_bound_probe import authenticated_principal


def _policy_for_diagnostic(st: Any) -> OperatorPolicy:
    # _eligible confere Google + email explicitamente permitido nos Secrets;
    # este grant é APENAS do diagnóstico e não deve ser usado no relatório.
    principal = authenticated_principal(st)
    return OperatorPolicy(
        issuer=principal.issuer, audience=principal.audience,
        grants={principal.subject: {READ}},
    )


def start_test_work_session(st: Any, *, http: Any = None) -> bool:
    """Emite no banco e mantém no backend de sessão, sem tocar dados comerciais."""
    if st.secrets.get("HF53_WORK_SESSION_GATE_ENABLED") is not True:
        return False
    allowed, _ = _eligible(st)
    if not allowed:
        return False
    if st.session_state.get(HANDLE_KEY):
        return False
    try:
        principal = authenticated_principal(st)
        _policy_for_diagnostic(st)
        url, headers = _backend(st)
        if http is None:
            import requests
            http = requests.Session()
        handle = issue_staging_session(
            post=http.post, base_url=url, headers=headers,
            principal=principal, now=datetime.now(timezone.utc),
            ttl_seconds=900,
        )
        st.session_state[HANDLE_KEY] = handle
        return True
    except Exception:
        return False


def check_test_work_session(st: Any, *, http: Any = None) -> bool:
    if http is None:
        import requests
        http = requests.Session()
    try:
        return authorized_work_session(
            st, policy=_policy_for_diagnostic(st),
            action=READ, get=http.get,
        ) is not None
    except Exception:
        return False


def revoke_test_work_session(st: Any, *, http: Any = None) -> bool:
    if http is None:
        import requests
        http = requests.Session()
    return revoke_local_work_session(st, patch=http.patch)


def render_work_session_diagnostic(st: Any) -> None:
    st.subheader("Sessão de trabalho revogável — homologação")
    if st.secrets.get("HF53_WORK_SESSION_GATE_ENABLED") is not True:
        st.caption("Teste de sessão de trabalho desativado.")
        return
    allowed, _ = _eligible(st)
    if not allowed:
        st.caption("Login Google de operador de teste obrigatório.")
        return
    st.caption(
        "Sessão de teste de até 15 minutos. A cada execução verifica identidade, "
        "estado remoto e permissão de diagnóstico. Não consulta clientes."
    )
    try:
        import requests
        http = requests.Session()
        handle = st.session_state.get(HANDLE_KEY)
        if not handle:
            if st.button("Iniciar sessão de trabalho de teste"):
                if start_test_work_session(st, http=http):
                    st.success("Sessão de homologação criada. Use Verificar para validar.")
                else:
                    st.error("Não foi possível criar sessão de teste.")
            return
        if st.button("Verificar sessão ativa no servidor"):
            if check_test_work_session(st, http=http):
                st.success("Sessão ativa, identidade Google e permissão de teste confirmadas.")
            else:
                st.warning("Sessão expirada, revogada ou não autorizada.")
        if st.button("Revogar sessão de trabalho"):
            if revoke_test_work_session(st, http=http):
                st.success("Sessão revogada no Supabase de homologação.")
            else:
                st.warning("Revogação não confirmada. A sessão local foi descartada.")
    except Exception:
        st.error("Verificação de sessão indisponível. Acesso privado permanece fechado.")
