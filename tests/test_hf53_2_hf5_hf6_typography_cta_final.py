import io
from pathlib import Path

from PIL import Image

from marketing_template_engine import render_template, _format_phone_br


def test_hf6_version_and_phone_format():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == '20.4.9-I8.13.5-HF53.3-HF7'
    assert _format_phone_br('11972949533') == '(11) 97294-9533'
    assert _format_phone_br('5511972949533') == '(11) 97294-9533'


def test_hf6_renders_final_qa_natal_feed():
    src = Image.new('RGB', (420, 620), (40, 235, 70))
    buf = io.BytesIO(); src.save(buf, 'PNG')
    art = render_template(
        buf.getvalue(),
        (1080, 1350),
        template_id='splash_premium_anna',
        title='COPO LONG DRINK NEOM',
        subtitle='Natal: Um presente útil com a sua identidade',
        description='Design exclusivo • Fácil de usar • Material de qualidade • Personalizado • Múltiplos usos',
        cta='CONHEÇA ESTE PRODUTO',
        phone='11972949533',
        palette_override={
            'primary': '#B71C1C', 'secondary': '#166B34', 'accent': '#D4AF37',
            'background': '#FFFDF4', 'text': '#5D1A16', 'metallic': '#D4AF37',
        },
    )
    im = Image.open(io.BytesIO(art)).convert('RGB')
    assert im.size == (1080, 1350)
    # O CTA deve conter verde forte e branco suficiente para o handset legível.
    green = white = 0
    for y in range(1000, 1110, 2):
        for x in range(565, 675, 2):
            r, g, b = im.getpixel((x, y))
            if g > 120 and g > r * 1.25 and g > b * 1.15:
                green += 1
            if r > 235 and g > 235 and b > 235:
                white += 1
    assert green > 250
    assert white > 100
    # Rodapé emocional deve ocupar a área central inferior, não ficar preso à esquerda.
    darkish = 0
    for y in range(1280, 1330, 3):
        for x in range(250, 830, 3):
            r, g, b = im.getpixel((x, y))
            if r < 190 and g < 170 and b < 120:
                darkish += 1
    assert darkish > 100
