import io
from pathlib import Path
from PIL import Image, ImageDraw
import marketing_template_engine as engine


def _sample():
    im=Image.new('RGB',(900,1200),(244,242,238))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((150,120,750,1080),radius=90,fill=(25,25,30))
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue()


def test_hf8_hf1_prompt_spec_is_fixed_and_explicit():
    spec=engine.ANNA_PROMPT_SPEC
    assert spec['versao']=='HF53.3-HF8-HF4'
    assert spec['layout_fixo']==[
        'logo','titulo','faixa','beneficios','produto','selo_central',
        'ideal_para','cta_whatsapp','faixa_emocional','rodape',
    ]
    assert spec['cta']=='FAÇA SEU PEDIDO!'
    assert 'TESTADO' in spec['selo_superior']
    assert spec['faixa_emocional']=='Pequenos detalhes que fazem toda a diferença!'
    assert spec['formatos']['Instagram Feed']==(1080,1080)
    assert spec['formatos']['Facebook']==(1080,1080)
    assert spec['formatos']['Instagram Story']==(1080,1920)


def test_hf8_hf1_anna_is_validation_and_master_is_frozen():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip()=='20.4.9-I8.13.5-HF53.3-HF8-HF4'
    anna=next(x for x in engine.listar_templates() if x['id']=='anna_social_redes')
    master=next(x for x in engine.listar_templates() if x['id']=='splash_premium_anna')
    assert anna['versao_template']=='HF53.3-HF8-HF4'
    assert anna['status_template']=='Em validação'
    assert master['versao_template']=='HF53.2-HF5-HF7'
    assert master['status_template']=='Homologado'


def test_hf8_hf1_all_network_shapes_render_natively():
    for size in ((1080,1350),(1080,1080),(1080,1920),(1920,1080)):
        data=engine.render_template(_sample(),size,template_id='anna_social_redes',title='Chaveiros 3D',subtitle='Permanente',description='Ideal para presentes, brindes e lembranças.',cta='Conheça este produto',phone='(11) 97294-9533',photo_mode='recortar')
        im=Image.open(io.BytesIO(data))
        assert im.size==size
        assert len(data)>25000


def test_hf8_hf1_code_uses_prompt_visual_modules():
    code=Path('marketing_template_engine.py').read_text(encoding='utf-8')
    start=code.index('def _render_anna_social_native')
    end=code.index('def _render_splash_premium_square',start)
    fn=code[start:end]
    for token in ('approval_seal','big_title','promise_ribbon','benefits_block','product_stage','message_badge','applications','cta_box','slogan_box','footer_band'):
        assert token in fn
    assert 'Vitrine de aplicações' in fn
    assert 'FAÇA SEU PEDIDO!' in code
