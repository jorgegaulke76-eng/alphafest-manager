from pathlib import Path

from catalogo_midias_service import (
    chave_estado_catalogo_pertence_ao_formulario,
    resolver_galeria_fotos,
)


VERSAO = "20.4.9-I8.13.5-HF53.3-HF6"


def test_version_and_catalog_contract():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == VERSAO
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Fotos sempre editáveis" in app
    assert "_catalogo_resolver_galeria_fotos" in app
    assert "_catalogo_chave_estado_formulario" in app


def test_remote_photo_marked_for_removal_never_returns_from_stale_url_field():
    atuais = ["https://cdn.exemplo/a.jpg", "https://cdn.exemplo/b.jpg"]
    final = resolver_galeria_fotos(
        atuais,
        remover_indices=[0],
        principal_indice=0,
        # Simula o estado antigo do text_area ainda contendo a URL removida.
        urls_digitadas=atuais,
    )
    assert final == ["https://cdn.exemplo/b.jpg"]


def test_removing_principal_promotes_next_remaining_photo():
    atuais = ["data:image/png;base64,AAA", "data:image/png;base64,BBB"]
    final = resolver_galeria_fotos(
        atuais,
        remover_indices=[0],
        principal_indice=0,
        urls_digitadas=[],
    )
    assert final == ["data:image/png;base64,BBB"]


def test_selected_principal_is_preserved_only_when_it_still_exists():
    atuais = ["local-a", "https://cdn.exemplo/b.jpg", "local-c"]
    final = resolver_galeria_fotos(
        atuais,
        remover_indices=[],
        principal_indice=2,
        urls_digitadas=["https://cdn.exemplo/b.jpg"],
    )
    assert final[0] == "local-c"
    assert set(final) == set(atuais)


def test_deleting_url_line_removes_remote_photo_even_without_checkbox():
    atuais = ["local-a", "https://cdn.exemplo/b.jpg"]
    final = resolver_galeria_fotos(
        atuais,
        remover_indices=[],
        principal_indice=0,
        urls_digitadas=[],
    )
    assert final == ["local-a"]


def test_replace_all_ignores_old_gallery_and_accepts_fresh_photos():
    atuais = ["old-local", "https://cdn.exemplo/old.jpg"]
    final = resolver_galeria_fotos(
        atuais,
        remover_indices=[],
        principal_indice=0,
        urls_digitadas=["https://cdn.exemplo/new-url.jpg"],
        novas_referencias=["new-upload", "new-drive"],
        substituir_todas=True,
    )
    assert final == [
        "https://cdn.exemplo/new-url.jpg",
        "new-upload",
        "new-drive",
    ]


def test_catalog_form_state_matcher_clears_indexed_remove_widgets_too():
    assert chave_estado_catalogo_pertence_ao_formulario("cat_urls_3", "3")
    assert chave_estado_catalogo_pertence_ao_formulario("cat_remover_foto_3_0", "3")
    assert chave_estado_catalogo_pertence_ao_formulario("cat_principal_foto_3", "3")
    assert not chave_estado_catalogo_pertence_ao_formulario("cat_urls_30", "3")
    assert not chave_estado_catalogo_pertence_ao_formulario("outra_chave_3", "3")
