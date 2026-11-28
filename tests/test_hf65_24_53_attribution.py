"""HF65.24.53: contrato do vínculo explícito, auditoria e revogação."""
import pytest
from commercial_attribution_service import build_attribution_event, effective_attributions
from commercial_conversion_service import summarize_verified_campaign_sales


ORDERS = [{"numero_proposta": "P-1", "atendimento_id": "A-1",
           "pago": True, "valor_total": "150,00"}]
CONTACTS = [{"id": "A-1", "campanha": "natal_2026"}]


def event(when="2026-11-23T14:00:00-03:00", decision="confirmar",
          campaign="natal_2026", **kwargs):
    return build_attribution_event(
        numero_proposta=kwargs.get("numero_proposta", "P-1"),
        atendimento_id=kwargs.get("atendimento_id", "A-1"),
        campaign=campaign,
        decisao=decision,
        evidencia="mensagem_whatsapp",
        usuario="operador_teste",
        ocorrido_em=when,
        propostas=kwargs.get("propostas", ORDERS),
        atendimentos=kwargs.get("atendimentos", CONTACTS),
    )


def test_confirm_then_revoke_with_no_revenue():
    first = event()
    assert effective_attributions([first]) == [
        {"numero_proposta": "P-1", "campaign": "natal_2026"}
    ]
    assert summarize_verified_campaign_sales(ORDERS, effective_attributions([first]))[
        "natal_2026"]["paid_revenue"] == 150
    removed = event("2026-11-23T14:01:00-03:00", "revogar")
    assert effective_attributions([first, removed]) == []
    assert summarize_verified_campaign_sales(ORDERS, effective_attributions([first, removed])) == {}


def test_conflicting_events_at_same_instant_are_not_attributed():
    assert effective_attributions([
        event(campaign="natal"),
        event(campaign="professores"),
    ]) == []


def test_change_with_unique_timestamps_is_traceable():
    assert effective_attributions([
        event(campaign="natal"),
        event("2026-11-23T14:02:00-03:00", campaign="professores"),
    ]) == [{"numero_proposta": "P-1", "campaign": "professores"}]


@pytest.mark.parametrize("campaign", ["cliente@email.com", "11999999999",
    "natal 2026", "https://site", ""])
def test_invalid_campaign_rejected(campaign):
    with pytest.raises(ValueError):
        event(campaign=campaign)


def test_wrong_order_contact_link_and_duplicated_proposal_rejected():
    with pytest.raises(ValueError):
        event(atendimento_id="A-2")
    with pytest.raises(ValueError):
        event(propostas=ORDERS + ORDERS)


def test_timezone_required_and_unknown_evidence_rejected():
    with pytest.raises(ValueError):
        event(when="2026-11-23T14:00:00")
    with pytest.raises(ValueError):
        build_attribution_event(numero_proposta="P-1", atendimento_id="A-1",
            campaign="natal", decisao="confirmar", evidencia="inventada",
            usuario="operador", ocorrido_em="2026-11-23T14:00:00-03:00",
            propostas=ORDERS, atendimentos=CONTACTS)


def test_unvalidated_events_do_not_resolve_to_sales():
    assert effective_attributions([
        {"numero_proposta": "P-1", "campaign": "invalid space",
         "atendimento_id": "A-1", "decisao": "confirmar",
         "ocorrido_em": "2026-11-23T14:00:00-03:00"},
    ]) == []
