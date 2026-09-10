import io
from pathlib import Path

from PIL import Image

from marketing_template_engine import render_template, _unique_application_sources


def _solid_png(rgb):
    image = Image.new("RGB", (420, 620), rgb)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def test_hf5_hf5_version_and_deduplication_contract():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF8-HF7"
    primary = Image.open(io.BytesIO(_solid_png((230, 30, 60)))).convert("RGBA")
    sources = _unique_application_sources(
        primary,
        [
            _solid_png((230, 30, 60)),  # duplicada: deve ser ignorada
            _solid_png((30, 180, 70)),
            _solid_png((30, 80, 220)),
            _solid_png((245, 190, 30)),
        ],
    )
    assert len(sources) == 4


def test_hf5_hf5_renders_distinct_application_thumbnails_and_final_qa():
    colors = [
        (230, 30, 60),
        (30, 180, 70),
        (30, 80, 220),
        (245, 190, 30),
    ]
    main = _solid_png(colors[0])
    art = render_template(
        main,
        (1080, 1350),
        template_id="splash_premium_anna",
        title="COPO LONG DRINK NEON",
        subtitle="Natal: Um presente útil com a sua identidade",
        description="Design exclusivo • Fácil de usar • Material de qualidade • Personalizado • Múltiplos usos",
        cta="CONHEÇA ESTE PRODUTO",
        phone="(11) 97294-9533",
        palette_override={
            "primary": "#B71C1C",
            "secondary": "#166B34",
            "accent": "#D4AF37",
            "background": "#FFFDF4",
            "text": "#5D1A16",
            "metallic": "#D4AF37",
        },
        application_images=[_solid_png(c) for c in colors],
    )
    with Image.open(io.BytesIO(art)).convert("RGB") as image:
        # centros conhecidos dos quatro círculos de aplicações
        samples = [image.getpixel((x, 1019)) for x in (70, 196, 322, 448)]
        assert len(set(samples)) == 4, samples
        # CTA deve conter área verde substancial do ícone refinado do WhatsApp
        greenish = 0
        for y in range(1010, 1098, 4):
            for x in range(570, 665, 4):
                r, g, b = image.getpixel((x, y))
                if g > 115 and g > r * 1.25 and g > b * 1.1:
                    greenish += 1
        assert greenish >= 40
