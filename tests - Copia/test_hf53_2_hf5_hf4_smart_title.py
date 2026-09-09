from PIL import Image, ImageDraw

from alpha_marketing_designer import build_design_plan, validate_design_plan
from marketing_template_engine import _fit_wrapped_font


def test_hf4_title_keeps_full_product_name_without_ellipsis():
    name = "Copo Long Drink Neon Personalizado 500 ml"
    plan = build_design_plan(
        {"Nome": name, "Descricao": "Copo neon para festas e eventos.", "Categoria": "Brindes"},
        "Vender", "Natal", ["Instagram Feed"],
    )
    assert plan["title"] == name.upper()
    assert plan["channels"]["Instagram Feed"]["title"] == name.upper()
    assert "…" not in plan["title"] and "..." not in plan["title"]
    assert validate_design_plan(plan)["ok"]


def test_hf4_renderer_wraps_complete_title_in_at_most_three_lines():
    raw = "COPO LONG DRINK NEON PERSONALIZADO 500 ML"
    image = Image.new("RGBA", (1080, 1350), "white")
    draw = ImageDraw.Draw(image, "RGBA")
    _font, lines, _line_h = _fit_wrapped_font(draw, raw, 690, 218, 124, 44, 3, bold=True)
    assert 1 <= len(lines) <= 3
    assert " ".join(lines) == raw
    assert all("…" not in line and "..." not in line for line in lines)
