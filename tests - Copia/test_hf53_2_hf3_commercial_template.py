from pathlib import Path


def test_hf53_2_hf3_version_and_autopilot_template_contract():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF8-HF3"
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'template_id="splash_premium_anna"' in app
    assert '"template_nome": "Template Mestre Comercial AlphaFest"' in app


def test_hf53_2_hf3_template_is_full_palette_professional():
    engine = Path("marketing_template_engine.py").read_text(encoding="utf-8")
    assert "HF53.2-HF5 — Template Mestre Comercial profissional (1080x1350 nativo)" in engine
    assert 'fill=primary' in engine
    assert 'fill=accent' in engine
    assert 'photo_box=(510,448,1045,965)' in engine
    assert 'draw.rounded_rectangle(cta_box' in engine
