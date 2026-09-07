from site_visual_hf48_service import aplicar_visual_hf48


def _base():
    return """<html><head><style></style></head><body><header class='header'><div class='header-in'><img class='brand-logo'><div class='brand-copy'><strong>AlphaFest</strong><span>x</span></div><div class='header-actions'></div></div></header><nav class='site-nav'><div class='site-nav-in'><button type='button' data-site-scroll='inicio'>Início</button><button type='button' data-site-scroll='produtos'>Produtos</button></div></nav><section class='hero' id='inicio'></section><main class='main'><section id='produtos'><input id='search'></section></main><section class='site-section pink' id='servicos'></section><footer class='footer'></footer><div class='preview-bar'>X</div></body></html>"""


def test_hf501_hf1_remove_rotulos_circulados_e_preserva_carrossel():
    catalogo=[{'nome':'Caneca','categoria':'Canecas','subcategoria':'Porcelana','site_ativo':True,'destaque':True,'descricao':'Teste'}]
    html=aplicar_visual_hf48(_base(), catalogo, {'nome':'AlphaFest'}, usar_mascotes=True)
    assert 'Thu + Fox · AlphaFest' not in html
    assert 'Destaques da semana, campanhas e datas especiais' not in html
    assert 'Em destaque agora' not in html
    assert 'hf50-carousel-track' in html
    assert 'hf50-carousel-arrow' in html
    assert 'hf50-carousel-dots' in html
    assert 'PRÉVIA INTERNA HF51.1-HF2' in html
