from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (720, 960), (235, 232, 225))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((170, 140, 550, 860), radius=70, fill=(30, 32, 35))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf8_hf4_version_and_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF8'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF8'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'


def test_hf8_hf4_ideal_para_uses_semantic_icons_not_product_thumbnails():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'def _draw_theme_icon' in src
    assert 'NÃO repete miniatura do produto' in src
    assert '_draw_theme_icon(draw,x+card_w//2' in src
    # bloco HF4 não deve mais decidir entre foto real e placeholder nos cards
    block = src.split('# Vitrine "Ideal para" — HF53.3-HF8-HF8:',1)[1].split('# CTA:',1)[0]
    assert 'ImageOps.fit' not in block
    assert 'application_images' not in block


def test_hf8_hf4_feed_renders_square_with_icon_cards():
    data = engine.render_template(
        _sample(), (1080,1080), template_id='anna_social_redes',
        title='Gravação Laser', subtitle='Corporativo',
        description='Presentes, brindes e empresas.', cta='FAÇA SEU PEDIDO!',
        phone='(11) 97294-9533', photo_mode='auto'
    )
    im = Image.open(BytesIO(data))
    assert im.size == (1080,1080)
    assert len(data) > 50000
