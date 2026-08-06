"""AlphaFest Marketing Template Engine.

Versão 18.1.2 — Fontes portáteis e produto integrado ao template.
A arte nasce em um canvas quadrado 1080x1080, baseado na composição aprovada
pela AlphaFest. Os canais verticais e horizontais recebem extensões decorativas,
sem reduzir o tamanho dos textos da peça principal.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from alphafest_font_manager import get_font, resolve_font_path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = "alphafest_agencia"

EMBEDDED_TEMPLATES: dict[str, dict[str, Any]] = {
    "alphafest_agencia": {
        "id": "alphafest_agencia",
        "nome": "AlphaFest Agência",
        "descricao": "Template oficial azul, branco e rosa, baseado na arte aprovada da AlphaFest.",
        "paleta": {
            "fundo": "#FFFFFF",
            "azul": "#087CE8",
            "azul_escuro": "#07349B",
            "azul_claro": "#DDF5FF",
            "rosa": "#EF2A92",
            "amarelo": "#FFD12B",
            "texto": "#102D50",
            "verde": "#20B956",
        },
    },
}


def listar_templates() -> list[dict[str, str]]:
    return [
        {"id": key, "nome": str(value.get("nome") or key), "descricao": str(value.get("descricao") or "")}
        for key, value in EMBEDDED_TEMPLATES.items()
    ]


def carregar_template(template_id: str = DEFAULT_TEMPLATE) -> dict[str, Any]:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", template_id or DEFAULT_TEMPLATE)
    cfg = EMBEDDED_TEMPLATES.get(safe) or EMBEDDED_TEMPLATES[DEFAULT_TEMPLATE]
    return {**cfg, "paleta": dict(cfg["paleta"])}


def _resolve_font_path(bold: bool = False, serif: bool = False, italic: bool = False) -> str:
    """Compatibilidade: resolve a fonte portátil fornecida pelo matplotlib."""
    return resolve_font_path(bold=bool(bold), serif=bool(serif), italic=bool(italic))


def _font(size: int, *, bold: bool = False, serif: bool = False, italic: bool = False):
    """Carrega somente fonte vetorial portátil; nunca usa bitmap minúscula."""
    return get_font(max(8, int(size)), bold=bool(bold), serif=bool(serif), italic=bool(italic))

def _hex(value: str, alpha: int = 255):
    raw = str(value or "#000000").lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    try:
        return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)
    except Exception:
        return (0, 0, 0, alpha)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, minimum: int, *, bold=True, serif=False, italic=False):
    for size in range(start, minimum - 1, -2):
        font = _font(size, bold=bold, serif=serif, italic=italic)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
        if box[2] - box[0] <= max_width:
            return font
    return _font(minimum, bold=bold, serif=serif, italic=italic)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = re.sub(r"\s+", " ", str(text or "")).strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
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


def _load_logo(path: Path, max_size: tuple[int, int]) -> Image.Image | None:
    if not path.exists():
        return None
    try:
        logo = Image.open(path).convert("RGBA")
        # O logo oficial já possui transparência. Só removemos áreas totalmente
        # pretas quando o arquivo legado tiver sido salvo sem canal alfa.
        if logo.getextrema()[3] == (255, 255):
            pixels = logo.load()
            for y in range(logo.height):
                for x in range(logo.width):
                    r, g, b, a = pixels[x, y]
                    if max(r, g, b) < 20:
                        pixels[x, y] = (r, g, b, 0)
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)
        logo.thumbnail(max_size, Image.Resampling.LANCZOS)
        return logo
    except Exception:
        return None


def _draw_check(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill, *, icon: str = "check"):
    white = (255, 255, 255, 255)
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fill)
    if icon == "star":
        # estrela simples e legível
        pts = [(cx, cy-radius+6), (cx+8, cy-7), (cx+radius-5, cy-7), (cx+12, cy+5),
               (cx+18, cy+radius-5), (cx, cy+13), (cx-18, cy+radius-5), (cx-12, cy+5),
               (cx-radius+5, cy-7), (cx-8, cy-7)]
        draw.polygon(pts, outline=white)
    elif icon == "diamond":
        draw.polygon([(cx,cy-radius+7),(cx+radius-7,cy-3),(cx,cy+radius-7),(cx-radius+7,cy-3)], outline=white)
    elif icon == "heart":
        draw.ellipse((cx-radius//2,cy-radius//3,cx,cy+radius//3), fill=white)
        draw.ellipse((cx,cy-radius//3,cx+radius//2,cy+radius//3), fill=white)
        draw.polygon([(cx-radius//2,cy),(cx+radius//2,cy),(cx,cy+radius//2)], fill=white)
    else:
        draw.line((cx-radius//2, cy, cx-radius//8, cy+radius//3), fill=white, width=5)
        draw.line((cx-radius//8, cy+radius//3, cx+radius//2, cy-radius//3), fill=white, width=5)


def _draw_phone(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill):
    white = (255,255,255,255)
    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=fill)
    draw.arc((cx-radius//2,cy-radius//2,cx+radius//2,cy+radius//2),125,315,fill=white,width=6)
    draw.line((cx-radius//3,cy-radius//3,cx-radius//2,cy-radius//2),fill=white,width=6)
    draw.line((cx+radius//3,cy+radius//3,cx+radius//2,cy+radius//2),fill=white,width=6)


def _soft_shadow(alpha: Image.Image, blur: int = 22, opacity: int = 105) -> Image.Image:
    """Cria uma sombra suave usando o canal alfa real do produto."""
    shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(max(2, blur)))
    shadow_alpha = shadow_alpha.point(lambda value: int(value * opacity / 255))
    shadow = Image.new("RGBA", alpha.size, (0, 31, 78, 0))
    shadow.putalpha(shadow_alpha)
    return shadow


def _remove_background_fallback(source: Image.Image) -> Image.Image:
    """Recorte local sem serviços externos, adequado a fundos simples.

    O algoritmo estima a cor do fundo pelas bordas, torna transparentes os
    pixels conectados a elas e suaviza o contorno. Ele é usado quando OpenCV
    não está disponível ou quando o GrabCut não produz uma máscara útil.
    """
    image = ImageOps.exif_transpose(source).convert("RGBA")
    # PNG já transparente: não destruir o recorte original.
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] < 245:
        return image

    small = image.copy()
    small.thumbnail((700, 700), Image.Resampling.LANCZOS)
    rgb = small.convert("RGB")
    w, h = rgb.size
    pixels = rgb.load()
    border = []
    step = max(1, min(w, h) // 80)
    for x in range(0, w, step):
        border.extend((pixels[x, 0], pixels[x, h - 1]))
    for y in range(0, h, step):
        border.extend((pixels[0, y], pixels[w - 1, y]))
    border.sort(key=lambda c: c[0] + c[1] + c[2])
    sample = border[len(border) // 2] if border else (255, 255, 255)

    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    visited = bytearray(w * h)
    queue = []
    for x in range(w):
        queue.append((x, 0)); queue.append((x, h - 1))
    for y in range(h):
        queue.append((0, y)); queue.append((w - 1, y))

    def similar(c):
        dr, dg, db = c[0] - sample[0], c[1] - sample[1], c[2] - sample[2]
        return dr * dr + dg * dg + db * db < 58 * 58

    head = 0
    while head < len(queue):
        x, y = queue[head]; head += 1
        idx = y * w + x
        if visited[idx]:
            continue
        visited[idx] = 1
        if not similar(pixels[x, y]):
            continue
        mp[x, y] = 0
        if x: queue.append((x - 1, y))
        if x + 1 < w: queue.append((x + 1, y))
        if y: queue.append((x, y - 1))
        if y + 1 < h: queue.append((x, y + 1))

    mask = mask.filter(ImageFilter.GaussianBlur(1.8))
    mask = mask.resize(image.size, Image.Resampling.LANCZOS)
    image.putalpha(mask)
    return image


def _remove_background(source: Image.Image) -> Image.Image:
    """Recorta o produto localmente; OpenCV é opcional e há fallback Pillow."""
    image = ImageOps.exif_transpose(source).convert("RGBA")
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] < 245:
        return image
    try:
        import cv2  # type: ignore
        import numpy as np

        rgb = np.array(image.convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        if min(w, h) < 24:
            return image
        mask = np.zeros((h, w), np.uint8)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        margin_x = max(2, int(w * 0.035))
        margin_y = max(2, int(h * 0.035))
        rect = (margin_x, margin_y, max(2, w - margin_x * 2), max(2, h - margin_y * 2))
        cv2.grabCut(bgr, mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
        binary = np.where((mask == 1) | (mask == 3), 255, 0).astype("uint8")

        # Mantém preferencialmente componentes próximos ao centro da foto.
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
        if count > 1:
            center = np.array([w / 2, h / 2])
            candidates = []
            for label in range(1, count):
                area = stats[label, cv2.CC_STAT_AREA]
                if area < w * h * 0.006:
                    continue
                distance = np.linalg.norm(centroids[label] - center)
                score = area / (1.0 + distance * 2.0)
                candidates.append((score, label))
            if candidates:
                keep = max(candidates)[1]
                binary = np.where(labels == keep, 255, 0).astype("uint8")

        coverage = float((binary > 0).mean())
        if coverage < 0.035 or coverage > 0.92:
            return _remove_background_fallback(image)
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        binary = cv2.GaussianBlur(binary, (0, 0), 1.6)
        result = image.copy()
        result.putalpha(Image.fromarray(binary, mode="L"))
        return result
    except Exception:
        return _remove_background_fallback(image)


def _trim_transparent(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image


def _paste_photo(canvas: Image.Image, source: Image.Image, box: tuple[int,int,int,int], radius: int = 28):
    """Integra o produto ao template, sem quadro ou fundo retangular."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    product = _trim_transparent(_remove_background(source))
    if not product.getbbox():
        product = ImageOps.exif_transpose(source).convert("RGBA")

    # Ocupa a área útil, preservando a forma original do produto.
    product.thumbnail((w, h), Image.Resampling.LANCZOS)
    px = x1 + (w - product.width) // 2
    py = y1 + (h - product.height) // 2

    # Sombra deslocada, usando a silhueta real; o fundo do template continua visível.
    alpha = product.getchannel("A")
    shadow = _soft_shadow(alpha, blur=max(12, int(min(product.size) * 0.045)), opacity=95)
    canvas.alpha_composite(shadow, (px + 16, py + 20))
    canvas.alpha_composite(product, (px, py))


