from pathlib import Path


def test_category_cards_use_alphafest_palette():
    src = Path("site_visual_hf48_service.py").read_text(encoding="utf-8")
    for token in (
        ".hf48-category-card:nth-child(7n+1){background:linear-gradient(135deg,#bfe2ff,#8fcaf7)",
        ".hf48-category-card:nth-child(7n+2){background:linear-gradient(135deg,#ffc6e0,#f59ac8)",
        ".hf48-category-card:nth-child(7n+3){background:linear-gradient(135deg,#ffe899,#ffd467)",
        ".hf48-category-card:nth-child(7n+4){background:linear-gradient(135deg,#ddc9ff,#b89af0)",
        ".hf48-category-card:nth-child(7n+5){background:linear-gradient(135deg,#bdf3d8,#82deb3)",
        ".hf48-category-card:nth-child(7n+6){background:linear-gradient(135deg,#ffc7b8,#ff9e86)",
        ".hf48-category-card:nth-child(7n){background:linear-gradient(135deg,#c4dcff,#8ebcf3)",
    ):
        assert token in src


def test_version():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.2-HF5-HF3"
