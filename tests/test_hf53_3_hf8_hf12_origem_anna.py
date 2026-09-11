from pathlib import Path
import marketing_template_engine as engine


def test_hf12_package_and_anna_renderer_versions():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF8-HF12"
    anna = next(x for x in engine.listar_templates() if x["id"] == "anna_social_redes")
    master = next(x for x in engine.listar_templates() if x["id"] == "splash_premium_anna")
    assert anna["versao_template"] == "HF53.3-HF8-HF11"
    assert master["versao_template"] == "HF53.2-HF5-HF7"
    assert master["oficial"] and master["protegido"]


def test_hf12_origin_uses_real_anna_template_version():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "def _marketing_designer_version" in app
    assert "_mkt_designer_version = _marketing_designer_version(_mkt_template_id, _mkt_template_version)" in app
    assert '"origem_criativa": f"Designer Comercial AlphaFest {_mkt_designer_version}"' in app
    assert '"designer_rules_version": _mkt_designer_version' in app
    # O caminho de criação não pode mais carimbar HF10 diretamente.
    create_block = app[app.index("_mkt_id = f\"MKT-AUTO-"):app.index("conteudos.insert(0, _mkt_record)")]
    assert "Designer Comercial AlphaFest HF53.3-HF8-HF10" not in create_block


def test_hf12_normalizes_mislabeled_hf11_records():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "def _marketing_normalizar_origem_anna" in app
    assert 'versao != "HF53.3-HF8-HF11"' in app
    assert 'item["origem_criativa"] = "Designer Comercial AlphaFest HF53.3-HF8-HF11"' in app
    assert 'item["designer_rules_version"] = "HF53.3-HF8-HF11"' in app
    assert "_marketing_normalizar_origem_anna(dados)" in app
