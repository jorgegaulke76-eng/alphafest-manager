from pathlib import Path
SRC=Path('site_visual_hf48_service.py').read_text(encoding='utf-8')
APP=Path('app.py').read_text(encoding='utf-8')
def test_mobile_more_contract():
    assert 'HF51.4-HF3' in SRC
    assert 'hf50-mobile-more' in SRC
    assert "new Set(['Serviços','Quem Somos','Contato','Galeria'])" in SRC
    assert "☰ <span>Mais</span>" in SRC
    assert '.site-nav .hf50-mobile-hide{display:none!important}' in SRC
    assert '@media(min-width:621px){.hf50-mobile-more{display:none!important}}' in SRC

def test_version_and_production_contract():
    assert 'HF51.4-HF3' in APP
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF52.2-HF1-HF3'
