from pathlib import Path
from PIL import Image
import io

from alpha_marketing_designer import build_design_plan, sanitize_channel_copy, validate_design_plan, validate_art_bytes


def test_gravacao_laser_uses_specific_commercial_copy_and_channel_limits():
    p={"Nome":"GRAVAÇÃO LASER","Descricao":"Gravação personalizada em copos e brindes.","Categoria":"Gravação Laser"}
    plan=build_design_plan(p,"Vender","",["Instagram Feed","Instagram Story"])
    assert "durável" in plan["subtitle"].casefold()
    assert len(plan["benefits"]) <= 5
    assert len(plan["channels"]["Instagram Story"]["subtitle"]) <= 54
    assert validate_design_plan(plan)["ok"] is True


def test_copy_sanitizer_removes_duplicate_lines():
    text="Conheça este produto\n\nConheça este produto\nPersonalizado do seu jeito\n#AlphaFest"
    out=sanitize_channel_copy(text,"Instagram Feed")
    assert out.count("Conheça este produto") == 1
    assert "#AlphaFest" in out


def test_art_validator_requires_exact_channel_dimensions():
    bio=io.BytesIO()
    img=Image.new("RGB",(1080,1350),"white")
    for y in range(250,1100):
        for x in range(180,900):
            if (x+y) % 19 < 8:
                img.putpixel((x,y),(230,35,120))
    img.save(bio,"PNG")
    assert validate_art_bytes(bio.getvalue(),(1080,1350))["ok"] is True
    assert validate_art_bytes(bio.getvalue(),(1080,1920))["ok"] is False
    blank=io.BytesIO(); Image.new("RGB",(1080,1350),"white").save(blank,"PNG")
    assert validate_art_bytes(blank.getvalue(),(1080,1350))["ok"] is False


def test_hf53_2_hf1_ui_contract_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Designer Comercial AlphaFest" in app
    assert "quality_gate" in app
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip()=="20.4.9-I8.13.5-HF53.3-HF5"
