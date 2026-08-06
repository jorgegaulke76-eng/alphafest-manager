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


def _product_profile(title: str, description: str) -> dict[str, Any]:
    """Transforma dados livres em conteúdo publicitário curto e consistente."""
    raw = re.sub(r"\s+", " ", str(title or "Produto AlphaFest")).strip()
    low = raw.casefold()
    if "leopardo" in low or "voronoi" in low:
        return {
            "title1": "LEOPARDO",
            "title2": "Voronoi",
            "subtitle": "Design moderno que transforma qualquer ambiente!",
            "benefits": [
                ("DESIGN EXCLUSIVO", "Geometria marcante e visual sofisticado."),
                ("IMPRESSÃO 3D PREMIUM", "Alta definição em cada detalhe da peça."),
                ("ACABAMENTO IMPECÁVEL", "Linhas limpas e estrutura resistente."),
                ("DECORAÇÃO ELEGANTE", "Ideal para salas, escritórios e presentes."),
                ("PEÇA SOB ENCOMENDA", "Produção personalizada pela AlphaFest."),
            ],
            "seal": "PEÇA\nEXCLUSIVA",
            "center": "Elegância,\ntecnologia e\ndesign em uma\núnica peça!",
            "pink": "Produzido com cuidado e personalidade!",
            "footer": ["EXCLUSIVO", "MODERNO", "ALTA QUALIDADE", "PRESENTE PERFEITO"],
        }
    first, second = _title_words(raw)
    parsed = _parse_benefits(description, carregar_template(DEFAULT_TEMPLATE)["beneficios_padrao"])
    descs = [
        "Valoriza o produto e chama atenção.",
        "Prático, rápido e pronto para usar.",
        "Acabamento bonito e resistente.",
        "Ideal para presentes e ocasiões especiais.",
        "Personalizado do seu jeito.",
    ]
    return {
        "title1": first,
        "title2": second,
        "subtitle": "Personalizado do seu jeito!",
        "benefits": [(_benefit_heading(x, i), descs[i]) for i, x in enumerate(parsed[:5])],
        "seal": "TESTADO E\nAPROVADO!",
        "center": "Detalhes que\nencantam e\nfazem toda a\ndiferença!",
        "pink": "Pequenos detalhes que fazem toda a diferença!",
        "footer": ["PRÁTICO", "CRIATIVO", "VALORIZA SEU PRODUTO", "AUMENTA SUAS VENDAS"],
    }


