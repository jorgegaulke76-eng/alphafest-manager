import io
from pathlib import Path
from PIL import Image
import marketing_template_engine as engine


def _sample() -> bytes:
    im=Image.new('RGB',(700,900),(230,226,220))
    from PIL import ImageDraw
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((140,90,560,820),radius=70,fill=(35,35,40))
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue()


def test_hf53_3_hf3_version_and_template_metadata():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF9'
    anna=next(x for x in engine.listar_templates() if x['id']=='anna_social_redes')
    assert anna['versao_template']=='HF53.3-HF8-HF9'
    assert anna['status_template']=='Em validação'
    assert anna['oficial'] is False


def test_hf53_3_hf3_campaign_label_does_not_replace_commercial_promise():
    profile=engine._product_profile('Gravação Laser','', 'Permanente')
    assert profile['subtitle']=='Personalização durável para presentes, brindes e empresas'


def test_hf53_3_hf3_renders_reference_structure_in_all_network_shapes():
    for size in ((1080,1350),(1080,1920),(1080,1080),(1920,1080)):
        data=engine.render_template(
            _sample(), size, template_id='anna_social_redes', title='Gravação Laser',
            subtitle='Permanente', description='Personalização resistente e elegante.',
            cta='Conheça este produto', phone='(11) 97294-9533', photo_mode='preservar'
        )
        im=Image.open(io.BytesIO(data))
        assert im.size==size
        assert len(data)>20000
