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


def test_campanha_identificada_apos_acesso_direto_conta_apenas_cliques_posteriores():
    from datetime import datetime, timedelta, timezone
    from site_metrics_service import _campaign_opportunities

    now = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)

    def event(minute, kind, campaign="", source=""):
        return {
            "created_at": (now + timedelta(minutes=minute)).isoformat(),
            "event_type": kind,
            "session_id": "sessao-de-teste",
            "page_path": "/",
            "utm_campaign": campaign,
            "utm_source": source,
        }

    events = [
        event(0, "page_view"),                    # entrada direta
        event(1, "whatsapp_click"),               # ANTES da campanha
        event(2, "page_view", "natal-2026", "instagram"),
        event(3, "product_open"),
        event(4, "whatsapp_click"),
        event(5, "page_view", "outra-campanha", "facebook"),
        event(6, "whatsapp_click"),
    ]
    summary = _campaign_opportunities(
        events, now - timedelta(seconds=1), now + timedelta(minutes=10)
    )
    assert len(summary) == 1
    row = summary[0]
    assert row["campanha"] == "natal-2026"
    assert row["canal"] == "instagram"
    assert row["sessoes"] == 1
    assert row["sessoes_whatsapp"] == 1
    assert row["cliques_whatsapp"] == 2


def test_nome_real_do_catalogo_usa_slug_correto_com_acentos():
    from site_vitrine_service import _slug

    nome = "Bubble Personalizado com Confetes e Balões Metalizado"
    url = campaign_link("instagram", "stories", "natal-2026", "Produto específico", nome)
    slug = parse_qs(urlparse(url).query)["produto"][0]
    assert slug == _slug(nome)
    assert slug == "bubble-personalizado-com-confetes-e-baloes-metalizado"


def test_geracao_da_vitrine_mantem_identificador_e_nao_publica_produto_desmarcado():
    from site_vitrine_service import gerar_html_vitrine

    produtos = [
        {"Nome": "Bubble Personalizado com Confetes e Balões Metalizado",
         "Descricao": "Bubble de festa", "Imagens": ["https://example.com/bubble.webp"],
         "PublicarSite": True, "Ativo": True, "Categoria": "BALÃO"},
        {"Nome": "ARCO DE BALÃO TRADICIONAL",
         "Descricao": "Arco decorativo", "Imagens": ["https://example.com/arco.webp"],
         "PublicarSite": True, "Ativo": True, "Categoria": "BALÃO"},
        {"Nome": "Produto Interno",
         "Descricao": "Reservado", "Imagens": ["https://example.com/interno.webp"],
         "PublicarSite": False, "Ativo": True, "Categoria": "OUTROS"},
    ]
    html = gerar_html_vitrine(produtos, {"nome": "AlphaFest", "celular": "11972949533"}, modo_preview=True)
    assert 'data-product="bubble-personalizado-com-confetes-e-baloes-metalizado"' in html
    assert 'data-product="arco-de-balao-tradicional"' in html
    assert 'data-product="produto-interno"' not in html
    assert 'class="product-card product-card-compact"' in html


def test_renomeacao_mantem_link_antigo_quando_nome_anterior_esta_nos_aliases():
    from site_vitrine_service import gerar_html_vitrine

    produtos = [
        {"Nome": "Bubble Novo", "Aliases": ["Bubble Antigo", "Promo Compartilhada"],
         "Descricao": "Bubble de festa", "Imagens": ["https://example.com/bubble.webp"],
         "PublicarSite": True, "Ativo": True, "Categoria": "BALÃO"},
        {"Nome": "Balão Premium", "Aliases": ["Promo Compartilhada", "Bubble Novo"],
         "Descricao": "Balão decorado", "Imagens": ["https://example.com/balao.webp"],
         "PublicarSite": True, "Ativo": True, "Categoria": "BALÃO"},
    ]
    html = gerar_html_vitrine(produtos, {"nome": "AlphaFest", "celular": "11972949533"}, modo_preview=True)
    assert 'data-product="bubble-novo" data-product-aliases="bubble-antigo"' in html
    assert 'data-product="balao-premium" data-product-aliases=""' in html
    # Alias ambíguo não pode direcionar o cliente ao produto errado.
    assert 'data-product-aliases="promo-compartilhada"' not in html
    assert 'data-product-aliases="bubble-novo"' not in html


def test_link_utm_antigo_eh_preservado_pelo_mesmo_slug_de_alias():
    url = campaign_link(
        "instagram", "stories", "natal-2026", "Produto específico", "Bubble Antigo"
    )
    params = parse_qs(urlparse(url).query)
    assert params["produto"] == ["bubble-antigo"]
    assert params["utm_campaign"] == ["natal-2026"]


def test_lista_publicada_filtra_slugs_invalidos_e_ambiguos():
    from site_metrics_dashboard_ui import published_products_from_html

    public_html = """
    <article class="product-card product-card-compact" data-detail-name="Bubble &amp; Balões" data-product="bubble-baloes"></article>
    <article class="product-card" data-product="caneca-personalizada" data-detail-name="Caneca Personalizada"></article>
    <article class="product-card" data-product="caneca-personalizada" data-detail-name="Caneca Duplicada"></article>
    <article class="product-card" data-product="codigo?privado=1" data-detail-name="Link inválido"></article>
    <article class="outro-card" data-product="nao-e-produto" data-detail-name="Outra seção"></article>
    <article class="product-card" data-product="sem-nome"></article>
    """
    assert published_products_from_html(public_html) == (
        ("Bubble & Balões", "bubble-baloes"),
    )


def test_lista_publicada_cacheada_nao_dispara_requisicoes_repetidas(monkeypatch):
    import site_metrics_dashboard_ui as ui

    calls = []

    class Response:
        content = (
            b'<article class="product-card product-card-compact" '
            b'data-detail-name="Bubble Personalizado" data-product="bubble-personalizado"></article>'
        )

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    ui.published_products_cached.cache_clear()
    monkeypatch.setattr(ui.requests, "get", fake_get)
    try:
        first = ui.published_products_cached(123456)
        second = ui.published_products_cached(123456)
        assert first == second == (("Bubble Personalizado", "bubble-personalizado"),)
        assert len(calls) == 1
        assert calls[0][0] == "https://alphafest.com.br/"
        assert calls[0][1]["timeout"] == 15
    finally:
        ui.published_products_cached.cache_clear()
