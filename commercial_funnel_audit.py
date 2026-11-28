"""HF65.24.53 — auditoria somente leitura do funil da Central de Oportunidades.

Não reclassifica o histórico nem presume recebimento a partir do campo
'etapa_captacao' = 'Venda fechada'. Não há cálculo monetário neste módulo.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from proposal_status import status_bool, proposta_encerrada


def audit_opportunity_funnel(
    contacts: Iterable[Mapping[str, Any]],
    proposals: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    """Indicadores de diagnóstico; nunca equivalem a vendas atribuídas a campanhas.

    O vínculo usado é o identificador explícito atendimento.id ↔
    proposta.atendimento_id existente no Manager. Números de proposta
    duplicados são tratados como ambíguos e excluídos do indicador de pagos.
    """
    contacts = [c for c in contacts if isinstance(c, Mapping)]
    proposals = [p for p in proposals if isinstance(p, Mapping)]
    ids: set[str] = set()
    duplicates: set[str] = set()
    for c in contacts:
        cid = str(c.get("id") or "").strip()
        if cid in ids:
            duplicates.add(cid)
        elif cid:
            ids.add(cid)

    unique_contacts = {
        str(c.get("id")).strip(): c for c in contacts
        if str(c.get("id") or "").strip()
        and str(c.get("id")).strip() not in duplicates
    }
    proposal_ids: set[str] = set()
    duplicate_proposals: set[str] = set()
    for p in proposals:
        number = str(p.get("numero_proposta") or "").strip()
        if number in proposal_ids:
            duplicate_proposals.add(number)
        elif number:
            proposal_ids.add(number)

    linked = defaultdict(list)
    for p in proposals:
        number = str(p.get("numero_proposta") or "").strip()
        aid = str(p.get("atendimento_id") or "").strip()
        if number and number not in duplicate_proposals and aid in unique_contacts:
            linked[aid].append(p)

    marked_sales = sum(
        str(c.get("etapa_captacao") or "").strip().casefold() == "venda fechada"
        for c in unique_contacts.values()
    )
    linked_ids = {aid for aid, values in linked.items() if values}
    paid_proposals = sum(
        status_bool(dict(p), "pago") and not proposta_encerrada(dict(p))
        for values in linked.values() for p in values
    )
    return {
        "contatos_unicos": len(unique_contacts),
        "marcados_venda_fechada": marked_sales,
        "contatos_com_proposta_vinculada": len(linked_ids),
        "propostas_pagamento_confirmado": paid_proposals,
        "vendas_atribuidas_campanha": 0,  # Exige reconciliação comercial separada.
    }
