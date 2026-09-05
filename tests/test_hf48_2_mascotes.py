from pathlib import Path

from site_completo_service import gerar_html_site_completo


def _catalogo():
    return [{
        "Nome": "Caneca personalizada",
        "Categoria": "Canecas",
        "Subcategoria": "Porcelana",
        "Descricao": "Caneca personalizada",
        "Imagens": ["https://example.com/caneca.jpg"],
        "PublicarSite": True,
    }]


def test_hf482_mascotes_sao_opt_in_e_embutidos_so_na_previa_especifica():
    empresa = {"whatsapp_catalogo": "11972949533"}
    hf481 = gerar_html_site_completo(_catalogo(), empresa, modo_preview=True, usar_taxonomia_catalogo=True, visual_hf48=True)
    hf482 = gerar_html_site_completo(_catalogo(), empresa, modo_preview=True, usar_taxonomia_catalogo=True, visual_hf48=True, mascotes_hf48=True)
    assert "PRÉVIA INTERNA HF48.1" in hf481
    assert "Thu + Fox · AlphaFest" not in hf481
    assert "PRÉVIA INTERNA HF48.2" in hf482
    assert "Thu + Fox · AlphaFest" in hf482
    assert "data:image/webp;base64," in hf482
    assert "A Fox separou inspirações reais para você." not in hf482  # sem Galeria ligada


def test_hf482_ativos_existem_e_manager_prepara_sob_demanda():
    raiz = Path('.')
    for nome in ["thu_fox_hero.webp", "fox_galeria.webp", "thu_fox_cta.webp"]:
        caminho = raiz / "assets" / "mascotes" / nome
        assert caminho.exists()
        assert caminho.stat().st_size < 100_000
    app = Path("app.py").read_text(encoding="utf-8")
    assert '"🦊 Thu + Fox no novo Site — HF48.2"' in app
    assert '"🦊 Preparar / atualizar prévia Thu + Fox HF48.2"' in app
    assert "mascotes_hf48=True" in app
    bloco_prod = app.split('# HF44 — publicação assistida no Worker', 1)[1]
    chamada = bloco_prod.split('pacote_producao_hf44 =', 1)[0]
    assert "mascotes_hf48=True" not in chamada
