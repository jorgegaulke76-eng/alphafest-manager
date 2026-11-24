"""HF53: verificar apenas presença dos 3 documentos e zero divulgação de value."""
import pytest

from hf65_24_53_staging_readiness import (
    EXPECTED, check_staging_document_presence, render_staging_readiness,
)
from test_hf65_24_53_http_diagnostic import UI, STAGING_URL


class Response:
    status_code = 200
    def __init__(self, items): self.items = items
    def raise_for_status(self): return None
    def json(self): return self.items


def _get(existing, calls):
    def get(url, *, headers, params, timeout, allow_redirects):
        calls.append((url, params))
        assert url == STAGING_URL + "/rest/v1/app_data"
        assert params["select"] == "key" and params["limit"] == "2"
        assert not allow_redirects and timeout == 10
        k = params["key"][3:]
        return Response([{"key": k}] if k in existing else [])
    return get


def test_presence_checks_exactly_three_fixed_keys_and_no_values():
    calls = []
    keys = {EXPECTED[0][0]}
    found = check_staging_document_presence(
        get=_get(keys, calls), base_url=STAGING_URL,
        headers={"apikey":"sb_secret_fake"},
    )
    assert len(calls) == 3
    assert found == {k: (k in keys) for k,_ in EXPECTED}
    assert all("value" not in str(call) for call in calls)


@pytest.mark.parametrize("url", [
    "https://guejrwlblcxptzlobhit.supabase.co",
    "http://hvaptsdhaxrdxgqqpicu.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co.attacker.invalid",
])
def test_invalid_base_never_sends_secrets(url):
    calls = []
    with pytest.raises(PermissionError):
        check_staging_document_presence(
            get=_get(set(), calls), base_url=url,
            headers={"apikey":"sb_secret_fake"},
        )
    assert calls == []


def test_ui_denies_before_http_without_login_or_diag_flag():
    ui = UI(enabled=False)
    calls = []
    render_staging_readiness(ui, get=_get(set(), calls))
    assert calls == []
    assert not any(x == "warning" for x,_ in ui.messages)


def test_ui_displays_no_customer_content_and_reports_absence():
    ui = UI()
    ui.secrets["HF53_STAGING_SERVICE_KEY"] = "sb_secret_backend_fake"
    render_staging_readiness(ui, get=_get(set(), []))
    assert any(kind == "warning" for kind,_ in ui.messages)
    text = str(ui.messages)
    assert "sb_secret_backend_fake" not in text
    assert "value" not in text
