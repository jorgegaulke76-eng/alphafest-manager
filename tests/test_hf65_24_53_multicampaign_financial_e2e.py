"""HF65.24.53 — ensaio E2E MULTICAMPANHA integralmente fictício.

Não usa HTTP, Supabase, Streamlit, extrato bancário ou dados AlphaFest.
O diário SQLite é descartado ao final. Confere seleção manual, pagamentos,
estorno, cancelamento, cobrança mensal, duplicata e revogação.
"""
from decimal import Decimal
import sqlite3
from uuid import uuid4

from commercial_attribution_sqlite_lab import (
    append_validated_event_lab, current_revision, install_test_schema, read_events,
)
from commercial_verified_report import build_verified_commercial_report


CONTACTS = [
    {"id": f"AT{i}", "etapa_captacao": "Venda fechada" if i in (1, 2, 3) else "Novo contato"}
    for i in range(1, 10)
]
PROPOSALS = [
    {"numero_proposta": "PED1", "atendimento_id": "AT1", "pago": True, "valor_total": "120,00"},
    {"numero_proposta": "PED2", "atendimento_id": "AT2", "pago": True, "valor_total": "80,00"},
    {"numero_proposta": "PED3", "atendimento_id": "AT3", "pago": True, "valor_total": "200,00",
     "valor_recebido": "90,00"},
    {"numero_proposta": "PED4", "atendimento_id": "AT4", "pago": True, "valor_total": "300,00",
     "modalidade_cobranca": "Mensalista"},
    {"numero_proposta": "PED5", "atendimento_id": "AT5", "pago": True, "valor_total": "150,00",
     "cancelado_cliente": True},
    {"numero_proposta": "PED6", "atendimento_id": "AT6", "pago": True, "valor_total": "90,00",
     "valor_estornado": "90,00"},
    {"numero_proposta": "PED7", "atendimento_id": "AT7", "pago": False, "valor_total": "60,00"},
    {"numero_proposta": "PED8", "atendimento_id": "AT8", "pago": True, "valor_total": "70,00"},
    {"numero_proposta": "PED9", "atendimento_id": "AT9", "pago": True, "valor_total": "50,00"},
    # Número duplicado: precisa ser rejeitado mesmo se o registro parece pago.
    {"numero_proposta": "PED9", "atendimento_id": "AT9", "pago": True, "valor_total": "50,00"},
]


def _event(conn, *, number, contact, campaign, decision="confirmar", minute=0):
    return append_validated_event_lab(
        conn,
        event_id=str(uuid4()),
        expected_revision=current_revision(conn, number),
        numero_proposta=number,
        atendimento_id=contact,
        campaign=campaign,
        decisao=decision,
        evidencia="referencia_cliente",
        usuario="operador_ficticio",
        ocorrido_em=f"2026-11-24T10:{minute:02d}:00-03:00",
        propostas=PROPOSALS,
        atendimentos=CONTACTS,
    )


def test_multiple_campaigns_from_manual_links_through_financial_exceptions_and_revocation():
    with sqlite3.connect(":memory:", isolation_level=None) as conn:
        install_test_schema(conn)
        # Primeiro: nenhuma mensagem, clique ou contato sem vínculo vira receita.
        empty = build_verified_commercial_report(CONTACTS, PROPOSALS, read_events(conn))
        assert empty["receita_atribuida"] == Decimal("0")
        assert empty["pedidos_pagos_atribuidos"] == 0

        # Vínculos MANUAIS independentes, e não cliques de analytics.
        for i, campaign in enumerate([
            "natal_2026", "instagram", "natal_2026",
            "instagram", "natal_2026", "instagram",
            "natal_2026", "natal_2026",
        ], 1):
            _event(conn, number=f"PED{i}", contact=f"AT{i}", campaign=campaign)
        report = build_verified_commercial_report(CONTACTS, PROPOSALS, read_events(conn))
        assert report["pedidos_pagos_atribuidos"] == 3
        assert report["receita_atribuida"] == Decimal("270.00")
        assert report["campanhas"] == [
            {"campanha": "instagram", "pedidos_pagos_atribuidos": 1,
             "receita_atribuida": Decimal("80.00")},
            {"campanha": "natal_2026", "pedidos_pagos_atribuidos": 2,
             "receita_atribuida": Decimal("190.00")},
        ]

        # Retirada do vínculo é registrada, não apagada.
        _event(conn, number="PED8", contact="AT8", campaign="natal_2026",
               decision="revogar", minute=1)
        final = build_verified_commercial_report(CONTACTS, PROPOSALS, read_events(conn))
        assert final["pedidos_pagos_atribuidos"] == 2
        assert final["receita_atribuida"] == Decimal("200.00")
        assert final["campanhas"] == [
            {"campanha": "instagram", "pedidos_pagos_atribuidos": 1,
             "receita_atribuida": Decimal("80.00")},
            {"campanha": "natal_2026", "pedidos_pagos_atribuidos": 1,
             "receita_atribuida": Decimal("120.00")},
        ]
        assert len(read_events(conn)) == 9
        assert "NÃO comprova crédito bancário" in final["aviso"]


def test_duplicate_number_rejected_at_link_confirmation():
    with sqlite3.connect(":memory:", isolation_level=None) as conn:
        install_test_schema(conn)
        from pytest import raises
        with raises(ValueError, match="ausente/duplicado"):
            _event(conn, number="PED9", contact="AT9", campaign="natal_2026")
        assert read_events(conn) == []
