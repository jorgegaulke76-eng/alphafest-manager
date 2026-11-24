"""Ponte OIDC: sem login, claims ou revogação válidos não há acesso."""
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

from commercial_streamlit_oidc_bridge import authenticate_streamlit_oidc_user
from commercial_session_guard import SessionRejected
from commercial_operator_policy import OperatorPolicy, READ

NOW = datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc)
TS = int(NOW.timestamp())


class FakeUser:
    def __init__(self, claims, logged=True):
        self.claims = claims
        self.is_logged_in = logged

    def to_dict(self):
        return dict(self.claims)


def credentials(**overrides):
    data = {
        "sub": "operator-example",
        "iss": "https://issuer.example",
        "aud": "manager-example",
        "sid": "active-session",
        "iat": TS - 50,
        "exp": TS + 900,
        "email": "not-for-permissions@example.com",
        "verified": False,
    }
    data.update(overrides)
    return data


def authenticate(user, **kwargs):
    params = {
        "st": SimpleNamespace(user=user),
        "expected_issuer": "https://issuer.example",
        "expected_audience": "manager-example",
        "is_session_active": lambda subject, sid: subject == "operator-example" and sid == "active-session",
        "now": NOW,
    }
    params.update(kwargs)
    return authenticate_streamlit_oidc_user(**params)


def test_native_login_claims_revalidated_and_email_ignored():
    operator = authenticate(FakeUser(credentials()))
    assert operator.subject == "operator-example"
    policy = OperatorPolicy(
        issuer="https://issuer.example", audience="manager-example",
        grants={"operator-example": {READ}},
    )
    assert policy.permitted(operator, READ)


@pytest.mark.parametrize("changes", [
    {"sid": None}, {"exp": None}, {"exp": TS - 1},
    {"iat": TS + 600}, {"iss": "untrusted"}, {"aud": "wrong"},
])
def test_incomplete_stale_or_wrong_provider_denied(changes):
    with pytest.raises(SessionRejected):
        authenticate(FakeUser(credentials(**changes)))


def test_logged_out_and_missing_runtime_denied():
    with pytest.raises(SessionRejected):
        authenticate(FakeUser(credentials(), logged=False))
    with pytest.raises(SessionRejected):
        authenticate_streamlit_oidc_user(
            SimpleNamespace(), expected_issuer="x", expected_audience="y",
            is_session_active=lambda *_: True, now=NOW,
        )


def test_revocation_service_unavailable_denied():
    with pytest.raises(SessionRejected):
        authenticate(
            FakeUser(credentials()),
            is_session_active=lambda *_: (_ for _ in ()).throw(RuntimeError("offline"))
        )


def test_revoked_session_denied():
    with pytest.raises(SessionRejected):
        authenticate(FakeUser(credentials()), is_session_active=lambda *_: False)


def test_exposed_email_does_not_override_subject_allowlist():
    operator = authenticate(FakeUser(credentials(email="admin@alphafest.example")))
    policy = OperatorPolicy(
        issuer="https://issuer.example", audience="manager-example",
        grants={"someone-else": {READ}},
    )
    assert not policy.permitted(operator, READ)


def test_legacy_jorge_anna_fallback_never_authenticates_hf53():
    # app.py admite selecao de perfil para UX quando OIDC nao está disponivel.
    # Selecionar "Jorge" ou "Anna" não constitui sessão assinada.
    for selected_name in ("Jorge", "Anna"):
        st = SimpleNamespace(
            user=FakeUser(credentials(), logged=False),
            session_state={"usuario_atual_fallback": selected_name},
        )
        with pytest.raises(SessionRejected):
            authenticate_streamlit_oidc_user(
                st, expected_issuer="https://issuer.example",
                expected_audience="manager-example",
                is_session_active=lambda *_: True, now=NOW,
            )


def test_legacy_fallback_without_st_user_is_always_denied():
    st = SimpleNamespace(session_state={"usuario_atual_fallback": "Jorge"})
    with pytest.raises(SessionRejected):
        authenticate_streamlit_oidc_user(
            st, expected_issuer="https://issuer.example",
            expected_audience="manager-example",
            is_session_active=lambda *_: True, now=NOW,
        )
