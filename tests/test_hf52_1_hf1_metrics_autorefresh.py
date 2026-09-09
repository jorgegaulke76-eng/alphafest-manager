from pathlib import Path


def test_hf52_1_hf1_metrics_autorefresh_contract():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'st.fragment(run_every="30s")' in app
    assert '↻ Atualizar agora' in app
    assert 'Atualizado há ' in app
    assert 'site_metrics_refresh_hf52_1_hf1' in app


def test_hf52_1_hf1_version():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF4"
