from pathlib import Path

from site_completo_service import gerar_html_site_completo


def _catalogo():
    return [
        {
            "Nome": "Caneca personalizada",
            "Categoria": "Brindes",
            "Subcategoria": "Canecas",
            "Descricao": "Caneca personalizada para presente",
            "PublicarSite": True,
            "Imagens": ["https://example.com/caneca.jpg"],
        }
    ]


def test_ordem_comercial_hf52_2_hf1_e_galeria_no_menu():
    empresa = {
        "nome": "AlphaFest",
        "whatsapp_catalogo": "11972949533",
        "instagram_url": "https://www.instagram.com/alphafest10/",
        "facebook_url": "https://www.facebook.com/alphafest10",
        "tiktok_url": "https://www.tiktok.com/@alphafest",
        "youtube_url": "https://www.youtube.com/@alphafest",
    }
    html = gerar_html_site_completo(
        _catalogo(), empresa, modo_preview=True,
        usar_taxonomia_catalogo=True, incluir_galeria=True,
        visual_hf48=True, mascotes_hf48=True,
    )
    ids = ['id="categorias"', 'id="servicos"', 'id="quem-somos"', 'id="contato"', 'id="fale-alphafest"', 'id="produtos"', 'id="galeria"']
    pos = [html.index(x) for x in ids]
    assert pos == sorted(pos)
    assert 'data-site-scroll="galeria"' in html
    assert 'id="como-funciona"' not in html
    assert 'class="hf48-brand-cta"' not in html
    assert 'Instagram' in html and 'Facebook' in html and 'TikTok' in html and 'YouTube' in html


def test_redes_vazias_nao_criam_links_errados():
    html = gerar_html_site_completo(
        _catalogo(), {"whatsapp_catalogo": "11972949533", "tiktok_url": "", "youtube_url": ""},
        modo_preview=True, usar_taxonomia_catalogo=True, incluir_galeria=True,
        visual_hf48=True, mascotes_hf48=True,
    )
    assert 'https://www.instagram.com/alphafest10/' in html
    assert 'https://www.facebook.com/alphafest10' in html
    assert 'tiktok.com/@' not in html
    assert 'youtube.com/@' not in html


def test_versao_hf52_2_hf1():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.2-HF5-HF5'
