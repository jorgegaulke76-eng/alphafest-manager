"""Diagnóstico HTTP real protegido: testes sem rede e sem segredos reais."""
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

from hf65_24_53_http_diagnostic import _eligible, render_http_diagnostic, STAGING_URL

EMAIL = "operator@example.invalid"
EXP = datetime.now(timezone.utc).timestamp() + 7200
EXPECTED = "Leitura HTTP privada de homologação confirmada; nenhuma escrita."


class FakeUser:
    is_logged_in = True
    def __init__(self, **overrides):
        self.claims = {
            "iss": "https://accounts.google.com", "email_verified": True,
            "email": EMAIL, "exp": EXP,
        }
        self.claims.update(overrides)
    def to_dict(self):
        return dict(self.claims)


class UI:
    def __init__(self, *, enabled=True, user=None, target=STAGING_URL, click=True):
        self.user = FakeUser() if user is None else user
        self.secrets = {
            "HF53_HTTP_DIAG_ENABLED": enabled,
            "HF53_STAGING_SUPABASE_URL": target,
            "HF53_STAGING_SERVICE_KEY": "fake-secret-backend-only",
            "HF53_HTTP_DIAG_ALLOWED_EMAIL": EMAIL,
        }
        self.click = click
        self.messages = []
    def subheader(self, message): self.messages.append(("subheader", message))
    def caption(self, message): self.messages.append(("caption", message))
    def button(self, message): return self.click
    def success(self, message): self.messages.append(("success", message))
    def error(self, message): self.messages.append(("error", message))


def test_explicit_opt_in_and_allowlist_require_google_claims():
    ui=UI()
    assert _eligible(ui) == (True, None)
    assert _eligible(UI(enabled=False))[0] is False
    assert _eligible(UI(target="https://guejrwlblcxptzlobhit.supabase.co"))[0] is False
    assert _eligible(UI(user=FakeUser(email_verified=False)))[0] is False
    assert _eligible(UI(user=FakeUser(email="someone-else@example.invalid")))[0] is False
    assert _eligible(UI(user=FakeUser(iss="https://attacker.example")))[0] is False
    assert _eligible(UI(user=FakeUser(exp=0)))[0] is False


@pytest.mark.parametrize("reason", ["disabled", "wrong_project", "outsider", "logged_out"])
def test_no_http_before_authorization(reason):
    ui = UI()
    if reason == "disabled": ui.secrets["HF53_HTTP_DIAG_ENABLED"] = False
    if reason == "wrong_project": ui.secrets["HF53_STAGING_SUPABASE_URL"] = "https://other.supabase.co"
    if reason == "outsider": ui.user = FakeUser(email="visitor@example.invalid")
    if reason == "logged_out": ui.user = FakeUser(); ui.user.is_logged_in = False
    calls = []
    render_http_diagnostic(ui, probe=lambda **kw: calls.append(kw) or EXPECTED)
    assert calls == []
    assert not any(kind == "success" for kind, _ in ui.messages)


def test_authorized_click_calls_read_only_probe_and_hides_secrets():
    ui = UI()
    calls = []
    def probe(**kwargs):
        calls.append(kwargs)
        return EXPECTED
    render_http_diagnostic(ui, probe=probe)
    assert calls == [{
        "base_url": STAGING_URL, "service_key": "fake-secret-backend-only",
        "write_enabled": False,
    }]
    assert any(kind == "success" for kind, _ in ui.messages)
    assert "fake-secret-backend-only" not in str(ui.messages)
    assert EMAIL not in str(ui.messages)


def test_probe_failure_is_generic_and_never_leaks_credentials():
    ui = UI()
    def probe(**kwargs):
        raise ValueError("fake-secret-backend-only private content")
    render_http_diagnostic(ui, probe=probe)
    assert any(kind == "error" for kind, _ in ui.messages)
    assert "fake-secret-backend-only" not in str(ui.messages)


def test_no_http_when_user_did_not_click():
    ui = UI(click=False)
    calls = []
    render_http_diagnostic(ui, probe=lambda **kw: calls.append(kw))
    assert calls == []
