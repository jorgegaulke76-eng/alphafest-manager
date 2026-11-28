"""Teste de contrato HTTP de sessão, com rede 100% simulada."""
from datetime import datetime, timezone, timedelta
import pytest

from commercial_operator_policy import VerifiedOperator
from commercial_server_session_postgrest import (
    issue_staging_session, active_staging_session, revoke_staging_session,
    SessionHttpDenied,
)

URL = "https://hvaptsdhaxrdxgqqpicu.supabase.co"
HEADERS = {"apikey": "fake-server-key", "Authorization": "Bearer fake-server-key"}
NOW = datetime(2026, 11, 24, 14, 0, tzinfo=timezone.utc)
USER = VerifiedOperator("operator-opaque", "issuer", "audience")
OTHER = VerifiedOperator("different", "issuer", "audience")


class Response:
    status_code = 200
    def __init__(self, rows): self.rows = rows
    def raise_for_status(self): return None
    def json(self): return self.rows


class MockTransport:
    def __init__(self):
        self.docs = {}
        self.calls = []
    def post(self, endpoint, *, headers, json, params, timeout, allow_redirects):
        assert endpoint.endswith("/rest/v1/hf53_server_sessions")
        assert not allow_redirects
        assert headers["Prefer"] == "return=representation"
        assert "handle" not in json and len(json["handle_sha256"]) == 64
        self.docs[json["handle_sha256"]] = dict(json, revoked_at=None)
        self.calls.append("post")
        return Response([{"handle_sha256": json["handle_sha256"]}])
    def get(self, endpoint, *, headers, params, timeout, allow_redirects):
        assert not allow_redirects
        self.calls.append("get")
        digest = params["handle_sha256"][3:]
        row = self.docs.get(digest)
        return Response([row] if row else [])
    def patch(self, endpoint, *, headers, params, json, timeout, allow_redirects):
        assert not allow_redirects
        self.calls.append("patch")
        digest = params["handle_sha256"][3:]
        row = self.docs.get(digest)
        if row is None or row["subject"] != params["subject"][3:] or row["revoked_at"]:
            return Response([])
        row["revoked_at"] = json["revoked_at"]
        return Response([{"handle_sha256": digest}])


def test_issue_check_revoke_and_deny_cross_identity():
    mock = MockTransport()
    handle = issue_staging_session(
        post=mock.post, base_url=URL, headers=HEADERS, principal=USER, now=NOW)
    assert handle not in str(mock.docs)
    assert active_staging_session(
        get=mock.get, base_url=URL, headers=HEADERS,
        principal=USER, handle=handle, now=NOW)
    assert not active_staging_session(
        get=mock.get, base_url=URL, headers=HEADERS,
        principal=OTHER, handle=handle, now=NOW)
    assert not revoke_staging_session(
        patch=mock.patch, base_url=URL, headers=HEADERS,
        principal=OTHER, handle=handle, now=NOW)
    assert revoke_staging_session(
        patch=mock.patch, base_url=URL, headers=HEADERS,
        principal=USER, handle=handle, now=NOW)
    assert not active_staging_session(
        get=mock.get, base_url=URL, headers=HEADERS,
        principal=USER, handle=handle, now=NOW)


def test_expiration_and_network_failure_fail_closed():
    mock = MockTransport()
    handle = issue_staging_session(
        post=mock.post, base_url=URL, headers=HEADERS,
        principal=USER, now=NOW, ttl_seconds=1)
    assert not active_staging_session(
        get=mock.get, base_url=URL, headers=HEADERS,
        principal=USER, handle=handle, now=NOW+timedelta(seconds=1))
    assert not active_staging_session(
        get=lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("offline")),
        base_url=URL, headers=HEADERS, principal=USER, handle=handle, now=NOW)


@pytest.mark.parametrize("url", [
    "https://guejrwlblcxptzlobhit.supabase.co",
    "https://evil.example", "http://hvaptsdhaxrdxgqqpicu.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co.attacker.example",
])
def test_no_key_sent_to_other_hosts(url):
    calls=[]
    with pytest.raises(SessionHttpDenied):
        issue_staging_session(post=lambda *a,**k: calls.append(1),
                              base_url=url,headers=HEADERS,principal=USER,now=NOW)
    assert calls == []


def test_missing_authorization_and_invalid_ttl_fail_before_http():
    calls=[]
    with pytest.raises(SessionHttpDenied):
        issue_staging_session(post=lambda *a,**k: calls.append(1),
          base_url=URL,headers={"apikey":"fake"},principal=USER,now=NOW)
    with pytest.raises(SessionHttpDenied):
        issue_staging_session(post=lambda *a,**k: calls.append(1),
          base_url=URL,headers=HEADERS,principal=USER,now=NOW,ttl_seconds=9999)
    assert calls == []
