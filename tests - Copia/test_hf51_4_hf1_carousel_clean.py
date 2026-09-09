from pathlib import Path


def test_hf51_4_hf1_remove_selo_interno_do_carrossel_publico():
    src = (Path(__file__).resolve().parents[1] / "site_visual_hf48_service.py").read_text(encoding="utf-8")
    assert "DESTAQUE ESCOLHIDO" not in src.upper()
    assert "Destaque AlphaFest" not in src
    assert "hf50-carousel-actions" in src
    assert "Ver produto" in src
    assert 'class="hf50-carousel-whatsapp"' not in src
