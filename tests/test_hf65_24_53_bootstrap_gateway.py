"""Gateway privado de bootstrap: testes de permissões e rede simulada."""
from types import SimpleNamespace

import pytest

from commercial_bootstrap_server_gateway import bootstrap_verified_private_history
from commercial_operator_policy import VerifiedOperator, OperatorPolicy, BOOTSTRAP, READ, WRITE
from commercial_private_document_adapter import DOCUMENT_KEY, PrivateStoreDenied


USER = VerifiedOperator("operator-bootstrap", "test-issuer", "test-audience")
POLICY = OperatorPolicy(
    issuer="test-issuer", audience="test-audience",
    grants={"operator-bootstrap": {BOOTSTRAP}, "operator-read": {READ, WRITE}},
)


class Response:
    def __init__(self, rows):
        self.rows = rows

    def raise_for_status(self):
        return None

    def json(self):
        return self.rows


class Cloud:
    def __init__(self, mode="service", online=True):
        self.mode = mode
        self.online = online
        self.document = None
        self.calls = 0
        self._SESSION = SimpleNamespace(get=self.get, post=self.post)

    def credential_mode(self):
        return self.mode

    def online_configured(self):
        return self.online

    def _config(self):
        return "https://example.supabase.co", "server-only-test-key"

    def _headers(self):
        return {"apikey": "server-only-test-key"}

    def get(self, url, *, headers, params, timeout):
        self.calls += 1
        assert url == "https://example.supabase.co/rest/v1/app_data"
        assert params["key"] == "eq." + DOCUMENT_KEY
        return Response([] if self.document is None else [
            {"key": DOCUMENT_KEY, "value": self.document},
        ])

    def post(self, url, *, headers, params, json, timeout):
        self.calls += 1
        assert headers["Prefer"] == "resolution=ignore-duplicates,return=representation"
        assert params["on_conflict"] == "key"
        if self.document is not None:
            return Response([])
        self.document = dict(json["value"])
        return Response([{"key": DOCUMENT_KEY, "value": self.document}])


def run(cloud, **overrides):
    options = {
        "session": object(),
        "authenticate": lambda _: USER,
        "policy": POLICY,
        "cloud": cloud,
    }
    options.update(overrides)
    return bootstrap_verified_private_history(**options)


def test_authorized_first_creation_and_idempotent_retry():
    cloud = Cloud()
    assert run(cloud) == "created"
    assert run(cloud) == "existing"
    assert cloud.document == {"events": []}
    assert cloud.calls == 4


@pytest.mark.parametrize("replacement", [
    {"authenticate": None},
    {"authenticate": lambda _: None},
    {"authenticate": lambda _: {"sub": "operator-bootstrap"}},
    {"authenticate": lambda _: (_ for _ in ()).throw(RuntimeError("offline"))},
    {"authenticate": lambda _: VerifiedOperator("operator-read", "test-issuer", "test-audience")},
    {"authenticate": lambda _: VerifiedOperator("operator-bootstrap", "evil-issuer", "test-audience")},
    {"authenticate": lambda _: VerifiedOperator("operator-bootstrap", "test-issuer", "other-audience")},
    {"policy": None},
])
def test_no_network_without_verified_bootstrap_permission(replacement):
    cloud = Cloud()
    with pytest.raises(PrivateStoreDenied):
        run(cloud, **replacement)
    assert cloud.calls == 0


@pytest.mark.parametrize("mode,online", [
    ("anon", True), ("none", True), ("service", False)
])
def test_no_network_without_service_credential(mode, online):
    cloud = Cloud(mode=mode, online=online)
    with pytest.raises(PrivateStoreDenied):
        run(cloud)
    assert cloud.calls == 0


def test_does_not_overwrite_existing_document():
    cloud = Cloud()
    cloud.document = {"events": []}
    assert run(cloud) == "existing"
    assert cloud.document == {"events": []}
    assert cloud.calls == 1
