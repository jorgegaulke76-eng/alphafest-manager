"""HF53: teste HTTP POST/GET/PATCH ficticio, estritamente na homologacao.

NAO autentica sessao do Manager: testa somente infraestrutura de revogacao.
Uma linha de teste, com assunto sintético e expiração de 60 s, permanece
revogada para auditoria. Nao cria clientes, pedidos, pagamentos ou ACL reais.
"""
from __future__ import annotations

from datetime import datetime, timezone
from secrets import token_hex
from typing import Any

from commercial_operator_policy import VerifiedOperator
from commercial_server_session_postgrest import (
    issue_staging_session, active_staging_session, revoke_staging_session,
)

SUCCESS = "Criacao, consulta e revogacao HTTP confirmadas em homologacao."
STAGING = "https://hvaptsdhaxrdxgqqpicu.supabase.co"


def run_session_write_probe(
    *, base_url: str, service_key: str, http: Any = None,
) -> str:
    if base_url != STAGING or not isinstance(service_key, str) or not service_key.strip():
        raise ValueError("Ambiente de homologacao invalido.")
    if http is None:
        import requests
        http = requests.Session()
    # Nunca usar o sujeito do usuario final neste ensaio de infraestrutura.
    principal = VerifiedOperator(
        "hf53-diag-" + token_hex(12), "hf53-diagnostic-only", "hf53-test-only"
    )
    headers = {"apikey": service_key}
    if not service_key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + service_key
    stamp = datetime.now(timezone.utc)
    handle = issue_staging_session(
        post=http.post, base_url=base_url, headers=headers,
        principal=principal, now=stamp, ttl_seconds=60,
    )
    # Revogar mesmo quando falhar a consulta intermediaria.
    try:
        active = active_staging_session(
            get=http.get, base_url=base_url, headers=headers,
            principal=principal, handle=handle, now=stamp,
        )
    finally:
        revoked = revoke_staging_session(
            patch=http.patch, base_url=base_url, headers=headers,
            principal=principal, handle=handle, now=datetime.now(timezone.utc),
        )
    if not active or not revoked:
        raise RuntimeError("Teste HTTP de sessao nao confirmado.")
    if active_staging_session(
        get=http.get, base_url=base_url, headers=headers,
        principal=principal, handle=handle, now=datetime.now(timezone.utc),
    ):
        raise RuntimeError("Sessao ainda ativa apos revogacao.")
    return SUCCESS
