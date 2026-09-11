from pathlib import Path


def test_hf15_package_and_locked_model_reference_behavior():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF15'
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'HF53.3-HF8-HF15: Template Anna — Redes Sociais • correção do palco sem sobreposição de produto • Mestre HF7 intacto.' in app
    renderer = Path('marketing_anna_renderer_hf11.py').read_text(encoding='utf-8')
    assert 'HF15: após a conferência visual final' in renderer
    assert 'return reference_view.copy()' in renderer
