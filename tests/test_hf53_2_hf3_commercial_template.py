from pathlib import Path


def test_hf53_2_hf3_version_and_autopilot_template_contract():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.2-HF3"
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'template_id="splash_premium_anna"' in app
    assert '"template_nome": "Comercial Profissional AlphaFest"' in app


def test_hf53_2_hf3_template_is_full_palette_professional():
    engine = Path("marketing_template_engine.py").read_text(encoding="utf-8")
    assert "HF53.2-HF3 — Template Comercial Profissional AlphaFest" in engine
    assert 'fill=primary' in engine
    assert 'fill=accent' in engine
    assert 'photo_box=(585,270,1042,720)' in engine
    assert 'phone_box=(555,805,1040,915)' in engine
