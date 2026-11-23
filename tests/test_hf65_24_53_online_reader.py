"""HF65.24.53 — falha fechada na leitura remota de histórico privado."""
import pytest

from commercial_online_document_reader import (
    PrivateDocumentUnavailable, load_private_document_online_only as read,
)


class Response:
    def __init__(self, payload, error=False):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise RuntimeError("HTTP indisponível")

    def json(self):
        return self.payload


def client(payload, *, error=False, record=None):
    def get(url, *, headers, params, timeout):
        if record is not None:
            record.append((url, headers, params, timeout))
        return Response(payload, error)
    return get


KW = {"base_url": "https://supabase.example", "headers": {"apikey": "ficticia"}}


def test_existing_empty_document_is_valid_and_no_local_read():
    records = []
    result = read(get=client([{"value": {"events": []}}], record=records), **KW)
    assert result == {"events": []}
    assert records[0][2] == {
        "select": "value", "key": "eq.hf65_24_53_attribution_events_private_db", "limit": "2"
    }


@pytest.mark.parametrize("payload", [
    [], [{"value": None}], [{"value": {"outra": []}}],
    [{"value": {"events": "invalido"}}], [{}],
    [{"value": {"events": []}}, {"value": {"events": []}}], {},
])
def test_missing_or_bad_remote_is_refused(payload):
    with pytest.raises(PrivateDocumentUnavailable):
        read(get=client(payload), **KW)


def test_offline_error_is_refused_not_replaced_with_cache():
    with pytest.raises(PrivateDocumentUnavailable):
        read(get=client([], error=True), **KW)


def test_only_approved_document_key_and_https():
    with pytest.raises(PrivateDocumentUnavailable):
        read(get=client([]), document_key="historico_orcamentos", **KW)
    with pytest.raises(PrivateDocumentUnavailable):
        read(get=client([]), base_url="http://unsafe.example",
             headers={"apikey": "ficticia"})


def test_missing_service_request_header_rejected():
    with pytest.raises(PrivateDocumentUnavailable):
        read(get=client([]), base_url="https://supabase.example", headers={})
