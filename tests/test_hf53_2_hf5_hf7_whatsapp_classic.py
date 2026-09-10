import io
from pathlib import Path
from PIL import Image

from marketing_template_engine import render_template, WHATSAPP_ICON_PATH


def test_hf7_uses_classic_whatsapp_asset():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF8-HF6'
    assert WHATSAPP_ICON_PATH.exists()
    icon = Image.open(WHATSAPP_ICON_PATH).convert('RGBA')
    assert icon.size == (256, 256)
    # cantos transparentes: o quadriculado da referência não entra na arte
    assert icon.getpixel((0, 0))[3] < 32
    # área útil contém verde e branco suficientes para o símbolo clássico
    green = white = 0
    for r, g, b, a in icon.getdata():
        if a > 200 and g > 100 and g > r * 1.2 and g > b * 1.15:
            green += 1
        if a > 200 and r > 230 and g > 230 and b > 230:
            white += 1
    assert green > 15000
    assert white > 5000


def test_hf7_renders_classic_whatsapp_in_cta():
    src = Image.new('RGB', (420, 620), (80, 240, 70))
    buf = io.BytesIO(); src.save(buf, 'PNG')
    art = render_template(
        buf.getvalue(), (1080, 1350), template_id='splash_premium_anna',
        title='COPO LONG DRINK NEOM',
        subtitle='Natal: Um presente útil com a sua identidade',
        description='Design exclusivo • Fácil de usar • Material de qualidade • Personalizado • Múltiplos usos',
        cta='CONHEÇA ESTE PRODUTO', phone='11972949533',
        palette_override={
            'primary': '#B71C1C', 'secondary': '#166B34', 'accent': '#D4AF37',
            'background': '#FFFDF4', 'text': '#5D1A16', 'metallic': '#D4AF37',
        },
    )
    im = Image.open(io.BytesIO(art)).convert('RGB')
    assert im.size == (1080, 1350)
    # área do ícone oficial: muito verde + branco do balão/handset
    green = white = 0
    for y in range(1005, 1105):
        for x in range(570, 670):
            r, g, b = im.getpixel((x, y))
            if g > 105 and g > r * 1.15 and g > b * 1.1:
                green += 1
            if r > 225 and g > 225 and b > 225:
                white += 1
    assert green > 2500
    assert white > 700
