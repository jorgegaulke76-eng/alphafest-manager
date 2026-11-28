"""HF65.24.53 — contrato de validade e revogação de sessão no servidor."""
from datetime import datetime, timezone

import pytest

from commercial_session_guard import SessionRejected, verify_authenticated_session
from commercial_operator_policy import OperatorPolicy, READ


NOW = datetime(2026, 11, 23, 19, 0, tzinfo=timezone.utc)
NOW_TS = int(NOW.timestamp())
ISSUER = "https://id.example"
AUDIENCE = "manager-staging"


def claims(**updates):
    item = {
        "verified": True, "sub": "opaque-subject",
        "iss": ISSUER, "aud": AUDIENCE, "sid": "server-session-id",
        "iat": NOW_TS - 100, "exp": NOW_TS + 900,
    }
    item.update(updates)
    return item


def auth(c, *, active=lambda sub, sid: True):
    return verify_authenticated_session(
        object(), verify_provider=lambda _: c,
        is_session_active=active, expected_issuer=ISSUER,
        expected_audience=AUDIENCE, now=NOW,
    )


def test_signed_verified_and_active_session_yields_operator_for_policy():
    identity = auth(claims())
    policy = OperatorPolicy(
        issuer=ISSUER, audience=AUDIENCE,
        grants={"opaque-subject": {READ}},
    )
    assert policy.permitted(identity, READ)


@pytest.mark.parametrize("bad", [
    {"verified": False}, {"verified": "true"}, {"sub": ""},
    {"iss": "https://evil.example"}, {"aud": "another-app"},
    {"sid": ""}, {"exp": NOW_TS}, {"exp": NOW_TS - 1},
    {"iat": NOW_TS + 1000}, {"iat": NOW_TS + 10, "exp": NOW_TS + 5},
    {"exp": True}, {"iat": None},
])
def test_invalid_and_expired_sessions_fail_closed(bad):
    with pytest.raises(SessionRejected):
        auth(claims(**bad))


def test_revoked_session_blocks_access():
    with pytest.raises(SessionRejected):
        auth(claims(), active=lambda sub, sid: False)


def test_session_provider_failure_denied():
    def fail(_):
        raise RuntimeError("provider offline")
    with pytest.raises(SessionRejected):
        verify_authenticated_session(
            object(), verify_provider=fail,
            is_session_active=lambda *_: True,
            expected_issuer=ISSUER, expected_audience=AUDIENCE, now=NOW,
        )


def test_revocation_provider_failure_denied():
    def fail(*_):
        raise RuntimeError("revocation unavailable")
    with pytest.raises(SessionRejected):
        auth(claims(), active=fail)


def test_unverified_mapping_does_not_become_operator():
    with pytest.raises(SessionRejected):
        auth({"sub": "opaque-subject", "iss": ISSUER, "aud": AUDIENCE})


def test_no_provider_callbacks_denied():
    with pytest.raises(SessionRejected):
        verify_authenticated_session(
            object(), verify_provider=None,
            is_session_active=lambda *_: True,
            expected_issuer=ISSUER, expected_audience=AUDIENCE, now=NOW,
        )


@pytest.mark.parametrize("bad", [
    {"sub": " opaque-subject"}, {"sub": "opaque-subject "},
    {"sid": " server-session-id"}, {"sid": "server-session-id "},
    {"sub": " "}, {"sid": " "},
])
def test_noncanonical_ids_rejected_before_session_lookup(bad):
    checked = []
    with pytest.raises(SessionRejected, match="Identidade de sessão inválida"):
        auth(claims(**bad), active=lambda *args: checked.append(args) or True)
    assert checked == []


@pytest.mark.parametrize("issuer,audience", [
    (" "+ISSUER, AUDIENCE), (ISSUER+" ", AUDIENCE),
    (ISSUER, " "+AUDIENCE), (ISSUER, AUDIENCE+" "),
    (None, AUDIENCE), (ISSUER, None),
    (123, AUDIENCE), (ISSUER, 123),
])
def test_invalid_policy_issuer_audience_fail_before_provider(issuer, audience):
    verified = []
    with pytest.raises(SessionRejected, match="Emissor/público"):
        verify_authenticated_session(
            object(), verify_provider=lambda _: verified.append(True) or claims(),
            is_session_active=lambda *_: True, expected_issuer=issuer,
            expected_audience=audience, now=NOW,
        )
    assert verified == []
