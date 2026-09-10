from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

import marketing_template_engine as engine


def _sample():
    im = Image.new('RGB', (665, 880), (220, 224, 228))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 400, 665, 880), fill=(185, 135, 88))
    d.rounded_rectangle((70, 200, 295, 720), radius=40, fill=(28, 30, 34))
    d.rounded_rectangle((280, 170, 600, 760), radius=50, fill=(24, 26, 29))
    out = BytesIO(); im.save(out, 'PNG'); return out.getvalue()


def test_hf8_hf8_version_and_skin_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF8'
    anna = next(x for x in engine.listar_templates() if x['id'] == 'anna_social_redes')
    master = next(x for x in engine.listar_templates() if x['id'] == 'splash_premium_anna')
    assert anna['versao_template'] == 'HF53.3-HF8-HF8'
    assert 'Skin Mestre 1' in anna['descricao']
    assert master['versao_template'] == 'HF53.2-HF5-HF7'
    assert master['oficial'] is True and master['protegido'] is True


def test_hf8_hf8_skin_asset_is_fixed_only_where_needed():
    path = Path('assets/marketing/anna_skin_master_1.png')
    ref = Path('assets/marketing/anna_skin_master_1_reference.png')
    assert path.exists() and ref.exists()
    im = Image.open(path).convert('RGBA')
    assert im.size == (1080, 1080)
    # topo e rodapé têm pele gráfica; miolo continua transparente/dinâmico
    assert im.getpixel((100, 50))[3] > 200
    assert im.getpixel((500, 500))[3] == 0
    assert im.getpixel((500, 1050))[3] > 200


def test_hf8_hf8_renderer_uses_skin_and_dynamic_product():
    src = Path('marketing_anna_renderer.py').read_text(encoding='utf-8')
    assert 'def _load_skin_master' in src
    assert 'anna_skin_master_1.png' in src
    assert 'zoom editorial conservador' in src
    assert 'NÃO repete miniatura do produto' in src
    assert 'whatsapp_classic.png' in src

    data = engine.render_template(
        _sample(), (1080, 1080), template_id='anna_social_redes',
        title='GRAVAÇÃO LASER',
        subtitle='CORPORATIVO: Personalização durável para presentes, brindes e empresas',
        description='Gravação a laser em copos e brindes personalizados.',
        cta='FAÇA SEU PEDIDO!', phone='(11) 97294-9533', photo_mode='auto'
    )
    im = Image.open(BytesIO(data))
    assert im.size == (1080, 1080)
    assert len(data) > 100000


def test_hf8_hf8_network_shapes_remain_supported():
    for size in ((1080,1080), (1080,1920), (1920,1080)):
        data = engine.render_template(
            _sample(), size, template_id='anna_social_redes', title='CHAVEIROS 3D',
            subtitle='Transforme sua marca em pequenas obras de arte!',
            description='Presentes, brindes e lembranças.', cta='FAÇA SEU PEDIDO!',
            phone='(11) 97294-9533', photo_mode='auto'
        )
        assert Image.open(BytesIO(data)).size == size
