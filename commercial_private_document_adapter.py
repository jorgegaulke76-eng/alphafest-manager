"""HF65.24.53 — adaptador opcional para app_data, NÃO ativado no Manager.

Reutiliza o documento JSON e o compare-and-swap existentes, sem criar tabela.
O chamador deve injetar exclusivamente funções confiáveis do SERVIDOR.
Sem autenticação/autorização verificada e modo service, falha fechado.
Não deve ser chamado de código público, componentes HTML ou clientes REST.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any
from uuid import UUID

from commercial_attribution_service import (
    build_attribution_event, effective_attributions, validate_event_history,
)

DOCUMENT_KEY = "hf65_24_53_attribution_events_private_db"
MAX_EVENTS = 10000


class PrivateStoreDenied(PermissionError):
    pass


class PrivateStoreConflict(RuntimeError):
    pass


def _authorized(principal: Any, action: str, authorize: Callable[[Any, str], bool],
                credential_mode: Callable[[], str]) -> None:
    """Não aceita o texto de um formulário como prova de identidade."""
    if not callable(authorize) or not callable(credential_mode):
        raise PrivateStoreDenied("Autorização do servidor obrigatória.")
    if credential_mode() != "service" or authorize(principal, action) is not True:
        raise PrivateStoreDenied("Acesso negado ou banco sem credencial de servidor.")


def _valid_document(value: Any) -> dict[str, Any]:
    if value in (None, {}):
        return {"events": []}
    if not isinstance(value, dict) or set(value) != {"events"}:
        raise ValueError("Documento de auditoria em formato desconhecido.")
    events = value["events"]
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise ValueError("Histórico de auditoria inválido ou acima do limite.")
    for row in events:
        if not isinstance(row, dict) or set(row) != {
            "event_id", "numero_proposta", "atendimento_id", "campaign",
            "decisao", "evidencia", "usuario", "ocorrido_em"
        }:
            raise ValueError("Evento persistido em formato inesperado.")
        try:
            UUID(str(row["event_id"]))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("ID de evento inválido.") from None
    return {"events": deepcopy(events)}


def read_private_events(*, principal: Any, authorize: Callable[[Any, str], bool],
                        credential_mode: Callable[[], str],
                        load: Callable[[str], Any]) -> list[dict[str, str]]:
    _authorized(principal, "read_attribution", authorize, credential_mode)
    if not callable(load):
        raise PrivateStoreDenied("Leitura oficial indisponível.")
    return _valid_document(load(DOCUMENT_KEY))["events"]


def append_private_event(*, principal: Any,
                         authorize: Callable[[Any, str], bool],
                         credential_mode: Callable[[], str],
                         load: Callable[[str], Any],
                         save_cas: Callable[[str, Any, Any], tuple[bool, str]],
                         event_id: str, numero_proposta: str, atendimento_id: str,
                         campaign: str, decisao: str, evidencia: str,
                         ocorrido_em: str, usuario_verificado: str,
                         propostas: list[dict[str, Any]],
                         atendimentos: list[dict[str, Any]]) -> dict[str, str]:
    """Somente grava com identidade validada e CAS confirmado pelo servidor.

    save_cas deve apontar para cloud_db.save_document_cas com local_path
    configurado exclusivamente pelo servidor e sem aceitar fallback local.
    O evento é criado novamente a partir de dados oficiais no momento da
    operação; o operador deve vir da sessão autenticada, nunca do formulário.
    """
    _authorized(principal, "write_attribution", authorize, credential_mode)
    if not callable(load) or not callable(save_cas):
        raise PrivateStoreDenied("Persistência de servidor não configurada.")
    try:
        UUID(str(event_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("ID idempotente inválido.") from None
    event = build_attribution_event(
        numero_proposta=numero_proposta, atendimento_id=atendimento_id,
        campaign=campaign, decisao=decisao, evidencia=evidencia,
        usuario=usuario_verificado, ocorrido_em=ocorrido_em,
        propostas=propostas, atendimentos=atendimentos,
    )
    raw_before = load(DOCUMENT_KEY)
    before = _valid_document(raw_before)
    existing = [e for e in before["events"] if e["event_id"] == str(event_id)]
    full = {"event_id": str(event_id), **event}
    if existing:
        if len(existing) == 1 and existing[0] == full:
            return event
        raise PrivateStoreConflict("ID de evento reutilizado com conteúdo diferente.")
    if len(before["events"]) >= MAX_EVENTS:
        raise PrivateStoreConflict("Limite de auditoria atingido; arquivamento necessário.")
    validated = validate_event_history(
        [dict(x) for x in before["events"] if x["numero_proposta"] == numero_proposta],
        propostas, atendimentos,
    )
    related = [x for x in before["events"] if x["numero_proposta"] == numero_proposta]
    if len(validated) != len(related):
        raise PrivateStoreConflict("Histórico existente contém evento inconsistente.")
    if related and any(e["atendimento_id"] != atendimento_id for e in related):
        raise PrivateStoreConflict("Pedido possui outro atendimento no histórico.")
    proposed = {"events": before["events"] + [full]}
    # O documento ainda pode não existir: CAS espera a versão real lida.
    expected = raw_before if raw_before in (None, {}) else before
    ok, reason = save_cas(DOCUMENT_KEY, expected, proposed)
    if ok is not True or reason != "online":
        raise PrivateStoreConflict("Gravação não confirmada; confira a revisão do documento.")
    return event
