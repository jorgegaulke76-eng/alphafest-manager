"""HF53: ensaio seguro POST/GET/PATCH, sem acesso real a banco."""
from datetime import datetime, timezone

from commercial_server_session_postgrest import SessionHttpDenied
from hf65_24_53_session_write_probe import run_session_write_probe, SUCCESS
from hf65_24_53_http_diagnostic import render_session_write_diagnostic
from test_hf65_24_53_http_diagnostic import UI, STAGING_URL
from test_hf65_24_53_session_postgrest import MockTransport


def test_session_http_probe_roundtrip_with_mock_server():
    http = MockTransport()
    outcome = run_session_write_probe(
        base_url=STAGING_URL, service_key="sb_secret_fake_for_test", http=http,
    )
    assert outcome == SUCCESS
    assert http.calls == ["post", "get", "patch", "get"]
    assert len(http.docs) == 1
    assert all(row["revoked_at"] for row in http.docs.values())
    assert all(row["subject"].startswith("hf53-diag-") for row in http.docs.values())


def test_write_probe_requires_explicit_flag_and_verified_google_operator():
    ui = UI()
    ui.secrets["HF53_SESSION_WRITE_DIAG_ENABLED"] = False
    calls = []
    render_session_write_diagnostic(ui, probe=lambda **kw: calls.append(kw))
    assert calls == []

    ui.secrets["HF53_SESSION_WRITE_DIAG_ENABLED"] = True
    ui.user.is_logged_in = False
    render_session_write_diagnostic(ui, probe=lambda **kw: calls.append(kw))
    assert calls == []


def test_write_probe_never_echoes_secret_and_cannot_target_production():
    ui = UI()
    ui.secrets["HF53_SESSION_WRITE_DIAG_ENABLED"] = True
    calls = []
    render_session_write_diagnostic(
        ui, probe=lambda **kw: calls.append(kw) or SUCCESS,
    )
    assert len(calls) == 1
    assert all("fake-secret-backend-only" not in str(x) for x in ui.messages)
    assert any(k == "success" for k, _ in ui.messages)

    from pytest import raises
    with raises(ValueError):
        run_session_write_probe(
            base_url="https://guejrwlblcxptzlobhit.supabase.co",
            service_key="sb_secret_fake_for_test", http=MockTransport(),
        )
