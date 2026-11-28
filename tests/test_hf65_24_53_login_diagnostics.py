"""HF53: diagnóstico de login sem expor claims."""
from types import SimpleNamespace

from hf65_24_53_homologacao_login import oidc_readiness, render


AUTH = {
    "redirect_uri": "https://localhost.invalid/oauth2callback",
    "cookie_secret": "ficticio",
    "client_id": "client-ficticio",
    "client_secret": "ficticio",
    "server_metadata_url": "https://issuer.invalid/.well-known/openid-configuration",
}
CLAIMS = {
    "sub": "private-id", "iss": "https://issuer.invalid", "aud": "test-app",
    "iat": 100, "exp": 200,
}


class User:
    def __init__(self, *, logged=True, sid=None):
        self.is_logged_in = logged
        self._claims = dict(CLAIMS)
        if sid is not None:
            self._claims["sid"] = sid
    def to_dict(self):
        return dict(self._claims)


def test_no_secrets_does_not_claim_oidc_ready():
    status = oidc_readiness(SimpleNamespace(secrets={}, user=User()))
    assert status["oidc_configured"] is False
    assert status["oidc_claims_complete"] is False


def test_logged_out_refuses_identity_even_with_session_fallback():
    status = oidc_readiness(SimpleNamespace(
        secrets={"auth": AUTH}, user=User(logged=False),
        session_state={"usuario_atual_fallback": "Jorge"},
    ))
    assert status["oidc_configured"] is True
    assert status["logged_in"] is False
    assert status["oidc_claims_complete"] is False


def test_google_style_id_token_without_sid_reports_blocker():
    status = oidc_readiness(SimpleNamespace(secrets={"auth": AUTH}, user=User()))
    assert status["logged_in"] is True
    assert status["claims_present"]["sub"]
    assert status["session_identifier_present"] is False
    assert status["oidc_claims_complete"] is False


def test_full_claims_only_meet_diagnostic_not_acl():
    status = oidc_readiness(SimpleNamespace(secrets={"auth": AUTH}, user=User(sid="session-test")))
    assert status["oidc_claims_complete"] is True
    assert status["hf53_access_authorized"] is False
    assert "sub" not in status
    assert "tokens" not in status


class FakeUI:
    def __init__(self, *, logged=False, sid=None, configured=True, click=False):
        self.secrets = {"auth": AUTH} if configured else {}
        self.user = User(logged=logged, sid=sid)
        self.click = click
        self.actions = []
    def title(self, value): self.actions.append(("title", value))
    def caption(self, value): self.actions.append(("caption", value))
    def warning(self, value): self.actions.append(("warning", value))
    def info(self, value): self.actions.append(("info", value))
    def success(self, value): self.actions.append(("success", value))
    def write(self, value): self.actions.append(("write", value))
    def button(self, value):
        return self.click
    def login(self): self.actions.append(("login", True))
    def logout(self): self.actions.append(("logout", True))


def test_missing_oidc_configuration_cannot_start_login():
    ui = FakeUI(configured=False, click=True)
    render(ui)
    assert not any(k == "login" for k, _ in ui.actions)
    assert any(k == "warning" for k, _ in ui.actions)


def test_login_only_on_explicit_click():
    ui = FakeUI(click=True)
    render(ui)
    assert ("login", True) in ui.actions


def test_logged_in_diagnostics_do_not_print_subject_or_tokens():
    ui = FakeUI(logged=True)
    render(ui)
    assert not any("private-id" in str(value) for _, value in ui.actions)
    assert not any(k == "login" for k, _ in ui.actions)
    assert any(k == "warning" and "sid" in str(value) for k, value in ui.actions)


def test_claims_complete_do_not_imply_verified_revocation_or_acl():
    # Mesmo com atributos OIDC presentes, este app somente diagnostica.
    status = oidc_readiness(SimpleNamespace(
        secrets={"auth": AUTH}, user=User(sid="simulated-sid"),
    ))
    assert status["oidc_claims_complete"] is True
    assert status["hf53_access_authorized"] is False
