from pathlib import Path

from PIL import Image

from marketing_template_engine import _paste_photo


def test_hf5_hf2_photo_is_physically_clipped_to_protected_zone():
    canvas = Image.new("RGBA", (360, 300), (8, 16, 32, 255))
    # Simula foto cadastrada muito maior que a caixa do produto. Este era o
    # cenário que fazia os copos atravessarem título e benefícios no HF5-HF1.
    source = Image.new("RGBA", (1800, 1400), (220, 30, 70, 255))
    box = (190, 70, 340, 250)

    _paste_photo(
        canvas,
        source,
        box,
        mode="original",
        product_title="Gravação Laser",
        upscale=True,
    )

    background = (8, 16, 32, 255)
    # Toda a coluna protegida de texto à esquerda permanece intocada.
    for point in ((0, 0), (189, 70), (120, 150), (189, 249), (200, 69), (340, 150)):
        assert canvas.getpixel(point) == background
    # A foto continua visível dentro da própria zona.
    assert canvas.getpixel((260, 160)) != background


def test_hf5_hf2_package_version():
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF8-HF8"
