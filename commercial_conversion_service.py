"""HF65.24.53 — reconciliação comercial determinística e somente leitura.

Não consulta Supabase, não altera pedidos nem deduz vendas de cliques.
Aceita propostas oficiais com número e flags de pagamento e associações
explícitas e auditáveis fornecidas pelo operador. Ainda não ligado à UI.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Iterable, Mapping

from proposal_status import (
    proposta_encerrada,
    proposta_faturamento_mensal,
    status_bool,
)


def _amount(value: Any) -> Decimal | None:
    """Lê centavos apenas em formatos inequívocos; nunca arredonda silenciosamente.

    Aceita inteiro simples, decimal com exatamente duas casas, formato BRL
    agrupado com vírgula e número Decimal/float finito já estruturado.
    Recusa pontos ambíguos (1.234), notação exponencial e três casas.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            numeric = Decimal(str(value))
            if numeric.is_finite() and numeric > 0 and numeric.as_tuple().exponent >= -2:
                return numeric
        except (InvalidOperation, ValueError, TypeError):
            pass
        return None
    raw = str(value).strip()
    if raw.startswith("R$"):
        raw = raw[2:].strip()
    if not raw:
        return None
    if "," in raw:
        # BR: 1234,56 ou 1.234,56. Não aceitar separadores inconsistentes.
        match = re.fullmatch(r"(?:[0-9]+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+),[0-9]{2}", raw)
        if not match:
            return None
        raw = raw.replace(".", "").replace(",", ".")
    elif "." in raw:
        if not re.fullmatch(r"[0-9]+\.[0-9]{2}", raw):
            return None
    elif not re.fullmatch(r"[0-9]+", raw):
        return None
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return amount if amount.is_finite() and amount > 0 else None

def summarize_verified_campaign_sales(
    orders: Iterable[Mapping[str, Any]],
    attributions: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Contabiliza apenas propostas oficiais pagas com vínculo inequívoco.

    orders: numero_proposta, pago, cancelado_cliente, modalidade_cobranca,
      e total/valor_total/total_geral (quando preço fechado confirmado).
    attributions: numero_proposta, campaign; vínculo informado e conferido
      manualmente, nunca inferido por CPF, telefone, nome ou sessão.

    Exclui propostas encerradas/canceladas, mensalistas (liquidação deve vir
    de sua fonte financeira), IDs duplicados, valores inválidos e vínculos
    de campanha contraditórios.
    """
    by_order: dict[str, set[str]] = defaultdict(set)
    for item in attributions:
        order_id = str(item.get("numero_proposta") or "").strip()
        campaign = str(item.get("campaign") or "").strip().lower()
        if order_id and campaign and len(campaign) <= 120 and all(
            ch.isascii() and (ch.isalnum() or ch in "_-") for ch in campaign
        ):
            # Não armazenar dados pessoais nem texto livre no identificador.
            if not re.search(r"\d{9,}", campaign):
                by_order[order_id].add(campaign)

    seen: set[str] = set()
    duplicate: set[str] = set()
    unique: dict[str, Mapping[str, Any]] = {}
    for order in orders:
        number = str(order.get("numero_proposta") or "").strip()
        if not number:
            continue
        if number in seen:
            duplicate.add(number)
        seen.add(number)
        unique[number] = order

    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"paid_orders": 0, "paid_revenue": Decimal("0")}
    )
    for number, order in unique.items():
        if number in duplicate or len(by_order[number]) != 1:
            continue
        if not status_bool(dict(order), "pago"):
            continue
        if proposta_encerrada(dict(order)) or proposta_faturamento_mensal(dict(order)):
            continue
        # Não estimar valor a partir de preço de catálogo ou métricas.
        raw_amount = next(
            (order[key] for key in ("valor_total", "total", "total_geral")
             if order.get(key) not in (None, "")), None
        )
        amount = _amount(raw_amount)
        if amount is None:
            continue
        campaign = next(iter(by_order[number]))
        totals[campaign]["paid_orders"] += 1
        totals[campaign]["paid_revenue"] += amount
    return dict(totals)
