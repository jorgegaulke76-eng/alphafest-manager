from pathlib import Path

def test_hf53_2_hf4_master_template_contract():
    engine=Path("marketing_template_engine.py").read_text(encoding="utf-8")
    app=Path("app.py").read_text(encoding="utf-8")
    assert "HF53.2-HF5 — Template Mestre Comercial profissional (1080x1350 nativo)" in engine
    assert "produto protagonista" in engine
    assert "Template Mestre Comercial AlphaFest" in app
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip()=="20.4.9-I8.13.5-HF53.2-HF5-HF6"
