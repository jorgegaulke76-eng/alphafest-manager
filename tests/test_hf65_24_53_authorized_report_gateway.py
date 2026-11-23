"""Fluxo privado de relatório HF65.24.53 — sem dados ou rede reais."""
from types import SimpleNamespace
from decimal import Decimal
import pytest

from commercial_authorized_report_gateway import build_authorized_commercial_report
from commercial_operator_policy import VerifiedOperator, OperatorPolicy, READ
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_online_document_reader import PrivateDocumentUnavailable
from commercial_private_document_adapter import DOCUMENT_KEY

USER = VerifiedOperator("test-operator", "test-issuer", "test-app")
POLICY = OperatorPolicy(
    issuer="test-issuer", audience="test-app",
    grants={"test-operator": {READ}},
)

PROPOSALS = [{"numero_proposta": "P1", "atendimento_id": "A1",
              "pago": True, "valor_total": "79,90"}]
CONTACTS = [{"id": "A1", "etapa_captacao": "Venda fechada"}]
EVENT = {
    "event_id": "f4e8358a-ae18-4d21-8424-439d56b82391",
    "numero_proposta": "P1", "atendimento_id": "A1",
    "campaign": "natal_2026", "decisao": "confirmar",
    "evidencia": "referencia_cliente", "usuario": "test-operator",
    "ocorrido_em": "2026-11-23T19:00:00+00:00",
}


class Response:
    def __init__(self, events):
        self.events = events
    def raise_for_status(self):
        return None
    def json(self):
        return [{"value": {"events": self.events}}]


class Cloud:
    def __init__(self, events=None, *, mode="service"):
        self.events = [] if events is None else events
        self.mode = mode
        self.calls = 0
        self._SESSION = SimpleNamespace(get=self.get)
    def credential_mode(self):
        return self.mode
    def online_configured(self):
        return True
    def _config(self):
        return "https://example.supabase.co", "private-test-key"
    def _headers(self):
        return {"apikey": "private-test-key"}
    def get(self, url, *, headers, params, timeout):
        self.calls += 1
        assert params["key"] == "eq." + DOCUMENT_KEY
        return Response(self.events)


def run(cloud, **overrides):
    kwargs = dict(
        session=object(),
        authenticate=lambda _: USER,
        authorize=POLICY.permitted,
        cloud=cloud,
        load_official_snapshots=lambda: (PROPOSALS, CONTACTS),
    )
    kwargs.update(overrides)
    return build_authorized_commercial_report(**kwargs)


def test_complete_authorized_report_and_revocation():
    cloud = Cloud([EVENT])
    report = run(cloud)
    assert report["pedidos_pagos_atribuidos"] == 1
    assert report["receita_atribuida"] == Decimal("79.90")
    assert report["campanhas"][0]["campanha"] == "natal_2026"

    cloud.events.append({**EVENT,
        "event_id": "7bb5e721-a237-4a30-9a60-920dd56c0981",
        "decisao": "revogar",
        "ocorrido_em": "2026-11-23T19:01:00+00:00",
    })
    assert run(cloud)["receita_atribuida"] == Decimal("0")


@pytest.mark.parametrize("overrides", [
    {"authenticate": lambda _: None},
    {"authenticate": lambda _: {"sub": "test-operator"}},
    {"authenticate": lambda _: VerifiedOperator("other", "test-issuer", "test-app")},
    {"authorize": lambda *_: False},
    {"authorize": lambda *_: True, "authenticate": lambda _: None},
])
def test_rejected_session_does_not_read_snapshots_or_remote(overrides):
    cloud = Cloud([EVENT])
    called = []
    kwargs = dict(load_official_snapshots=lambda: called.append(1))
    kwargs.update(overrides)
    with pytest.raises(PrivateStoreDenied):
        run(cloud, **kwargs)
    assert cloud.calls == 0
    assert called == []


def test_offline_or_malformed_snapshots_do_not_return_revenue():
    cloud = Cloud([EVENT])
    with pytest.raises(PrivateStoreDenied):
        run(cloud, load_official_snapshots=lambda: (_ for _ in ()).throw(OSError()))
    for bad in (None, (PROPOSALS,), (PROPOSALS, {}), ([None], CONTACTS)):
        with pytest.raises(PrivateStoreDenied):
            run(cloud, load_official_snapshots=lambda b=bad: b)


def test_no_pending_payment_or_only_whatsapp_counted_as_sale():
    cloud = Cloud([EVENT])
    proposals = [{"numero_proposta": "P1", "atendimento_id": "A1",
                  "pago": False, "valor_total": "79,90"}]
    report = run(cloud, load_official_snapshots=lambda: (proposals, CONTACTS))
    assert report["pedidos_pagos_atribuidos"] == 0
    assert report["receita_atribuida"] == Decimal("0")


def test_bad_remote_history_never_produces_a_report():
    cloud = Cloud([{"unexpected": True}])
    with pytest.raises((ValueError, PrivateDocumentUnavailable)):
        run(cloud)


def test_event_referring_to_missing_official_proposal_blocks_entire_report():
    cloud = Cloud([EVENT, {**EVENT,
        "event_id": "e7261eb4-13e5-43f5-b30a-5f8bd25bd5e7",
        "numero_proposta": "REMOVED-ORDER",
        "atendimento_id": "A2",
        "ocorrido_em": "2026-11-23T19:02:00+00:00",
    }])
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        run(cloud)


def test_relocated_official_contact_blocks_entire_report():
    cloud = Cloud([EVENT])
    proposals = [{**PROPOSALS[0], "atendimento_id": "ANOTHER"}]
    with pytest.raises(ValueError, match="Histórico comercial diverge"):
        run(cloud, load_official_snapshots=lambda: (proposals, CONTACTS))
