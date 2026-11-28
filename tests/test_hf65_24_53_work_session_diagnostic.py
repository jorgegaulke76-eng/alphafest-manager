"""HF53: sessão de trabalho persistida entre reruns simulados do Streamlit."""
from hf65_24_53_work_session_diagnostic import (
    start_test_work_session, check_test_work_session, revoke_test_work_session,
)
from commercial_work_session_gate import HANDLE_KEY
from test_hf65_24_53_oidc_bound_probe import make_ui
from test_hf65_24_53_session_postgrest import MockTransport


def setup():
    ui = make_ui()
    ui.secrets["HF53_WORK_SESSION_GATE_ENABLED"] = True
    ui.secrets["HF53_STAGING_SERVICE_KEY"] = "sb_secret_test_only"
    ui.session_state = {}
    return ui, MockTransport()


def test_realistic_start_rerun_check_revoke_and_reject_old_handle():
    ui, remote = setup()
    assert start_test_work_session(ui, http=remote)
    old_handle = ui.session_state[HANDLE_KEY]
    # Os reruns na mesma conexão preservam session_state.
    assert check_test_work_session(ui, http=remote)
    assert not start_test_work_session(ui, http=remote)  # Sem sessão duplicada.
    assert revoke_test_work_session(ui, http=remote)
    assert HANDLE_KEY not in ui.session_state
    ui.session_state[HANDLE_KEY] = old_handle
    assert not check_test_work_session(ui, http=remote)
    assert len(remote.docs) == 1
    assert next(iter(remote.docs.values()))["revoked_at"] is not None


def test_flag_or_login_missing_never_creates_session():
    ui, remote = setup()
    ui.secrets["HF53_WORK_SESSION_GATE_ENABLED"] = False
    assert not start_test_work_session(ui, http=remote)
    ui.secrets["HF53_WORK_SESSION_GATE_ENABLED"] = True
    ui.user.is_logged_in = False
    assert not start_test_work_session(ui, http=remote)
    assert not remote.calls
    assert HANDLE_KEY not in ui.session_state


def test_wrong_project_or_changed_identity_deny_after_session_issued():
    ui, remote = setup()
    assert start_test_work_session(ui, http=remote)
    ui.secrets["HF53_STAGING_SUPABASE_URL"] = "https://guejrwlblcxptzlobhit.supabase.co"
    assert not check_test_work_session(ui, http=remote)
    ui.secrets["HF53_STAGING_SUPABASE_URL"] = "https://hvaptsdhaxrdxgqqpicu.supabase.co"
    ui.user.claims["sub"] = "another-user"
    assert not check_test_work_session(ui, http=remote)
