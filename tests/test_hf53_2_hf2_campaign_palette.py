from pathlib import Path


def test_autopilot_has_campaign_palette_selector():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Cores da campanha" in app
    assert "Colorido Infantil" in app
    assert "Vermelho Promocional" in app
    assert "Preto Premium" in app
    assert "palette_override=_mkt_palette" in app
    assert '"paleta_visual": dict(_mkt_palette)' in app


def test_version_hf53_2_hf2():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip()=="20.4.9-I8.13.5-HF53.3"
