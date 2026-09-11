from pathlib import Path


def test_hf14_versions_and_visual_contract():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF14'
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'HF53.3-HF8-HF14: Template Anna — Redes Sociais • ajuste fino visual do Anna com base HF11 • Mestre HF7 intacto.' in app
    renderer = Path('marketing_anna_renderer_hf11.py').read_text(encoding='utf-8')
    assert 'ANNA_RENDERER_VERSION = "HF53.3-HF8-HF11"' in renderer
    assert 'stage_box = (592, 216, 1042, 742)' in renderer
    assert 'cx, cy, r = 540, 744, 76' in renderer
    assert 'zoom = 1.12' in renderer
