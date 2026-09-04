from pathlib import Path


def test_hf46_1_galeria_e_privada_e_nao_publica_site():
    app = Path("app.py").read_text(encoding="utf-8")
    cloud = Path("cloud_db.py").read_text(encoding="utf-8")
    assert "📸 Galeria de Trabalhos" in app
    assert "Nada desta aba é publicado no site" in app
    assert "upload_private_gallery_image" in app
    assert 'GALERIA_TRABALHOS_BUCKET = "galeriatrabalhos"' in cloud
    assert '"public": False' in cloud


def test_hf46_1_galeria_esta_no_backup_e_tem_travas_de_curadoria():
    app = Path("app.py").read_text(encoding="utf-8")
    assert '("galeria_trabalhos_db", ARQUIVO_GALERIA_TRABALHOS, [])' in app
    assert "autorizado_publicacao" in app
    assert "selecionado_site" in app
    assert "disabled=not autorizado_gal" in app


def test_hf46_1_cloud_storage_nao_tem_fallback_publico():
    cloud = Path("cloud_db.py").read_text(encoding="utf-8")
    inicio = cloud.index("def upload_private_gallery_image")
    fim = cloud.index("def read_private_gallery_image", inicio)
    bloco = cloud[inicio:fim]
    assert "/storage/v1/object/{GALERIA_TRABALHOS_BUCKET}/" in bloco
    assert "/object/public/catalogo/" not in bloco
