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
from datetime import datetime

from commercial_attribution_service import (
    build_attribution_event, clean_campaign, validate_event_history,
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
        raise PrivateStoreConflict("Histórico remoto não inicializado; criação automática proibida.")
    if not isinstance(value, dict) or set(value) != {"events"}:
        raise ValueError("Documento de auditoria em formato desconhecido.")
    events = value["events"]
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise ValueError("Histórico de auditoria inválido ou acima do limite.")
    seen_ids: set[str] = set()
    for row in events:
        if not isinstance(row, dict) or set(row) != {
            "event_id", "numero_proposta", "atendimento_id", "campaign",
            "decisao", "evidencia", "usuario", "ocorrido_em"
        }:
            raise ValueError("Evento persistido em formato inesperado.")
        event_id = row["event_id"]
        try:
            if not isinstance(event_id, str) or str(UUID(event_id)) != event_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError("ID de evento inválido ou não canônico.") from None
        if event_id in seen_ids:
            raise PrivateStoreConflict("Histórico contém ID de evento duplicado.")
        seen_ids.add(event_id)
        for field, maximum in (("numero_proposta", 120), ("atendimento_id", 120),
                               ("usuario", 80)):
            value = row[field]
            if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                raise ValueError("Identificador de evento inválido.")
        if row["numero_proposta"] != row["numero_proposta"].strip() or (
            row["atendimento_id"] != row["atendimento_id"].strip()
        ) or row["usuario"] != row["usuario"].strip():
            raise ValueError("Identificador não canônico.")
        if not isinstance(row["campaign"], str):
            raise ValueError("Campanha armazenada inválida.")
        if clean_campaign(row["campaign"]) != row["campaign"]:
            raise ValueError("Campanha não canônica.")
        if row["decisao"] not in ("confirmar", "revogar") or row["evidencia"] not in (
            "mensagem_whatsapp", "referencia_cliente", "link_utm_conferido",
            "atendimento_manual"
        ):
            raise ValueError("Decisão ou evidência inválida no histórico.")
        try:
            stamp = row["ocorrido_em"]
            if not isinstance(stamp, str):
                raise ValueError()
            moment = datetime.fromisoformat(stamp)
            if moment.tzinfo is None or moment.utcoffset() is None:
                raise ValueError()
            if moment.isoformat() != stamp:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Horário do histórico inválido.") from None
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
    before = _valid_document(load(DOCUMENT_KEY))
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
    # Somente PATCH/CAS de documento já criado e conferido separadamente.
    # A inicialização via UPSERT não é atômica com a verificação de ausência.
    ok, reason = save_cas(DOCUMENT_KEY, before, proposed)
    if ok is not True or reason != "online":
        raise PrivateStoreConflict("Gravação não confirmada; confira a revisão do documento.")
    return event
