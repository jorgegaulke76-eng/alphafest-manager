from pathlib import Path


def test_hf16_package_mentions_dynamic_palette():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF16'
    renderer = Path('marketing_anna_renderer_hf11.py').read_text(encoding='utf-8')
    assert '_build_adaptive_palette_for_generic' in renderer
    assert '_extract_product_palette' in renderer
    assert 'skin = None' in renderer
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'HF53.3-HF8-HF16: Template Anna — Redes Sociais • paleta dinâmica para produtos genéricos • Mestre HF7 intacto.' in app
