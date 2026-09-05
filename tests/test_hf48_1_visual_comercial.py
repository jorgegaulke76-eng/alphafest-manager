from pathlib import Path

from site_completo_service import gerar_html_site_completo


def _catalogo():
    return [
        {
            "Nome": "Caneca personalizada",
            "Categoria": "Canecas",
            "Subcategoria": "Porcelana",
            "Descricao": "Caneca personalizada para presente",
            "Imagens": ["https://example.com/caneca.jpg"],
            "PublicarSite": True,
        },
        {
            "Nome": "Topo de bolo",
            "Categoria": "Festas & Personalizados",
            "Subcategoria": "Topos de bolo",
            "Descricao": "Topo personalizado",
            "Imagens": ["https://example.com/topo.jpg"],
            "PublicarSite": True,
        },
    ]


def test_hf481_visual_e_opt_in_e_preserva_padrao():
    empresa = {"whatsapp_catalogo": "11972949533", "slogan": "O poder de estar presente em cada presente!"}
    base = gerar_html_site_completo(_catalogo(), empresa, modo_preview=True, usar_taxonomia_catalogo=True)
    novo = gerar_html_site_completo(_catalogo(), empresa, modo_preview=True, usar_taxonomia_catalogo=True, visual_hf48=True)
    assert "PRÉVIA INTERNA HF48.1" not in base
    assert "hf48-topline" not in base
    assert "PRÉVIA INTERNA HF48.1" in novo
    assert "hf48-topline" in novo
    assert "O que você está procurando?" in novo
    assert 'id="categorias"' in novo
    assert "Explore por categoria" in novo
    assert "Como pedir na AlphaFest" in novo


def test_hf481_categoria_visual_dispara_filtro_existente():
    novo = gerar_html_site_completo(_catalogo(), {}, modo_preview=True, usar_taxonomia_catalogo=True, visual_hf48=True)
    assert "data-hf48-cat" in novo
    assert "category-filter" in novo
    assert "filtro.click()" in novo
    assert "scrollIntoView" in novo


def test_hf481_manager_so_prepara_sob_demanda_e_hf44_nao_usa_flag():
    app = Path("app.py").read_text(encoding="utf-8")
    assert '"🎨 Novo visual comercial do Site — HF48.1"' in app
    assert '"🎨 Preparar / atualizar novo visual HF48.1"' in app
    assert "visual_hf48=True" in app
    assert "reaproveita exatamente os mesmos dados já cadastrados" in app
    bloco_prod = app.split('# HF44 — publicação assistida no Worker', 1)[1]
    chamada = bloco_prod.split('pacote_producao_hf44 =', 1)[0]
    assert "visual_hf48=True" not in chamada
