"""Engine de templates visuais do Alpha Marketing Studio.

O layout fica separado da interface e das regras de negócio. Cada template pode
ser evoluído sem alterar o fluxo de campanhas do AlphaFest Manager.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_TEMPLATE = "alphafest_classico"

# Registro interno dos templates oficiais. Nesta fase ele é a fonte de verdade
# para evitar dependência de arquivos externos no Streamlit Cloud.
EMBEDDED_TEMPLATES: dict[str, dict[str, Any]] = {
    "alphafest_classico": {
        "id": "alphafest_classico",
        "nome": "AlphaFest Clássico",
        "descricao": "Modelo comercial azul e branco com título forte, foto, benefícios e CTA.",
        "paleta": {
            "fundo": "#FFFFFF",
            "azul": "#0873DF",
            "azul_escuro": "#063B89",
            "azul_claro": "#EAF6FF",
            "rosa": "#EB2A92",
        },
        "beneficios_padrao": ["Design exclusivo", "Alta qualidade", "Feito para encantar", "Personalizado"],
        "decoracoes": [
            [115, 188, 9, "#EB2A92"],
            [435, 82, 8, "#FFD447"],
            [1018, 164, 7, "#FFD447"],
            [458, 1015, 7, "#0873DF"],
            [1005, 995, 8, "#EB2A92"],
        ],
    },
}


def listar_templates() -> list[dict[str, str]]:
    return [
        {
            "id": template_id,
            "nome": str(cfg.get("nome") or template_id),
            "descricao": str(cfg.get("descricao") or ""),
        }
        for template_id, cfg in EMBEDDED_TEMPLATES.items()
    ]


def carregar_template(template_id: str = DEFAULT_TEMPLATE) -> dict[str, Any]:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", template_id or DEFAULT_TEMPLATE)
    cfg = EMBEDDED_TEMPLATES.get(safe_id) or EMBEDDED_TEMPLATES[DEFAULT_TEMPLATE]
    # Cópia rasa e das estruturas mutáveis principais para impedir alterações
    # acidentais no registro global durante uma renderização.
    result = dict(cfg)
    result["paleta"] = dict(cfg.get("paleta", {}))
    result["beneficios_padrao"] = list(cfg.get("beneficios_padrao", []))
    result["decoracoes"] = [list(item) for item in cfg.get("decoracoes", [])]
    return result


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _hex(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = str(value or "#000000").lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
    except Exception:
        return (0, 0, 0, alpha)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str]:
    words = str(text or "").strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=font)
        if (box[2] - box[0]) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines)) < len(" ".join(words)):
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return lines


def _transparent_logo(path: Path, max_size: tuple[int, int]) -> Image.Image | None:
    if not path.exists():
        return None
    try:
        logo = Image.open(path).convert("RGBA")
        px = logo.load()
        for y in range(logo.height):
            for x in range(logo.width):
                r, g, b, a = px[x, y]
                brightness = max(r, g, b)
                spread = brightness - min(r, g, b)
                # Remove fundo quase preto, preservando azul, rosa e branco da marca.
                if brightness < 42 and spread < 30:
                    a = 0
                elif brightness < 85 and spread < 20:
                    a = int(a * max(0.0, (brightness - 42) / 43))
                px[x, y] = (r, g, b, a)
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)
        logo.thumbnail(max_size, Image.Resampling.LANCZOS)
        return logo
    except Exception:
        return None


def _parse_benefits(description: str, fallback: Iterable[str]) -> list[str]:
    clean = re.sub(r"[•✓✔|]", ",", str(description or ""))
    pieces = [p.strip(" .:-") for p in re.split(r"[,;\n]", clean) if p.strip(" .:-")]
    pieces = [p for p in pieces if 2 <= len(p) <= 34]
    result = pieces[:4]
    for item in fallback:
        if len(result) >= 4:
            break
        if item not in result:
            result.append(item)
    return result[:4]


def render_template(
    image_bytes: bytes,
    size: tuple[int, int],
    *,
    template_id: str = DEFAULT_TEMPLATE,
    title: str,
    subtitle: str = "Personalize seus momentos",
    description: str = "",
    price: str = "",
    cta: str = "FAÇA SEU PEDIDO!",
    phone: str = "11 97294-9533",
    logo_path: str | Path | None = None,
) -> bytes:
    cfg = carregar_template(template_id)
    width, height = size
    sx, sy = width / 1080.0, height / 1350.0
    palette = cfg.get("paleta", {})
    blue = _hex(palette.get("azul", "#0873DF"))
    dark_blue = _hex(palette.get("azul_escuro", "#063B89"))
    pink = _hex(palette.get("rosa", "#EB2A92"))
    pale = _hex(palette.get("azul_claro", "#EAF6FF"))

    canvas = Image.new("RGBA", (width, height), _hex(palette.get("fundo", "#FFFFFF")))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Formas orgânicas do padrão AlphaFest.
    draw.ellipse((-340*sx, -175*sy, 560*sx, 250*sy), fill=blue)
    draw.ellipse((710*sx, -120*sy, 1215*sx, 250*sy), fill=dark_blue)
    draw.arc((-100*sx, -95*sy, 710*sx, 300*sy), 8, 172, fill=_hex("#61CEFF"), width=max(10, int(18*sx)))
    draw.ellipse((-160*sx, 1040*sy, 410*sx, 1480*sy), fill=_hex("#DDF3FF"))
    draw.ellipse((820*sx, 1080*sy, 1190*sx, 1410*sy), fill=_hex("#FCE4F2"))
    for x, y, r, color in cfg.get("decoracoes", []):
        draw.ellipse(((x-r)*sx, (y-r)*sy, (x+r)*sx, (y+r)*sy), fill=_hex(color))

    # Marca integrada ao topo, sem cartão.
    logo = _transparent_logo(Path(logo_path or BASE_DIR / "logo.png"), (int(310*sx), int(150*sy)))
    if logo:
        canvas.alpha_composite(logo, (int(65*sx), int(42*sy)))

    # Título grande: protagonista da peça.
    title_font = _font(max(48, int(76*sx)), True)
    subtitle_font = _font(max(25, int(35*sx)), True)
    title_lines = _wrap(draw, title or "Produto AlphaFest", title_font, int(470*sx), 3)
    y = int(235*sy)
    for idx, line in enumerate(title_lines):
        draw.text((55*sx, y), line, font=title_font, fill=dark_blue if idx == 0 else blue)
        y += int(82*sy)

    subtitle_lines = _wrap(draw, subtitle, subtitle_font, int(455*sx), 2)
    sy_text = max(y + int(8*sy), int(470*sy))
    for line in subtitle_lines:
        draw.text((58*sx, sy_text), line, font=subtitle_font, fill=pink)
        sy_text += int(43*sy)

    # Foto principal ampla, sobreposta às formas, como nas artes comerciais.
    source = Image.open(io.BytesIO(image_bytes))
    source = ImageOps.exif_transpose(source).convert("RGB")
    box = (500, 215, 1025, 770)
    x1, y1, x2, y2 = [int(v * (sx if i % 2 == 0 else sy)) for i, v in enumerate(box)]
    fw, fh = x2 - x1, y2 - y1
    photo = ImageOps.fit(source, (fw, fh), method=Image.Resampling.LANCZOS)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    radius = max(18, int(35*sx))
    shadow_draw.rounded_rectangle((x1+12, y1+18, x2+12, y2+18), radius=radius, fill=(0, 42, 100, 58))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(10, int(18*sx))))
    canvas.alpha_composite(shadow)
    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw, fh), radius=radius, fill=255)
    canvas.paste(photo.convert("RGBA"), (x1, y1), mask)

    # Benefícios grandes, organizados em lista comercial.
    benefit_title_font = _font(max(25, int(34*sx)), True)
    benefit_font = _font(max(22, int(30*sx)), True)
    draw.text((70*sx, 720*sy), "APLICÁVEL EM:", font=benefit_title_font, fill=dark_blue)
    benefits = _parse_benefits(description, cfg.get("beneficios_padrao", ["Bolos", "Doces", "Bolachas", "Drinks"]))
    columns = [(70, 790), (320, 790), (70, 875), (320, 875)]
    for benefit, (bx, by) in zip(benefits, columns):
        cx, cy = int(bx*sx), int(by*sy)
        draw.ellipse((cx, cy, cx+48*sx, cy+48*sy), fill=blue)
        check_font = _font(max(18, int(25*sx)), True)
        draw.text((cx+10*sx, cy+4*sy), "✓", font=check_font, fill=(255,255,255,255))
        lines = _wrap(draw, benefit, benefit_font, int(185*sx), 2)
        ty = cy + int(4*sy)
        for line in lines:
            draw.text((cx+62*sx, ty), line, font=benefit_font, fill=dark_blue)
            ty += int(34*sy)

    # Selo opcional de preço.
    if str(price).strip():
        draw.ellipse((735*sx, 770*sy, 1005*sx, 1010*sy), fill=pink)
        price_label_font = _font(max(20, int(27*sx)), True)
        price_font = _font(max(31, int(44*sx)), True)
        draw.text((805*sx, 815*sy), "A PARTIR DE", font=price_label_font, fill=(255,255,255,255))
        price_lines = _wrap(draw, str(price), price_font, int(210*sx), 2)
        py = int(865*sy)
        for line in price_lines:
            bbox = draw.textbbox((0,0), line, font=price_font)
            tw = bbox[2]-bbox[0]
            draw.text(((870*sx)-(tw/2), py), line, font=price_font, fill=(255,255,255,255))
            py += int(48*sy)

    # Rodapé comercial de leitura imediata.
    footer_y = int(1040*sy)
    draw.rounded_rectangle((48*sx, footer_y, 1032*sx, 1295*sy), radius=max(24, int(34*sx)), fill=blue)
    cta_font = _font(max(34, int(48*sx)), True)
    phone_font = _font(max(31, int(44*sx)), True)
    small_font = _font(max(18, int(24*sx)), False)
    cta_text = str(cta or "FAÇA SEU PEDIDO!").upper()
    cta_lines = _wrap(draw, cta_text, cta_font, int(540*sx), 2)
    cty = int(1090*sy)
    for line in cta_lines:
        draw.text((85*sx, cty), line, font=cta_font, fill=(255,255,255,255))
        cty += int(56*sy)
    draw.text((85*sx, 1208*sy), str(phone), font=phone_font, fill=(255,255,255,255))
    draw.text((650*sx, 1162*sy), "Personalizados em geral", font=small_font, fill=(255,255,255,230))
    draw.text((650*sx, 1203*sy), "Balões • Lembranças", font=small_font, fill=(255,255,255,230))

    output = io.BytesIO()
    canvas.convert("RGB").save(output, "PNG", optimize=True)
    return output.getvalue()
