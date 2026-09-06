from pathlib import Path
from PIL import Image


def test_hf50_hf2_logo_asset_has_horizontal_lockup():
    p = Path("assets/mascotes/logo_wordmark.webp")
    assert p.exists()
    im = Image.open(p)
    assert im.width > im.height * 3
    assert im.width >= 500

def test_hf50_hf2_header_css_prevents_crop():
    src = Path("site_visual_hf48_service.py").read_text(encoding="utf-8")
    assert "HF50.1-HF4" in src
    assert ".brand-logo{width:380px;height:96px;object-fit:contain;object-position:left center;display:block;overflow:visible" in src
    assert "min-height:96px;overflow:visible" in src
