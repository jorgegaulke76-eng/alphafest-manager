"""HF65.24.53 — reconciliação comercial determinística, sem I/O.

Este módulo não consulta Supabase, não altera pedidos e não deduz venda a partir
de um clique. Só considera confirmações explicitamente vinculadas a um pedido.
A integração com o Manager dependerá de revisão do esquema existente.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Any

CONFIRMED = frozenset({"pago", "paid"})
PENDING = frozenset({"orcamento", "orçamento", "pendente", "aprovado", "pronto", "entregue"})


def _amount(value: Any) -> Decimal | None:
    """Aceita apenas quantias não negativas fornecidas pela origem financeira."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def summarize_verified_campaign_sales(
    orders: Iterable[Mapping[str, Any]],
    attributions: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Soma pedidos PAGOS com vínculo explícito e unívoco a uma campanha.

    orders: order_id, status, amount.
    attributions: order_id, campaign (reconciliação confirmada no atendimento).

    Não aceita inferência por telefone, nome, data, sessão ou clique.
    IDs de pedido duplicados/conflitantes e múltiplas campanhas são excluídos.
    O chamador deve fornecer dados já autorizados, sem PII.
    """
    by_order: dict[str, set[str]] = defaultdict(set)
    for item in attributions:
        order_id = str(item.get("order_id") or "").strip()
        campaign = str(item.get("campaign") or "").strip().lower()
        if order_id and campaign and len(campaign) <= 120 and all(
            c.isascii() and (c.isalnum() or c in "_-") for c in campaign
        ):
            by_order[order_id].add(campaign)

    seen: set[str] = set()
    conflicted: set[str] = set()
    unique: dict[str, Mapping[str, Any]] = {}
    for order in orders:
        order_id = str(order.get("order_id") or "").strip()
        if not order_id:
            continue
        if order_id in seen:
            conflicted.add(order_id)
        seen.add(order_id)
        unique[order_id] = order

    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"paid_orders": 0, "paid_revenue": Decimal("0")}
    )
    for order_id, order in unique.items():
        if order_id in conflicted or len(by_order[order_id]) != 1:
            continue
        if str(order.get("status") or "").strip().lower() not in CONFIRMED:
            continue
        amount = _amount(order.get("amount"))
        if amount is None:
            continue
        campaign = next(iter(by_order[order_id]))
        totals[campaign]["paid_orders"] += 1
        totals[campaign]["paid_revenue"] += amount
    return dict(totals)
