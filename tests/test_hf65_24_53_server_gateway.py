"""Contrato do gateway: negar acesso antes de qualquer chamada ao banco."""
from types import SimpleNamespace
import pytest

from commercial_server_read_gateway import read_verified_operator_history
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_online_document_reader import PrivateDocumentUnavailable
from commercial_operator_policy import VerifiedOperator, OperatorPolicy, READ


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def raise_for_status(self):
        pass

    def json(self):
        return [{"value": self.value}]


class FakeCloud:
    def __init__(self, *, mode="service", online=True, value=None):
        self.mode = mode
        self.online = online
        self.value = {"events": []} if value is None else value
        self.calls = 0
        self._SESSION = SimpleNamespace(get=self.get)

    def credential_mode(self):
        return self.mode

    def online_configured(self):
        return self.online

    def _config(self):
        return "https://example.supabase.co", "server-only-secret"

    def _headers(self):
        return {"apikey": "server-only-secret"}

    def get(self, url, *, headers, params, timeout):
        self.calls += 1
        assert url == "https://example.supabase.co/rest/v1/app_data"
        assert params["key"] == "eq.hf65_24_53_attribution_events_private_db"
        return FakeResponse(self.value)


def auth(_):
    # O teste recebe a identidade de um autenticador fictício confiável.
    return VerifiedOperator("verified-operator-id", "test-issuer", "test-manager")


_POLICY = OperatorPolicy(
    issuer="test-issuer", audience="test-manager",
    grants={"verified-operator-id": {READ}},
)


def allow(principal, action):
    return _POLICY.permitted(principal, action)


def read(cloud, **kwargs):
    values = dict(session=object(), authenticate=auth, authorize=allow, cloud=cloud)
    values.update(kwargs)
    return read_verified_operator_history(**values)


def test_authorized_server_only_reads_remote():
    cloud = FakeCloud(value={"events": []})
    assert read(cloud) == []
    assert cloud.calls == 1


@pytest.mark.parametrize("replacement", [
    {"authenticate": None},
    {"authenticate": lambda _: None},
    {"authenticate": lambda _: {"email": "someone@example.com"}},
    {"authenticate": lambda _: {"subject": "verified-operator-id"}},
    {"authenticate": lambda _: (_ for _ in ()).throw(RuntimeError("auth unavailable"))},
    {"authorize": lambda *_: False},
    {"authorize": lambda *_: "True"},
    {"authorize": lambda *_: (_ for _ in ()).throw(RuntimeError("denied"))},
])
def test_authentication_and_permission_fail_closed_before_network(replacement):
    cloud = FakeCloud()
    with pytest.raises(PrivateStoreDenied):
        read(cloud, **replacement)
    assert cloud.calls == 0


@pytest.mark.parametrize("mode,online", [
    ("anon", True), ("none", True), ("service", False)
])
def test_database_permission_or_availability_fail_closed(mode, online):
    cloud = FakeCloud(mode=mode, online=online)
    with pytest.raises(PrivateStoreDenied):
        read(cloud)
    assert cloud.calls == 0


def test_invalid_remote_data_never_falls_back_to_cache():
    cloud = FakeCloud(value={"unexpected": []})
    with pytest.raises(PrivateDocumentUnavailable):
        read(cloud)
    assert cloud.calls == 1


def test_wrong_issuer_or_audience_denied_before_http():
    cloud = FakeCloud()
    for principal in (
        VerifiedOperator("verified-operator-id", "bad-issuer", "test-manager"),
        VerifiedOperator("verified-operator-id", "test-issuer", "wrong-app"),
    ):
        with pytest.raises(PrivateStoreDenied):
            read(cloud, authenticate=lambda _, p=principal: p)
    assert cloud.calls == 0
