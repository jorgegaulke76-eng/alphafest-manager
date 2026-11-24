"""HF65.24.53 — ponto de entrada protegido do relatório para Streamlit.

OPT-IN: não importado pelo app.py e não habilitado automaticamente.
A identidade precisa vir exclusivamente de login OIDC do runtime Streamlit.
A seleção legada Jorge/Anna nunca é consultada ou aceita como permissão.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_authorized_report_gateway import build_authorized_commercial_report
from commercial_operator_policy import OperatorPolicy, VerifiedOperator
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_streamlit_oidc_bridge import authenticate_streamlit_oidc_user


def build_streamlit_private_commercial_report(
    *, st: Any, policy: OperatorPolicy, cloud: Any,
    is_session_active: Callable[[str, str], bool],
    load_official_snapshots: Callable[[], tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Permissão privada apenas com configuração habilitada no servidor.

    st.secrets deve ser lido diretamente do servidor; NUNCA de session_state,
    argumentos de URL ou componente do browser. A implantação futura deve
    configurar OIDC e validação real de revogação; sem isso, falha fechada.
    """
    try:
        feature = st.secrets.get("HF65_24_53_PRIVATE_REPORT_ENABLED", "")
        enabled = feature is True or (isinstance(feature, str) and feature.lower() == "true")
    except Exception:
        enabled = False
    if not enabled:
        raise PrivateStoreDenied("Relatório comercial privado não habilitado no servidor.")
    if not isinstance(policy, OperatorPolicy) or not callable(is_session_active):
        raise PrivateStoreDenied("Política e controle de sessão indisponíveis.")

    # O autenticador real do Streamlit é executado durante cada acesso.
    # O login/claims devem estar ligados a um provedor confiável no backend.
    def authenticate(_session: Any) -> VerifiedOperator:
        return authenticate_streamlit_oidc_user(
            st, expected_issuer=policy.issuer,
            expected_audience=policy.audience,
            is_session_active=is_session_active,
        )

    return build_authorized_commercial_report(
        session=None, authenticate=authenticate, authorize=policy.permitted,
        cloud=cloud, load_official_snapshots=load_official_snapshots,
    )
