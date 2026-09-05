from pathlib import Path

from site_galeria_service import gerar_fragmento_galeria, resumir_galeria_site
from site_completo_service import gerar_html_site_completo


def _trabalho(**extra):
    base = {
        "produto": "Caneca Porcelana Personalizada",
        "categoria": "Canecas",
        "subcategoria": "Porcelana",
        "tema": "Dia da Secretária",
        "cor": "Rosa metalizado",
        "ocasiao": "Dia da Secretária",
        "fotos": ["trabalhos/foto1.webp", "trabalhos/foto2.webp"],
        "autorizado_publicacao": True,
        "selecionado_site": True,
        "arquivado": False,
    }
    base.update(extra)
    return base


def test_galeria_site_so_usa_autorizado_selecionado_nao_arquivado():
    galeria = [
        _trabalho(),
        _trabalho(produto="Sem autorização", autorizado_publicacao=False),
        _trabalho(produto="Não selecionado", selecionado_site=False),
        _trabalho(produto="Arquivado", arquivado=True),
    ]
    resumo = resumir_galeria_site(galeria)
    assert resumo["total_trabalhos"] == 1
    assert resumo["total_fotos"] == 2
    assert resumo["total_categorias"] == 1
    assert resumo["total_temas"] == 1


def test_fragmento_galeria_tem_filtros_fotos_e_whatsapp_contextual():
    frag = gerar_fragmento_galeria(
        [_trabalho()],
        {"whatsapp_catalogo": "11972949533"},
        imagem_resolver=lambda p: "data:image/webp;base64,AAAA" + p[-5:],
    )
    pagina = frag["html"] + frag["js"]
    assert 'id="galeria"' in pagina
    assert 'id="gallery-cat"' in pagina
    assert 'id="gallery-sub"' in pagina
    assert 'id="gallery-theme"' in pagina
    assert pagina.count('class="gallery-card"') == 2
    assert "Quero algo parecido" in pagina
    assert "Dia da Secretária" in pagina
    assert "wa.me/5511972949533" in pagina
    assert "refreshSub" in pagina and "refreshTheme" in pagina


def test_site_completo_hf471_adiciona_galeria_somente_quando_solicitada():
    catalogo = [{
        "Nome": "Caneca",
        "Categoria": "Canecas",
        "Subcategoria": "Porcelana",
        "Descricao": "Caneca personalizada",
        "Imagens": ["https://example.com/caneca.jpg"],
        "PublicarSite": True,
    }]
    galeria = [_trabalho()]
    novo = gerar_html_site_completo(
        catalogo,
        {"whatsapp_catalogo": "11972949533"},
        modo_preview=True,
        usar_taxonomia_catalogo=True,
        galeria_trabalhos=galeria,
        galeria_imagem_resolver=lambda p: "data:image/webp;base64,AAAA",
        incluir_galeria=True,
    )
    antigo = gerar_html_site_completo(catalogo, {}, modo_preview=False)
    assert "PRÉVIA INTERNA HF47.1" in novo
    assert '<a href="#galeria">Galeria</a>' in novo
    assert 'id="galeria"' in novo
    assert "Quero algo parecido" in novo
    assert 'id="galeria"' not in antigo
    assert '<a href="#galeria">Galeria</a>' not in antigo
    assert "PRÉVIA INTERNA HF47.1" not in antigo


def test_manager_prepara_previa_sob_demanda_e_hf44_permanece_sem_flag():
    app = Path("app.py").read_text(encoding="utf-8")
    assert '"📸 Prévia Galeria no Site — HF47.1"' in app
    assert '"🖼️ Preparar / atualizar prévia da Galeria"' in app
    assert "galeria_imagem_resolver=_galeria_trabalho_imagem_data_uri" in app
    assert "incluir_galeria=True" in app
    assert "as fotos privadas **não são carregadas ao abrir esta tela**" in app
    bloco_prod = app.split('# HF44 — publicação assistida no Worker', 1)[1]
    chamada = bloco_prod.split('pacote_producao_hf44 =', 1)[0]
    assert "incluir_galeria=True" not in chamada
