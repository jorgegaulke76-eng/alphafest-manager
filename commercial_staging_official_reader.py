"""Leitura oficial HF53 exclusivamente de documentos de HOMOLOGACAO.

As chaves sao contratos identificados no app.py legado, mas a leitura
e restrita ao projeto Supabase de teste. Nao migra dados reais nem consulta
producao. Autorizacao do operador precisa ocorrer ANTES de chamar este modulo;
retorna somente campos saneados, nunca os objetos JSON originais.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_official_snapshot_adapter import sanitize_official_manager_snapshots
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_server_session_postgrest import _endpoint as validate_staging_endpoint

PROPOSAL_KEY = "historico_orcamentos"
CONTACT_KEY = "atendimentos_db"
ALLOWED_KEYS = frozenset({PROPOSAL_KEY, CONTACT_KEY})


def _read_one(
    *, get: Callable[..., Any], base_url: str,
    headers: Mapping[str, str], key: str,
) -> Any:
    if key not in ALLOWED_KEYS or not callable(get):
        raise PrivateStoreDenied("Leitura de documento de homologacao nao autorizada.")
    try:
        # A validacao ocorre ANTES de transmitir a chave privada.
        endpoint = validate_staging_endpoint(base_url, headers)
        # O validador usa a tabela de sessoes; trocar somente sufixo fixo.
        endpoint = endpoint.rsplit("/", 1)[0] + "/app_data"
        response = get(
            endpoint, headers=dict(headers),
            params={"select": "value", "key": "eq." + key, "limit": "2"},
            timeout=10, allow_redirects=False,
        )
        response.raise_for_status()
        if type(response.status_code) is not int or not 200 <= response.status_code < 300:
            raise ValueError()
        rows = response.json()
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError()
        row = rows[0]
        if not isinstance(row, dict) or "value" not in row:
            raise ValueError()
        return row["value"]
    except Exception:
        raise PrivateStoreDenied("Documento oficial de homologacao indisponivel.") from None


def read_sanitized_staging_official_snapshots(
    *, get: Callable[..., Any], base_url: str,
    headers: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Nao oferece fallback: ambos os documentos precisam existir no staging."""
    raw_proposals = _read_one(
        get=get, base_url=base_url, headers=headers, key=PROPOSAL_KEY,
    )
    raw_contacts = _read_one(
        get=get, base_url=base_url, headers=headers, key=CONTACT_KEY,
    )
    return sanitize_official_manager_snapshots(
        historico_orcamentos=raw_proposals,
        atendimentos_db=raw_contacts,
    )
