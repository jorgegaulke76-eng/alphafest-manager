"""Engine de templates visuais do Alpha Marketing Studio.

Versão 15.2.1: Template Mestre AlphaFest v3, com hierarquia publicitária
inspirada nas peças oficiais da marca. O motor permanece independente da
interface Streamlit e recebe somente conteúdo da campanha.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = "alphafest_classico"

EMBEDDED_TEMPLATES: dict[str, dict[str, Any]] = {
    "alphafest_classico": {
        "id": "alphafest_classico",
        "nome": "AlphaFest Clássico",
        "descricao": "Template publicitário azul e branco com título gigante, foto protagonista e CTA forte.",
        "paleta": {
            "fundo": "#FFFFFF",
            "azul": "#0678E8",
            "azul_escuro": "#073C91",
            "azul_claro": "#DDF4FF",
            "rosa": "#EF2A92",
            "amarelo": "#FFD335",
            "texto": "#15324D",
        },
        "beneficios_padrao": ["Design exclusivo", "Fácil de usar", "Material de qualidade", "Múltiplos usos"],
    },
}


def listar_templates() -> list[dict[str, str]]:
    return [{"id": k, "nome": str(v.get("nome") or k), "descricao": str(v.get("descricao") or "")} for k, v in EMBEDDED_TEMPLATES.items()]


def carregar_template(template_id: str = DEFAULT_TEMPLATE) -> dict[str, Any]:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", template_id or DEFAULT_TEMPLATE)
    cfg = EMBEDDED_TEMPLATES.get(safe_id) or EMBEDDED_TEMPLATES[DEFAULT_TEMPLATE]
    out = dict(cfg)
    out["paleta"] = dict(cfg.get("paleta", {}))
    out["beneficios_padrao"] = list(cfg.get("beneficios_padrao", []))
    return out


def _font(size: int, bold: bool = False, serif: bool = False, italic: bool = False):
    if serif:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf" if italic else "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerifBoldItalic.ttf" if italic else "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf" if bold else "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=max(8, int(size)))
        except Exception:
            pass
    return ImageFont.load_default()


def _hex(value: str, alpha: int = 255):
    value = str(value or "#000000").lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)
    except Exception:
        return (0, 0, 0, alpha)


def _fit_font(draw, text: str, max_width: int, start: int, minimum: int, *, bold=True, serif=False, italic=False):
    for size in range(int(start), int(minimum) - 1, -2):
        f = _font(size, bold=bold, serif=serif, italic=italic)
        box = draw.textbbox((0, 0), text, font=f, stroke_width=1)
        if box[2] - box[0] <= max_width:
            return f
    return _font(minimum, bold=bold, serif=serif, italic=italic)


def _wrap(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width or not current:
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
        data = []
        for r, g, b, a in logo.getdata():
            bright = max(r, g, b)
            sat = bright - min(r, g, b)
            if bright <= 25:
                na = 0
            elif bright < 95 and sat < 35:
                na = int(a * ((bright - 25) / 70.0))
            else:
                na = a
            data.append((r, g, b, max(0, min(255, na))))
        logo.putdata(data)
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)
        logo.thumbnail(max_size, Image.Resampling.LANCZOS)
        return logo
    except Exception:
        return None


def _headline_lines(title: str) -> tuple[str, str]:
    clean = re.sub(r"\([^)]*\)", "", str(title or "Produto AlphaFest"))
    clean = re.sub(r"\s+", " ", clean).strip(" -–—")
    low = clean.casefold()
    if " para " in low:
        idx = low.index(" para ")
        return clean[:idx].upper(), ("para " + clean[idx + 6:]).strip()
    words = clean.split()
    connectors = {"de", "da", "do", "das", "dos", "e", "com"}
    significant = [w for w in words if w.casefold() not in connectors]
    if len(significant) >= 3:
        return significant[0].upper(), " ".join(significant[-2:]).title()
    if len(words) >= 4:
        return " ".join(words[:2]).upper(), " ".join(words[2:]).title()
    if len(words) == 3:
        return words[0].upper(), " ".join(words[1:]).title()
    if len(words) == 2:
        return clean.upper(), ""
    return clean.upper(), ""


def _parse_benefits(description: str, fallback: Iterable[str]) -> list[str]:
    text = re.sub(r"[•✓✔|]", "\n", str(description or ""))
    text = re.sub(r"\b(?:design único|acabamento impecável|versatilidade|material|estilo|uso)\s*:\s*", "\n", text, flags=re.I)
    parts = [re.sub(r"\s+", " ", p).strip(" .,:;-") for p in re.split(r"[\n;]", text)]
    good = [p for p in parts if 4 <= len(p) <= 55]
    result: list[str] = []
    for item in good:
        if item.casefold() not in {x.casefold() for x in result}:
            result.append(item)
        if len(result) == 4:
            break
    for item in fallback:
        if len(result) == 4:
            break
        if item.casefold() not in {x.casefold() for x in result}:
            result.append(item)
    return result[:4]


def _paste_rounded(canvas: Image.Image, photo: Image.Image, box: tuple[int, int, int, int], radius: int, shadow=True):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    photo = ImageOps.fit(photo.convert("RGB"), (w, h), method=Image.Resampling.LANCZOS).convert("RGBA")
    if shadow:
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((x1 + 14, y1 + 18, x2 + 14, y2 + 18), radius=radius, fill=(0, 36, 90, 82))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    canvas.paste(photo, (x1, y1), mask)


def _draw_check(draw, cx: int, cy: int, radius: int, fill, check=(255,255,255,255), width: int = 5):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fill)
    draw.line((cx-radius//2, cy, cx-radius//8, cy+radius//3), fill=check, width=max(2, width))
    draw.line((cx-radius//8, cy+radius//3, cx+radius//2, cy-radius//3), fill=check, width=max(2, width))

def _draw_phone(draw, cx: int, cy: int, radius: int, fill, line=(255,255,255,255), width: int = 5):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fill)
    # handset vector, avoiding dependence on emoji fonts
    draw.arc((cx-radius//2, cy-radius//2, cx+radius//2, cy+radius//2), 125, 315, fill=line, width=max(3, width))
    draw.line((cx-radius//3, cy-radius//3, cx-radius//2, cy-radius//2), fill=line, width=max(3, width))
    draw.line((cx+radius//3, cy+radius//3, cx+radius//2, cy+radius//2), fill=line, width=max(3, width))

def render_template(
    image_bytes: bytes,
    size: tuple[int, int],
    *,
    template_id: str = DEFAULT_TEMPLATE,
    title: str,
    subtitle: str = "Personalizado do seu jeito",
    description: str = "",
    price: str = "",
    cta: str = "FAÇA SEU PEDIDO!",
    phone: str = "11 97294-9533",
    logo_path: str | Path | None = None,
) -> bytes:
    cfg = carregar_template(template_id)
    p = cfg["paleta"]
    W, H = size
    sx, sy = W / 1080.0, H / 1350.0
    S = lambda n: int(n * min(sx, sy))
    X = lambda n: int(n * sx)
    Y = lambda n: int(n * sy)
    blue, dark, pale, pink, yellow, textc = (_hex(p[k]) for k in ("azul", "azul_escuro", "azul_claro", "rosa", "amarelo", "texto"))
    white = (255, 255, 255, 255)

    canvas = Image.new("RGBA", (W, H), white)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Moldura líquida superior e detalhes orgânicos.
    draw.ellipse((X(-220), Y(-170), X(470), Y(170)), fill=blue)
    draw.ellipse((X(760), Y(-190), X(1310), Y(160)), fill=dark)
    draw.arc((X(-100), Y(-40), X(1180), Y(300)), 4, 176, fill=_hex("#56D6FF"), width=max(5, S(13)))
    draw.arc((X(-55), Y(-18), X(1130), Y(260)), 7, 173, fill=white, width=max(4, S(10)))
    for x, y, r, color in [(108, 198, 7, pink), (175, 160, 5, yellow), (922, 196, 7, pink), (986, 152, 5, yellow), (452, 342, 5, blue)]:
        draw.ellipse((X(x-r), Y(y-r), X(x+r), Y(y+r)), fill=color)

    # Logo realmente protagonista, sem quadro branco.
    logo = _transparent_logo(Path(logo_path or BASE_DIR / "logo.png"), (X(390), Y(260)))
    if logo:
        canvas.alpha_composite(logo, ((W - logo.width) // 2, Y(4)))

    # Título em duas linhas, como nas peças da Anna.
    line1, line2 = _headline_lines(title)
    max_title_w = X(500)
    f1 = _fit_font(draw, line1, max_title_w, S(104), S(62), bold=True)
    draw.text((X(44), Y(250)), line1, font=f1, fill=dark, stroke_width=max(1, S(1)), stroke_fill=dark)
    title_bottom = Y(250) + (draw.textbbox((0, 0), line1, font=f1)[3])
    if line2:
        f2 = _fit_font(draw, line2, max_title_w, S(74), S(44), bold=True, serif=True, italic=True)
        draw.text((X(48), title_bottom - Y(8)), line2, font=f2, fill=blue)
        title_bottom += draw.textbbox((0, 0), line2, font=f2)[3] - Y(8)

    # Faixa de chamada forte.
    subtitle_text = re.sub(r"\s+", " ", str(subtitle or "Personalizado do seu jeito")).strip()
    sf = _fit_font(draw, subtitle_text, X(480), S(31), S(22), bold=True)
    ribbon_top = max(Y(470), title_bottom + Y(12))
    draw.rounded_rectangle((X(42), ribbon_top, X(550), ribbon_top + Y(72)), radius=S(14), fill=dark)
    # pequenas pontas da faixa
    draw.polygon([(X(42), ribbon_top+Y(16)), (X(18), ribbon_top+Y(36)), (X(42), ribbon_top+Y(56))], fill=blue)
    draw.text((X(65), ribbon_top + Y(16)), subtitle_text, font=sf, fill=white)

    # Foto protagonista, maior e mais integrada.
    source = Image.open(io.BytesIO(image_bytes))
    source = ImageOps.exif_transpose(source).convert("RGB")
    photo_box = (X(575), Y(360), X(1035), Y(890))
    _paste_rounded(canvas, source, photo_box, S(34), shadow=True)
    draw.rounded_rectangle(photo_box, radius=S(34), outline=white, width=max(2, S(5)))

    # Benefícios grandes, com ícones e separadores.
    benefits = _parse_benefits(description, cfg["beneficios_padrao"])
    y = max(Y(590), ribbon_top + Y(110))
    benefit_title_font = _font(S(27), bold=True)
    benefit_detail_font = _font(S(20), bold=False)
    detail_defaults = [
        "Visual que encanta e valoriza o produto.",
        "Prático, rápido e pronto para usar.",
        "Acabamento resistente e bem produzido.",
        "Ideal para diferentes ocasiões e presentes.",
    ]
    for i, item in enumerate(benefits):
        cy = y + Y(i * 105)
        _draw_check(draw, X(77), cy + Y(29), S(29), blue, width=S(5))
        title_text = item.upper()
        tf = _fit_font(draw, title_text, X(390), S(27), S(20), bold=True)
        draw.text((X(122), cy - Y(2)), title_text, font=tf, fill=dark)
        for j, ln in enumerate(_wrap(draw, detail_defaults[i], benefit_detail_font, X(390), 2)):
            draw.text((X(122), cy + Y(32 + j * 24)), ln, font=benefit_detail_font, fill=textc)
        draw.line((X(122), cy + Y(86), X(520), cy + Y(86)), fill=_hex("#74BDF0"), width=max(1, S(2)))

    # Selo de preço/oferta com presença visual.
    if str(price).strip():
        cx, cy, rr = X(455), Y(990), S(88)
        draw.ellipse((cx-rr, cy-rr, cx+rr, cy+rr), fill=white, outline=blue, width=max(3, S(5)))
        pf = _fit_font(draw, str(price), rr*2-S(20), S(35), S(23), bold=True)
        label = _font(S(16), bold=True)
        draw.text((cx-S(53), cy-S(42)), "A PARTIR DE", font=label, fill=dark)
        bb = draw.textbbox((0, 0), str(price), font=pf)
        draw.text((cx-(bb[2]-bb[0])//2, cy-S(5)), str(price), font=pf, fill=pink)

    # CTA grande como na referência, em bloco branco sobre o rodapé azul.
    footer_top = Y(935)
    draw.rounded_rectangle((X(560), footer_top, X(1035), Y(1125)), radius=S(25), fill=white, outline=_hex("#D9ECFA"), width=max(2, S(3)))
    cta_text = str(cta or "FAÇA SEU PEDIDO!").upper()
    cf = _fit_font(draw, cta_text, X(430), S(45), S(30), bold=True)
    cb = draw.textbbox((0, 0), cta_text, font=cf)
    draw.text((X(797)-(cb[2]-cb[0])//2, Y(963)), cta_text, font=cf, fill=dark)
    phone_text = str(phone or "11 97294-9533")
    phone_font = _fit_font(draw, phone_text, X(390), S(53), S(38), bold=True)
    # ícone telefone simples
    _draw_phone(draw, X(625), Y(1058), S(35), blue, width=S(5))
    draw.text((X(680), Y(1027)), phone_text, font=phone_font, fill=dark)

    # Pincel rosa com frase curta.
    draw.rounded_rectangle((X(600), Y(1140), X(1015), Y(1215)), radius=S(15), fill=pink)
    tag = "Pequenos detalhes que fazem toda a diferença!"
    tagf = _fit_font(draw, tag, X(385), S(22), S(16), bold=True, serif=True, italic=True)
    tb = draw.textbbox((0, 0), tag, font=tagf)
    draw.text((X(807)-(tb[2]-tb[0])//2, Y(1160)), tag, font=tagf, fill=white)

    # Rodapé institucional com benefícios rápidos.
    draw.rectangle((0, Y(1250), W, H), fill=dark)
    footer_items = ["PRÁTICO", "CRIATIVO", "VALORIZA SEU PRODUTO", "AUMENTA SUAS VENDAS"]
    ff = _font(S(18), bold=True)
    positions = [55, 275, 500, 805]
    for pos, txt in zip(positions, footer_items):
        _draw_check(draw, X(pos+14), Y(1296), S(14), white, check=blue, width=S(3))
        draw.text((X(pos+38), Y(1282)), txt, font=ff, fill=white)

    output = io.BytesIO()
    canvas.convert("RGB").save(output, "PNG", optimize=True)
    return output.getvalue()
