"""HF65.24.53 — inicialização privada *somente inserir se ausente*.

Contrato experimental de homologação, NÃO integrado ao Manager/Supabase.
A operação insert_if_absent deve ser atomicamente implementada no banco
(UNIQUE(key) + INSERT ... ON CONFLICT DO NOTHING), sem upsert de atualização.
O serviço não pode confiar em uma leitura de cache ou JSON local.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from commercial_private_document_adapter import (
    DOCUMENT_KEY, PrivateStoreConflict, PrivateStoreDenied, _valid_document,
)
from commercial_operator_policy import VerifiedOperator


class BootstrapUnavailable(RuntimeError):
    pass


def initialize_private_history_if_absent(
    *, principal: VerifiedOperator,
    approve_initialization: Callable[[VerifiedOperator], bool],
    credential_mode: Callable[[], str],
    read_online: Callable[[str], Any],
    insert_if_absent: Callable[[str, dict[str, Any]], bool],
) -> str:
    """Inicializa documento vazio sem sobrescrever dados ou reparar histórico.

    Retorna 'created' se inserção atômica foi confirmada e 'existing' se
    outra sessão já inicializou documento íntegro. Ausência de confirmação,
    documento inesperado ou callbacks inseguros bloqueiam o processo.
    Permissão de bootstrap é separada de permissões de leitura e gravação.
    """
    if not isinstance(principal, VerifiedOperator) or not principal.subject.strip():
        raise PrivateStoreDenied("Operador não autenticado.")
    if not all(callable(x) for x in (
        approve_initialization, credential_mode, read_online, insert_if_absent,
    )):
        raise PrivateStoreDenied("Serviço privado incompleto.")
    try:
        allowed = (credential_mode() == "service" and
                   approve_initialization(principal) is True)
    except Exception:
        allowed = False
    if not allowed:
        raise PrivateStoreDenied("Inicialização não autorizada.")
    try:
        existing = read_online(DOCUMENT_KEY)
    except Exception:
        raise BootstrapUnavailable("Leitura remota indisponível.") from None
    if existing is not None:
        _valid_document(existing)
        return "existing"
    # insert_if_absent precisa ser uma operação condicional ATÔMICA.
    # Em hipótese alguma fazer save_document ou upsert merge-duplicates.
    try:
        inserted = insert_if_absent(DOCUMENT_KEY, {"events": []})
    except Exception:
        raise BootstrapUnavailable("Inserção privada não confirmada.") from None
    if inserted is not True and inserted is not False:
        raise BootstrapUnavailable("Resposta de inserção desconhecida.")
    try:
        after = read_online(DOCUMENT_KEY)
    except Exception:
        raise BootstrapUnavailable("Confirmação remota indisponível.") from None
    if after is None:
        raise BootstrapUnavailable("Documento ausente após a tentativa.")
    valid = _valid_document(after)
    if inserted:
        if valid != {"events": []}:
            # A criação pode ter sido seguida de uma escrita concorrente;
            # não presumir estado vazio nem retornar sucesso enganoso.
            raise PrivateStoreConflict("Histórico mudou durante a inicialização.")
        return "created"
    return "existing"
