"""Testes de regressão dos links comerciais HF65.24.52."""
from urllib.parse import parse_qs, urlparse

import pytest

from site_metrics_dashboard_ui import campaign_link


def test_produto_gera_link_rastreavel():
    url = campaign_link("instagram", "stories", "natal-2026", "Produto específico", "bubble-personalizado")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "alphafest.com.br"
    assert parsed.path == "/"
    assert params == {
        "produto": ["bubble-personalizado"],
        "utm_source": ["instagram"],
        "utm_medium": ["stories"],
        "utm_campaign": ["natal-2026"],
    }


def test_destinos_antigos_permanecem_compativeis():
    assert campaign_link("google", "cpc", "brindes", "Para Empresas").startswith(
        "https://alphafest.com.br/empresas/?utm_source=google"
    )
    assert campaign_link("instagram", "bio", "natal", "Página inicial").startswith(
        "https://alphafest.com.br/?utm_source=instagram"
    )


def test_slug_ausente_rejeitado():
    with pytest.raises(ValueError):
        campaign_link("instagram", "post", "natal", "Produto específico", "")


def test_campanhas_contam_sessoes_e_cliques_sem_presumir_vendas():
    from datetime import datetime, timedelta, timezone
    from site_metrics_service import _campaign_opportunities

    now = datetime(2026, 11, 20, 20, 0, tzinfo=timezone.utc)

    def row(minutes, event, session, campaign="", source="", path="/"):
        return {
            "created_at": (now + timedelta(minutes=minutes)).isoformat(),
            "event_type": event,
            "session_id": session,
            "utm_campaign": campaign,
            "utm_source": source,
            "page_path": path,
        }

    rows = [
        row(0, "page_view", "a", "natal-2026", "instagram"),
        row(1, "product_open", "a"),
        row(2, "whatsapp_click", "a"),
        row(3, "whatsapp_click", "a"),
        row(0, "page_view", "b", "natal-2026", "instagram"),
        row(0, "page_view", "c", "natal-2026", "facebook"),
        row(1, "whatsapp_click", "c"),
        row(0, "page_view", "d"),
        row(1, "whatsapp_click", "d"),
    ]
    result = _campaign_opportunities(
        rows, now - timedelta(minutes=1), now + timedelta(minutes=10)
    )
    indexed = {(x["campanha"], x["canal"]): x for x in result}
    instagram = indexed[("natal-2026", "instagram")]
    assert instagram["sessoes"] == 2
    assert instagram["sessoes_whatsapp"] == 1
    assert instagram["cliques_whatsapp"] == 2
    assert instagram["percentual"] == 50.0
    facebook = indexed[("natal-2026", "facebook")]
    assert facebook["sessoes"] == 1
    assert facebook["sessoes_whatsapp"] == 1
    assert facebook["cliques_whatsapp"] == 1
    assert len(indexed) == 2
