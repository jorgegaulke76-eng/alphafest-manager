from pathlib import Path


def test_footer_reuses_header_wordmark():
    src = Path("site_completo_service.py").read_text(encoding="utf-8")
    assert 'logo_rodape_match = re.search' in src
    assert 'class="hf52-footer-brand-logo"' in src
    assert 'src="{html.escape(logo_rodape_src, quote=True)}"' in src
    assert '.hf52-footer-brand-logo{' in src


def test_version_hf52_2_hf1_hf3():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF2"
