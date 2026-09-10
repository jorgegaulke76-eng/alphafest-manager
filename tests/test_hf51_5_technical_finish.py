from pathlib import Path

from site_production_service import preparar_html_producao, gerar_pacote_producao
import io, zipfile


def test_hf51_5_structured_data_and_brand_meta():
    html = '<html><head><title>AlphaFest</title></head><body><img loading="lazy" src="x.jpg"></body></html>'
    out = preparar_html_producao(html)
    assert 'id="alphafest-structured-data"' in out
    assert '"@type":"Organization"' in out
    assert '"@type":"WebSite"' in out
    assert 'name="theme-color"' in out
    assert 'name="application-name"' in out
    assert 'name="author"' in out
    assert 'loading="lazy" decoding="async"' in out


def test_hf51_5_sitemap_is_enriched():
    blob = gerar_pacote_producao('<html><head></head><body></body></html>', versao_manager='20.4.9-I8.13.5-HF51.5')
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        sm = zf.read('sitemap.xml').decode('utf-8')
        assert '<lastmod>' in sm
        assert '<changefreq>weekly</changefreq>' in sm
        assert '<priority>1.0</priority>' in sm
        status = zf.read('STATUS-PRODUCAO.json').decode('utf-8')
        assert '20.4.9-I8.13.5-HF51.5' in status


def test_version_file_hf51_5():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF8'
