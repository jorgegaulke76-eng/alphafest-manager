"""E2E simulado do fluxo privado sem consultar clientes reais."""
import pytest

from commercial_private_document_adapter import PrivateStoreDenied
from commercial_staging_integrated_report import build_integrated_staging_commercial_report
from commercial_work_session_gate import HANDLE_KEY
from test_hf65_24_53_work_session_gate import setup
from test_hf65_24_53_authorized_report_gateway import Cloud, EVENT


class Response:
    status_code = 200
    def __init__(self, data): self.data = data
    def raise_for_status(self): return None
    def json(self): return self.data


class Http:
    def __init__(self, session_transport):
        self.sessions = session_transport
        self.snapshot_calls = []
        self.documents = {
            "historico_orcamentos": [
                {"numero_proposta": "P1", "atendimento_id": "A1",
                 "pago": True, "valor_total": "79,90",
                 "cliente_nome": "NOME_SENSIVEL",
                 "telefone": "11999999999"},
            ],
            "atendimentos_db": {
                "config": {"api_secret": "SEGREDO"},
                "itens": [
                    {"id": "A1", "etapa_captacao": "Venda fechada",
                     "mensagem": "CONVERSA_PRIVADA"}
                ],
            },
        }
    def get(self, url, **kwargs):
        if url.endswith("/hf53_server_sessions"):
            return self.sessions.get(url, **kwargs)
        assert url.endswith("/app_data")
        self.snapshot_calls.append(kwargs["params"]["key"])
        key = kwargs["params"]["key"][3:]
        if key not in self.documents:
            return Response([])
        return Response([{"value": self.documents[key]}])


def prepared():
    st, sessions, principal, _ = setup()
    st.secrets["HF53_COMMERCIAL_ACL_ENABLED"] = True
    st.secrets["HF53_COMMERCIAL_READ_SUBJECTS"] = [principal.subject]
    st.secrets["HF65_24_53_PRIVATE_REPORT_ENABLED"] = True
    return st, sessions, Http(sessions), Cloud([EVENT])


def test_full_integrated_report_reads_only_after_acl_and_live_session():
    st, sessions, http, cloud = prepared()
    report = build_integrated_staging_commercial_report(st=st, cloud=cloud, http=http)
    assert report["pedidos_pagos_atribuidos"] == 1
    assert str(report["receita_atribuida"]) == "79.90"
    assert http.snapshot_calls == [
        "eq.historico_orcamentos", "eq.atendimentos_db",
    ]
    assert cloud.calls == 1


@pytest.mark.parametrize("mode", ["disabled", "acl_disabled", "wrong_subject", "no_session"])
def test_denial_happens_before_any_commercial_http(mode):
    st, sessions, http, cloud = prepared()
    if mode == "disabled":
        st.secrets["HF65_24_53_PRIVATE_REPORT_ENABLED"] = False
    if mode == "acl_disabled":
        st.secrets["HF53_COMMERCIAL_ACL_ENABLED"] = False
    if mode == "wrong_subject":
        st.secrets["HF53_COMMERCIAL_READ_SUBJECTS"] = ["f" * 64]
    if mode == "no_session":
        st.session_state.pop(HANDLE_KEY)
    before = list(sessions.calls)
    with pytest.raises(PrivateStoreDenied):
        build_integrated_staging_commercial_report(st=st, cloud=cloud, http=http)
    assert sessions.calls == before
    assert cloud.calls == 0
    assert http.snapshot_calls == []


def test_missing_official_document_fails_not_replaced_with_local_file():
    st, sessions, http, cloud = prepared()
    del http.documents["atendimentos_db"]
    with pytest.raises(PrivateStoreDenied):
        build_integrated_staging_commercial_report(st=st, cloud=cloud, http=http)
    assert cloud.calls == 1
    assert http.snapshot_calls == [
        "eq.historico_orcamentos", "eq.atendimentos_db",
    ]