def _draw_ribbon(draw: ImageDraw.ImageDraw, box: tuple[int,int,int,int], fill, text: str, font, text_fill=(255,255,255,255)):
    x1,y1,x2,y2=box
    h=y2-y1
    draw.polygon([(x1,y1+h//5),(x1-28,y1+h//2),(x1,y2-h//5)], fill=fill)
    draw.polygon([(x2,y1+h//5),(x2+28,y1+h//2),(x2,y2-h//5)], fill=fill)
    draw.rounded_rectangle(box, radius=max(10,h//5), fill=fill)
    lines=_wrap(draw,text,font,max(20,x2-x1-30),2)
    line_h=max(22,int(getattr(font,'size',28)*1.02))
    total=len(lines)*line_h
    yy=y1+(h-total)//2
    for line in lines:
        bb=draw.textbbox((0,0),line,font=font)
        draw.text(((x1+x2-(bb[2]-bb[0]))//2,yy),line,font=font,fill=text_fill)
        yy+=line_h


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
    """Renderiza a campanha no Template Agência AlphaFest.

    O desenho nasce em uma grade quadrada de agência e é adaptado ao canal.
    A identidade, logo, tipografia e CTA permanecem fixos; produto e textos variam.
    """
    cfg = carregar_template(template_id)
    p = cfg["paleta"]
    W, H = size
    sx, sy = W / 1080.0, H / 1350.0
    scale = min(sx, sy)
    S=lambda n:max(1,int(n*scale)); X=lambda n:int(n*sx); Y=lambda n:int(n*sy)
    blue=_hex(p["azul"]); dark=_hex(p["azul_escuro"]); pale=_hex(p["azul_claro"])
    pink=_hex(p["rosa"]); yellow=_hex(p["amarelo"]); textc=_hex(p["texto"]); white=(255,255,255,255)
    profile=_product_profile(title,description)
    if subtitle and subtitle.strip() and subtitle.strip().casefold() not in {"personalizado do seu jeito","personalize seus momentos"}:
        profile["subtitle"] = re.sub(r"\s+"," ",subtitle).strip()

    canvas=Image.new("RGBA",(W,H),white)
    draw=ImageDraw.Draw(canvas,"RGBA")

    # Moldura líquida e confetes: identidade oficial AlphaFest.
    draw.rounded_rectangle((X(8),Y(8),X(1072),Y(1342)),radius=S(38),fill=white,outline=pale,width=S(4))
    draw.ellipse((X(-190),Y(-140),X(360),Y(145)),fill=blue)
    draw.ellipse((X(790),Y(-130),X(1270),Y(155)),fill=dark)
    draw.arc((X(-90),Y(-35),X(1170),Y(345)),4,176,fill=_hex("#49D4FF"),width=S(15))
    draw.arc((X(-70),Y(-10),X(1150),Y(310)),5,175,fill=white,width=S(8))
    for x,y,r,c in [(88,180,8,pink),(160,145,6,yellow),(230,186,5,blue),(845,170,7,pink),(930,145,6,yellow),(1010,185,5,blue),(490,310,5,pink),(550,325,5,blue),(430,1140,7,blue),(500,1160,6,pink)]:
        draw.ellipse((X(x-r),Y(y-r),X(x+r),Y(y+r)),fill=c)

    # Logo oficial enviado pelo usuário, sem caixa branca.
    logo=_transparent_logo(Path(logo_path or BASE_DIR/'logo.png'),(X(390),Y(245)))
    if logo:
        canvas.alpha_composite(logo,((W-logo.width)//2,Y(-2)))

    # Selo superior direito.
    scx,scy,sr=X(930),Y(205),S(92)
    draw.ellipse((scx-sr,scy-sr,scx+sr,scy+sr),fill=dark,outline=white,width=S(6))
    sf=_font(S(25),bold=True)
    lines=str(profile['seal']).split('\n')
    yy=scy-S(35)
    for line in lines:
        bb=draw.textbbox((0,0),line,font=sf); draw.text((scx-(bb[2]-bb[0])//2,yy),line,font=sf,fill=white); yy+=S(31)

    # Título principal ocupa a área dominante, como na arte da Anna.
    t1=str(profile['title1']); t2=str(profile['title2'])
    f1=_fit_font(draw,t1,X(545),S(132),S(74),bold=True,serif=True,italic=True)
    draw.text((X(38),Y(205)),t1,font=f1,fill=dark,stroke_width=S(2),stroke_fill=white)
    if t2:
        f2=_fit_font(draw,t2,X(540),S(100),S(56),bold=True,serif=True,italic=True)
        draw.text((X(54),Y(330)),t2,font=f2,fill=blue,stroke_width=S(1),stroke_fill=white)

    # Faixa azul comercial.
    ribf=_fit_font(draw,profile['subtitle'],X(500),S(34),S(23),bold=True)
    _draw_ribbon(draw,(X(40),Y(455),X(575),Y(545)),dark,profile['subtitle'],ribf)

    # Foto principal integrada e ligeiramente inclinada visualmente por sombra.
    source=ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert('RGB')
    photo_box=(X(625),Y(250),X(1040),Y(845))
    _paste_rounded(canvas,source,photo_box,S(38),shadow=True)
    draw.rounded_rectangle(photo_box,radius=S(38),outline=white,width=S(7))

    # Benefícios em coluna de agência, com cinco blocos.
    by=Y(585)
    benefits=list(profile['benefits'])[:5]
    for i,(head,desc) in enumerate(benefits):
        cy=by+Y(i*96)
        _draw_check(draw,X(72),cy+Y(24),S(27),dark,width=S(5))
        hf=_fit_font(draw,head,X(365),S(33),S(25),bold=True)
        draw.text((X(112),cy-Y(5)),head,font=hf,fill=dark)
        df=_font(S(21))
        for j,line in enumerate(_wrap(draw,desc,df,X(370),2)):
            draw.text((X(112),cy+Y(30+j*23)),line,font=df,fill=textc)
        draw.line((X(112),cy+Y(78),X(490),cy+Y(78)),fill=_hex('#69BDED'),width=S(2))

    # Selo central de mensagem.
    ccx,ccy,cr=X(520),Y(800),S(88)
    draw.ellipse((ccx-cr,ccy-cr,ccx+cr,ccy+cr),fill=white,outline=blue,width=S(4))
    cf=_font(S(24),bold=True)
    c_lines=str(profile['center']).split('\n'); yy=ccy-S(54)
    for line in c_lines:
        bb=draw.textbbox((0,0),line,font=cf); draw.text((ccx-(bb[2]-bb[0])//2,yy),line,font=cf,fill=dark); yy+=S(30)

    # Preço opcional.
    if str(price).strip():
        prx,pry,prr=X(500),Y(1080),S(68)
        draw.ellipse((prx-prr,pry-prr,prx+prr,pry+prr),fill=white,outline=blue,width=S(4))
        pf=_fit_font(draw,str(price),S(130),S(34),S(22),bold=True)
        bb=draw.textbbox((0,0),str(price),font=pf); draw.text((prx-(bb[2]-bb[0])//2,pry-S(12)),str(price),font=pf,fill=pink)

    # CTA e WhatsApp: maior impacto da metade inferior.
    cta_text=str(cta or 'FAÇA SEU PEDIDO!').upper()
    ctaf=_fit_font(draw,cta_text,X(455),S(56),S(38),bold=True)
    bb=draw.textbbox((0,0),cta_text,font=ctaf)
    draw.text((X(800)-(bb[2]-bb[0])//2,Y(900)),cta_text,font=ctaf,fill=dark)
    draw.rounded_rectangle((X(565),Y(965),X(1045),Y(1090)),radius=S(34),fill=dark)
    _draw_phone(draw,X(625),Y(1027),S(37),_hex('#1DB954'),width=S(6))
    ph=str(phone or '11 97294-9533')
    phf=_fit_font(draw,ph,X(360),S(62),S(42),bold=True)
    draw.text((X(680),Y(990)),ph,font=phf,fill=white)

    # Faixa rosa e bloco "Ideal para" usando rótulos, pois a foto varia por produto.
    draw.rounded_rectangle((X(610),Y(1110),X(1025),Y(1190)),radius=S(18),fill=pink)
    pf=_fit_font(draw,profile['pink'],X(375),S(24),S(18),bold=True,serif=True,italic=True)
    for i,line in enumerate(_wrap(draw,profile['pink'],pf,X(370),2)):
        bb=draw.textbbox((0,0),line,font=pf); draw.text((X(817)-(bb[2]-bb[0])//2,Y(1122+i*28)),line,font=pf,fill=white)

    # Rodapé oficial.
    draw.rectangle((0,Y(1245),W,H),fill=dark)
    ff=_font(S(18),bold=True)
    positions=[45,285,520,805]
    for pos,txt in zip(positions,profile['footer']):
        _draw_check(draw,X(pos+15),Y(1295),S(14),white,check=blue,width=S(3))
        draw.text((X(pos+40),Y(1282)),txt,font=ff,fill=white)

    output=io.BytesIO(); canvas.convert('RGB').save(output,'PNG',optimize=True); return output.getvalue()
