"""Testes isolados da reconciliação HF65.24.53."""
from decimal import Decimal

from commercial_conversion_service import summarize_verified_campaign_sales as summarize


def test_only_paid_with_explicit_order_link():
    actual = summarize(
        [
            {"order_id": "1", "status": "Pago", "amount": "129.90"},
            {"order_id": "2", "status": "Aprovado", "amount": "70"},
            {"order_id": "3", "status": "Pago", "amount": "100"},
        ],
        [
            {"order_id": "1", "campaign": "natal-2026"},
            {"order_id": "2", "campaign": "natal-2026"},
        ],
    )
    assert actual == {"natal-2026": {"paid_orders": 1, "paid_revenue": Decimal("129.90")}}


def test_ambiguous_or_duplicate_link_excluded():
    actual = summarize(
        [
            {"order_id": "1", "status": "Pago", "amount": "50"},
            {"order_id": "2", "status": "Pago", "amount": "40"},
            {"order_id": "2", "status": "Pago", "amount": "40"},
        ],
        [
            {"order_id": "1", "campaign": "facebook"},
            {"order_id": "1", "campaign": "instagram"},
            {"order_id": "2", "campaign": "natal"},
        ],
    )
    assert actual == {}


def test_refuse_invalid_amount_and_personal_data_in_campaign():
    actual = summarize(
        [
            {"order_id": "1", "status": "Pago", "amount": "-1"},
            {"order_id": "2", "status": "Pago", "amount": "NaN"},
            {"order_id": "3", "status": "Pago", "amount": "19.90"},
            {"order_id": "4", "status": "Pago", "amount": True},
        ],
        [
            {"order_id": "1", "campaign": "natal"},
            {"order_id": "2", "campaign": "natal"},
            {"order_id": "3", "campaign": "cliente@email.com"},
            {"order_id": "4", "campaign": "natal"},
        ],
    )
    assert actual == {}


def test_duplicate_identical_attribution_does_not_duplicate_revenue():
    actual = summarize(
        [{"order_id": "1", "status": "paid", "amount": "12.50"}],
        [{"order_id": "1", "campaign": "campanha_a"}, {"order_id": "1", "campaign": "campanha_a"}],
    )
    assert actual["campanha_a"] == {"paid_orders": 1, "paid_revenue": Decimal("12.50")}