def _product_profile(title: str, description: str, subtitle: str) -> dict[str, Any]:
    raw = re.sub(r"\([^)]*\)", " ", str(title or "Produto AlphaFest"))
    raw = re.sub(r"^[^\wÀ-ÿ]+", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    low = raw.casefold()
    if "leopardo" in low or "voronoi" in low:
        return {
            "title1": "Leopardo",
            "title2": "Voronoi",
            "subtitle": subtitle if subtitle and "personaliz" not in subtitle.casefold() else "Design moderno que transforma qualquer ambiente!",
            "benefits": [
                ("DESIGN EXCLUSIVO", "Geometria marcante que valoriza sua decoração.", "star"),
                ("IMPRESSÃO 3D PREMIUM", "Alta definição e precisão em cada detalhe.", "check"),
                ("MATERIAL DE QUALIDADE", "Estrutura resistente e acabamento durável.", "diamond"),
                ("DECORAÇÃO ELEGANTE", "Ideal para salas, escritórios e aparadores.", "check"),
                ("PRESENTE ESPECIAL", "Uma peça sofisticada para surpreender.", "heart"),
            ],
            "center": "Elegância,\ntecnologia e\ndesign em uma\núnica peça!",
            "badge": "PEÇA\nEXCLUSIVA",
            "pink": "Produção personalizada sob encomenda!",
            "footer": ["EXCLUSIVO", "MODERNO", "ALTA QUALIDADE", "PRESENTE PERFEITO"],
        }

    words = raw.split()
    if " para " in raw.casefold():
        idx = raw.casefold().index(" para ")
        t1 = raw[:idx]
        t2 = "para " + raw[idx+6:]
    elif len(words) >= 3:
        t1 = " ".join(words[:2])
        t2 = " ".join(words[2:])
    elif len(words) == 2:
        t1,t2 = words
    else:
        t1,t2 = raw,""
    clean_desc = re.sub(r"\s+", " ", description or "").strip()
    generic = [
        ("DESIGN EXCLUSIVO", "Criado para encantar e valorizar seu produto.", "star"),
        ("FÁCIL DE USAR", "Prático, rápido e pronto para aproveitar.", "check"),
        ("MATERIAL DE QUALIDADE", "Resistente, durável e bem-acabado.", "diamond"),
        ("PERSONALIZADO", "Produzido conforme a sua necessidade.", "check"),
        ("MÚLTIPLOS USOS", clean_desc[:58] or "Ideal para diferentes ocasiões.", "heart"),
    ]
    return {
        "title1": t1,
        "title2": t2,
        "subtitle": subtitle or "Personalizado do seu jeito!",
        "benefits": generic,
        "center": "Detalhes que\nencantam e\nfazem toda a\ndiferença!",
        "badge": "TESTADO E\nAPROVADO!",
        "pink": "Pequenos detalhes que fazem toda a diferença!",
        "footer": ["PRÁTICO", "CRIATIVO", "VALORIZA SEU PRODUTO", "AUMENTA SUAS VENDAS"],
    }


def _draw_liquid_corners(draw: ImageDraw.ImageDraw, blue, dark, pink, yellow):
    # Ondas e respingos 3D simulados em vetores sólidos, com pequenos brilhos.
    draw.pieslice((-150,-150,430,290),0,180,fill=blue)
    draw.pieslice((760,-160,1230,270),0,180,fill=dark)
    draw.arc((-120,-95,1190,330),5,175,fill=_hex("#55D8FF"),width=13)
    for cx,cy,r,color in [(75,165,9,pink),(130,125,7,yellow),(205,172,6,blue),(870,150,8,pink),(945,112,7,yellow),(1015,170,6,blue)]:
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=color)
    # gotas inferiores decorativas
    for cx,cy,rx,ry,color in [(455,790,24,10,blue),(500,815,14,25,pink),(540,790,20,9,blue)]:
        draw.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=color)


