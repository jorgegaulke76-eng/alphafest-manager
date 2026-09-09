from pathlib import Path


def test_hf492_grade_rapida_autosave_existe_e_preserva_hf44():
    app = Path("app.py").read_text(encoding="utf-8")
    assert '#### ⚡ Edição rápida do site · auto-save' in app
    assert '"🌐 Publicar": bool(_prod_hf492.get("PublicarSite", False))' in app
    assert '"💰 Mostrar preço": bool(_prod_hf492.get("ExibirPrecoSite", False))' in app
    assert '"⭐ Destaque": bool(_prod_hf492.get("Destaque", False))' in app
    assert '_registro_hf492["PublicarSite"] = bool(_pub_hf492)' in app
    assert '_registro_hf492["ExibirPrecoSite"] = bool(_preco_hf492)' in app
    assert '_registro_hf492["Destaque"] = bool(_dest_hf492)' in app
    assert 'salvar_catalogo(_catalogo_hf492)' in app
    assert 'O site não é publicado automaticamente' in app
    assert '🚀 Produção oficial — HF51.4-HF3 · motor HF44' in app


def test_hf492_versao_manager():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF6"
