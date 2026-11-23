"""Verificações de pré-publicação da HF65.24.52 — SEM acessar a rede.

O site de teste usa credenciais públicas falsas. Não chama Cloudflare nem
Supabase e não executa publicar_pacote (deploy=100%).
"""
from __future__ import annotations

import io
from unittest.mock import patch
import zipfile

import pytest

from site_cloudflare_publish_service import extrair_pacote_publico, fingerprint_pacote
from site_metrics_service import inject_tracking
import site_metrics_service as metrics
from site_production_service import gerar_pacote_producao, preparar_html_producao

FAKE_SITE = (
    '<!doctype html><html lang="pt-BR"><head><title>AlphaFest</title></head><body>'
    '<main><article class="product-card" data-product="bubble-personalizado" '
    'data-detail-name="Bubble Personalizado">'
    '<h2>Bubble Personalizado</h2>'
    '<a href="https://wa.me/5511999999999?text=Solicitar%20or%C3%A7amento">'
    'Solicitar orçamento</a></article></main></body></html>'
)


def test_producao_preserva_rastreador_comercial_e_nao_publica_simulador():
    cfg = {
        "url": "https://hf52-preflight.invalid",
        "key": "sb_publishable_PREPUBLICACAO_FICTICIO",
    }
    with patch.object(metrics, "tracking_available", return_value=True), patch.object(
        metrics, "public_config", return_value=cfg
    ):
        html = inject_tracking(FAKE_SITE)
        pacote = gerar_pacote_producao(
            html,
            total_produtos=1,
            versao_manager="HF65.24.52-PREFLIGHT-FICTICIO",
            dicas_content=[],
        )

    with zipfile.ZipFile(io.BytesIO(pacote)) as arq:
        assert arq.testzip() is None
        names = set(arq.namelist())
        assert {
            "index.html", "404.html", "robots.txt", "sitemap.xml",
            "manifest.webmanifest", "sw.js", "empresas/index.html",
            "STATUS-PRODUCAO.json",
        } <= names

    assets, modules = extrair_pacote_publico(pacote)
    assert {"/index.html", "/robots.txt", "/sitemap.xml",
            "/empresas/index.html"} <= set(assets)
    home = assets["/index.html"].decode("utf-8")
    assert 'id="alphafest-site-metrics"' in home
    assert "fetch(endpoint" in home  # rastreador de produção, não o mock Pages
    assert "https://hf52-preflight.invalid" in home
    assert "data-product=\"bubble-personalizado\"" in home
    assert 'name="robots" content="noindex,nofollow,noarchive"' not in home
    assert "window.__HF52_PREVIEW_EVENTS" not in home
    assert "hf52-pages-protections" not in home
    assert "PRÉVIA ONLINE HF65.24.52" not in home
    assert b"Allow: /" in assets["/robots.txt"]
    assert "main.js" not in modules  # gerado no publicador Worker, não no ZIP
    assert len(fingerprint_pacote(pacote)) == 16


@pytest.mark.parametrize("marker", [
    "HOMOLOGAÇÃO",
    "SITE PARALELO HF40",
    "NÃO PUBLICADO EM ALPHAFEST.COM.BR",
    "noindex,nofollow,noarchive",
])
def test_html_producao_recusa_marcadores_de_staging(marker):
    with pytest.raises(ValueError):
        preparar_html_producao(FAKE_SITE.replace("</body>", marker + "</body>"))
