"""HF53: identidade Google real vinculada somente a ensaio revogavel."""
from datetime import datetime, timezone, timedelta

import pytest

from commercial_operator_policy import VerifiedOperator
from hf65_24_53_oidc_bound_probe import (
    authenticated_principal, run_bound_session_probe,
    render_bound_session_diagnostic, SUCCESS,
)
from test_hf65_24_53_http_diagnostic import UI
from test_hf65_24_53_session_postgrest import MockTransport

NOW = datetime.now(timezone.utc)


def make_ui():
    ui = UI()
    ui.secrets["HF53_OIDC_BOUND_DIAG_ENABLED"] = True
    ui.secrets["auth"] = {
        "client_id": "hf53-google-client-id",
        "cookie_secret": "a-very-long-backend-cookie-secret-for-hf53-diagnostic",
    }
    ui.user.claims.update({
        "sub": "google-subject-test-001",
        "iss": "https://accounts.google.com",
        "aud": "hf53-google-client-id",
        "iat": NOW.timestamp() - 20,
        "exp": NOW.timestamp() + 600,
    })
    return ui


def test_google_identity_is_pseudonymous_and_not_user_supplied():
    ui = make_ui()
    principal = authenticated_principal(ui, now=NOW)
    assert isinstance(principal, VerifiedOperator)
    assert principal.subject != "google-subject-test-001"
    assert len(principal.subject) == 64
    assert principal == authenticated_principal(ui, now=NOW)
    ui.user.claims["sub"] = "another-google-sub"
    assert authenticated_principal(ui, now=NOW).subject != principal.subject


@pytest.mark.parametrize("change", [
    {"aud": "wrong-client"},
    {"iss": "https://attacker.invalid"},
    {"sub": ""},
    {"sub": " leading-space"},
    {"iat": float("nan")},
    {"exp": float("inf")},
    {"exp": 1},
    {"iat": NOW.timestamp() + 500},
])
def test_invalid_google_identity_fails_closed(change):
    ui = make_ui()
    ui.user.claims.update(change)
    with pytest.raises(PermissionError):
        authenticated_principal(ui, now=NOW)


def test_missing_backend_cookie_secret_or_wrong_client_denied():
    ui = make_ui()
    ui.secrets["auth"]["cookie_secret"] = "too-short"
    with pytest.raises(PermissionError):
        authenticated_principal(ui, now=NOW)
    ui = make_ui()
    ui.secrets["auth"]["client_id"] = "different-client"
    with pytest.raises(PermissionError):
        authenticated_principal(ui, now=NOW)


def test_google_bound_session_roundtrip_without_persisting_google_sub():
    ui = make_ui()
    mock = MockTransport()
    assert run_bound_session_probe(ui, http=mock, now=NOW) == SUCCESS
    assert mock.calls == ["post", "get", "patch", "get"]
    assert len(mock.docs) == 1
    row = next(iter(mock.docs.values()))
    assert row["subject"] != "google-subject-test-001"
    assert row["revoked_at"] is not None
    assert "hf53-diag-" not in row["subject"]


def test_no_write_when_flag_disabled_or_identity_invalid():
    ui = make_ui()
    ui.secrets["HF53_OIDC_BOUND_DIAG_ENABLED"] = False
    mock = MockTransport()
    with pytest.raises(PermissionError):
        run_bound_session_probe(ui, http=mock, now=NOW)
    assert mock.calls == []
    ui.secrets["HF53_OIDC_BOUND_DIAG_ENABLED"] = True
    ui.user.claims["aud"] = "bad-client"
    with pytest.raises(PermissionError):
        run_bound_session_probe(ui, http=mock, now=NOW)
    assert mock.calls == []


def test_ui_requires_explicit_permission_and_hides_secrets():
    ui = make_ui()
    ui.secrets["HF53_OIDC_BOUND_DIAG_ENABLED"] = False
    calls = []
    render_bound_session_diagnostic(ui, runner=lambda st: calls.append(st) or SUCCESS)
    assert calls == []
    ui.secrets["HF53_OIDC_BOUND_DIAG_ENABLED"] = True
    render_bound_session_diagnostic(ui, runner=lambda st: calls.append(st) or SUCCESS)
    assert calls == [ui]
    assert any(k == "success" for k, _ in ui.messages)
    assert "google-subject-test-001" not in str(ui.messages)
    assert "a-very-long-backend-cookie-secret" not in str(ui.messages)
