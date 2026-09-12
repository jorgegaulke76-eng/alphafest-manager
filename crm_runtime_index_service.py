"""Índice leve de leitura para Atendimentos / CRM do AlphaFest Manager.

HF34: evita varrer Clientes e Histórico inteiro uma vez por atendimento para
calcular o Índice Alpha. O módulo é puro e somente leitura: não grava, não muda
status e não altera a fila operacional.
"""
from __future__ import annotations

from typing import Any, Callable


def _name_key(value: Any) -> str:
    return str(value or "").strip().lower()


def build_crm_read_index(
    historico: list[dict[str, Any]] | None,
    clientes: list[dict[str, Any]] | None,
    *,
    phone_key: Callable[[Any], str],
    proposal_total: Callable[[dict[str, Any]], float],
) -> dict[str, Any]:
    """Pré-indexa clientes e propostas usados pelo cálculo do Índice Alpha.

    As propostas são guardadas por posição. Quando telefone e nome apontam para
    a mesma proposta, a união por posição impede contagem em duplicidade e
    reproduz o ``OR`` da implementação histórica.
    """
    client_phones: set[str] = set()
    client_names: set[str] = set()
    for raw in clientes or []:
        if not isinstance(raw, dict):
            continue
        tel = str(phone_key(raw.get("whatsapp") or raw.get("telefone")) or "")
        nome = _name_key(raw.get("nome"))
        if tel:
            client_phones.add(tel)
        if nome:
            client_names.add(nome)

    proposals: list[dict[str, Any]] = []
    by_phone: dict[str, list[int]] = {}
    by_name: dict[str, list[int]] = {}

    for raw in historico or []:
        if not isinstance(raw, dict):
            continue
        tel = str(phone_key(raw.get("cliente_whatsapp") or raw.get("whatsapp") or raw.get("telefone")) or "")
        nome = _name_key(raw.get("cliente_nome"))
        qualifies = bool(raw.get("aprovado") or raw.get("pago"))
        total = 0.0
        if qualifies:
            try:
                total = float(proposal_total(raw) or 0.0)
            except Exception:
                total = 0.0

        pos = len(proposals)
        proposals.append({"qualifies": qualifies, "total": total})
        if tel:
            by_phone.setdefault(tel, []).append(pos)
        if nome:
            by_name.setdefault(nome, []).append(pos)

    return {
        "client_phones": client_phones,
        "client_names": client_names,
        "proposals": proposals,
        "by_phone": by_phone,
        "by_name": by_name,
        "history_size": len(proposals),
        "client_size": len(client_phones) + len(client_names),
    }


def crm_relationship_stats(
    item: dict[str, Any] | None,
    index: dict[str, Any] | None,
    *,
    phone_key: Callable[[Any], str],
) -> dict[str, Any]:
    """Retorna cadastro existente + compras/valor histórico para um atendimento."""
    item = item or {}
    index = index or {}
    tel = str(phone_key(item.get("telefone")) or "")
    nome = _name_key(item.get("cliente"))

    client_exists = bool(
        (tel and tel in (index.get("client_phones") or set()))
        or (nome and nome in (index.get("client_names") or set()))
    )

    positions: set[int] = set()
    if tel:
        positions.update(int(p) for p in (index.get("by_phone") or {}).get(tel, []))
    if nome:
        positions.update(int(p) for p in (index.get("by_name") or {}).get(nome, []))

    proposals = index.get("proposals") or []
    compras = 0
    valor_historico = 0.0
    for pos in positions:
        if pos < 0 or pos >= len(proposals):
            continue
        row = proposals[pos]
        if row.get("qualifies"):
            compras += 1
            try:
                valor_historico += float(row.get("total") or 0.0)
            except Exception:
                pass

    return {
        "client_exists": client_exists,
        "purchases": compras,
        "historical_value": valor_historico,
        "matched_proposals": len(positions),
    }
