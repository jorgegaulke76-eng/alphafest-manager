import io
from pathlib import Path
from PIL import Image, ImageDraw
import marketing_template_engine as engine


def _sample():
    im=Image.new("RGB",(900,900),(238,235,230))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((250,110,650,800),radius=80,fill=(30,30,35))
    b=io.BytesIO(); im.save(b,"PNG"); return b.getvalue()


def test_hf53_3_hf6_version_and_grid_contract():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip()=="20.4.9-I8.13.5-HF53.3-HF8-HF8"
    anna=next(x for x in engine.listar_templates() if x["id"]=="anna_social_redes")
    assert anna["versao_template"]=="HF53.3-HF8-HF8"
    assert anna["status_template"]=="Em validação"
    code=Path("marketing_template_engine.py").read_text(encoding="utf-8")
    start=code.index("def _render_anna_social_native")
    end=code.index("def _render_splash_premium_square",start)
    fn=code[start:end]
    assert "grade editorial aprovada" in fn
    assert "logo_novo_alphafest.png" in fn
    assert "Cards visuais reais" in fn


def test_hf53_3_hf6_native_networks_and_master_frozen():
    master=next(x for x in engine.listar_templates() if x["id"]=="splash_premium_anna")
    assert master["versao_template"]=="HF53.2-HF5-HF7"
    for size in ((1080,1350),(1080,1080),(1080,1920),(1920,1080)):
        data=engine.render_template(_sample(),size,template_id="anna_social_redes",title="Gravação Laser",subtitle="Permanente",description="Personalização resistente e elegante.",cta="Conheça este produto",phone="(11) 97294-9533",photo_mode="preservar")
        im=Image.open(io.BytesIO(data))
        assert im.size==size
        assert len(data)>25000
