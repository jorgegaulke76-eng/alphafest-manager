"""HF65.24.53 — demonstrativo comercial privado, puro e somente leitura.

Não consulta Supabase nem deduz receita de tráfego ou status do atendimento.
Recebe snapshots já autorizados; devolve somente agregados por campanha.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any, Iterable, Mapping

from commercial_attribution_service import effective_attributions
from commercial_conversion_service import summarize_verified_campaign_sales
from commercial_funnel_audit import audit_opportunity_funnel


def build_verified_commercial_report(
    contacts: Iterable[Mapping[str, Any]],
    proposals: Iterable[Mapping[str, Any]],
    audited_events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Consolida separadamente fatos do atendimento e receita conservadora.

    Os eventos auditados precisam vir de armazenamento privado autorizado.
    Jamais construir a partir de web analytics.
    """
    contacts = [dict(x) for x in contacts if isinstance(x, Mapping)]
    proposals = [dict(x) for x in proposals if isinstance(x, Mapping)]
    events = [dict(x) for x in audited_events if isinstance(x, Mapping)]
    audit = audit_opportunity_funnel(contacts, proposals)
    links = effective_attributions(events)

    # Recusar atribuição se a ligação mudou após a confirmação.
    proposal_counts = Counter(
        str(p.get("numero_proposta") or "").strip() for p in proposals
    )
    contact_counts = Counter(str(c.get("id") or "").strip() for c in contacts)
    indexed = {
        str(p.get("numero_proposta") or "").strip(): p for p in proposals
        if str(p.get("numero_proposta") or "").strip()
    }
    verified = []
    for link in links:
        number = link["numero_proposta"]
        p = indexed.get(number)
        if not p or proposal_counts[number] != 1:
            continue
        aid = str(p.get("atendimento_id") or "").strip()
        if not aid or contact_counts[aid] != 1:
            continue
        rows = [
            e for e in events if str(e.get("numero_proposta") or "").strip() == number
        ]
        if not rows or any(
            str(e.get("atendimento_id") or "").strip() != aid for e in rows
        ):
            continue
        verified.append(link)

    sales = summarize_verified_campaign_sales(proposals, verified)
    campaigns = [
        {
            "campanha": key,
            "pedidos_pagos_atribuidos": record["paid_orders"],
            "receita_atribuida": record["paid_revenue"],
        }
        for key, record in sorted(sales.items())
    ]
    return {
        "contatos_unicos": audit["contatos_unicos"],
        "marcacoes_venda_fechada": audit["marcados_venda_fechada"],
        "propostas_pagamento_confirmado": audit["propostas_pagamento_confirmado"],
        "pedidos_pagos_atribuidos": sum(x["pedidos_pagos_atribuidos"] for x in campaigns),
        "receita_atribuida": sum((x["receita_atribuida"] for x in campaigns), Decimal("0")),
        "campanhas": campaigns,
        "aviso": (
            "Receita atribuída experimental: apenas propostas pagas com vínculo "
            "manual inequívoco. Não representa liquidação contábil nem mensagens "
            "recebidas automaticamente. Mensalistas, estornos e pagamentos parciais "
            "exigem reconciliação financeira separada."
        ),
    }
