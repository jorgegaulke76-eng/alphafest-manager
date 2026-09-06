from pathlib import Path

from PIL import Image

from site_visual_hf48_service import aplicar_visual_hf48


def _base():
    return """<html><head><style></style></head><body><header class='header'><div class='header-in'><img class='brand-logo'><div class='brand-copy'><strong>AlphaFest</strong><span>x</span></div><div class='header-actions'></div></div></header><nav class='site-nav'><div class='site-nav-in'><button type='button' data-site-scroll='inicio'>Início</button><button type='button' data-site-scroll='produtos'>Produtos</button></div></nav><section class='hero' id='inicio'></section><main class='main'><section id='produtos'><input id='search'></section></main><section class='site-section pink' id='servicos'></section><footer class='footer'></footer><div class='preview-bar'>X</div></body></html>"""


def test_hf48_2_hf1_remove_contadores_do_hero_e_usa_beneficios():
    html = aplicar_visual_hf48(_base(), [{'nome':'A','categoria':'Festas','subcategoria':'Topo','site_ativo':True}], {'nome':'AlphaFest'}, usar_mascotes=True)
    assert 'produtos na vitrine' not in html
    assert 'categorias atuais' not in html
    assert 'Personalização que conta sua história' in html
    assert 'Qualidade em cada detalhe' in html
    assert 'Ideias para todas as ocasiões' in html
    assert 'PRÉVIA INTERNA HF50.1-HF4' in html


def test_assets_mascotes_hf48_2_hf1_tem_transparencia_real():
    raiz = Path(__file__).resolve().parents[1] / 'assets' / 'mascotes'
    for nome in ('thu_fox_hero.webp','fox_galeria.webp','thu_fox_cta.webp'):
        im = Image.open(raiz / nome).convert('RGBA')
        assert im.getchannel('A').getextrema()[0] == 0
