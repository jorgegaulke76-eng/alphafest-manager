from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

import marketing_template_engine as engine
import marketing_anna_renderer as anna


def _sample(variable_bg=False):
    im = Image.new('RGB', (720, 960), (230, 224, 214))
    d = ImageDraw.Draw(im)
    if variable_bg:
        d.rectangle((0, 0, 720, 420), fill=(190, 214, 228))
        d.rectangle((0, 420, 720, 960), fill=(185, 135, 88))
    d.rounded_rectangle((125, 145, 345, 815), radius=50, fill=(30, 32, 35))
    d.rounded_rectangle((330, 105, 610, 860), radius=60, fill=(25, 27, 30))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf8_hf7_version_and_template_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF7'
    anna_tpl = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna_tpl['versao_template'] == 'HF53.3-HF8-HF7'
    assert anna_tpl['status_template'] == 'Em validação'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'
    assert master['oficial'] is True and master['protegido'] is True


def test_hf8_hf7_visual_contract_has_outline_organic_photo_and_compact_cta():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'stroke_width=8' in src and 'stroke_width=4' in src
    assert 'fallback fotográfico premium com recorte orgânico' in src
    assert 'cta=(622,807,1055,925)' in src
    assert 'text_x1,text_x2=730,1042' in src
    assert 'whatsapp_classic.png' in src
    assert 'mantém SOMENTE ícones temáticos aprovados' in src


def test_hf8_hf7_auto_mode_does_not_force_grabcut_on_variable_background(monkeypatch):
    called = {'grabcut': False}
    def fail_if_called(source):
        called['grabcut'] = True
        raise AssertionError('GrabCut não deve ser forçado no modo auto')
    monkeypatch.setattr(anna, '_remove_grabcut_background', fail_if_called)
    layer, pos = anna._product_layer(_sample(variable_bg=True), (0, 0, 500, 550), 'auto')
    assert called['grabcut'] is False
    assert layer.size == (500, 550)
    assert layer.getchannel('A').getextrema()[0] < 255


def test_hf8_hf7_feed_story_horizontal_render():
    for size in ((1080,1080),(1080,1920),(1920,1080)):
        data = engine.render_template(
            _sample(variable_bg=True), size, template_id='anna_social_redes', title='GRAVAÇÃO LASER',
            subtitle='CORPORATIVO: Personalização durável para presentes, brindes e empresas',
            description='Gravação a laser em copos e brindes personalizados.', cta='FAÇA SEU PEDIDO!',
            phone='(11) 97294-9533', photo_mode='auto'
        )
        im = Image.open(BytesIO(data))
        assert im.size == size
        assert len(data) > 50000
