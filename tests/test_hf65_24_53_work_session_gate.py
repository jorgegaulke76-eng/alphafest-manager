"""HF53: verifica OIDC + revogacao remota + ACL em cada acesso."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from commercial_operator_policy import OperatorPolicy, READ, WRITE
from commercial_work_session_gate import (
    authorized_work_session, revoke_local_work_session, HANDLE_KEY,
)
from commercial_server_session_postgrest import issue_staging_session
from hf65_24_53_oidc_bound_probe import authenticated_principal
from test_hf65_24_53_oidc_bound_probe import make_ui, NOW
from test_hf65_24_53_session_postgrest import MockTransport, URL

KEY = "sb_secret_fake_backend_only"


def setup():
    ui = make_ui()
    ui.secrets["HF53_WORK_SESSION_GATE_ENABLED"] = True
    ui.secrets["HF53_STAGING_SERVICE_KEY"] = KEY
    ui.session_state = {}
    transport = MockTransport()
    principal = authenticated_principal(ui, now=NOW)
    policy = OperatorPolicy(
        issuer=principal.issuer, audience=principal.audience,
        grants={principal.subject: {READ}},
    )
    headers = {"apikey": KEY}
    handle = issue_staging_session(
        post=transport.post, base_url=URL, headers=headers,
        principal=principal, now=NOW, ttl_seconds=900,
    )
    ui.session_state[HANDLE_KEY] = handle
    return ui, transport, principal, policy


def test_valid_work_session_checks_remote_state_and_acl_per_access():
    ui, remote, principal, policy = setup()
    assert authorized_work_session(
        ui, policy=policy, action=READ, get=remote.get, now=NOW
    ) == principal
    assert authorized_work_session(
        ui, policy=policy, action=WRITE, get=remote.get, now=NOW
    ) is None
    assert authorized_work_session(
        ui, policy=policy, action=READ, get=remote.get,
        now=NOW+timedelta(minutes=16),
    ) is None


def test_revocation_rejects_next_read_even_when_local_handle_remains():
    ui, remote, _, policy = setup()
    handle = ui.session_state[HANDLE_KEY]
    assert authorized_work_session(ui, policy=policy, action=READ, get=remote.get, now=NOW)
    assert revoke_local_work_session(ui, patch=remote.patch, now=NOW)
    assert HANDLE_KEY not in ui.session_state
    # Simula outro dispositivo com o handle anterior, que nao pode ignorar revogacao.
    ui.session_state[HANDLE_KEY] = handle
    assert authorized_work_session(ui, policy=policy, action=READ, get=remote.get, now=NOW) is None


def test_stale_or_changed_google_identity_is_rejected_before_remote_access():
    ui, remote, _, policy = setup()
    before = list(remote.calls)
    ui.user.claims["sub"] = "different-account"
    assert authorized_work_session(ui, policy=policy, action=READ, get=remote.get, now=NOW) is None
    assert remote.calls == before


def test_no_local_handle_disabled_gate_and_backend_failure_deny():
    ui, remote, _, policy = setup()
    ui.secrets["HF53_WORK_SESSION_GATE_ENABLED"] = False
    assert authorized_work_session(ui, policy=policy, action=READ, get=remote.get, now=NOW) is None
    ui.secrets["HF53_WORK_SESSION_GATE_ENABLED"] = True
    ui.session_state.clear()
    assert authorized_work_session(ui, policy=policy, action=READ, get=remote.get, now=NOW) is None
    ui, remote, _, policy = setup()
    assert authorized_work_session(
        ui, policy=policy, action=READ,
        get=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
        now=NOW,
    ) is None
    ui.secrets["HF53_STAGING_SUPABASE_URL"] = "https://guejrwlblcxptzlobhit.supabase.co"
    assert authorized_work_session(ui, policy=policy, action=READ, get=remote.get, now=NOW) is None


def test_cannot_authorize_using_name_email_or_forged_policy_without_subject():
    ui, remote, principal, _ = setup()
    wrong_policy = OperatorPolicy(
        issuer=principal.issuer, audience=principal.audience,
        grants={"Jorge": {READ}, "operator@example.invalid": {READ}},
    )
    before = list(remote.calls)
    assert authorized_work_session(ui, policy=wrong_policy, action=READ, get=remote.get, now=NOW) is None
    assert remote.calls == before


def test_missing_backend_revocation_denies_and_drops_handle():
    ui, remote, _, _ = setup()
    assert not revoke_local_work_session(
        ui, patch=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
        now=NOW,
    )
    assert HANDLE_KEY not in ui.session_state


def test_commercial_acl_does_not_depend_on_http_diagnostic_flag_or_email_allowlist():
    ui, remote, principal, policy = setup()
    ui.secrets["HF53_HTTP_DIAG_ENABLED"] = False
    ui.secrets.pop("HF53_HTTP_DIAG_ALLOWED_EMAIL", None)
    assert authorized_work_session(
        ui, policy=policy, action=READ, get=remote.get, now=NOW
    ) == principal
    # OIDC ainda é obrigatório sem os diagnósticos.
    ui.user.claims["email_verified"] = False
    assert authorized_work_session(
        ui, policy=policy, action=READ, get=remote.get, now=NOW
    ) is None
