from pathlib import Path

def test_hf17_manual_palette_priority_contract():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF17'
    app=Path('app.py').read_text(encoding='utf-8')
    engine=Path('marketing_template_engine.py').read_text(encoding='utf-8')
    renderer=Path('marketing_anna_renderer_hf11.py').read_text(encoding='utf-8')
    assert '_mkt_palette["__palette_mode"] = "manual"' in app
    assert '_mkt_palette["__palette_mode"] = "auto"' in app
    assert '"__palette_mode": str(override.get("__palette_mode") or "manual")' in engine
    assert 'if mode != "auto":' in renderer
