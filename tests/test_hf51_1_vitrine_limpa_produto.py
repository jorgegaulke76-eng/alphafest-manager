from site_vitrine_service import gerar_html_vitrine


def _empresa():
    return {"nome":"AlphaFest","whatsapp_catalogo":"11999998888"}


def _produto(nome="Caneca", **extra):
    base={
        "Nome":nome,
        "Descricao":"Descrição completa do produto para aparecer somente na ficha.",
        "Imagens":["https://example.com/caneca.jpg"],
        "Categoria":"CANECAS",
        "Subcategoria":"PORCELANA",
        "Preco":"29,90",
        "PublicarSite":True,
    }
    base.update(extra)
    return base


def test_card_publico_fica_so_foto_e_nome_sem_selo_descricao_preco_cta():
    html=gerar_html_vitrine([_produto(Destaque=True,ExibirPrecoSite=True)],_empresa(),usar_taxonomia_catalogo=True)
    card=html.split('<article class="product-card product-card-compact"',1)[1].split('</article>',1)[0]
    assert '⭐ Destaque' not in card
    assert '<p>' not in card
    assert 'Pedir orçamento' not in card
    assert '<div class="price">' not in card
    assert '<h3>Caneca</h3>' in card
    assert 'https://example.com/caneca.jpg' in card


def test_ficha_recebe_descricao_e_preco_quando_manager_autoriza():
    html=gerar_html_vitrine([_produto(ExibirPrecoSite=True)],_empresa(),usar_taxonomia_catalogo=True)
    assert 'data-detail-description="Descrição completa do produto para aparecer somente na ficha."' in html
    assert 'data-detail-price="R$ 29,90"' in html
    assert 'id="product-detail-modal"' in html
    assert 'id="product-detail-image"' in html
    assert 'id="product-detail-whatsapp"' in html


def test_ficha_oculta_preco_quando_manager_nao_autoriza():
    html=gerar_html_vitrine([_produto(ExibirPrecoSite=False)],_empresa(),usar_taxonomia_catalogo=True)
    assert 'data-detail-price=""' in html
    assert 'data-detail-price="R$ 29,90"' not in html


def test_relacionados_priorizam_mesma_subcategoria_e_categoria():
    html=gerar_html_vitrine([
        _produto("Caneca A"),
        _produto("Caneca B"),
        _produto("Caneca C",Subcategoria="INOX"),
    ],_empresa(),usar_taxonomia_catalogo=True)
    assert 'Você também pode gostar' in html
    assert 'function relatedFor(card)' in html
    assert 'sameSub' in html and 'sameCat' in html
