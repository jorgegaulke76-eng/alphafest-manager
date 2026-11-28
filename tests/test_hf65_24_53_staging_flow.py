"""Homologação ponta a ponta da HF65.24.53 em SQLite descartável.

Simula apenas registros fictícios; nunca alcança Manager ou Supabase reais.
"""
import sqlite3
from uuid import uuid4
from decimal import Decimal

from commercial_attribution_sqlite_lab import (
    install_test_schema, append_validated_event_lab, current_revision, read_events
)
from commercial_verified_report import build_verified_commercial_report


def test_complete_staging_flow_with_revocation():
    contacts = [{"id": "AT-FICTICIO", "etapa_captacao": "Venda fechada"}]
    proposals = [{"numero_proposta": "PED-FICTICIO", "atendimento_id": "AT-FICTICIO",
                  "pago": True, "valor_total": "79,90"}]
    with sqlite3.connect(":memory:", isolation_level=None) as conn:
        install_test_schema(conn)

        def insert(decision, campaign, when):
            return append_validated_event_lab(
                conn, event_id=str(uuid4()),
                expected_revision=current_revision(conn, "PED-FICTICIO"),
                numero_proposta="PED-FICTICIO", atendimento_id="AT-FICTICIO",
                campaign=campaign, decisao=decision,
                evidencia="referencia_cliente", usuario="operador_ficticio",
                ocorrido_em=when, propostas=proposals, atendimentos=contacts
            )

        assert build_verified_commercial_report(
            contacts, proposals, read_events(conn)
        )["receita_atribuida"] == 0
        insert("confirmar", "campanha_natal", "2026-11-23T16:00:00-03:00")
        report = build_verified_commercial_report(contacts, proposals, read_events(conn))
        assert report["pedidos_pagos_atribuidos"] == 1
        assert report["receita_atribuida"] == Decimal("79.90")
        insert("revogar", "campanha_natal", "2026-11-23T16:01:00-03:00")
        report = build_verified_commercial_report(contacts, proposals, read_events(conn))
        assert report["receita_atribuida"] == 0
        assert len(read_events(conn)) == 2
