from pathlib import Path
from site_production_service import preparar_html_producao


def test_hf51_3_vitrine_tem_seo_e_otimizacoes():
    src = Path('site_vitrine_service.py').read_text(encoding='utf-8')
    assert 'meta property="og:type"' in src
    assert 'twitter:card' in src
    assert 'content-visibility:auto' in src
    assert 'decoding="async"' in src
    assert 'fetchpriority="low"' in src
    assert 'class="brand-logo"' in src


def test_hf51_3_producao_injeta_canonical_e_robots_sem_duplicar_description():
    html = '<!doctype html><html><head><title>x</title><meta name="description" content="x"></head><body><img loading="lazy" src="x.jpg"></body></html>'
    out = preparar_html_producao(html)
    assert 'rel="canonical" href="https://alphafest.com.br/"' in out
    assert 'name="robots" content="index,follow,max-image-preview:large"' in out
    assert out.count('name="description"') == 1
    assert 'loading="lazy" decoding="async"' in out


def test_versao_hf51_3():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF51.4-HF1'
