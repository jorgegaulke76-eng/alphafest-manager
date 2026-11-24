"""PostgREST de bootstrap somente com HTTP simulado, sem credenciais reais."""
import copy

import pytest

from commercial_bootstrap_postgrest_contract import (
    PrivateBootstrapHttpError,
    read_bootstrap_document_optional as read,
    insert_bootstrap_document_if_absent as insert,
)
from commercial_private_bootstrap import initialize_private_history_if_absent
from commercial_private_document_adapter import DOCUMENT_KEY
from commercial_operator_policy import VerifiedOperator

URL = "https://hvaptsdhaxrdxgqqpicu.supabase.co"
HEADERS = {"apikey": "test-key", "Content-Type": "application/json"}


class FakeResponse:
    def __init__(self, rows=None, failed=False, status_code=200):
        self.rows, self.failed = rows, failed
        self.status_code = status_code

    def raise_for_status(self):
        if self.failed:
            raise RuntimeError("HTTP 503")

    def json(self):
        return copy.deepcopy(self.rows)


class FakeHttp:
    def __init__(self, initial=None):
        self.document = copy.deepcopy(initial)
        self.calls = []

    def get(self, url, *, headers, params, timeout, allow_redirects):
        assert allow_redirects is False
        self.calls.append(("get", url, headers, params))
        assert params["key"] == "eq." + DOCUMENT_KEY
        return FakeResponse([] if self.document is None else [
            {"key": DOCUMENT_KEY, "value": self.document}
        ])

    def post(self, url, *, headers, params, json, timeout, allow_redirects):
        assert allow_redirects is False
        self.calls.append(("post", url, headers, params, copy.deepcopy(json)))
        assert headers["Prefer"] == "resolution=ignore-duplicates,return=representation"
        assert "merge-duplicates" not in headers["Prefer"]
        assert params == {"on_conflict": "key", "select": "key,value"}
        if self.document is not None:
            return FakeResponse([])
        self.document = copy.deepcopy(json["value"])
        return FakeResponse([{"key": DOCUMENT_KEY, "value": self.document}])


def read_kwargs(fake):
    return dict(get=fake.get, base_url=URL, headers=HEADERS)


def insert_kwargs(fake):
    return dict(post=fake.post, base_url=URL, headers=HEADERS,
                document_key=DOCUMENT_KEY, document={"events": []})


def test_absent_is_only_confirmed_empty_http_array():
    fake = FakeHttp()
    assert read(**read_kwargs(fake)) is None
    assert len(fake.calls) == 1


def test_insert_once_does_not_overwrite_document():
    fake = FakeHttp()
    assert insert(**insert_kwargs(fake)) is True
    assert insert(**insert_kwargs(fake)) is False
    assert read(**read_kwargs(fake)) == {"events": []}
    assert fake.document == {"events": []}


def test_existing_document_is_preserved_verbatim():
    fake = FakeHttp({"events": []})
    assert insert(**insert_kwargs(fake)) is False
    assert fake.document == {"events": []}


@pytest.mark.parametrize("body", [
    {}, None, "not a list", [{"value": {"events": []}}],
    [{"key": "unrelated", "value": {"events": []}}],
    [{"key": DOCUMENT_KEY, "value": {"unexpected": []}}],
    [{"key": DOCUMENT_KEY, "value": {"events": []}}] * 2,
])
def test_bad_get_never_faked_as_absent(body):
    with pytest.raises(PrivateBootstrapHttpError):
        read(get=lambda *a, **k: FakeResponse(body),
             base_url=URL, headers=HEADERS)


@pytest.mark.parametrize("body", [
    {}, None, "bad", [{"key": "other", "value": {"events": []}}],
    [{"key": DOCUMENT_KEY, "value": {"events": [{"bad": True}]}}],
])
def test_unexpected_insert_response_never_reports_success(body):
    with pytest.raises(PrivateBootstrapHttpError):
        insert(post=lambda *a, **k: FakeResponse(body),
               base_url=URL, headers=HEADERS, document_key=DOCUMENT_KEY,
               document={"events": []})


def test_http_failure_does_not_count_as_missing_document():
    with pytest.raises(PrivateBootstrapHttpError):
        read(get=lambda *a, **k: FakeResponse([], failed=True),
             base_url=URL, headers=HEADERS)


def test_http_failure_does_not_count_as_conflict():
    with pytest.raises(PrivateBootstrapHttpError):
        insert(post=lambda *a, **k: FakeResponse([], failed=True),
               base_url=URL, headers=HEADERS, document_key=DOCUMENT_KEY,
               document={"events": []})


def test_disallow_other_document_and_insecure_url():
    fake = FakeHttp()
    with pytest.raises(PrivateBootstrapHttpError):
        read(get=fake.get, base_url=URL, headers=HEADERS,
             document_key="historico_orcamentos")
    with pytest.raises(PrivateBootstrapHttpError):
        insert(post=fake.post, base_url="http://example", headers=HEADERS,
               document_key=DOCUMENT_KEY, document={"events": []})
    assert not fake.calls


def test_full_bootstrap_with_mock_postgrest_and_authorization():
    fake = FakeHttp()
    user = VerifiedOperator("operator-test", "issuer-test", "app-test")
    kwargs = {
        "principal": user,
        "approve_initialization": lambda p: p == user,
        "credential_mode": lambda: "service",
        "read_online": lambda key: read(
            get=fake.get, base_url=URL, headers=HEADERS, document_key=key
        ),
        "insert_if_absent": lambda key, value: insert(
            post=fake.post, base_url=URL, headers=HEADERS,
            document_key=key, document=value,
        ),
    }
    assert initialize_private_history_if_absent(**kwargs) == "created"
    assert initialize_private_history_if_absent(**kwargs) == "existing"
    assert [call[0] for call in fake.calls].count("post") == 1


@pytest.mark.parametrize("unsafe_url", [
    "https://evil.example",
    "https://guejrwlblcxptzlobhit.supabase.co",
    "https://other.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co.evil.example",
    "https://user:secret@example.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co/rest/v1/app_data",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co?redirect=https://evil.example",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co#fragment",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co:8443",
    "http://example.supabase.co",
])
def test_no_secret_sent_to_untrusted_endpoint(unsafe_url):
    fake = FakeHttp()
    with pytest.raises(PrivateBootstrapHttpError):
        read(get=fake.get, base_url=unsafe_url, headers=HEADERS)
    with pytest.raises(PrivateBootstrapHttpError):
        insert(post=fake.post, base_url=unsafe_url, headers=HEADERS,
               document_key=DOCUMENT_KEY, document={"events": []})
    assert fake.calls == []


@pytest.mark.parametrize("status_code", [301, 302, 307, 308, 401, 500])
def test_redirects_and_http_errors_cannot_claim_missing_or_inserted(status_code):
    with pytest.raises(PrivateBootstrapHttpError):
        read(get=lambda *a, **k: FakeResponse([], status_code=status_code),
             base_url=URL, headers=HEADERS)
    with pytest.raises(PrivateBootstrapHttpError):
        insert(post=lambda *a, **k: FakeResponse([], status_code=status_code),
               base_url=URL, headers=HEADERS, document_key=DOCUMENT_KEY,
               document={"events": []})
