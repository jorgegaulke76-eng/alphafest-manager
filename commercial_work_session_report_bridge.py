"""HF53 — ponte do relatorio privado para sessão Google revogável + ACL.

Nao importado pelo app.py nem pela tela de diagnóstico. Esta funcao nao
habilita a feature: precisa de flags de servidor, identidade OIDC, sessão
viva consultada remotamente e permissão READ. Fontes oficiais também devem
ser fornecidas pelo servidor; nunca aceitar dados de formulário/navegador.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_authorized_report_gateway import build_authorized_commercial_report
from commercial_operator_policy import OperatorPolicy, READ, VerifiedOperator
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_work_session_gate import authorized_work_session


def build_work_session_commercial_report(
    *, st: Any, policy: OperatorPolicy, cloud: Any,
    get_session: Callable[..., Any],
    load_official_snapshots: Callable[[], tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Cada chamada precisa de nova consulta de sessao e ACL."""
    try:
        if st.secrets.get("HF65_24_53_PRIVATE_REPORT_ENABLED") is not True:
            raise PrivateStoreDenied("Relatorio privado desativado.")
        if not isinstance(policy, OperatorPolicy) or not callable(get_session):
            raise PrivateStoreDenied("Verificacao de sessao nao configurada.")
        principal = authorized_work_session(
            st, policy=policy, action=READ, get=get_session,
        )
        if not isinstance(principal, VerifiedOperator):
            raise PrivateStoreDenied("Login, sessao ou privilegio de leitura invalidos.")
    except PrivateStoreDenied:
        raise
    except Exception:
        raise PrivateStoreDenied("Acesso privado indisponivel.") from None

    def recheck_session() -> None:
        # As leituras remotas não são atômicas. Uma revogação entre o
        # diário de atribuições e os snapshots não pode herdar a decisão
        # de acesso anterior; exigir nova consulta remota e a mesma identidade.
        current = authorized_work_session(
            st, policy=policy, action=READ, get=get_session,
        )
        if current != principal:
            raise PrivateStoreDenied(
                "Sessão revogada ou permissão alterada durante a leitura."
            )

    def guarded_snapshots():
        recheck_session()
        return load_official_snapshots()

    # O gateway consulta o diário privado com ACL e, depois, o snapshot
    # guardado. Conferir uma última vez antes de devolver qualquer agregado.
    report = build_authorized_commercial_report(
        session=None, authenticate=lambda _session: principal,
        authorize=policy.permitted, cloud=cloud,
        load_official_snapshots=guarded_snapshots,
    )
    recheck_session()
    return report
