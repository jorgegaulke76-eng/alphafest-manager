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


def test_hf9_version_and_anna_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF9'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF9'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'
    assert master['oficial'] and master['protegido']


def test_hf9_approved_reference_and_preview_assets_exist():
    for name in (
        'assets/marketing/anna_skin_master_1_reference.png',
        'assets/marketing/anna_skin_master_1.png',
        'assets/marketing/template_anna_redes_preview.png',
        'assets/marketing/whatsapp_classic.png',
    ):
        p = Path(name)
        assert p.exists() and p.stat().st_size > 1000


def test_hf9_renderer_contract_product_integrated_and_cyan_signature():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'def _product_stage_photo' in src
    assert 'fundo desfocado + produto nítido' in src
    assert 'sem mancha rosa estrutural' in src
    assert 'faixa cyan clara + texto azul escuro' in src
    assert 'whatsapp_classic.png' in src
    assert 'SOMENTE ícones temáticos' in src


def test_hf9_feed_and_story_render():
    for size in ((1080,1080), (1080,1920), (1920,1080)):
        data = engine.render_template(
            _sample(), size, template_id='anna_social_redes', title='GRAVAÇÃO LASER',
            subtitle='CORPORATIVO: Personalização durável para presentes, brindes e empresas',
            description='Personalização premium em copos e brindes.',
            phone='(11) 97294-9533', photo_mode='auto'
        )
        im = Image.open(BytesIO(data))
        assert im.size == size
        assert len(data) > 50000
