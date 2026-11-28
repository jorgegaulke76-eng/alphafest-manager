"""HF65.24.53 — gateway opcional de bootstrap no SERVIDOR, desligado.

Não é importado pelo Manager. O autenticador deve validar a sessão em backend,
a política deve usar sujeitos opacos; cloud só pode ser um cliente de servidor
com segredo protegido e conexão ao banco de HOMOLOGAÇÃO.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from commercial_operator_policy import VerifiedOperator, OperatorPolicy, BOOTSTRAP
from commercial_private_bootstrap import initialize_private_history_if_absent
from commercial_bootstrap_postgrest_contract import (
    read_bootstrap_document_optional, insert_bootstrap_document_if_absent,
)
from commercial_private_document_adapter import PrivateStoreDenied


def bootstrap_verified_private_history(
    *, session: Any,
    authenticate: Callable[[Any], VerifiedOperator | None],
    policy: OperatorPolicy,
    cloud: Any,
) -> str:
    """Configura HTTP somente após validar identidade e permissão exclusiva."""
    if not callable(authenticate) or not isinstance(policy, OperatorPolicy):
        raise PrivateStoreDenied("Autenticação e política privadas obrigatórias.")
    try:
        principal = authenticate(session)
    except Exception:
        raise PrivateStoreDenied("Autenticação do servidor indisponível.") from None
    if not isinstance(principal, VerifiedOperator):
        raise PrivateStoreDenied("Operador não verificado.")
    if not policy.permitted(principal, BOOTSTRAP):
        raise PrivateStoreDenied("Inicialização do diário não autorizada.")
    try:
        if cloud.credential_mode() != "service" or not cloud.online_configured():
            raise PrivateStoreDenied("Banco privado indisponível.")
        url, _secret = cloud._config()
        headers = cloud._headers()
        client = cloud._SESSION
        get = client.get
        post = client.post
    except PrivateStoreDenied:
        raise
    except Exception:
        raise PrivateStoreDenied("Cliente de servidor não configurado.") from None

    return initialize_private_history_if_absent(
        principal=principal,
        approve_initialization=lambda operator: policy.permitted(operator, BOOTSTRAP),
        credential_mode=cloud.credential_mode,
        read_online=lambda key: read_bootstrap_document_optional(
            get=get, base_url=url, headers=headers, document_key=key,
        ),
        insert_if_absent=lambda key, value: insert_bootstrap_document_if_absent(
            post=post, base_url=url, headers=headers, document_key=key,
            document=value,
        ),
    )
