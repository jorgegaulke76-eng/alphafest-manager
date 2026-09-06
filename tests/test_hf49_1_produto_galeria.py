from site_completo_service import gerar_html_site_completo


def _catalogo():
    return [{
        "Nome":"CANECA PORCELANA PERSONALIZADA",
        "Ativo":True,
        "PublicarSite":True,
        "ProntoSite":True,
        "Categoria":"CANECAS PORCELANA COM ALÇA",
        "Subcategoria":"CANECAS",
        "Descricao":"Caneca personalizada",
        "Imagem":"",
    }]


def test_produto_com_trabalho_real_ganha_cta_e_foco_galeria():
    # O teste usa as chaves que o serviço normalizado reconhece na camada pública.
    catalogo=[{
        "Nome":"CANECA PORCELANA PERSONALIZADA","Ativo":True,"Status":"Ativo",
        "PublicarSite":True,
        "Categoria":"CANECAS PORCELANA COM ALÇA","Subcategoria":"CANECAS",
        "Descricao":"Caneca personalizada","Imagens":["https://example.com/produto.webp"]
    }]
    galeria=[{
        "produto":"CANECA PORCELANA PERSONALIZADA","categoria":"CANECAS PORCELANA COM ALÇA",
        "subcategoria":"CANECAS","tema":"DIA DA SECRETÁRIA","fotos":["https://example.com/caneca.webp"],
        "autorizado_publicacao":True,"selecionado_site":True,"arquivado":False,
    }]
    html=gerar_html_site_completo(catalogo,{"nome":"AlphaFest"},usar_taxonomia_catalogo=True,
        galeria_trabalhos=galeria,incluir_galeria=True,limite_fotos_galeria=24)
    assert 'data-product="caneca-porcelana-personalizada"' in html
    assert '📸 Ver trabalhos realizados' in html
    assert 'data-gallery-product="caneca-porcelana-personalizada"' in html
    assert 'gallery-product-focus' in html
    assert 'alphaFestGalleryShowProduct' in html


def test_sem_trabalho_selecionado_nao_mostra_cta():
    catalogo=[{
        "Nome":"CANECA PORCELANA PERSONALIZADA","Ativo":True,"Status":"Ativo",
        "PublicarSite":True,
        "Categoria":"CANECAS PORCELANA COM ALÇA","Subcategoria":"CANECAS","Descricao":"Caneca","Imagens":["https://example.com/produto.webp"],"PublicarSite":True
    }]
    html=gerar_html_site_completo(catalogo,{"nome":"AlphaFest"},usar_taxonomia_catalogo=True,
        galeria_trabalhos=[],incluir_galeria=True)
    assert '📸 Ver trabalhos realizados' not in html
