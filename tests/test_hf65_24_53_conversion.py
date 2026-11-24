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



def test_refuse_ambiguous_or_overprecise_amounts():
    orders = [
        {"numero_proposta": str(n), "pago": True, "valor_total": value}
        for n, value in enumerate(
            ["1.234", "12.345", "1e3", "R$ 1.23,45", "R$ 1.234", "0,00",
             "-100,00", "100,0", "100.000", "1_000", "1.234,567"], 1
        )
    ]
    links = [{"numero_proposta": str(n), "campaign": "natal"}
             for n in range(1, len(orders) + 1)]
    assert summarize(orders, links) == {}


def test_precise_cents_and_structured_numbers():
    result = summarize(
        [
            {"numero_proposta": "1", "pago": True, "total": "1.234,56"},
            {"numero_proposta": "2", "pago": True, "total": "1234.56"},
            {"numero_proposta": "3", "pago": True, "total": 12.5},
            {"numero_proposta": "4", "pago": True, "total": Decimal("0.25")},
        ],
        [{"numero_proposta": str(i), "campaign": "natal"} for i in range(1, 5)],
    )
    assert result["natal"]["paid_orders"] == 4
    assert result["natal"]["paid_revenue"] == Decimal("2481.87")


def test_refuse_nonpositive_and_float_with_fractional_cent():
    result = summarize(
        [
            {"numero_proposta": "1", "pago": True, "total": 0},
            {"numero_proposta": "2", "pago": True, "total": 1.234},
            {"numero_proposta": "3", "pago": True, "total": Decimal("10.001")},
        ],
        [{"numero_proposta": str(i), "campaign": "natal"} for i in (1, 2, 3)],
    )
    assert result == {}


def test_invalid_link_for_same_order_blocks_otherwise_valid_attribution():
    orders = [{"numero_proposta": "1", "pago": True, "valor_total": "120,00"}]
    links = [
        {"numero_proposta": "1", "campaign": "natal_2026"},
        {"numero_proposta": "1", "campaign": "cliente@email.com"},
    ]
    assert summarize(orders, links) == {}


def test_sensitive_number_in_second_link_invalidates_order():
    orders = [{"numero_proposta": "1", "pago": True, "total": "120,00"}]
    links = [
        {"numero_proposta": "1", "campaign": "natal"},
        {"numero_proposta": "1", "campaign": "11999999999"},
    ]
    assert summarize(orders, links) == {}


def test_payment_partials_refunds_and_pending_balances_require_review():
    base = {"pago": True, "valor_total": "200,00"}
    variations = [
        {"pagamento_parcial": True},
        {"pago_parcial": "sim"},
        {"estornado": True},
        {"reembolsado": True},
        {"chargeback": True},
        {"status_pagamento": "Parcialmente pago"},
        {"situacao_pagamento": "estornado"},
        {"status_financeiro": "Pendente"},
        {"valor_pago": "100,00"},
        {"valor_recebido": "150,00"},
        {"total_recebido": "NaN"},
        {"valor_estornado": "30,00"},
        {"valor_reembolsado": "10,00"},
        {"saldo_pendente": "50,00"},
        {"saldo_devedor": "10,00"},
    ]
    orders = [dict(base, numero_proposta=str(i), **variation)
              for i, variation in enumerate(variations, 1)]
    links = [{"numero_proposta": str(i), "campaign": "natal"}
             for i in range(1, len(orders) + 1)]
    assert summarize(orders, links) == {}


def test_full_payment_with_explicit_amount_remains_commercial_not_accounting():
    order = {
        "numero_proposta": "fully-paid", "pago": True,
        "valor_total": "250,00", "valor_recebido": "250,00",
        "valor_estornado": "0,00", "saldo_pendente": "0,00",
    }
    result = summarize([order], [{"numero_proposta": "fully-paid", "campaign": "natal"}])
    assert result["natal"] == {"paid_orders": 1, "paid_revenue": Decimal("250.00")}


def test_one_partial_payment_does_not_hide_other_fully_paid_order():
    orders = [
        {"numero_proposta": "1", "pago": True, "valor_total": "100,00",
         "valor_pago": "40,00"},
        {"numero_proposta": "2", "pago": True, "valor_total": "80,00",
         "valor_pago": "80,00"},
    ]
    links = [{"numero_proposta": str(i), "campaign": "natal"} for i in (1, 2)]
    assert summarize(orders, links) == {
        "natal": {"paid_orders": 1, "paid_revenue": Decimal("80.00")}
    }
