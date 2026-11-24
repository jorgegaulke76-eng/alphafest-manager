"""HF65.24.53: entrada Streamlit protegida, sem conexão real."""
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

from commercial_streamlit_private_report_entry import (
    build_streamlit_private_commercial_report as build,
)
from commercial_operator_policy import OperatorPolicy, READ
from commercial_private_document_adapter import PrivateStoreDenied


ISS = "https://issuer.test"
AUD = "manager-homologacao"
SUB = "subject-verified"
POLICY = OperatorPolicy(issuer=ISS, audience=AUD, grants={SUB: {READ}})


class User:
    def __init__(self, *, logged=True, subject=SUB, expired=False):
        self.is_logged_in = logged
        now = int(datetime.now(timezone.utc).timestamp())
        self.claims = {
            "sub": subject, "iss": ISS, "aud": AUD,
            "sid": "session-verified", "iat": now - 30,
            "exp": now - 1 if expired else now + 900,
        }
    def to_dict(self):
        return dict(self.claims)


class Response:
    status_code = 200
    def raise_for_status(self):
        pass
    def json(self):
        return [{"value": {"events": []}}]


class Cloud:
    def __init__(self):
        self.calls = 0
        self._SESSION = SimpleNamespace(get=self.get)
    def credential_mode(self):
        return "service"
    def online_configured(self):
        return True
    def _config(self):
        return "https://hvaptsdhaxrdxgqqpicu.supabase.co", "fictitious-key"
    def _headers(self):
        return {"apikey": "fictitious-key"}
    def get(self, url, **kwargs):
        self.calls += 1
        assert kwargs["allow_redirects"] is False
        return Response()


def perform(*, secrets=None, user=None, policy=POLICY, checker=None):
    cloud = Cloud()
    calls = []
    fake_st = SimpleNamespace(
        secrets={} if secrets is None else secrets,
        user=User() if user is None else user,
        session_state={"usuario_atual_fallback": "Jorge"},
    )
    try:
        report = build(
            st=fake_st, policy=policy, cloud=cloud,
            is_session_active=(lambda sub, sid: sub == SUB and sid == "session-verified") if checker is None else checker,
            load_official_snapshots=lambda: (calls.append(True) or [], []),
        )
        return report, cloud.calls, len(calls)
    except Exception as err:
        return err, cloud.calls, len(calls)


def test_feature_disabled_by_default_ignores_legacy_selected_jorge():
    result, reads, snapshots = perform()
    assert isinstance(result, PrivateStoreDenied)
    assert reads == snapshots == 0


@pytest.mark.parametrize("flag", ["true", True])
def test_authenticated_authorized_approved_flag_can_read_private_report(flag):
    result, reads, snapshots = perform(secrets={"HF65_24_53_PRIVATE_REPORT_ENABLED": flag})
    assert result["receita_atribuida"] == 0
    assert reads == snapshots == 1


@pytest.mark.parametrize("user,checker", [
    (User(logged=False), None),
    (User(expired=True), None),
    (User(subject="unauthorized-subject"), None),
    (User(), lambda *_: False),
    (User(), lambda *_: (_ for _ in ()).throw(RuntimeError("revocation offline"))),
])
def test_no_reliable_login_or_grant_never_accesses_remote(user, checker):
    result, reads, snapshots = perform(
        secrets={"HF65_24_53_PRIVATE_REPORT_ENABLED": True},
        user=user, checker=checker,
    )
    assert isinstance(result, PrivateStoreDenied)
    assert reads == snapshots == 0


@pytest.mark.parametrize("flag", [False, "false", "1", "yes", None, 1])
def test_non_explicit_feature_flag_denied(flag):
    result, reads, snapshots = perform(
        secrets={"HF65_24_53_PRIVATE_REPORT_ENABLED": flag},
    )
    assert isinstance(result, PrivateStoreDenied)
    assert reads == snapshots == 0


def test_legacy_anna_fallback_not_used_for_authentication():
    st = SimpleNamespace(
        secrets={"HF65_24_53_PRIVATE_REPORT_ENABLED": True},
        session_state={"usuario_atual_fallback": "Anna"},
    )
    cloud = Cloud()
    with pytest.raises(PrivateStoreDenied):
        build(
            st=st, policy=POLICY, cloud=cloud,
            is_session_active=lambda *_: True,
            load_official_snapshots=lambda: ([], []),
        )
    assert cloud.calls == 0


@pytest.mark.parametrize("invalid_url", [
    "https://guejrwlblcxptzlobhit.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co.evil.example",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co/path",
    "http://hvaptsdhaxrdxgqqpicu.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co?redirect=1",
])
def test_wrong_database_is_rejected_before_http(invalid_url):
    cloud = Cloud()
    cloud._config = lambda: (invalid_url, "fictitious-key")
    st = SimpleNamespace(
        secrets={"HF65_24_53_PRIVATE_REPORT_ENABLED": True},
        user=User(), session_state={"usuario_atual_fallback": "Jorge"},
    )
    snapshots = []
    with pytest.raises(PrivateStoreDenied, match="homologação"):
        build(
            st=st, policy=POLICY, cloud=cloud,
            is_session_active=lambda *_: True,
            load_official_snapshots=lambda: (snapshots.append(True) or [], []),
        )
    assert cloud.calls == 0
    assert snapshots == []


def test_anon_client_blocked_before_http_even_with_valid_login():
    cloud = Cloud()
    cloud.credential_mode = lambda: "anon"
    st = SimpleNamespace(
        secrets={"HF65_24_53_PRIVATE_REPORT_ENABLED": True}, user=User(),
    )
    with pytest.raises(PrivateStoreDenied):
        build(st=st, policy=POLICY, cloud=cloud,
              is_session_active=lambda *_: True,
              load_official_snapshots=lambda: ([], []))
    assert cloud.calls == 0
