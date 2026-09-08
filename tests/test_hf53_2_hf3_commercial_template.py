from pathlib import Path


def test_hf53_2_hf3_version_and_autopilot_template_contract():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.2-HF4"
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'template_id="splash_premium_anna"' in app
    assert '"template_nome": "Template Mestre Comercial AlphaFest"' in app


def test_hf53_2_hf3_template_is_full_palette_professional():
    engine = Path("marketing_template_engine.py").read_text(encoding="utf-8")
    assert "HF53.2-HF4 — Template Mestre Comercial AlphaFest" in engine
    assert 'fill=primary' in engine
    assert 'fill=accent' in engine
    assert 'photo_box=(585,285,1036,790)' in engine
    assert 'draw.rounded_rectangle((530,870,1040,980)' in engine
