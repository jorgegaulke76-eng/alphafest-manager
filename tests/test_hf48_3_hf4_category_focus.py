from site_vitrine_service import gerar_html_vitrine


def _produto(nome, categoria, subcategoria):
    return {
        "Nome": nome,
        "Categoria": categoria,
        "Subcategoria": subcategoria,
        "Descricao": "Produto para teste da navegação focada.",
        "Imagens": ["https://example.com/produto.jpg"],
        "PublicarSite": True,
    }


def test_categoria_selecionada_entra_em_modo_focado_com_voltar():
    html = gerar_html_vitrine(
        [
            _produto("Topo", "Festas", "Topos de bolo"),
            _produto("Tag", "Festas", "Papelaria"),
            _produto("Caneca", "Brindes", "Canecas"),
        ],
        {"whatsapp_catalogo": "11972949533"},
        modo_preview=False,
        usar_taxonomia_catalogo=True,
    )

    assert 'id="taxonomy-focus" hidden' in html
    assert 'id="taxonomy-cats"' in html
    assert 'id="taxonomy-back"' in html
    assert '← Voltar às categorias' in html
    assert 'id="taxonomy-focus-label"' in html
    assert "catsBox.hidden=focado" in html
    assert "focusBox.hidden=!focado" in html
    assert "focusLabel.textContent=focado?catLabel:'Categoria'" in html
    assert "const categorias=document.getElementById('categorias')" in html
    assert "categorias.scrollIntoView" in html
    assert "if(input) input.value=''" in html
