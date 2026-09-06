from pathlib import Path

from site_completo_service import gerar_html_site_completo


def test_hf483_producao_visual_sem_contadores_do_hero():
    catalogo=[{"Nome":"Caneca","Categoria":"Canecas","Subcategoria":"Porcelana","Descricao":"x","Imagens":["https://example.com/a.jpg"],"PublicarSite":True}]
    pagina=gerar_html_site_completo(catalogo,{"whatsapp_catalogo":"11999999999"},modo_preview=False,usar_taxonomia_catalogo=True,incluir_galeria=True,visual_hf48=True,mascotes_hf48=True)
    assert "produtos na vitrine" not in pagina
    assert "categorias atuais" not in pagina
    assert "Personalização que conta sua história" in pagina
    assert "Thu + Fox · AlphaFest" in pagina
    assert "PRÉVIA INTERNA" not in pagina


def test_hf483_manager_publica_visual_aprovado_pelo_motor_hf44():
    app=Path("app.py").read_text(encoding="utf-8")
    bloco=app.split('# HF48.3 — produção oficial passa a usar o visual aprovado',1)[1].split('pacote_producao_hf44 =',1)[0]
    for flag in ("usar_taxonomia_catalogo=True","incluir_galeria=True","visual_hf48=True","mascotes_hf48=True"):
        assert flag in bloco
    assert "limite_fotos_galeria=48" in bloco
    assert 'versao_manager="20.4.9-I8.13.5-HF48.3-HF2"' in app
