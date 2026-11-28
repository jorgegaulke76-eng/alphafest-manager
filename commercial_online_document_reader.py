"""HF65.24.53 — leitura remota estrita de documentos privados do Manager.

Integração ainda NÃO ativada. O chamador do servidor fornece a sessão HTTP,
cabeçalhos da credencial de serviço e URL base; estes nunca são exibidos.
Sem fallback local, criação de documento ou retorno silencioso de dados vazios.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_private_document_adapter import DOCUMENT_KEY
from commercial_bootstrap_postgrest_contract import _validate_args, PrivateBootstrapHttpError


class PrivateDocumentUnavailable(RuntimeError):
    """Falha fechada: documento oficial ausente, inválido ou indisponível."""


def load_private_document_online_only(
    *, get: Callable[..., Any], base_url: str,
    headers: Mapping[str, str], document_key: str = DOCUMENT_KEY,
    timeout: int = 10,
) -> dict[str, Any]:
    """Consulta estritamente app_data com chave permitida, via servidor.

    Os cabeçalhos devem ser preparados no servidor após verificar credencial
    service e autorização; isso não substitui RLS nem autenticação.
    """
    if document_key != DOCUMENT_KEY:
        raise PrivateDocumentUnavailable("Chave de documento não autorizada.")
    if not callable(get):
        raise PrivateDocumentUnavailable("Conexão remota segura não configurada.")
    try:
        endpoint = _validate_args(base_url, headers, document_key)
    except PrivateBootstrapHttpError:
        raise PrivateDocumentUnavailable("Endpoint ou credencial privada inválida.") from None
    try:
        response = get(
            endpoint,
            headers=dict(headers),
            params={"select": "value", "key": "eq." + document_key, "limit": "2"},
            timeout=timeout, allow_redirects=False,
        )
        response.raise_for_status()
        if not isinstance(response.status_code, int) or not 200 <= response.status_code < 300:
            raise PrivateDocumentUnavailable("Status HTTP não confirmado.")
        rows = response.json()
    except Exception as exc:
        raise PrivateDocumentUnavailable("Falha ao consultar histórico privado online.") from None
    if not isinstance(rows, list) or len(rows) != 1:
        raise PrivateDocumentUnavailable("Histórico privado ausente ou ambíguo.")
    row = rows[0]
    if not isinstance(row, dict) or not isinstance(row.get("value"), dict):
        raise PrivateDocumentUnavailable("Documento remoto inválido.")
    value = row["value"]
    if set(value) != {"events"} or not isinstance(value["events"], list):
        raise PrivateDocumentUnavailable("Estrutura de histórico remoto inválida.")
    return value
