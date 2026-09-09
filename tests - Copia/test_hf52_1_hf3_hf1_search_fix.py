from site_vitrine_service import gerar_html_vitrine
from site_visual_hf48_service import aplicar_visual_hf48


def _produto(nome, descricao):
    return {
        "Nome": nome,
        "Categoria": "PERSONALIZADOS",
        "Subcategoria": "GERAL",
        "Descricao": descricao,
        "Ativo": True,
        "PublicarSite": True,
        "ProntoSite": True,
        "Imagens": ["https://example.com/x.jpg"],
    }


def test_busca_nao_usa_palavra_curta_do_produto_como_substring_da_consulta():
    html = gerar_html_vitrine([
        _produto("CANECA PORCELANA", "Presente personalizado"),
        _produto("ARCO DE BALAO", "Uma decoração para a festa"),
    ], {"nome": "AlphaFest"}, usar_taxonomia_catalogo=True)
    assert "word.length>=3 && token.includes(word)" in html
    assert "token.length>=3 && word.startsWith" not in html


def test_busca_do_cabecalho_reseta_categoria_e_dispara_filtro_global():
    base = gerar_html_vitrine([_produto("CANECA PORCELANA", "Caneca")], {"nome": "AlphaFest"}, usar_taxonomia_catalogo=True)
    page = aplicar_visual_hf48(base, [_produto('CANECA PORCELANA', 'Caneca')], {'nome':'AlphaFest'}, usar_mascotes=False)
    assert 'document.querySelector(\'.filter[data-cat="todos"]\')' in page
    assert "productInput.dispatchEvent(new Event('input',{bubbles:true}))" in page
