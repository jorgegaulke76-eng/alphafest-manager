import io
from pathlib import Path
from PIL import Image, ImageDraw
import marketing_template_engine as engine


def _sample():
    im=Image.new('RGB',(900,1200),(236,232,226))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((180,100,720,1100),radius=80,fill=(35,35,38))
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue()


def test_hf53_3_hf7_version_and_template_state():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip()=='20.4.9-I8.13.5-HF53.3-HF8-HF9'
    anna=next(x for x in engine.listar_templates() if x['id']=='anna_social_redes')
    master=next(x for x in engine.listar_templates() if x['id']=='splash_premium_anna')
    assert anna['versao_template']=='HF53.3-HF8-HF9'
    assert anna['status_template']=='Em validação'
    assert master['versao_template']=='HF53.2-HF5-HF7'
    assert master['status_template']=='Homologado'


def test_hf53_3_hf7_native_shapes_render():
    for size in ((1080,1350),(1080,1080),(1080,1920),(1920,1080)):
        data=engine.render_template(_sample(),size,template_id='anna_social_redes',title='Gravação Laser',subtitle='Corporativo',description='Personalização durável para presentes, brindes e empresas.',cta='Conheça este produto',phone='(11) 97294-9533',photo_mode='preservar')
        im=Image.open(io.BytesIO(data))
        assert im.size==size
        assert len(data)>25000


def test_hf53_3_hf7_visual_contract_in_code():
    code=Path('marketing_template_engine.py').read_text(encoding='utf-8')
    start=code.index('def _render_anna_social_native')
    end=code.index('def _render_splash_premium_square',start)
    fn=code[start:end]
    assert 'logo_novo_alphafest.png' in fn
    assert 'Manchete comercial' in fn
    assert 'Palco grande' in fn
    assert 'grade final' in fn
