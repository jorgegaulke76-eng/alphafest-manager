"""Engine de templates visuais do Alpha Marketing Studio.

Versão 16.1.0: Alpha Designer Engine v2, com hierarquia publicitária
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


def _benefit_heading(text: str, index: int) -> str:
    """Resume textos extensos em títulos publicitários curtos."""
    value = re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")
    low = value.casefold()
    rules = [
        (("voronoi", "geométrica", "geometrica"), "ESTILO VORONOI"),
        (("decor", "interior", "ambiente"), "DECORAÇÃO ELEGANTE"),
        (("acabamento", "resistente", "qualidade"), "ACABAMENTO PREMIUM"),
        (("exclusivo", "único", "unico", "personal"), "DESIGN EXCLUSIVO"),
        (("presente", "ocasi"), "PRESENTE ESPECIAL"),
        (("prático", "pratico", "fácil", "facil"), "FÁCIL DE USAR"),
    ]
    for keys, label in rules:
        if any(k in low for k in keys):
            return label
    words = [w for w in value.split() if len(w) > 2][:3]
    return (" ".join(words) or f"BENEFÍCIO {index + 1}").upper()


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

def _draw_splash(draw: ImageDraw.ImageDraw, cx: int, cy: int, rx: int, ry: int, fill):
    """Desenha uma mancha orgânica simples, leve e reutilizável."""
    draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=fill)
    for ox, oy, rr in [(-rx, -ry//4, ry//3), (rx, -ry//5, ry//3), (-rx//2, ry, ry//4), (rx//2, ry, ry//4)]:
        draw.ellipse((cx+ox-rr, cy+oy-rr, cx+ox+rr, cy+oy+rr), fill=fill)


def _title_words(title: str) -> tuple[str, str]:
    """Converte nomes longos em duas linhas publicitárias de alto impacto."""
    raw = str(title or "Produto AlphaFest")
    parenthetical = " ".join(re.findall(r"\(([^)]*)\)", raw))
    clean = re.sub(r"\([^)]*\)", " ", raw)
    clean = re.sub(r"^[^\wÀ-ÿ]+", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" -–—")
    words = clean.split()
    if not words:
        return "PRODUTO", "ALPHAFEST"

    low = [w.casefold() for w in words]
    if "para" in low:
        idx = low.index("para")
        first = " ".join(words[:idx]).upper() or words[0].upper()
        second = "para " + " ".join(words[idx + 1:])
        return first, second.strip().title().replace("Para ", "para ", 1)

    stop = {"de", "da", "do", "das", "dos", "e", "com", "estilo", "modelo"}
    meaningful = [w for w in words if w.casefold() not in stop]
    if len(meaningful) >= 3:
        tail = [meaningful[-1]]
        if parenthetical:
            extra = [w for w in parenthetical.split() if w.casefold() not in stop]
            if extra:
                tail.append(extra[-1])
        elif len(meaningful) >= 4:
            tail.insert(0, meaningful[-2])
        return meaningful[0].upper(), " ".join(tail).title()
    if len(meaningful) == 2:
        return meaningful[0].upper(), meaningful[1].title()
    if len(words) >= 2:
        return words[0].upper(), " ".join(words[1:3]).title()
    return words[0].upper(), ""


def _title_block(draw: ImageDraw.ImageDraw, title: str, box: tuple[int, int, int, int], dark, blue):
    """Título publicitário grande, com leitura imediata mesmo em celular."""
    x1, y1, x2, y2 = box
    first, second = _title_words(title)
    max_w = x2 - x1

    f1 = _fit_font(draw, first, max_w, 162, 96, bold=True)
    b1 = draw.textbbox((0, 0), first, font=f1, stroke_width=2)
    draw.text((x1, y1), first, font=f1, fill=dark, stroke_width=2, stroke_fill=(255, 255, 255, 235))
    y = y1 + (b1[3] - b1[1]) - 4

    if second:
        f2 = _fit_font(draw, second, max_w - 8, 92, 56, bold=True, serif=True, italic=True)
        draw.text((x1 + 6, y), second, font=f2, fill=blue, stroke_width=1, stroke_fill=(255,255,255,220))
        b2 = draw.textbbox((0, 0), second, font=f2, stroke_width=1)
        y += (b2[3] - b2[1]) + 6
    return min(y, y2)


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
    """Renderiza a peça completa no Alpha Designer Engine v2.

    A composição usa um canvas base 1080x1350 e é escalada para todos os
    formatos. O template prioriza leitura no celular: título, foto e contato.
    """
    cfg = carregar_template(template_id)
    p = cfg["paleta"]
    W, H = size
    sx, sy = W / 1080.0, H / 1350.0
    scale = min(sx, sy)
    S = lambda n: max(1, int(n * scale))
    X = lambda n: int(n * sx)
    Y = lambda n: int(n * sy)

    blue = _hex(p["azul"])
    dark = _hex(p["azul_escuro"])
    pale = _hex(p["azul_claro"])
    pink = _hex(p["rosa"])
    yellow = _hex(p["amarelo"])
    textc = _hex(p["texto"])
    white = (255, 255, 255, 255)

    canvas = Image.new("RGBA", (W, H), white)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Fundo com moldura líquida AlphaFest, sem ocupar a área útil.
    draw.rounded_rectangle((X(10), Y(10), X(1070), Y(1340)), radius=S(36), fill=white, outline=pale, width=S(4))
    _draw_splash(draw, X(160), Y(26), X(280), Y(115), blue)
    _draw_splash(draw, X(925), Y(15), X(250), Y(105), dark)
    draw.arc((X(-80), Y(-25), X(1160), Y(330)), 8, 172, fill=_hex("#52D6FF"), width=S(14))
    draw.arc((X(-55), Y(-5), X(1135), Y(290)), 8, 172, fill=white, width=S(8))

    # Confetes discretos, mantendo o DNA da referência.
    for x, y, r, color in [
        (95, 205, 8, pink), (160, 165, 6, yellow), (225, 215, 5, blue),
        (875, 195, 7, pink), (945, 160, 6, yellow), (1005, 215, 5, blue),
        (515, 318, 5, blue), (560, 335, 5, pink),
    ]:
        draw.ellipse((X(x-r), Y(y-r), X(x+r), Y(y+r)), fill=color)

    # Logo grande, integrado ao splash superior.
    logo = _transparent_logo(Path(logo_path or BASE_DIR / "logo.png"), (X(470), Y(285)))
    if logo:
        canvas.alpha_composite(logo, ((W - logo.width) // 2, Y(-8)))

    # Título protagonista: ocupa a maior área de leitura da peça.
    title_bottom = _title_block(draw, title, (X(45), Y(205), X(610), Y(500)), dark, blue)

    # Faixa promocional forte.
    subtitle_text = re.sub(r"\s+", " ", str(subtitle or "Personalizado do seu jeito")).strip()
    ribbon_y = max(Y(465), title_bottom + Y(8))
    draw.polygon([(X(34), ribbon_y+Y(13)), (X(8), ribbon_y+Y(43)), (X(34), ribbon_y+Y(72))], fill=blue)
    draw.rounded_rectangle((X(34), ribbon_y, X(590), ribbon_y+Y(86)), radius=S(18), fill=dark)
    sf = _fit_font(draw, subtitle_text, X(505), S(36), S(25), bold=True)
    for i, line in enumerate(_wrap(draw, subtitle_text, sf, X(505), 2)):
        bb = draw.textbbox((0,0), line, font=sf)
        draw.text((X(312)-(bb[2]-bb[0])//2, ribbon_y+Y(14+i*34)), line, font=sf, fill=white)

    # Fotografia invade a composição e domina o lado direito.
    source = Image.open(io.BytesIO(image_bytes))
    source = ImageOps.exif_transpose(source).convert("RGB")
    photo_box = (X(548), Y(315), X(1044), Y(930))
    _paste_rounded(canvas, source, photo_box, S(38), shadow=True)
    draw.rounded_rectangle(photo_box, radius=S(38), outline=white, width=S(7))

    # Selo superior direito, como elemento publicitário real.
    seal_cx, seal_cy, seal_r = X(940), Y(252), S(88)
    draw.ellipse((seal_cx-seal_r, seal_cy-seal_r, seal_cx+seal_r, seal_cy+seal_r), fill=dark, outline=white, width=S(5))
    seal_font = _font(S(24), bold=True)
    for idx, txt in enumerate(["TESTADO E", "APROVADO!"]):
        bb = draw.textbbox((0,0), txt, font=seal_font)
        draw.text((seal_cx-(bb[2]-bb[0])//2, seal_cy-S(31)+idx*S(29)), txt, font=seal_font, fill=white)

    # Benefícios visíveis e com hierarquia, no estilo da referência.
    benefits = _parse_benefits(description, cfg["beneficios_padrao"])
    benefit_y = max(Y(610), ribbon_y+Y(112))
    details = [
        "Valoriza o produto e chama atenção.",
        "Prático, rápido e pronto para usar.",
        "Acabamento bonito e resistente.",
        "Ideal para presentes e ocasiões especiais.",
    ]
    for i, item in enumerate(benefits):
        cy = benefit_y + Y(i*112)
        icon_x = X(78)
        _draw_check(draw, icon_x, cy+Y(28), S(30), dark, width=S(5))
        heading = _benefit_heading(item, i)
        tf = _fit_font(draw, heading, X(395), S(36), S(28), bold=True)
        draw.text((X(125), cy-Y(4)), heading, font=tf, fill=dark)
        df = _font(S(24), bold=False)
        for j, line in enumerate(_wrap(draw, details[i], df, X(405), 2)):
            draw.text((X(125), cy+Y(34+j*25)), line, font=df, fill=textc)
        draw.line((X(125), cy+Y(91), X(535), cy+Y(91)), fill=_hex("#78BFEF"), width=S(2))

    # Preço opcional em selo, sem competir com o WhatsApp.
    if str(price).strip():
        cx, cy, rr = X(455), Y(1040), S(90)
        draw.ellipse((cx-rr, cy-rr, cx+rr, cy+rr), fill=white, outline=blue, width=S(5))
        label = _font(S(17), bold=True)
        draw.text((cx-S(52), cy-S(47)), "A PARTIR DE", font=label, fill=dark)
        pf = _fit_font(draw, str(price), rr*2-S(18), S(39), S(25), bold=True)
        bb = draw.textbbox((0,0), str(price), font=pf)
        draw.text((cx-(bb[2]-bb[0])//2, cy-S(7)), str(price), font=pf, fill=pink)

    # CTA é o segundo protagonista da peça.
    cta_text = str(cta or "FAÇA SEU PEDIDO!").upper()
    cf = _fit_font(draw, cta_text, X(450), S(62), S(42), bold=True)
    cb = draw.textbbox((0,0), cta_text, font=cf)
    draw.text((X(805)-(cb[2]-cb[0])//2, Y(950)), cta_text, font=cf, fill=dark)

    # Bloco WhatsApp grande, com alto contraste.
    draw.rounded_rectangle((X(548), Y(1010), X(1042), Y(1145)), radius=S(32), fill=dark)
    _draw_phone(draw, X(625), Y(1075), S(38), blue, width=S(6))
    phone_text = str(phone or "11 97294-9533")
    phone_font = _fit_font(draw, phone_text, X(365), S(66), S(46), bold=True)
    draw.text((X(680), Y(1037)), phone_text, font=phone_font, fill=white)

    # Faixa rosa e rodapé informativo.
    draw.rounded_rectangle((X(605), Y(1162), X(1018), Y(1234)), radius=S(15), fill=pink)
    tag_lines = ["Pequenos detalhes que", "fazem toda a diferença!"]
    tagf = _font(S(19), bold=True, serif=True, italic=True)
    for i, tag in enumerate(tag_lines):
        tb = draw.textbbox((0,0), tag, font=tagf)
        draw.text((X(811)-(tb[2]-tb[0])//2, Y(1172+i*27)), tag, font=tagf, fill=white)

    draw.rectangle((0, Y(1250), W, H), fill=dark)
    footer_items = ["PRÁTICO", "CRIATIVO", "VALORIZA SEU PRODUTO", "AUMENTA SUAS VENDAS"]
    ff = _font(S(19), bold=True)
    positions = [48, 270, 500, 805]
    for pos, txt in zip(positions, footer_items):
        _draw_check(draw, X(pos+15), Y(1297), S(14), white, check=blue, width=S(3))
        draw.text((X(pos+40), Y(1283)), txt, font=ff, fill=white)

    output = io.BytesIO()
    canvas.convert("RGB").save(output, "PNG", optimize=True)
    return output.getvalue()
