from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (720, 960), (224, 218, 207))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((155, 120, 565, 870), radius=72, fill=(28, 30, 34))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf8_hf5_version_and_template_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF9'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF9'
    assert anna['status_template'] == 'Em validação'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'


def test_hf8_hf5_keeps_ideal_para_semantic_icons_and_stronger_hierarchy():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'mantém SOMENTE ícones temáticos aprovados' in src
    assert '_draw_theme_icon(draw,x+card_w//2' in src
    for token in ('Logo splash correto com peso', 'Manchete editorial', 'Produto: palco maior',
                  'Benefícios: maior contraste', 'CTA dominante', 'Faixa rosa forte'):
        assert token in src


def test_hf8_hf5_anna_feed_stays_square_and_story_stays_vertical():
    for size in ((1080,1080), (1080,1920), (1920,1080)):
        data = engine.render_template(
            _sample(), size, template_id='anna_social_redes', title='GRAVAÇÃO LASER',
            subtitle='CORPORATIVO • Personalização durável para presentes, brindes e empresas',
            description='Presentes, brindes e empresas.', cta='FAÇA SEU PEDIDO!',
            phone='(11) 97294-9533', photo_mode='auto'
        )
        im = Image.open(BytesIO(data))
        assert im.size == size
        assert len(data) > 50000


def test_hf8_hf5_master_contract_stays_frozen():
    assert engine.ANNA_PROMPT_SPEC['formatos']['Instagram Feed'] == (1080,1080)
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert master['versao_template'] == 'HF53.2-HF5-HF7'
    assert master['oficial'] is True
    assert master['protegido'] is True
