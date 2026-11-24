"""HF53: bridge do relatório exige sessão backend viva e ACL antes de ler."""
from decimal import Decimal
import pytest

from commercial_operator_policy import OperatorPolicy, READ
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_work_session_report_bridge import build_work_session_commercial_report
from commercial_work_session_gate import revoke_local_work_session
from test_hf65_24_53_work_session_gate import setup
from test_hf65_24_53_authorized_report_gateway import (
    Cloud, EVENT, PROPOSALS, CONTACTS
)


def build(ui, remote, policy, cloud, calls):
    return build_work_session_commercial_report(
        st=ui, policy=policy, cloud=cloud, get_session=remote.get,
        load_official_snapshots=lambda: (calls.append("snapshots") or PROPOSALS, CONTACTS),
    )


def test_report_uses_live_google_session_and_acl_before_cloud():
    ui, remote, principal, policy = setup()
    ui.secrets["HF65_24_53_PRIVATE_REPORT_ENABLED"] = True
    cloud = Cloud([EVENT])
    calls = []
    report = build(ui, remote, policy, cloud, calls)
    assert report["pedidos_pagos_atribuidos"] == 1
    assert report["receita_atribuida"] == Decimal("79.90")
    assert cloud.calls == 1
    assert calls == ["snapshots"]
    assert revoke_local_work_session(ui, patch=remote.patch) is True
    with pytest.raises(PrivateStoreDenied):
        build(ui, remote, policy, cloud, calls)
    assert cloud.calls == 1
    assert calls == ["snapshots"]


def test_report_disabled_does_not_query_session_or_commercial_data():
    ui, remote, _, policy = setup()
    cloud = Cloud([EVENT])
    calls = []
    before = list(remote.calls)
    with pytest.raises(PrivateStoreDenied):
        build(ui, remote, policy, cloud, calls)
    assert remote.calls == before
    assert cloud.calls == 0
    assert calls == []


def test_report_not_permitted_even_with_login_and_live_session():
    ui, remote, principal, _ = setup()
    ui.secrets["HF65_24_53_PRIVATE_REPORT_ENABLED"] = True
    cloud = Cloud([EVENT])
    calls = []
    policy = OperatorPolicy(
        issuer=principal.issuer, audience=principal.audience,
        grants={"another-subject": {READ}},
    )
    before = list(remote.calls)
    with pytest.raises(PrivateStoreDenied):
        build(ui, remote, policy, cloud, calls)
    assert remote.calls == before
    assert cloud.calls == 0
    assert calls == []


def test_report_denied_when_revocation_backend_fails():
    ui, remote, _, policy = setup()
    ui.secrets["HF65_24_53_PRIVATE_REPORT_ENABLED"] = True
    cloud = Cloud([EVENT])
    calls = []
    with pytest.raises(PrivateStoreDenied):
        build_work_session_commercial_report(
            st=ui, policy=policy, cloud=cloud,
            get_session=lambda *_a, **_k: (_ for _ in ()).throw(OSError("network offline")),
            load_official_snapshots=lambda: (calls.append(1) or PROPOSALS, CONTACTS),
        )
    assert cloud.calls == 0
    assert calls == []
