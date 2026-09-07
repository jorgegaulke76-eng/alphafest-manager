from pathlib import Path
from PIL import Image


def test_hf50_hf2_logo_asset_has_horizontal_lockup():
    p = Path("assets/mascotes/logo_wordmark_transparent.png")
    assert p.exists()
    im = Image.open(p)
    assert im.width > im.height * 3
    assert im.width >= 500

def test_hf50_hf2_header_css_prevents_crop():
    src = Path("site_visual_hf48_service.py").read_text(encoding="utf-8")
    assert "HF51.4" in src
    assert ".brand-logo{width:410px;height:84px;object-fit:contain;object-position:left center;display:block;overflow:visible" in src
    assert ".hf48-topline{display:none!important}" in src
    assert ".site-nav{top:66px;background:#0b8fdf" in src
    assert "min-height:84px;overflow:visible" in src
