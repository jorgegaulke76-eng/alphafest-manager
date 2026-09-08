from alpha_marketing_designer import build_design_plan, validate_design_plan


def test_hf5_hf1_long_product_description_is_normalized_before_review():
    product = {
        "Nome": "Gravação Laser",
        "Categoria": "Gravação",
        "Descricao": (
            "Personalização profissional e durável para presentes, brindes corporativos, empresas e ações especiais de campanha Outubro Rosa. "
            "Produção sob encomenda com acabamento de qualidade."
        ),
    }
    plan = build_design_plan(product, "Vender", "Outubro Rosa", ["Instagram Feed"])
    assert all(len(x) <= 72 for x in plan["benefits"])
    assert len(plan["title"]) <= 52
    assert len(plan["subtitle"]) <= 120
    review = validate_design_plan(plan)
    assert review["ok"], review
    assert review["failed"] == []
    assert plan["rules_version"] == "HF53.2-HF5-HF2"


def test_hf5_hf1_review_reports_failed_rule_names():
    review = validate_design_plan({"title":"", "subtitle":"", "benefits":[], "cta":"", "channels":{}})
    assert not review["ok"]
    assert review["failed"]
    assert "Título presente" in review["failed"]
