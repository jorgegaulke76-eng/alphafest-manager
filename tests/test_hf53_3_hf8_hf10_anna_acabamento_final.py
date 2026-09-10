from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw
import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (665, 880), (226, 232, 238))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 420, 665, 880), fill=(188, 136, 91))
    d.rounded_rectangle((65, 175, 300, 740), radius=45, fill=(30, 31, 34))
    d.rounded_rectangle((285, 150, 610, 785), radius=55, fill=(25, 26, 29))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf10_version_and_master_still_frozen():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF10'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF10'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'
    assert master['oficial'] and master['protegido']


def test_hf10_contract_title_photo_seal_and_cards():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'palco fotográfico nítido, sem efeito embaçado' in src
    assert 'ImageFilter.UnsharpMask' in src
    assert 'o selo oficial é a última camada' in src
    assert '_approval_seal_overlay' in src
    assert 'serif=True, italic=True' in src
    assert 'fill=white, outline=' in src  # cards Ideal para continuam com fundo


def test_hf10_feed_render():
    data = engine.render_template(
        _sample(), (1080,1080), template_id='anna_social_redes', title='GRAVAÇÃO LASER',
        subtitle='CORPORATIVO: Personalização durável para presentes, brindes e empresas',
        description='Personalização premium em copos e brindes.',
        phone='(11) 97294-9533', photo_mode='auto'
    )
    im = Image.open(BytesIO(data))
    assert im.size == (1080,1080)
    assert len(data) > 50000
