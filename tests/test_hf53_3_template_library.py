from pathlib import Path

import marketing_template_engine as engine


def test_hf53_3_version():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF5"


def test_official_master_is_first_homologated_and_protected():
    catalog = engine.listar_templates()
    assert catalog
    official = catalog[0]
    assert official["id"] == "splash_premium_anna"
    assert official["oficial"] is True
    assert official["protegido"] is True
    assert official["autopilot_aprovado"] is True
    assert official["status_template"] == "Homologado"
    assert official["versao_template"] == "HF53.2-HF5-HF7"
    assert Path(official["preview"]).exists()


def test_autopilot_catalog_only_contains_approved_templates():
    approved = engine.listar_templates_autopilot()
    assert approved
    assert all(item.get("autopilot_aprovado") for item in approved)
    assert approved[0]["id"] == "splash_premium_anna"


def test_hf53_3_ui_uses_library_selection_and_records_template_metadata():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Biblioteca de Templates Comerciais" in app
    assert '"Template comercial"' in app
    assert "_mkt_templates_catalog = listar_templates_marketing()" in app
    assert "template_id=_mkt_template_id" in app
    assert '"template_status": _mkt_template_status' in app
    assert '"template_versao": _mkt_template_version' in app
    assert '"template_oficial": bool(_mkt_template.get("oficial"))' in app


def test_imported_templates_are_not_auto_approved_by_catalog_layer(monkeypatch):
    fake = [{
        "id": "externo_teste",
        "nome": "Externo Teste",
        "source": "library",
        "autopilot_aprovado": True,
        "oficial": True,
        "protegido": True,
    }]
    monkeypatch.setattr(engine, "list_library_templates", lambda: fake)
    item = next(x for x in engine.listar_templates() if x["id"] == "externo_teste")
    assert item["autopilot_aprovado"] is False
    assert item["oficial"] is False
    assert item["protegido"] is False


def test_official_template_id_is_reserved_against_imports():
    import io
    import json
    import zipfile
    import template_library_engine as library

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("config.json", json.dumps({"id": "splash_premium_anna", "nome": "Fake"}))
        zf.writestr("layout.json", "{}")
        zf.writestr("fundo.png", b"not-important-for-id-check")
    try:
        library.install_template_zip(buf.getvalue(), replace=True)
    except ValueError as exc:
        assert "protegido" in str(exc).casefold()
    else:
        raise AssertionError("ID oficial protegido não pode ser importado")


def test_library_loader_never_shadows_official_id():
    import template_library_engine as library
    assert library.load_library_template("splash_premium_anna") is None
