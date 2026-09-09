import io
from pathlib import Path
from PIL import Image

import marketing_template_engine as engine
import template_library_engine as library


def _sample_png() -> bytes:
    im = Image.new('RGB', (900, 1200), (236, 238, 240))
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((180, 120, 720, 1080), radius=90, fill=(30, 30, 35))
    d.rectangle((250, 210, 650, 300), fill=(215, 215, 220))
    buf = io.BytesIO(); im.save(buf, 'PNG'); return buf.getvalue()


def test_hf53_3_hf1_version():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF5-HF1'


def test_anna_social_is_second_protected_template_in_validation():
    catalog = engine.listar_templates()
    anna = next(item for item in catalog if item['id'] == 'anna_social_redes')
    assert anna['status_template'] == 'Em validação'
    assert anna['versao_template'] == 'HF53.3-HF5'
    assert anna['protegido'] is True
    assert anna['oficial'] is False
    assert anna['autopilot_aprovado'] is True


def test_anna_social_is_available_for_controlled_autopilot_test():
    ids = [item['id'] for item in engine.listar_templates_autopilot()]
    assert ids[0] == 'splash_premium_anna'
    assert 'anna_social_redes' in ids


def test_anna_social_renders_natively_for_all_image_network_shapes():
    expected = {
        (1080, 1350),  # Instagram Feed / Carrossel
        (1080, 1920),  # Story / Status
        (1080, 1080),  # Facebook atual no Manager
        (1920, 1080),  # horizontal/capa futura
    }
    for size in expected:
        data = engine.render_template(
            _sample_png(), size,
            template_id='anna_social_redes',
            title='Copo Long Drink Neon',
            subtitle='Natal',
            description='Um presente personalizado para marcar momentos especiais.',
            cta='Conheça este produto',
            phone='(11) 97294-9533',
            photo_mode='preservar',
        )
        out = Image.open(io.BytesIO(data))
        assert out.size == size
        assert len(data) > 20000


def test_anna_social_id_cannot_be_shadowed_by_imported_zip():
    assert 'anna_social_redes' in library.RESERVED_TEMPLATE_IDS
    assert library.load_library_template('anna_social_redes') is None


def test_ui_exposes_native_network_sizes_and_validation_state():
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'Template Anna — Redes Sociais' in app
    assert 'Formatos gerados nativamente' in app
    assert '🧪 {_mkt_template_status.upper()}' in app
    assert 'Designer Comercial AlphaFest HF53.3-HF5' in app
