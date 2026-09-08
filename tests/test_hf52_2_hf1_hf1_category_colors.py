from pathlib import Path


def test_category_cards_use_alphafest_palette():
    src = Path("site_visual_hf48_service.py").read_text(encoding="utf-8")
    for token in (
        ".hf48-category-card:nth-child(7n+1){background:#eaf7ff",
        ".hf48-category-card:nth-child(7n+2){background:#fff0f7",
        ".hf48-category-card:nth-child(7n+3){background:#fff8dd",
        ".hf48-category-card:nth-child(7n+4){background:#f2edff",
        ".hf48-category-card:nth-child(7n+5){background:#ebfff7",
        ".hf48-category-card:nth-child(7n+6){background:#fff0e8",
        ".hf48-category-card:nth-child(7n){background:#eef5ff",
    ):
        assert token in src


def test_version():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF52.2-HF1-HF1"
