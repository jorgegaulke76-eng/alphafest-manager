from pathlib import Path
from PIL import Image


def test_hf514_hf3_clean_header_logo_asset():
    root = Path(__file__).resolve().parents[1]
    p = root / "assets/mascotes/logo_wordmark_transparent.png"
    assert p.exists()
    img = Image.open(p).convert("RGBA")
    assert img.size == (520, 150)
    alpha = img.getchannel("A")
    assert alpha.getpixel((519, 149)) == 0
    assert alpha.getpixel((0, 149)) == 0
    src = (root / "site_visual_hf48_service.py").read_text(encoding="utf-8")
    assert 'logo_wordmark_transparent.png' in src
    assert 'background:transparent!important' in src
