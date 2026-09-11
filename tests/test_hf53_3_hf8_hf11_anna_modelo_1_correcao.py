from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw
import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (720, 900), (232, 235, 238))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 470, 720, 900), fill=(176, 127, 88))
    d.rounded_rectangle((70, 165, 330, 780), radius=48, fill=(28, 29, 32))
    d.rounded_rectangle((320, 145, 675, 820), radius=58, fill=(24, 25, 28))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf11_version_and_master_hf7_still_frozen():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF11'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF11'
    assert master['versao_template'] == 'HF53.2-HF5-HF7'
    assert master['oficial'] and master['protegido']


def test_hf11_visual_contract_modelo_anna_1():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    # Título travado no modelo aprovado quando for Gravação Laser.
    assert '_load_model_reference' in src
    assert '_is_modelo_anna_1_locked' in src
    assert '_render_modelo_anna_1_locked' in src
    assert 'anna_skin_master_1_reference.png' in src
    # fallback anterior continua documentado para outros títulos dinâmicos
    assert 'serif=True, italic=True' in src
    for width in ('stroke_width=14', 'stroke_width=11', 'stroke_width=8', 'stroke_width=3'):
        assert width in src
    # foto nítida, enquadramento mais aberto e um único selo ao final
    assert 'palco fotográfico nítido, sem desfoque do conteúdo' in src
    assert 'zoom = 1.02' in src
    assert 'Garante 1 único selo oficial e sempre como camada final' in src
    assert '_skin_without_approval_seal' in src
    assert '_approval_seal_overlay' in src
    # elementos já aprovados preservados
    assert 'whatsapp_classic.png' in src
    assert 'Ideal para:' in src


def test_hf11_feed_story_horizontal_render():
    sample = _sample()
    for size in ((1080, 1080), (1080, 1920), (1920, 1080)):
        data = engine.render_template(
            sample, size, template_id='anna_social_redes', title='GRAVAÇÃO LASER',
            subtitle='CORPORATIVO: Personalização durável para presentes, brindes e empresas',
            description='Personalização premium em copos e brindes.',
            phone='(11) 97294-9533', photo_mode='auto'
        )
        im = Image.open(BytesIO(data))
        assert im.size == size
        assert len(data) > 50000
