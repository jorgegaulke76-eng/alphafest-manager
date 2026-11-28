"""HF53: leitura de documentos do Manager somente no Supabase de staging."""
import pytest

from commercial_private_document_adapter import PrivateStoreDenied
from commercial_staging_official_reader import read_sanitized_staging_official_snapshots

URL = "https://hvaptsdhaxrdxgqqpicu.supabase.co"
HEADERS = {"apikey": "sb_secret_only_test"}


class Response:
    status_code = 200
    def __init__(self, value): self.value = value
    def raise_for_status(self): pass
    def json(self): return [{"value": self.value}]


def demo_documents():
    return {
        "historico_orcamentos": {"itens": [
            {"numero_proposta": "EX-P1", "atendimento_id": "EX-A1",
             "pago": True, "valor_total": "79,90",
             "cliente_nome": "NAO_PUBLICAR", "telefone": "11912345678"},
        ]},
        "atendimentos_db": {"config": {"api_key": "SEGREDO"},
                            "itens": [{"id": "EX-A1", "etapa_captacao": "Venda fechada",
                                      "mensagem": "CONVERSA_PRIVADA"}]},
    }


def fake_get_for(documents, calls):
    def get(url, *, headers, params, timeout, allow_redirects):
        calls.append({"url": url, "params": params})
        assert url == URL + "/rest/v1/app_data"
        assert allow_redirects is False and timeout == 10
        assert headers == HEADERS
        key = params["key"][3:]
        if key not in documents:
            class Missing:
                status_code = 200
                def raise_for_status(self): pass
                def json(self): return []
            return Missing()
        return Response(documents[key])
    return get


def test_only_two_documents_read_and_personal_fields_removed():
    calls = []
    proposals, contacts = read_sanitized_staging_official_snapshots(
        get=fake_get_for(demo_documents(), calls),
        base_url=URL, headers=HEADERS,
    )
    assert [x["params"]["key"] for x in calls] == [
        "eq.historico_orcamentos", "eq.atendimentos_db"
    ]
    assert proposals == [{"numero_proposta": "EX-P1", "atendimento_id": "EX-A1",
                          "pago": True, "valor_total": "79,90"}]
    assert contacts == [{"id": "EX-A1", "etapa_captacao": "Venda fechada"}]
    raw = str((proposals, contacts))
    for forbidden in ("NAO_PUBLICAR", "11912345678", "SEGREDO", "CONVERSA_PRIVADA"):
        assert forbidden not in raw


@pytest.mark.parametrize("host", [
    "https://guejrwlblcxptzlobhit.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co.attacker.example",
    "http://hvaptsdhaxrdxgqqpicu.supabase.co",
    "https://hvaptsdhaxrdxgqqpicu.supabase.co/rest/v1",
])
def test_wrong_host_refused_before_any_http(host):
    calls = []
    with pytest.raises(PrivateStoreDenied):
        read_sanitized_staging_official_snapshots(
            get=fake_get_for(demo_documents(), calls), base_url=host,
            headers=HEADERS,
        )
    assert calls == []


def test_document_missing_or_ambiguous_aborts_without_fallback():
    for docs in (
        {"historico_orcamentos": []},
        {"historico_orcamentos": [], "atendimentos_db": []},
        {"historico_orcamentos": [], "atendimentos_db": {"itens": "invalid"}},
    ):
        calls=[]
        with pytest.raises(PrivateStoreDenied):
            read_sanitized_staging_official_snapshots(
                get=fake_get_for(docs, calls), base_url=URL, headers=HEADERS,
            )


def test_http_failure_never_returns_cached_or_local_documents():
    calls=[]
    def offline(*args, **kwargs):
        calls.append(1)
        raise OSError("backend offline")
    with pytest.raises(PrivateStoreDenied):
        read_sanitized_staging_official_snapshots(get=offline, base_url=URL, headers=HEADERS)
    assert calls == [1]


def test_staging_json_object_contract_rejects_legacy_root_array_or_extra_fields():
    original = demo_documents()
    for invalid in (
        original["historico_orcamentos"]["itens"],
        {"itens": original["historico_orcamentos"]["itens"], "unrecognized": True},
        {"itens": "not-a-list"},
    ):
        docs = dict(original, historico_orcamentos=invalid)
        with pytest.raises(PrivateStoreDenied):
            read_sanitized_staging_official_snapshots(
                get=fake_get_for(docs, []), base_url=URL, headers=HEADERS,
            )
