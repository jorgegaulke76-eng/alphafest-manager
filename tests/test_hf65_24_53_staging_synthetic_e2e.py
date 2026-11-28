"""HF53: fixture sintética em backend staging, sem documento oficial."""
from decimal import Decimal
import pytest

from hf65_24_53_staging_synthetic_e2e import (
    KEYS, read_staging_synthetic_commercial_report, render_staging_synthetic_report,
)
from test_hf65_24_53_http_diagnostic import UI, STAGING_URL


class Response:
    status_code = 200
    def __init__(self, rows): self.rows = rows
    def raise_for_status(self): return None
    def json(self): return self.rows


def fixtures():
    return {
        KEYS[0]: {"itens": [
            {"numero_proposta":"HF53-DEMO-P1","atendimento_id":"HF53-DEMO-A1","pago":True,"valor_total":"120,00"},
            {"numero_proposta":"HF53-DEMO-P2","atendimento_id":"HF53-DEMO-A2","pago":True,"valor_total":"80,00"},
            {"numero_proposta":"HF53-DEMO-P3","atendimento_id":"HF53-DEMO-A3","pago":True,"valor_total":"200,00","valor_recebido":"90,00"},
        ]},
        KEYS[1]: {"config":{}, "itens": [
            {"id":"HF53-DEMO-A1","etapa_captacao":"Venda fechada"},
            {"id":"HF53-DEMO-A2","etapa_captacao":"Venda fechada"},
            {"id":"HF53-DEMO-A3","etapa_captacao":"Venda fechada"},
        ]},
        KEYS[2]: {"events": [
            {"event_id":f"{i}"*8 + "-1111-4111-8111-" + f"{i}"*12,
             "numero_proposta":f"HF53-DEMO-P{i}","atendimento_id":f"HF53-DEMO-A{i}",
             "campaign":"natal_2026" if i != 2 else "instagram",
             "decisao":"confirmar","evidencia":"referencia_cliente",
             "usuario":"hf53_demo", "ocorrido_em":f"2026-11-24T10:0{i-1}:00-03:00"}
            for i in (1,2,3)
        ]},
    }


def get_for(docs, calls):
    def get(url, *, params, headers, timeout, allow_redirects):
        assert url == STAGING_URL + "/rest/v1/app_data"
        assert params["select"] == "value" and not allow_redirects
        key = params["key"][3:]
        calls.append(key)
        assert key in KEYS
        return Response([{"value": docs[key]}] if key in docs else [])
    return get


def test_full_synthetic_roundtrip_uses_only_fixture_keys():
    calls = []
    result = read_staging_synthetic_commercial_report(
        get=get_for(fixtures(), calls), base_url=STAGING_URL,
        headers={"apikey":"sb_secret_fake"},
    )
    assert calls == list(KEYS)
    assert result["pedidos_pagos_atribuidos"] == 2
    assert result["receita_atribuida"] == Decimal("200.00")
    assert [(r["campanha"],r["receita_atribuida"]) for r in result["campanhas"]] == [
        ("instagram", Decimal("80.00")), ("natal_2026", Decimal("120.00"))
    ]


def test_missing_document_or_unexpected_identity_denied():
    docs = fixtures()
    docs.pop(KEYS[2])
    with pytest.raises(PermissionError):
        read_staging_synthetic_commercial_report(
            get=get_for(docs, []), base_url=STAGING_URL,
            headers={"apikey":"sb_secret_fake"},
        )
    docs = fixtures()
    docs[KEYS[0]]["itens"][0]["numero_proposta"] = "REAL-P1"
    with pytest.raises(PermissionError):
        read_staging_synthetic_commercial_report(
            get=get_for(docs, []), base_url=STAGING_URL,
            headers={"apikey":"sb_secret_fake"},
        )


def test_production_host_never_receives_any_request():
    calls=[]
    with pytest.raises(PermissionError):
        read_staging_synthetic_commercial_report(
            get=get_for(fixtures(), calls),
            base_url="https://guejrwlblcxptzlobhit.supabase.co",
            headers={"apikey":"sb_secret_fake"},
        )
    assert calls == []


def test_ui_blocks_unauthenticated_users_before_http():
    st = UI(enabled=False)
    calls=[]
    render_staging_synthetic_report(st, get=get_for(fixtures(), calls))
    assert calls == []
