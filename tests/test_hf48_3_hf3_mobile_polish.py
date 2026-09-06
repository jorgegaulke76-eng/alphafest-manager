from site_visual_hf48_service import aplicar_visual_hf48


def _base():
    return """<html><head><style></style></head><body><header class='header'><div class='header-in'><img class='brand-logo'><div class='brand-copy'><strong>AlphaFest</strong><span>x</span></div><div class='header-actions'></div></div></header><nav class='site-nav'><div class='site-nav-in'><button type='button' data-site-scroll='inicio'>Início</button><button type='button' data-site-scroll='produtos'>Produtos</button></div></nav><section class='hero' id='inicio'></section><main class='main'><section id='produtos'><input id='search'></section></main><section class='site-section pink' id='servicos'></section><footer class='footer'></footer><div class='preview-bar'>X</div></body></html>"""


def test_hf483_hf3_mobile_reduz_faixa_e_antecipa_mascotes():
    html = aplicar_visual_hf48(_base(), [{'nome':'A','categoria':'Festas','subcategoria':'Topo','site_ativo':True}], {'nome':'AlphaFest'}, usar_mascotes=True)
    assert '.preview-bar{font-size:7px!important' in html
    assert '.hero-in{padding:32px 14px 38px;row-gap:28px}' in html
    assert '.hero-card.hf48-mascot-hero{min-height:455px;padding:26px 16px 245px;margin-top:4px}' in html
    assert '.hf48-hero-mascot-img{width:82%;right:7%;bottom:6px;max-height:250px}' in html
    assert 'PRÉVIA INTERNA HF50.1-HF5' in html
