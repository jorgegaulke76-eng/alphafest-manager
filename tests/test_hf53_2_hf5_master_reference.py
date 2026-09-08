import io
from pathlib import Path
from PIL import Image

from alpha_marketing_designer import build_design_plan, validate_art_bytes, validate_design_plan
from marketing_design_intelligence import detect_theme, get_theme
from marketing_template_engine import render_template


def _sample_png():
    image = Image.new("RGB", (480, 620), "white")
    # produto simples centralizado para exercitar recorte + upscale
    for y in range(120, 560):
        for x in range(130, 350):
            if ((x-240)/110)**2 + ((y-340)/220)**2 <= 1:
                image.putpixel((x,y), (35,35,38))
    out=io.BytesIO(); image.save(out,"PNG"); return out.getvalue()


def test_hf5_master_is_native_4x5_and_campaign_aware():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.2-HF5"
    assert detect_theme("Outubro Rosa") == "outubro_rosa"
    palette = get_theme("outubro_rosa")["palette"]
    art = render_template(
        _sample_png(), (1080,1350), template_id="splash_premium_anna",
        title="GRAVAÇÃO LASER",
        subtitle="Outubro Rosa: Personalização durável para presentes, brindes e empresas",
        description="Design exclusivo • Fácil de usar • Material de qualidade • Personalizado • Múltiplos usos",
        cta="CONHEÇA ESTE PRODUTO", phone="(11) 97294-9533",
        palette_override=palette, photo_mode="recortar",
    )
    with Image.open(io.BytesIO(art)) as image:
        assert image.size == (1080,1350)
    review=validate_art_bytes(art,(1080,1350))
    assert review["ok"], review


def test_hf5_design_plan_has_strong_gate_and_five_benefits_for_laser():
    plan=build_design_plan(
        {"Nome":"Gravação Laser","Descricao":"Personalização durável para presentes e empresas.","Categoria":"Gravação"},
        "Vender","Outubro Rosa",["Instagram Feed","Instagram Story"],
    )
    assert 3 <= len(plan["benefits"]) <= 5
    assert plan["cta"] == "CONHEÇA ESTE PRODUTO"
    review=validate_design_plan(plan)
    assert review["ok"], review
    assert len(review["checks"]) >= 9
