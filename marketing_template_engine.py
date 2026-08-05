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


def _headline_parts(title: str) -> tuple[str, str]:
    """Transforma nomes longos de catálogo em chamada publicitária curta."""
    clean = re.sub(r"\s+", " ", str(title or "Produto AlphaFest")).strip()
    clean = re.sub(r"\([^)]*\)", "", clean).strip()
    words = clean.split()
    if len(words) <= 3:
        return clean.upper(), ""
    # Mantém o tipo de produto e o principal identificador no título.
    main = " ".join(words[:3]).upper()
    rest = " ".join(words[3:]).strip(" -–—")
    return main, rest


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int, bold: bool = True):
    size = start_size
    while size > min_size:
        font = _font(size, bold)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
        size -= 2
    return _font(min_size, bold)


def _center_x(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return int((width - (box[2] - box[0])) / 2)


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
    """Renderiza o Template Mestre AlphaFest v2.

    A grade é fixa e inspirada nas peças comerciais da marca: marca e chamada no
    topo, benefícios à esquerda, produto como protagonista à direita e CTA forte
    no rodapé. O conteúdo pode variar sem desmontar a composição.
    """
    cfg = carregar_template(template_id)
    width, height = size
    sx, sy = width / 1080.0, height / 1350.0
    palette = cfg.get("paleta", {})
    blue = _hex(palette.get("azul", "#0873DF"))
    dark_blue = _hex(palette.get("azul_escuro", "#063B89"))
    pink = _hex(palette.get("rosa", "#EB2A92"))
    pale = _hex(palette.get("azul_claro", "#EAF6FF"))
    white = (255, 255, 255, 255)

    canvas = Image.new("RGBA", (width, height), white)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Moldura orgânica superior inspirada nas campanhas oficiais.
    draw.ellipse((-260*sx, -205*sy, 520*sx, 185*sy), fill=blue)
    draw.ellipse((655*sx, -180*sy, 1300*sx, 190*sy), fill=dark_blue)
    draw.arc((-120*sx, -65*sy, 1200*sx, 330*sy), 5, 175, fill=_hex("#58D2FF"), width=max(8, int(14*sx)))
    draw.arc((-75*sx, -35*sy, 1140*sx, 285*sy), 7, 173, fill=white, width=max(7, int(11*sx)))

    # Marca central, integrada à composição e sem caixa branca.
    logo = _transparent_logo(Path(logo_path or BASE_DIR / "logo.png"), (int(360*sx), int(205*sy)))
    if logo:
        lx = int((width - logo.width) / 2)
        canvas.alpha_composite(logo, (lx, int(24*sy)))

    # Pontos e brilhos decorativos discretos.
    for x, y, r, color in [
        (112, 220, 7, "#EB2A92"), (170, 178, 5, "#FFD447"),
        (925, 205, 7, "#EB2A92"), (980, 158, 5, "#FFD447"),
        (52, 530, 5, "#0873DF"), (1025, 530, 5, "#0873DF"),
    ]:
        draw.ellipse(((x-r)*sx, (y-r)*sy, (x+r)*sx, (y+r)*sy), fill=_hex(color))

    # Título publicitário: curto, centralizado e dominante.
    headline, remainder = _headline_parts(title)
    headline_font = _fit_font(draw, headline, int(950*sx), int(96*sx), int(54*sx), True)
    hx = _center_x(draw, headline, headline_font, width)
    draw.text((hx, int(210*sy)), headline, font=headline_font, fill=dark_blue)

    subtitle_text = str(subtitle or remainder or "Personalizado do seu jeito").strip()
    if remainder and remainder.casefold() not in subtitle_text.casefold():
        subtitle_text = f"{remainder} • {subtitle_text}"
    subtitle_font = _fit_font(draw, subtitle_text, int(880*sx), int(38*sx), int(24*sx), True)
    sub_box = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    ribbon_w = min(int(930*sx), (sub_box[2]-sub_box[0]) + int(100*sx))
    ribbon_x = int((width-ribbon_w)/2)
    ribbon_y = int(328*sy)
    draw.rounded_rectangle((ribbon_x, ribbon_y, ribbon_x+ribbon_w, ribbon_y+int(66*sy)), radius=int(20*sx), fill=blue)
    draw.text((_center_x(draw, subtitle_text, subtitle_font, width), ribbon_y+int(10*sy)), subtitle_text, font=subtitle_font, fill=white)

    # Foto protagonista integrada no lado direito.
    source = Image.open(io.BytesIO(image_bytes))
    source = ImageOps.exif_transpose(source).convert("RGB")
    x1, y1, x2, y2 = int(485*sx), int(420*sy), int(1025*sx), int(1010*sy)
    fw, fh = x2-x1, y2-y1
    photo = ImageOps.fit(source, (fw, fh), method=Image.Resampling.LANCZOS)
    radius = max(18, int(38*sx))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.rounded_rectangle((x1+13, y1+18, x2+13, y2+18), radius=radius, fill=(0, 35, 95, 72))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(8, int(18*sx))))
    canvas.alpha_composite(shadow)
    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw, fh), radius=radius, fill=255)
    canvas.paste(photo.convert("RGBA"), (x1, y1), mask)

    # Coluna de benefícios com leitura grande e rápida.
    benefits = _parse_benefits(description, cfg.get("beneficios_padrao", []))
    section_font = _font(max(27, int(35*sx)), True)
    draw.text((58*sx, 430*sy), "DESTAQUES", font=section_font, fill=dark_blue)
    benefit_title_font = _font(max(23, int(30*sx)), True)
    benefit_text_font = _font(max(18, int(23*sx)), False)
    benefit_y = 500
    for idx, benefit in enumerate(benefits[:4]):
        cy = int(benefit_y*sy)
        draw.ellipse((58*sx, cy, 114*sx, cy+56*sy), fill=blue)
        icon_font = _font(max(22, int(29*sx)), True)
        draw.text((74*sx, cy+5*sy), "✓", font=icon_font, fill=white)
        short = benefit.strip().rstrip(".")
        title_line = short.upper() if len(short) <= 24 else short[:22].rstrip()+"…"
        draw.text((132*sx, cy-2*sy), title_line, font=benefit_title_font, fill=dark_blue)
        detail = [
            "Qualidade que valoriza seu produto.",
            "Prático, bonito e pronto para encantar.",
            "Produção cuidadosa e acabamento especial.",
            "Feito para destacar sua ocasião.",
        ][idx]
        for line_no, line in enumerate(_wrap(draw, detail, benefit_text_font, int(315*sx), 2)):
            draw.text((132*sx, cy+(34+line_no*27)*sy), line, font=benefit_text_font, fill=_hex("#24364B"))
        benefit_y += 128

    # Selo circular de preço/oferta, quando informado.
    if str(price).strip():
        cx, cy, rr = int(355*sx), int(965*sy), int(105*sx)
        draw.ellipse((cx-rr, cy-rr, cx+rr, cy+rr), fill=white, outline=blue, width=max(5, int(6*sx)))
        label_font = _font(max(17, int(22*sx)), True)
        price_font = _fit_font(draw, str(price), int(170*sx), int(38*sx), int(23*sx), True)
        label = "A PARTIR DE"
        draw.text((_center_x(draw, label, label_font, rr*2)+cx-rr, cy-int(50*sy)), label, font=label_font, fill=dark_blue)
        draw.text((_center_x(draw, str(price), price_font, rr*2)+cx-rr, cy-int(8*sy)), str(price), font=price_font, fill=pink)

    # Rodapé de conversão: CTA e telefone são o segundo maior foco da peça.
    footer_y = int(1090*sy)
    draw.rectangle((0, footer_y, width, height), fill=dark_blue)
    draw.rectangle((0, footer_y, width, footer_y+int(12*sy)), fill=blue)
    cta_text = str(cta or "FAÇA SEU PEDIDO!").upper()
    cta_font = _fit_font(draw, cta_text, int(900*sx), int(50*sx), int(32*sx), True)
    draw.text((_center_x(draw, cta_text, cta_font, width), footer_y+int(30*sy)), cta_text, font=cta_font, fill=white)

    phone_text = str(phone or "11 97294-9533")
    phone_font = _fit_font(draw, phone_text, int(700*sx), int(64*sx), int(40*sx), True)
    phone_y = footer_y+int(100*sy)
    # Ícone simples de WhatsApp em círculo para manter compatibilidade sem fonte externa.
    circle_x = int(160*sx)
    circle_r = int(38*sx)
    draw.ellipse((circle_x-circle_r, phone_y, circle_x+circle_r, phone_y+2*circle_r), fill=blue, outline=white, width=max(3, int(4*sx)))
    phone_x = int(225*sx)
    draw.text((phone_x, phone_y-int(4*sy)), phone_text, font=phone_font, fill=white)

    tagline_font = _font(max(16, int(21*sx)), True)
    tagline = "QUALIDADE • CRIATIVIDADE • PERSONALIZAÇÃO"
    draw.text((_center_x(draw, tagline, tagline_font, width), int(1310*sy)), tagline, font=tagline_font, fill=(255,255,255,230))

    output = io.BytesIO()
    canvas.convert("RGB").save(output, "PNG", optimize=True)
    return output.getvalue()
