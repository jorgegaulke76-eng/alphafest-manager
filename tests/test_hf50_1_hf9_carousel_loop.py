from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "site_visual_hf48_service.py").read_text(encoding="utf-8")

def test_hf9_uses_forward_only_autoplay_and_infinite_clone_loop():
    assert "HF51.1-HF2" in SRC
    assert "timer=setInterval(forward,5200)" in SRC
    assert "cloneNode(true)" in SRC
    assert "if(idx>=slides.length)" in SRC
    assert "idx=0; paint(false)" in SRC
    assert "go(idx+1)" not in SRC
