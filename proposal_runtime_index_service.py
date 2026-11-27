"""Índices leves de leitura para propostas/orçamentos do AlphaFest Manager.

HF40: consolida, em uma única passagem, filtros e chaves usados na Central da
Anna e oferece uma visão atualizada do contato sem revarrer Clientes para cada
proposta. O módulo é puro e somente leitura: não grava nem altera propostas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class ProposalRuntimeIndex:
    items: tuple[dict[str, Any], ...]
    active: tuple[dict[str, Any], ...]
    active_recent: tuple[dict[str, Any], ...]
    today_recent: tuple[dict[str, Any], ...]
    deliveries_today: tuple[dict[str, Any], ...]
    by_number: dict[str, dict[str, Any]]
    search_text_by_object: dict[int, str]


def proposal_search_text(prop: dict[str, Any] | None) -> str:
    """Replica o texto histórico da busca rápida de propostas."""
    prop = prop or {}
    partes = [
        prop.get("numero_proposta", ""),
        prop.get("cliente_nome", ""),
        prop.get("whatsapp", prop.get("cliente_wa", "")),
        prop.get("documento", prop.get("cliente_cpf_cnpj", "")),
    ]
    partes.extend(item.get("produto", "") for item in (prop.get("itens", []) or []) if isinstance(item, dict))
    return " ".join(str(p) for p in partes).lower()


def proposal_recent_key(prop: dict[str, Any] | None) -> datetime:
    """Mesma chave de ordenação usada historicamente pela Central da Anna."""
    prop = prop or {}
    texto = str(
        prop.get("data_geracao")
        or prop.get("criado_em")
        or prop.get("created_at")
        or prop.get("data")
        or ""
    )
    formatos = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato)
        except (ValueError, TypeError):
            continue
    return datetime.min


def _value_is_today(value: Any, today: date) -> bool:
    """Replica `registro_eh_de_hoje` usando a data já resolvida do rerun."""
    if not value:
        return False
    texto = str(value).strip()
    formatos = (
        "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).date() == today
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date() == today
    except (ValueError, TypeError):
        return False


def proposal_is_today(prop: dict[str, Any] | None, today: date) -> bool:
    prop = prop or {}
    return any(
        _value_is_today(prop.get(campo), today)
        for campo in ("data_geracao", "data", "criado_em", "created_at")
    )


def _delivery_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value), "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def build_proposal_runtime_index(
    historico: Iterable[dict[str, Any]] | None,
    *,
    active_predicate: Callable[[dict[str, Any]], bool],
    today: date,
) -> ProposalRuntimeIndex:
    """Prepara a fotografia de leitura usada na Central em uma única passagem."""
    items = tuple(p for p in (historico or []) if isinstance(p, dict))
    active: list[dict[str, Any]] = []
    today_items: list[dict[str, Any]] = []
    deliveries_today: list[dict[str, Any]] = []
    by_number: dict[str, dict[str, Any]] = {}
    search_text_by_object: dict[int, str] = {}

    for prop in items:
        numero = str(prop.get("numero_proposta") or "").strip()
        if numero and numero not in by_number:
            by_number[numero] = prop
        search_text_by_object[id(prop)] = proposal_search_text(prop)

        is_active = bool(active_predicate(prop))
        if not is_active:
            continue
        active.append(prop)
        if proposal_is_today(prop, today):
            today_items.append(prop)
        if _delivery_date(prop.get("data_entrega")) == today:
            deliveries_today.append(prop)

    active_recent = tuple(sorted(active, key=proposal_recent_key, reverse=True))
    today_recent = tuple(sorted(today_items, key=proposal_recent_key, reverse=True))
    return ProposalRuntimeIndex(
        items=items,
        active=tuple(active),
        active_recent=active_recent,
        today_recent=today_recent,
        deliveries_today=tuple(deliveries_today),
        by_number=by_number,
        search_text_by_object=search_text_by_object,
    )


def filter_active_recent(index: ProposalRuntimeIndex, term: str = "") -> list[dict[str, Any]]:
    """Filtra a lista ativa já ordenada sem reconstruir o texto de cada proposta."""
    needle = str(term or "").strip().lower()
    if not needle:
        return list(index.active_recent)
    return [
        prop
        for prop in index.active_recent
        if needle in index.search_text_by_object.get(id(prop), proposal_search_text(prop))
    ]


def proposal_with_current_client_data(
    proposta: dict[str, Any] | None,
    cliente_atual: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Replica a visão atual do contato sem reler a base de Clientes.

    O cliente já vem resolvido por um índice externo. Itens, valores, datas e
    status continuam vindo integralmente da proposta histórica.
    """
    proposta = proposta or {}
    if not cliente_atual:
        return dict(proposta), None
    visao = dict(proposta)
    nome = cliente_atual.get("nome") or visao.get("cliente_nome", visao.get("cliente", ""))
    documento = cliente_atual.get("documento") or visao.get("documento", visao.get("cliente_cpf_cnpj", ""))
    whatsapp = cliente_atual.get("whatsapp") or visao.get("whatsapp", visao.get("cliente_wa", ""))
    visao.update({
        "cliente_nome": nome,
        "cliente": nome,
        "documento": documento,
        "cliente_cpf_cnpj": documento,
        "whatsapp": whatsapp,
        "cliente_wa": whatsapp,
        "email": cliente_atual.get("email", visao.get("email", "")),
        "cidade": cliente_atual.get("cidade", visao.get("cidade", "")),
        "relacionamento_id": cliente_atual.get("id", visao.get("relacionamento_id", "")),
    })
    return visao, cliente_atual
