"""Testes isolados da reconciliação HF65.24.53."""
from decimal import Decimal

from commercial_conversion_service import summarize_verified_campaign_sales as summarize


def test_only_official_paid_with_explicit_order_link():
    actual = summarize(
        [
            {"numero_proposta": "1", "pago": True, "valor_total": "129,90"},
            {"numero_proposta": "2", "aprovado": True, "pago": False, "valor_total": "70,00"},
            {"numero_proposta": "3", "pago": True, "valor_total": "100,00"},
        ],
        [
            {"numero_proposta": "1", "campaign": "natal-2026"},
            {"numero_proposta": "2", "campaign": "natal-2026"},
        ],
    )
    assert actual == {"natal-2026": {"paid_orders": 1, "paid_revenue": Decimal("129.90")}}


def test_ambiguous_or_duplicate_link_excluded():
    actual = summarize(
        [
            {"numero_proposta": "1", "pago": True, "valor_total": "50"},
            {"numero_proposta": "2", "pago": True, "valor_total": "40"},
            {"numero_proposta": "2", "pago": True, "valor_total": "40"},
        ],
        [
            {"numero_proposta": "1", "campaign": "facebook"},
            {"numero_proposta": "1", "campaign": "instagram"},
            {"numero_proposta": "2", "campaign": "natal"},
        ],
    )
    assert actual == {}


def test_refuse_invalid_amount_and_personal_data_in_campaign():
    actual = summarize(
        [
            {"numero_proposta": "1", "pago": True, "valor_total": "-1"},
            {"numero_proposta": "2", "pago": True, "valor_total": "NaN"},
            {"numero_proposta": "3", "pago": True, "valor_total": "19.90"},
            {"numero_proposta": "4", "pago": True, "valor_total": True},
        ],
        [
            {"numero_proposta": "1", "campaign": "natal"},
            {"numero_proposta": "2", "campaign": "natal"},
            {"numero_proposta": "3", "campaign": "cliente@email.com"},
            {"numero_proposta": "4", "campaign": "natal"},
        ],
    )
    assert actual == {}


def test_duplicate_identical_attribution_does_not_duplicate_revenue():
    actual = summarize(
        [{"numero_proposta": "1", "pago": True, "valor_total": "12.50"}],
        [{"numero_proposta": "1", "campaign": "campanha_a"},
         {"numero_proposta": "1", "campaign": "campanha_a"}],
    )
    assert actual["campanha_a"] == {"paid_orders": 1, "paid_revenue": Decimal("12.50")}


def test_cancelled_and_monthly_billing_excluded():
    actual = summarize(
        [
            {"numero_proposta": "1", "pago": True, "cancelado_cliente": True, "valor_total": "100"},
            {"numero_proposta": "2", "pago": True, "faturamento_mensal": True, "valor_total": "200"},
            {"numero_proposta": "3", "pago": True, "status_comercial": "recusado", "valor_total": "300"},
        ],
        [{"numero_proposta": str(i), "campaign": "natal"} for i in (1, 2, 3)],
    )
    assert actual == {}


def test_brazilian_format():
    result = summarize(
        [{"numero_proposta": "1", "pago": True, "valor_total": "R$ 1.234,56"}],
        [{"numero_proposta": "1", "campaign": "campanha_1"}],
    )
    assert result["campanha_1"]["paid_revenue"] == Decimal("1234.56")
