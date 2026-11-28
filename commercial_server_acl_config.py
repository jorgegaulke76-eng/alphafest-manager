"""HF53: política comercial de backend separada da allowlist de diagnóstico.

Somente Secrets de servidor contendo sujeitos opacos pseudonimizados (HMAC).
Emails, nomes, flags de sessão e usuário visual nunca viram permissões.
Não tem acesso a Supabase nem exibe os valores dos Secrets.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from commercial_operator_policy import OperatorPolicy, READ
from commercial_private_document_adapter import PrivateStoreDenied

OPAQUE_SUBJECT = re.compile(r"^[0-9a-f]{64}$")


def commercial_read_policy_from_server_secrets(st: Any) -> OperatorPolicy:
    """Fail-closed; exige grant comercial independente explicitamente configurado."""
    try:
        if st.secrets.get("HF53_COMMERCIAL_ACL_ENABLED") is not True:
            raise ValueError()
        grants = st.secrets.get("HF53_COMMERCIAL_READ_SUBJECTS")
        auth = st.secrets["auth"]
        if (not isinstance(grants, list) or not 1 <= len(grants) <= 20
            or any(not isinstance(x, str) or not OPAQUE_SUBJECT.fullmatch(x) for x in grants)
            or len(set(grants)) != len(grants)
            or not isinstance(auth, Mapping)
            or not isinstance(auth.get("client_id"), str)
            or not auth["client_id"].strip()):
            raise ValueError()
        return OperatorPolicy(
            issuer="https://accounts.google.com", audience=auth["client_id"],
            grants={subject: {READ} for subject in grants},
        )
    except Exception:
        raise PrivateStoreDenied("Política de leitura comercial ausente ou inválida.") from None
