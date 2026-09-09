from site_completo_service import gerar_html_site_completo


def test_hf501_hf7_carrossel_fica_entre_hero_e_categorias():
    catalogo = [
        {
            "Nome": "Caneca personalizada",
            "Categoria": "Canecas",
            "Subcategoria": "Porcelana",
            "Descricao": "Caneca personalizada para presente",
            "Imagens": ["https://example.com/caneca.jpg"],
            "PublicarSite": True,
            "Destaque": True,
            "CarrosselSite": True,
        }
    ]
    pagina = gerar_html_site_completo(
        catalogo,
        {"whatsapp_catalogo": "11972949533"},
        modo_preview=True,
        usar_taxonomia_catalogo=True,
        visual_hf48=True,
        mascotes_hf48=True,
    )
    hero = pagina.index('id="inicio"')
    carrossel = pagina.index('class="hf50-carousel"')
    categorias = pagina.index('id="categorias"')
    assert hero < carrossel < categorias
    assert '.hf48-hero-branded + .hf50-carousel' in pagina
    assert 'padding-top:0!important' in pagina
