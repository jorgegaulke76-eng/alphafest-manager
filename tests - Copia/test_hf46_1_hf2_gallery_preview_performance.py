from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
CLOUD = (ROOT / "cloud_db.py").read_text(encoding="utf-8")


def test_gallery_card_renders_multiple_preview_paths():
    assert "preview_paths = foto_paths[:4]" in APP
    assert "thumb_cols = c_img.columns(2)" in APP
    assert "+ {len(foto_paths) - len(preview_paths)} foto(s)" in APP


def test_private_gallery_bucket_is_cached_per_process():
    assert "_PRIVATE_GALLERY_BUCKET_READY = False" in CLOUD
    assert "if _PRIVATE_GALLERY_BUCKET_READY:" in CLOUD
    assert "_PRIVATE_GALLERY_BUCKET_READY = True" in CLOUD


def test_gallery_image_optimization_is_fast_webp():
    assert "img.thumbnail((1600, 1600))" in CLOUD
    assert 'format="WEBP", quality=80, method=3' in CLOUD
