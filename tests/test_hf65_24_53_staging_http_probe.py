"""Contrato local de probe HTTP; nunca consulta Supabase real."""
import pytest

from scripts.hf65_24_53_staging_http_probe import (
    run_probe, ProbeError, BASE, PREFIX,
)


class Response:
    def __init__(self, code, rows):
        self.status_code = code
        self._rows = rows
    def json(self):
        return self._rows


class FakeSession:
    def __init__(self):
        self.db = {}
        self.calls = []
    def _request(self, method, url, *, headers, params, timeout, allow_redirects,
                 json=None):
        assert url == BASE + "/rest/v1/app_data"
        assert allow_redirects is False
        assert timeout == 10
        assert headers["apikey"] == "sb_secret_fictitious"
        assert "Authorization" not in headers
        key = (json["key"] if method == "POST" else params["key"].removeprefix("eq."))
        assert key.startswith(PREFIX)
        self.calls.append(method)
        if method == "GET":
            return Response(200, [{"key": key, "value": self.db[key]}] if key in self.db else [])
        if method == "POST":
            assert params["on_conflict"] == "key"
            if key in self.db:
                return Response(201, [])
            self.db[key] = json["value"]
            return Response(201, [{"key": key, "value": self.db[key]}])
        if method == "DELETE":
            removed = self.db.pop(key, None)
            return Response(200, [{"key": key, "value": removed}] if removed is not None else [])
        raise AssertionError("unexpected method")
    def get(self, *args, **kwargs):
        return self._request("GET", *args, **kwargs)
    def post(self, *args, **kwargs):
        return self._request("POST", *args, **kwargs)
    def delete(self, *args, **kwargs):
        return self._request("DELETE", *args, **kwargs)


def test_read_only_default_no_write():
    s = FakeSession()
    result = run_probe(base_url=BASE, service_key="sb_secret_fictitious", session=s)
    assert "nenhuma escrita" in result
    assert s.calls == ["GET"]
    assert s.db == {}


def test_write_opt_in_conflict_and_cleanup():
    s = FakeSession()
    result = run_probe(base_url=BASE, service_key="sb_secret_fictitious",
                       write_enabled=True, session=s)
    assert "confirmados" in result
    assert s.calls == ["GET", "POST", "POST", "GET", "DELETE", "GET"]
    assert s.db == {}


@pytest.mark.parametrize("base", [
    "https://guejrwlblcxptzlobhit.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co.evil.example",
    "http://hvaptsdhaxrdxgqqpicu.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co?x=1",
    "https://user@hvaptsdhaxrdxgqqpicu.supabase.co",
])
def test_wrong_target_does_not_send_key(base):
    s = FakeSession()
    with pytest.raises(ProbeError):
        run_probe(base_url=base, service_key="sb_secret_fictitious",
                  write_enabled=True, session=s)
    assert s.calls == []


def test_missing_key_stops_before_network():
    s = FakeSession()
    with pytest.raises(ProbeError):
        run_probe(base_url=BASE, service_key="", session=s)
    assert s.calls == []


class BadWrite(FakeSession):
    def post(self, *a, **kw):
        result = super().post(*a, **kw)
        if self.calls.count("POST") == 2:
            return Response(200, [{"unexpected": "bad"}])
        return result


def test_failure_after_creation_always_cleans_probe_row():
    s = BadWrite()
    with pytest.raises(ProbeError):
        run_probe(base_url=BASE, service_key="sb_secret_fictitious",
                  write_enabled=True, session=s)
    assert s.db == {}
    assert "DELETE" in s.calls
