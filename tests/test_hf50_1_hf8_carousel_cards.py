from pathlib import Path

def test_hf501_hf8_carrossel_cards_maiores_responsivos():
    src = Path('site_visual_hf48_service.py').read_text(encoding='utf-8')
    assert 'min-height:235px' in src
    assert 'max-width:1480px' in src
    assert 'calc((100% - 42px)/4)' in src
    assert 'calc((100% - 14px)/2)' in src
    assert 'flex-basis:100%' in src
    assert 'PRÉVIA INTERNA HF50.1-HF9' in src
