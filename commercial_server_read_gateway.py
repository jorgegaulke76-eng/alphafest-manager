"""HF65.24.53 — gateway do servidor, SOMENTE LEITURA, ainda não integrado.

A identificação deve ser fornecida por autenticador confiável do servidor;
não aceita e-mail, nome ou papel recebido do formulário como autorização.
Não acessa o Supabase quando identidade ou privilégios não foram verificados.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from commercial_online_document_reader import load_private_document_online_only
from commercial_operator_policy import VerifiedOperator
from commercial_private_document_adapter import (
    DOCUMENT_KEY, PrivateStoreDenied, _valid_document,
)


def read_verified_operator_history(
    *, session: Any,
    authenticate: Callable[[Any], VerifiedOperator | None],
    authorize: Callable[[VerifiedOperator, str], bool],
    cloud: Any,
) -> list[dict[str, str]]:
    """Exige autenticação + autorização por ação e modo service antes de rede.

    authenticate(session) e authorize(principal, action) devem ser callbacks
    REAIS do servidor; não construir a identidade com st.session_state editável,
    texto da interface ou parâmetros de URL.
    """
    if not callable(authenticate) or not callable(authorize):
        raise PrivateStoreDenied("Autenticador e autorizador não configurados.")
    try:
        principal = authenticate(session)
    except Exception:
        raise PrivateStoreDenied("Autenticação indisponível.") from None
    if not isinstance(principal, VerifiedOperator):
        raise PrivateStoreDenied("Sessão não autenticada.")
    identity = str(principal.subject or "").strip()
    if not identity or len(identity) > 256:
        raise PrivateStoreDenied("Identidade não verificada.")
    try:
        allowed = authorize(principal, "read_attribution") is True
    except Exception:
        allowed = False
    if not allowed:
        raise PrivateStoreDenied("Sem permissão de leitura comercial.")
    try:
        if cloud.credential_mode() != "service" or not cloud.online_configured():
            raise PrivateStoreDenied("Acesso ao banco requer credencial privada.")
        url, _key = cloud._config()
        headers = cloud._headers()
        get = cloud._SESSION.get
    except PrivateStoreDenied:
        raise
    except Exception:
        raise PrivateStoreDenied("Configuração privada do banco indisponível.") from None
    # Este gateway não retorna documento local e não aceita chave arbitrária.
    value = load_private_document_online_only(
        get=get, base_url=url, headers=headers, document_key=DOCUMENT_KEY,
    )
    return _valid_document(value)["events"]
