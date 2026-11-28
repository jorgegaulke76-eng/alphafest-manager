"""HF65.24.53 — relatório privado completo, somente leitura, opt-in.

Integra autenticação, ACL, histórico exclusivamente remoto e snapshots
oficiais fornecidos pelo backend. NÃO altera dados nem é importado no app.
O provedor authenticate deve validar sessão criptograficamente no servidor.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_server_read_gateway import read_verified_operator_history
from commercial_verified_report import build_verified_commercial_report
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_operator_policy import VerifiedOperator


def build_authorized_commercial_report(
    *, session: Any,
    authenticate: Callable[[Any], VerifiedOperator | None],
    authorize: Callable[[VerifiedOperator, str], bool],
    cloud: Any,
    load_official_snapshots: Callable[[], tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Falha fechado; só calcula após autenticar e consultar fontes oficiais.

    Os callbacks são do servidor, nunca aceitar snapshots de formulário.
    A chamada mantém-se DESLIGADA até existir autenticador confiável.
    """
    if not callable(load_official_snapshots):
        raise PrivateStoreDenied("Fonte oficial do Manager não configurada.")
    # O gateway já verifica a identidade e ACL antes de consultar rede.
    events = read_verified_operator_history(
        session=session, authenticate=authenticate,
        authorize=authorize, cloud=cloud,
    )
    try:
        snapshots = load_official_snapshots()
    except Exception:
        raise PrivateStoreDenied("Fontes comerciais oficiais indisponíveis.") from None
    if (
        not isinstance(snapshots, tuple) or len(snapshots) != 2
        or any(not isinstance(part, list) for part in snapshots)
        or any(not all(isinstance(item, Mapping) for item in part)
               for part in snapshots)
    ):
        raise PrivateStoreDenied("Formato de dados oficiais inválido.")
    proposals, contacts = snapshots
    # A integridade do documento foi verificada no gateway.
    return build_verified_commercial_report(contacts, proposals, events)
