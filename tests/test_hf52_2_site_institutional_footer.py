from pathlib import Path

from site_completo_service import gerar_html_site_completo


def _empresa():
    return {
        "Nome": "AlphaFest",
        "Slogan": "O poder de estar presente em cada presente!",
        "Cidade": "Itatiba",
        "UF": "SP",
        "Celular": "11999999999",
    }


def test_hf52_2_hero_about_footer_and_gallery_order():
    html = gerar_html_site_completo(
        [],
        _empresa(),
        modo_preview=True,
        incluir_galeria=True,
        visual_hf48=True,
        mascotes_hf48=False,
        galeria_trabalhos=[],
    )
    assert "Ideias presentes em suas festas e em sua empresa" in html
    assert "destacando sua MARCA!" in html
    assert "Sou feliz e grata por ter o melhor time para oferecer o melhor a você!" in html
    assert "Estamos sempre de olho nas tendências do mercado" in html
    assert "Consagre ao Senhor tudo o que você faz" in html
    assert "Provérbios 16:3" in html
    assert "Desenvolvido por <strong>Jorge Gauke</strong>" in html
    assert "© 2026 AlphaFest" in html

    pos_produtos = html.index('id="produtos"')
    pos_servicos = html.index('id="servicos"')
    pos_quem = html.index('id="quem-somos"')
    pos_contato = html.index('id="contato"')
    pos_galeria = html.index('id="galeria"')
    pos_footer = html.index('<footer class="footer">')
    assert pos_servicos < pos_quem < pos_contato < pos_produtos < pos_galeria < pos_footer


def test_hf52_2_gallery_is_last_main_nav_item_when_enabled():
    html = gerar_html_site_completo([], _empresa(), modo_preview=True, incluir_galeria=True)
    nav = html.split('<nav class="site-nav"', 1)[1].split('</nav>', 1)[0]
    assert nav.rfind('Galeria') > nav.rfind('Contato')


def test_current_version_hf52_2():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF52.2-HF1-HF3'
