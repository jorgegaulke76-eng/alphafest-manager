from pathlib import Path

def test_hf514_hf2_carousel_clean_and_logo_asset():
    root = Path(__file__).resolve().parents[1]
    src = (root / "site_visual_hf48_service.py").read_text(encoding="utf-8")
    assert 'hf50-carousel-whatsapp' in src  # hidden by CSS regression guard
    assert 'class="hf50-carousel-whatsapp"' not in src
    assert 'AlphaFest · Personalizados & Balões</div>' not in src.split('if mascotes.get("hero"):',1)[1].split('else:',1)[0]
    assert 'opacity:1!important' in src
    assert 'filter:none!important' in src
    assert '.hf50-carousel-slide:after{display:none!important' in src
    assert (root / "assets/mascotes/logo_novo_alphafest.png").exists()
    assert (root / "assets/mascotes/logo_wordmark_transparent.png").exists()
