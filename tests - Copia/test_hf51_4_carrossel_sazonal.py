from pathlib import Path


def test_hf51_4_carrossel_sazonal_reaproveita_catalogo_e_nao_publica():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "Carrossel sazonal rápido" in source
    assert "CampanhasPermitidas" in source
    assert "🎠 Preencher carrossel" in source
    assert "🧹 Limpar carrossel" in source
    assert '"CarrosselSite"' in source
    assert "não publica o site" in source.lower() or "não publicado" in source.lower()
