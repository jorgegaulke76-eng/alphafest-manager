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
