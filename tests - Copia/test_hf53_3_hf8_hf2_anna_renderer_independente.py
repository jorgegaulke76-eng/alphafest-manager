from io import BytesIO
from pathlib import Path
from PIL import Image

import marketing_template_engine as engine


def _sample():
    im=Image.new('RGB',(900,900),(245,245,245))
    out=BytesIO(); im.save(out,'PNG'); return out.getvalue()


def test_hf8_hf2_version_and_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip()=='20.4.9-I8.13.5-HF53.3-HF8-HF3'
    anna=next(x for x in engine.listar_templates() if x['id']=='anna_social_redes')
    assert anna['versao_template']=='HF53.3-HF8-HF3'
    assert engine.ANNA_PROMPT_SPEC['formatos']['Instagram Feed']==(1080,1080)


def test_hf8_hf2_renderer_is_independent_module():
    src=Path('marketing_template_engine.py').read_text(encoding='utf-8')
    assert 'from marketing_anna_renderer import render_anna_prompt' in src
    assert 'final = render_anna_prompt(' in src
    assert Path('marketing_anna_renderer.py').exists()


def test_hf8_hf2_anna_square_and_story_render():
    for size in ((1080,1080),(1080,1920),(1920,1080)):
        data=engine.render_template(
            _sample(),size,template_id='anna_social_redes',title='Chaveiros 3D',
            subtitle='Transforme seu logo em pequenas obras de arte!',
            description='Ideal para presentes, brindes e lembranças.',
            cta='FAÇA SEU PEDIDO',phone='(11) 97294-9533',photo_mode='preservar'
        )
        im=Image.open(BytesIO(data))
        assert im.size==size


def test_hf8_hf2_app_uses_square_feed_only_for_anna():
    src=Path('app.py').read_text(encoding='utf-8')
    assert 'def _marketing_effective_size' in src
    assert 'template_id or "") == "anna_social_redes" and canal == "Instagram Feed"' in src
    assert 'return (1080, 1080)' in src
    # configuração global do Mestre continua 4:5
    assert '"Instagram Feed": {"size": (1080, 1350)' in src
