"""Contrato do relatório comercial privado HF65.24.53."""
from decimal import Decimal
import pytest

from commercial_verified_report import build_verified_commercial_report
from commercial_attribution_service import build_attribution_event


CONTACTS = [{"id": "A1", "etapa_captacao": "Venda fechada"}]
ORDERS = [{"numero_proposta": "P1", "atendimento_id": "A1",
           "pago": True, "valor_total": "125,90"}]


def link():
    return build_attribution_event(
        numero_proposta="P1", atendimento_id="A1", campaign="natal-2026",
        decisao="confirmar", evidencia="mensagem_whatsapp",
        usuario="operador_teste", ocorrido_em="2026-11-23T16:00:00-03:00",
        propostas=ORDERS, atendimentos=CONTACTS,
    )


def test_paid_order_with_verified_link_and_no_double_count():
    result = build_verified_commercial_report(CONTACTS, ORDERS, [link()])
    assert result["marcacoes_venda_fechada"] == 1
    assert result["pedidos_pagos_atribuidos"] == 1
    assert result["receita_atribuida"] == Decimal("125.90")
    assert result["campanhas"] == [
        {"campanha": "natal-2026",
         "pedidos_pagos_atribuidos": 1,
         "receita_atribuida": Decimal("125.90")}
    ]


def test_marked_sale_without_paid_order_is_not_revenue():
    orders = [dict(ORDERS[0], pago=False)]
    result = build_verified_commercial_report(CONTACTS, orders, [link()])
    assert result["marcacoes_venda_fechada"] == 1
    assert result["pedidos_pagos_atribuidos"] == 0
    assert result["receita_atribuida"] == 0


def test_link_without_confirmed_manual_evidence_has_no_revenue():
    result = build_verified_commercial_report(CONTACTS, ORDERS, [])
    assert result["receita_atribuida"] == 0


def test_changed_contact_link_refuses_attribution():
    changed = [dict(ORDERS[0], atendimento_id="A2")]
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        build_verified_commercial_report(CONTACTS, changed, [link()])

def test_duplicate_contact_id_refuses_attribution():
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        build_verified_commercial_report(CONTACTS + CONTACTS, ORDERS, [link()])

def test_duplicate_order_refuses_attribution():
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        build_verified_commercial_report(CONTACTS, ORDERS + ORDERS, [link()])

def test_cancelled_paid_order_excluded():
    cancelled = [dict(ORDERS[0], cancelado_cliente=True)]
    result = build_verified_commercial_report(CONTACTS, cancelled, [link()])
    assert result["receita_atribuida"] == 0


def test_revoked_attribution_excluded():
    revocation = dict(link(), decisao="revogar",
                      ocorrido_em="2026-11-23T16:01:00-03:00")
    result = build_verified_commercial_report(CONTACTS, ORDERS, [link(), revocation])
    assert result["receita_atribuida"] == 0


def test_forged_event_without_operator_or_evidence_is_rejected():
    forged = {"numero_proposta": "P1", "atendimento_id": "A1",
              "campaign": "natal-2026", "decisao": "confirmar",
              "ocorrido_em": "2026-11-23T16:00:00-03:00"}
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        build_verified_commercial_report(CONTACTS, ORDERS, [forged])

def test_invalid_intermediate_event_invalidates_entire_order_history():
    first = link()
    invalid = dict(link(), campaign="cliente@email.com",
                   ocorrido_em="2026-11-23T16:01:00-03:00")
    last = dict(link(), ocorrido_em="2026-11-23T16:02:00-03:00")
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        build_verified_commercial_report(CONTACTS, ORDERS, [first, invalid, last])

def test_event_operator_and_evidence_must_be_valid():
    bad = dict(link(), usuario="", evidencia="desconhecida")
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        build_verified_commercial_report(CONTACTS, ORDERS, [bad])

def test_manager_real_proposal_fields_are_commercial_not_bank_settlement():
    # app.py armazena valor_total e booleano pago nas propostas comuns.
    # Este cenário gera indicador COMERCIAL, não prova crédito financeiro.
    result = build_verified_commercial_report(CONTACTS, ORDERS, [link()])
    assert result["receita_atribuida"] == Decimal("125.90")
    assert "NÃO comprova crédito bancário" in result["aviso"]
    assert "valor_total/total é preço do pedido" in result["aviso"]


def test_monthly_billing_snapshot_excluded_even_when_marked_paid():
    # Fechamentos mensais são um documento separado do histórico de propostas.
    monthly = [dict(ORDERS[0], faturamento_mensal=True)]
    result = build_verified_commercial_report(CONTACTS, monthly, [link()])
    assert result["receita_atribuida"] == 0
    assert result["pedidos_pagos_atribuidos"] == 0
    assert "Fechamentos mensais ficam excluídos" in result["aviso"]


def test_explicit_partial_receipt_cannot_be_counted_as_full_campaign_sale():
    partial = [dict(ORDERS[0], valor_recebido="50,00")]
    result = build_verified_commercial_report(CONTACTS, partial, [link()])
    assert result["receita_atribuida"] == 0
    assert result["pedidos_pagos_atribuidos"] == 0