def _render_square(image_bytes: bytes, *, title: str, subtitle: str, description: str, price: str, cta: str, phone: str, logo_path: Path, cfg: dict[str,Any]) -> Image.Image:
    p = cfg["paleta"]
    blue,dark,pale,pink,yellow,textc,green = (_hex(p[k]) for k in ("azul","azul_escuro","azul_claro","rosa","amarelo","texto","verde"))
    white=(255,255,255,255)
    profile = _product_profile(title,description,subtitle)
    canvas=Image.new("RGBA",(1080,1080),white)
    draw=ImageDraw.Draw(canvas,"RGBA")
    _draw_liquid_corners(draw,blue,dark,pink,yellow)

    logo=_load_logo(logo_path,(270,220))
    if logo:
        canvas.alpha_composite(logo,((1080-logo.width)//2,-5))

    # Selo superior direito.
    sx,sy,sr=930,155,78
    draw.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=dark,outline=white,width=6)
    sf=_font(22,bold=True)
    yy=sy-28
    for line in profile["badge"].split("\n"):
        bb=draw.textbbox((0,0),line,font=sf)
        draw.text((sx-(bb[2]-bb[0])//2,yy),line,font=sf,fill=white)
        yy+=28

    # Título gigante — principal diferença da versão anterior.
    t1,t2=profile["title1"],profile["title2"]
    f1=_fit_font(draw,t1,600,145,82,bold=True,serif=True,italic=True)
    draw.text((32,165),t1,font=f1,fill=dark,stroke_width=2,stroke_fill=white)
    if t2:
        f2=_fit_font(draw,t2,580,96,58,bold=True,serif=True,italic=True)
        draw.text((54,290),t2,font=f2,fill=blue,stroke_width=1,stroke_fill=white)

    # Faixa azul abaixo do título.
    ribbon=(40,395,580,475)
    draw.polygon([(40,410),(12,435),(40,462)],fill=dark)
    draw.polygon([(580,410),(608,435),(580,462)],fill=dark)
    draw.rounded_rectangle(ribbon,radius=14,fill=dark)
    rf=_fit_font(draw,profile["subtitle"],500,31,22,bold=True)
    lines=_wrap(draw,profile["subtitle"],rf,500,2)
    yy=408 if len(lines)==2 else 422
    for line in lines:
        bb=draw.textbbox((0,0),line,font=rf)
        draw.text((310-(bb[2]-bb[0])//2,yy),line,font=rf,fill=white)
        yy+=31

    # Foto protagonista à direita.
    source=Image.open(io.BytesIO(image_bytes)).convert("RGB")
    _paste_photo(canvas,source,(585,190,1065,735),32)

    # Benefícios à esquerda.
    by=505
    for i,(head,desc,icon) in enumerate(profile["benefits"][:5]):
        cy=by+i*83
        _draw_check(draw,70,cy+22,25,dark,icon=icon)
        hf=_fit_font(draw,head,330,27,21,bold=True)
        draw.text((108,cy-3),head,font=hf,fill=dark)
        df=_font(18)
        for j,line in enumerate(_wrap(draw,desc,df,340,2)):
            draw.text((108,cy+27+j*20),line,font=df,fill=textc)
        draw.line((108,cy+70,435,cy+70),fill=_hex("#70BDEB"),width=2)

    # Selo central.
    cx,cy,cr=535,680,82
    draw.ellipse((cx-cr,cy-cr,cx+cr,cy+cr),fill=white,outline=blue,width=4)
    cf=_font(22,bold=True)
    yy=cy-52
    for line in profile["center"].split("\n"):
        bb=draw.textbbox((0,0),line,font=cf)
        draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=cf,fill=dark)
        yy+=27

    # CTA grande e WhatsApp.
    cta_text=(cta or "FAÇA SEU PEDIDO!").upper()
    ctaf=_fit_font(draw,cta_text,430,48,34,bold=True)
    bb=draw.textbbox((0,0),cta_text,font=ctaf)
    draw.text((830-(bb[2]-bb[0])//2,710),cta_text,font=ctaf,fill=dark)
    draw.rounded_rectangle((610,770,1045,875),radius=35,fill=dark)
    _draw_phone(draw,665,822,34,green)
    phf=_fit_font(draw,phone or "11 97294-9533",330,52,37,bold=True)
    draw.text((715,790),phone or "11 97294-9533",font=phf,fill=white)

    # Faixa rosa.
    draw.rounded_rectangle((625,890,1030,960),radius=16,fill=pink)
    pf=_fit_font(draw,profile["pink"],365,24,18,bold=True,serif=True,italic=True)
    lines=_wrap(draw,profile["pink"],pf,365,2)
    yy=900 if len(lines)==2 else 915
    for line in lines:
        bb=draw.textbbox((0,0),line,font=pf)
        draw.text((827-(bb[2]-bb[0])//2,yy),line,font=pf,fill=white)
        yy+=27

    # Preço opcional, sem roubar o CTA.
    if price.strip():
        draw.ellipse((475,835,585,945),fill=white,outline=blue,width=4)
        prf=_fit_font(draw,price,95,30,20,bold=True)
        bb=draw.textbbox((0,0),price,font=prf)
        draw.text((530-(bb[2]-bb[0])//2,875),price,font=prf,fill=pink)

    # Rodapé oficial.
    draw.rectangle((0,995,1080,1080),fill=dark)
    ff=_font(17,bold=True)
    positions=[35,280,520,800]
    for x,label in zip(positions,profile["footer"]):
        _draw_check(draw,x+18,1035,14,white)
        draw.text((x+42,1023),label,font=ff,fill=white)

    return canvas


def _adapt_channel(square: Image.Image, size: tuple[int,int], cfg: dict[str,Any]) -> Image.Image:
    W,H=size
    if (W,H)==(1080,1080):
        return square
    p=cfg["paleta"]
    blue,dark,pink,yellow=(_hex(p[k]) for k in ("azul","azul_escuro","rosa","amarelo"))
    # Mantemos a peça quadrada em tamanho máximo possível para não diminuir a
    # tipografia. O espaço excedente recebe continuação da identidade visual.
    if H>W:
        canvas=Image.new("RGBA",(W,H),(255,255,255,255))
        d=ImageDraw.Draw(canvas,"RGBA")
        d.rectangle((0,0,W,max(0,(H-W)//2)),fill=dark)
        d.rectangle((0,H-(H-W)//2,W,H),fill=dark)
        for x,y,r,c in [(80,70,8,pink),(180,110,6,yellow),(900,75,7,pink),(980,120,6,blue)]:
            d.ellipse((x-r,y-r,x+r,y+r),fill=c)
        y=(H-W)//2
        canvas.alpha_composite(square,(0,y))
        return canvas
    # Horizontal: centraliza a peça e usa fundo azul nas laterais.
    canvas=Image.new("RGBA",(W,H),dark)
    fitted=ImageOps.contain(square,(H,H),Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted,((W-fitted.width)//2,(H-fitted.height)//2))
    return canvas


def render_template(
    image_bytes: bytes,
    size: tuple[int,int],
    *,
    template_id: str=DEFAULT_TEMPLATE,
    title: str,
    subtitle: str="",
    description: str="",
    price: str="",
    cta: str="FAÇA SEU PEDIDO!",
    phone: str="11 97294-9533",
    logo_path: str|Path|None=None,
) -> bytes:
    cfg=carregar_template(template_id)
    square=_render_square(
        image_bytes,
        title=title,
        subtitle=subtitle,
        description=description,
        price=price,
        cta=cta,
        phone=phone,
        logo_path=Path(logo_path or BASE_DIR/"logo.png"),
        cfg=cfg,
    )
    final=_adapt_channel(square,size,cfg)
    output=io.BytesIO()
    final.convert("RGB").save(output,"PNG",optimize=True)
    return output.getvalue()
