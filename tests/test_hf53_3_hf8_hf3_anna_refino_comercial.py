from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (720, 960), (232, 228, 220))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((140, 150, 580, 850), radius=70, fill=(28, 30, 34))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf8_hf3_version_and_anna_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF8'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF8'
    assert anna['status_template'] == 'Em validação'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'


def test_hf8_hf3_square_renderer_keeps_network_contract():
    data = engine.render_template(
        _sample(), (1080,1080), template_id='anna_social_redes',
        title='Gravação Laser', subtitle='Corporativo • Personalização durável',
        description='Presentes, brindes e empresas.', cta='FAÇA SEU PEDIDO!',
        phone='(11) 97294-9533', photo_mode='auto'
    )
    im = Image.open(BytesIO(data))
    assert im.size == (1080,1080)
    assert len(data) > 50000


def test_hf8_hf3_renderer_has_commercial_refinement_contract():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    for token in (
        '_remove_grabcut_background', 'Logo splash correto', 'Manchete:',
        'Produto protagonista', 'Benefícios grandes', 'Vitrine "Ideal para"',
        'CTA: um dos três maiores pesos', 'Fechamento emocional em rosa',
    ):
        assert token in src


def test_hf8_hf3_feed_stays_square_only_for_anna():
    assert engine.ANNA_PROMPT_SPEC['formatos']['Instagram Feed'] == (1080,1080)
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'return (1080, 1080)' in app
    assert '"Instagram Feed": {"size": (1080, 1350)' in app
