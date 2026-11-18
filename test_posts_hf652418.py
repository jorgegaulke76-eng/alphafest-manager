from site_posts_service import _card, inject_home

def test_card_simples_sem_textos_publicos():
    p={"id":"p1","title":"Lembrança de Natal","description":"NÃO EXIBIR DESCRIÇÃO","category":"Natal","image_data_uri":"data:image/png;base64,aGVsbG8=","status":"publicado","featured":True,"created_at":"2026-11-18","expires_at":""}
    card=_card(p,"11972949533")
    assert "NÃO EXIBIR" not in card and "<h3>" not in card
    assert "Quero este" in card and "object-fit" not in card
    assert "wa.me/5511972949533" in card
    html=inject_home('<html><head></head><body><footer class="footer"></footer></body></html>',[p],"11972949533",preview=True)
    assert "object-fit:contain" in html and "max-height:390px" in html

def test_name_error_corrigido_na_geracao():
    from pathlib import Path
    source=Path(__file__).with_name("site_completo_service.py").read_text()
    assert "inject_posts_home(pagina, list(posts_content or []), numero," in source
    assert "inject_posts_home(pagina, list(posts_content or []), number," not in source
