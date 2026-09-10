from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (720, 960), (228, 220, 205))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((150, 120, 570, 875), radius=68, fill=(28, 30, 34))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf8_hf6_version_and_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF9'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF9'
    assert anna['status_template'] == 'Em validação'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'


def test_hf8_hf6_title_is_centered_smaller_and_top_is_organic_splash():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'title_x1, title_x2 = 34, 574' in src
    assert 'tx=title_x1+(title_area_w-tw)//2-bb[0]' in src
    assert 'start_size=80 if i==0 else 70' in src
    assert 'manchas superiores orgânicas' in src
    assert 'def blob(cx, cy, rx, ry, color, lobes)' in src


def test_hf8_hf6_uses_classic_whatsapp_asset_and_keeps_semantic_icons():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'assets" / "marketing" / "whatsapp_classic.png' in src
    assert 'whatsapp_classic.png' in src
    assert 'NÃO repete miniatura do produto' in src
    assert '_draw_theme_icon(draw,x+card_w//2' in src


def test_hf8_hf6_feed_renders_square():
    data = engine.render_template(
        _sample(), (1080,1080), template_id='anna_social_redes', title='GRAVAÇÃO LASER',
        subtitle='CORPORATIVO • Personalização durável para presentes, brindes e empresas',
        description='Presentes, brindes e empresas.', cta='FAÇA SEU PEDIDO!',
        phone='(11) 97294-9533', photo_mode='auto'
    )
    im = Image.open(BytesIO(data))
    assert im.size == (1080,1080)
    assert len(data) > 50000
