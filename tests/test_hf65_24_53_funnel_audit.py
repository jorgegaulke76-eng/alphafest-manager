"""Contrato de leitura do funil: não confundir estágio com pagamento."""
from commercial_funnel_audit import audit_opportunity_funnel


def test_marked_sale_does_not_prove_payment():
    result = audit_opportunity_funnel(
        [{"id": "a", "etapa_captacao": "Venda fechada", "campanha": "natal"}],
        [{"numero_proposta": "P1", "atendimento_id": "a", "aprovado": True, "pago": False}],
    )
    assert result["marcados_venda_fechada"] == 1
    assert result["contatos_com_proposta_vinculada"] == 1
    assert result["propostas_pagamento_confirmado"] == 0
    assert result["vendas_atribuidas_campanha"] == 0


def test_paid_proposal_without_manual_attribution_still_not_campaign_sale():
    result = audit_opportunity_funnel(
        [{"id": "a", "etapa_captacao": "Orçamento criado", "campanha": "natal"}],
        [{"numero_proposta": "P1", "atendimento_id": "a", "pago": True}],
    )
    assert result["propostas_pagamento_confirmado"] == 1
    assert result["vendas_atribuidas_campanha"] == 0


def test_duplicate_contacts_proposals_and_cancellation_excluded():
    result = audit_opportunity_funnel(
        [{"id": "a", "etapa_captacao": "Venda fechada"},
         {"id": "a", "etapa_captacao": "Venda fechada"},
         {"id": "b", "etapa_captacao": "Venda fechada"}],
        [{"numero_proposta": "P1", "atendimento_id": "b", "pago": True},
         {"numero_proposta": "P1", "atendimento_id": "b", "pago": True},
         {"numero_proposta": "P2", "atendimento_id": "b",
          "pago": True, "cancelado_cliente": True},
         {"numero_proposta": "P3", "atendimento_id": "a", "pago": True}],
    )
    assert result == {
        "contatos_unicos": 1,
        "marcados_venda_fechada": 1,
        "contatos_com_proposta_vinculada": 1,
        "propostas_pagamento_confirmado": 0,
        "vendas_atribuidas_campanha": 0,
    }
