from pathlib import Path
from PIL import Image


def test_hf50_hf2_logo_asset_has_safe_padding_and_alpha():
    p = Path("assets/mascotes/logo_wordmark.webp")
    assert p.exists()
    im = Image.open(p).convert("RGBA")
    alpha = im.getchannel("A")
    bbox = alpha.getbbox()
    assert bbox is not None
    left, top, right, bottom = bbox
    assert left > 0 and top > 0
    assert right < im.width and bottom < im.height


def test_hf50_hf2_header_css_prevents_crop():
    src = Path("site_visual_hf48_service.py").read_text(encoding="utf-8")
    assert "HF50.1-HF2" in src
    assert ".brand-logo{width:108px;height:78px;object-fit:contain;object-position:center;display:block;overflow:visible" in src
    assert "min-height:94px;overflow:visible" in src
