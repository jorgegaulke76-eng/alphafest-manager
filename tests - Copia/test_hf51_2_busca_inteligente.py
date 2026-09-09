from site_vitrine_service import gerar_html_vitrine, selecionar_produtos_vitrine


def _produto():
    return {
        "Nome": "Caneca Porcelana Personalizada",
        "Categoria": "PERSONALIZADOS",
        "Subcategoria": "CANECAS",
        "Descricao": "Caneca para presente corporativo e aniversário.",
        "Material": "Porcelana",
        "Processos": ["Sublimação"],
        "Campanhas": ["Dia da Secretária"],
        "Aliases": ["caneca personalizada", "mug"],
        "Variacoes": ["rosa metalizado"],
        "Tema": "Secretária",
        "Ocasião": "Presente",
        "Tags": ["brinde", "empresa"],
        "Ativo": True,
        "PublicarSite": True,
        "ProntoSite": True,
        "Imagens": ["https://example.com/caneca.jpg"],
        "Preco": "25,00",
    }


def test_busca_indexa_alias_tema_material_ocasiiao_e_campanha():
    produto = _produto()
    selecionados = selecionar_produtos_vitrine([produto], usar_taxonomia_catalogo=True)
    assert selecionados
    item = selecionados[0]
    assert "mug" in item["aliases"]
    html = gerar_html_vitrine([produto], {"nome": "AlphaFest"}, usar_taxonomia_catalogo=True)
    for termo in ["mug", "secretaria", "porcelana", "presente", "dia da secretaria", "rosa metalizado", "brinde"]:
        assert termo in html.lower()


def test_busca_tem_tolerancia_a_erro_de_digitacao():
    html = gerar_html_vitrine([_produto()], {"nome": "AlphaFest"}, usar_taxonomia_catalogo=True)
    assert "function editDistance" in html
    assert "function smartMatch" in html
    assert "smartMatch(c.dataset.search,q)" in html
    assert "Buscar produto, tema, material, ocasião, categoria" in html
