"""Contrato da fonte oficial: historico_orcamentos e atendimentos_db.itens."""
from decimal import Decimal
import pytest

from commercial_official_snapshot_adapter import (
    sanitize_official_manager_snapshots, make_sanitized_official_snapshot_loader,
)
from commercial_verified_report import build_verified_commercial_report
from commercial_private_document_adapter import PrivateStoreDenied


def _sample():
    return [
        {"numero_proposta": "P-1", "atendimento_id": "A-1", "pago": True,
         "valor_total": "120,00", "cliente": "SEGREDO CLIENTE",
         "telefone": "11999999999", "documento": "00000000000",
         "endereco": "rua confidencial"},
        {"numero_proposta": "P-2", "atendimento_id": "A-2", "pago": True,
         "valor_total": "80,00", "pagamento_parcial": True,
         "cliente_nome": "SEGREDO DOIS"},
    ], {"config": {"senha": "SEGREDO BACKEND"}, "itens": [
        {"id": "A-1", "etapa_captacao": "Venda fechada", "telefone": "11999999999",
         "mensagem": "PRIVADO", "cliente": "SEGREDO CLIENTE"},
        {"id": "A-2", "etapa_captacao": "Novo contato", "whatsapp": "11999999998"},
    ]}


def test_official_envelopes_keep_only_business_fields_and_drop_pii():
    source_proposals, source_contacts = _sample()
    proposals, contacts = sanitize_official_manager_snapshots(
        historico_orcamentos=source_proposals,
        atendimentos_db=source_contacts,
    )
    serialized = str((proposals, contacts))
    for secret in ("SEGREDO", "119999999", "PRIVADO", "rua confidencial"):
        assert secret not in serialized
    assert proposals == [
        {"numero_proposta": "P-1", "atendimento_id": "A-1", "pago": True,
         "valor_total": "120,00"},
        {"numero_proposta": "P-2", "atendimento_id": "A-2", "pago": True,
         "valor_total": "80,00", "pagamento_parcial": True},
    ]
    assert contacts == [
        {"id": "A-1", "etapa_captacao": "Venda fechada"},
        {"id": "A-2", "etapa_captacao": "Novo contato"},
    ]
    assert build_verified_commercial_report(contacts, proposals, [])["receita_atribuida"] == Decimal("0")


@pytest.mark.parametrize("bad_proposals,bad_contacts", [
    (None, {"itens": []}), ([], []), ([None], {"itens": []}),
    ([{"numero_proposta": "P-1"}], {"itens": []}),
    ([], {"itens": [{"cliente": "Sem id"}]}),
])
def test_bad_or_incomplete_snapshots_fail_closed(bad_proposals, bad_contacts):
    with pytest.raises(PrivateStoreDenied):
        sanitize_official_manager_snapshots(
            historico_orcamentos=bad_proposals,
            atendimentos_db=bad_contacts,
        )


def test_loader_reads_both_sources_once_and_never_uses_fallback():
    proposals, contacts = _sample()
    calls = []
    loader = make_sanitized_official_snapshot_loader(
        read_proposals=lambda: calls.append("propostas") or proposals,
        read_contacts=lambda: calls.append("atendimentos") or contacts,
    )
    normalized = loader()
    assert calls == ["propostas", "atendimentos"]
    assert len(normalized[0]) == 2 and len(normalized[1]) == 2
    failing = make_sanitized_official_snapshot_loader(
        read_proposals=lambda: proposals,
        read_contacts=lambda: (_ for _ in ()).throw(OSError("offline")),
    )
    with pytest.raises(PrivateStoreDenied):
        failing()
