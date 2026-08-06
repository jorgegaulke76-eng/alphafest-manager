"""AlphaFest Marketing Template Engine.

Versão 19.0.1 — Hotfix photo_mode e template padrão AlphaFest Agência — Padrão Anna.
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
DEFAULT_TEMPLATE = "splash_premium_anna"

EMBEDDED_TEMPLATES: dict[str, dict[str, Any]] = {
    "splash_premium_anna": {
        "id": "splash_premium_anna",
        "nome": "Splash Premium AlphaFest — Padrão Anna ⭐",
        "descricao": "Modelo oficial com título gigante, produto protagonista, benefícios, selo, aplicações e CTA forte.",
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
    "alphafest_agencia_anna": {
        "id": "alphafest_agencia_anna",
        "nome": "AlphaFest Agência — Padrão Anna ⭐",
        "descricao": "Template oficial inspirado na composição aprovada: título grande, benefícios à esquerda, produto protagonista, CTA forte e rodapé equilibrado.",
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
    # Compatibilidade com campanhas salvas antes da versão 19.0.1.
    if safe in {"alphafest_agencia", "alphafest_agencia_anna"}:
        safe = "splash_premium_anna"
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


def _shade(value: str, factor: float) -> str:
    rgba = _hex(value)
    factor = max(0.0, min(2.0, float(factor)))
    rgb = tuple(max(0, min(255, int(channel * factor))) for channel in rgba[:3])
    return "#%02X%02X%02X" % rgb


def _template_palette_from_override(cfg: dict[str, Any], override: dict[str, str] | None) -> dict[str, str]:
    """Resolve a paleta geral e as cores opcionais de cada componente."""
    p = dict(cfg["paleta"])
    if not override:
        return p
    primary = override.get("primary", p["azul_escuro"])
    secondary = override.get("secondary", p["azul"])
    accent = override.get("accent", p["rosa"])
    background = override.get("background", p["fundo"])
    text = override.get("text", p["texto"])
    metallic = override.get("metallic", p["amarelo"])
    p.update({
        "fundo": background,
        "azul": secondary,
        "azul_escuro": primary,
        "azul_claro": _shade(secondary, 1.35),
        "rosa": accent,
        "amarelo": metallic,
        "texto": text,
        # Cores por elemento. Quando ausentes, seguem a paleta principal.
        "cor_titulo": override.get("title_color", primary),
        "cor_titulo_secundario": override.get("title_secondary_color", secondary),
        "cor_banner": override.get("banner_color", primary),
        "cor_beneficios": override.get("benefits_color", primary),
        "cor_selo": override.get("seal_color", secondary),
        "cor_preco": override.get("price_color", metallic),
        "cor_preco_fundo": override.get("price_background", primary),
        "cor_cta": override.get("cta_color", primary),
        "cor_cta_texto": override.get("cta_text_color", "#FFFFFF"),
        "cor_rodape": override.get("footer_color", primary),
        "cor_rodape_texto": override.get("footer_text_color", "#FFFFFF"),
    })
    return p


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


def _draw_whatsapp(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill):
    """Desenha um ícone inspirado no WhatsApp: balão branco + telefone."""
    white = (255, 255, 255, 255)
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fill)
    bubble_r = int(radius * .66)
    draw.ellipse((cx-bubble_r, cy-bubble_r, cx+bubble_r, cy+bubble_r), outline=white, width=max(3, radius//7))
    draw.polygon([(cx-int(radius*.45), cy+int(radius*.42)), (cx-int(radius*.62), cy+int(radius*.67)), (cx-int(radius*.20), cy+int(radius*.55))], fill=white)
    draw.arc((cx-int(radius*.38), cy-int(radius*.38), cx+int(radius*.38), cy+int(radius*.38)), 125, 315, fill=white, width=max(4, radius//6))
    draw.line((cx-int(radius*.27), cy-int(radius*.27), cx-int(radius*.39), cy-int(radius*.39)), fill=white, width=max(4, radius//6))
    draw.line((cx+int(radius*.27), cy+int(radius*.27), cx+int(radius*.39), cy+int(radius*.39)), fill=white, width=max(4, radius//6))


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


def _paste_photo(canvas: Image.Image, source: Image.Image, box: tuple[int,int,int,int], radius: int = 28, *, mode: str = "auto", product_title: str = ""):
    """Posiciona a foto sem deformar e escolhe o tratamento adequado.

    ``auto`` preserva fotos de balões e produtos com cenário; nos demais casos,
    tenta remover o fundo. ``preservar`` mantém a foto inteira e ``recortar``
    força o recorte do produto.
    """
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    original = ImageOps.exif_transpose(source).convert("RGBA")
    title_low = str(product_title or "").casefold()
    preserve_auto = any(k in title_low for k in ("balão", "balao", "painel", "cenário", "cenario", "decoração completa"))
    preserve = mode == "preservar" or (mode == "auto" and preserve_auto)

    if preserve:
        # Foto inteira, sem esticar. Fundo suavemente arredondado para fotos de ambiente.
        photo = ImageOps.contain(original, (w, h), Image.Resampling.LANCZOS)
        px = x1 + (w - photo.width) // 2
        py = y1 + (h - photo.height) // 2
        mask = Image.new("L", photo.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, photo.width, photo.height), radius=min(radius, max(8, min(photo.size)//8)), fill=255)
        shadow_mask = mask.filter(ImageFilter.GaussianBlur(16))
        shadow = Image.new("RGBA", photo.size, (0, 35, 80, 0)); shadow.putalpha(shadow_mask.point(lambda v: int(v*.32)))
        canvas.alpha_composite(shadow, (px+10, py+14))
        canvas.paste(photo, (px, py), mask)
        return

    product = _trim_transparent(_remove_background(original) if mode in {"auto", "recortar"} else original)
    if not product.getbbox():
        product = original
    product.thumbnail((w, h), Image.Resampling.LANCZOS)
    px = x1 + (w - product.width) // 2
    py = y1 + (h - product.height) // 2
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

    if any(k in low for k in ("carimbo", "carimbos", "doces", "brigadeiro")):
        return {
            "title1": "Carimbos",
            "title2": "para Doces",
            "subtitle": subtitle or "Transforme seus doces em pequenas obras de arte!",
            "benefits": [
                ("DESIGN EXCLUSIVO", "Desenhos lindos que encantam e valorizam seus doces.", "star"),
                ("FÁCIL DE USAR", "É só pressionar e pronto! Prático, rápido e perfeito.", "check"),
                ("MATERIAL DE QUALIDADE", "Resistente, durável e fácil de limpar. Feito para durar!", "diamond"),
                ("SEGURO E CONFIÁVEL", "Material atóxico e próprio para uso em alimentos.", "leaf"),
                ("MÚLTIPLOS USOS", "Ideal para brigadeiros, doces finos, biscoitos e pasta americana.", "heart"),
            ],
            "center": "Deixe seus\nbrigadeiros,\ndoces e\nconfeitados ainda\nmais irresistíveis!",
            "badge": "TESTADO E\nAPROVADO!",
            "pink": "Pequenos detalhes que fazem toda a diferença!",
            "footer": ["PRÁTICO", "CRIATIVO", "VALORIZA SEUS DOCES", "AUMENTA SUAS VENDAS"],
            "applications": ["Brigadeiros", "Doces Finos", "Biscoitos", "Pasta Americana"],
        }

    if any(k in low for k in ("balão", "balao", "balon", "cake")):
        return {
            "title1": "Balão",
            "title2": "Cake Personalizado",
            "subtitle": subtitle or "Um detalhe especial para deixar sua festa inesquecível!",
            "benefits": [
                ("DESIGN EXCLUSIVO", "Criado especialmente para combinar com o tema da sua festa.", "star"),
                ("PERSONALIZAÇÃO TOTAL", "Nome, idade, cores e elementos escolhidos por você.", "check"),
                ("ACABAMENTO PREMIUM", "Impressão nítida, cores vivas e montagem cuidadosa.", "diamond"),
                ("PRONTO PARA USAR", "Chega preparado para completar a decoração da sua mesa.", "check"),
                ("FESTA INESQUECÍVEL", "Um destaque criativo para fotos e momentos especiais.", "heart"),
            ],
            "center": "Personalize\ncom o tema,\nnome e cores\nda sua festa!",
            "badge": "FEITO\nSOB MEDIDA",
            "pink": "Produção personalizada sob encomenda!",
            "footer": ["PERSONALIZADO", "CRIATIVO", "PRONTO PARA USAR", "FEITO COM CARINHO"],
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


def _draw_application_strip(canvas: Image.Image, source: Image.Image, labels: list[str], *, y: int, blue, dark, white):
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((28, y, 560, y + 132), radius=20, fill=(255,255,255,245), outline=blue, width=2)
    draw.polygon([(28,y+18),(12,y+36),(28,y+54)], fill=dark)
    draw.rounded_rectangle((28,y-15,190,y+24), radius=10, fill=blue)
    font = _font(19, bold=True)
    draw.text((52,y-10), "Ideal para:", font=font, fill=white)
    thumb = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), (90,90), method=Image.Resampling.LANCZOS)
    for i, label in enumerate(labels[:4]):
        cx = 88 + i*122
        mask = Image.new("L", (90,90), 0)
        ImageDraw.Draw(mask).ellipse((0,0,89,89), fill=255)
        canvas.paste(thumb.convert("RGBA"), (cx-45,y+27), mask)
        draw.ellipse((cx-47,y+25,cx+47,y+119), outline=blue, width=3)
        lf = _fit_font(draw, label, 108, 15, 11, bold=True)
        lines = _wrap(draw, label, lf, 108, 2)
        yy = y+113
        for line in lines:
            bb=draw.textbbox((0,0),line,font=lf)
            draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=lf,fill=dark)
            yy += 14



def _default_applications(profile: dict[str, Any], title: str) -> list[str]:
    apps = list(profile.get("applications") or [])
    if apps:
        return apps[:4]
    low = str(title or "").casefold()
    if any(k in low for k in ("balão", "balao", "cake")):
        return ["Aniversários", "Mesas", "Presentes", "Festas"]
    if any(k in low for k in ("papel arroz", "papel de arroz")):
        return ["Bolos", "Doces", "Biscoitos", "Drinks"]
    if any(k in low for k in ("topo", "topper")):
        return ["Bolos", "Mesas", "Fotos", "Festas"]
    if any(k in low for k in ("leopardo", "voronoi", "escultura")):
        return ["Salas", "Escritórios", "Presentes", "Decoração"]
    return ["Festas", "Presentes", "Decoração", "Momentos"]


def _render_splash_premium_square(image_bytes: bytes, *, title: str, subtitle: str, description: str, price: str, cta: str, phone: str, logo_path: Path, cfg: dict[str,Any], palette_override: dict[str,str] | None = None, photo_mode: str = "auto") -> Image.Image:
    """Renderizador próprio do Splash Premium — não reutiliza o layout legado."""
    p = _template_palette_from_override(cfg, palette_override)
    blue,dark,pink,yellow,textc,green = (_hex(p[k]) for k in ("azul","azul_escuro","rosa","amarelo","texto","verde"))
    title_color=_hex(p.get("cor_titulo", p["azul_escuro"]))
    title2_color=_hex(p.get("cor_titulo_secundario", p["azul"]))
    banner_color=_hex(p.get("cor_banner", p["azul_escuro"]))
    benefits_color=_hex(p.get("cor_beneficios", p["azul_escuro"]))
    seal_color=_hex(p.get("cor_selo", p["azul"]))
    cta_color=_hex(p.get("cor_cta", p["azul_escuro"]))
    cta_text_color=_hex(p.get("cor_cta_texto", "#FFFFFF"))
    footer_color=_hex(p.get("cor_rodape", p["azul_escuro"]))
    footer_text_color=_hex(p.get("cor_rodape_texto", "#FFFFFF"))
    white=(255,255,255,255)
    profile=_product_profile(title, description, subtitle)
    canvas=Image.new("RGBA",(1080,1080),_hex(p["fundo"]))
    draw=ImageDraw.Draw(canvas,"RGBA")

    # Moldura splash mais próxima da referência: ondas largas, brilhos e confetes.
    draw.pieslice((-170,-220,470,245),0,180,fill=blue)
    draw.pieslice((760,-210,1250,235),0,180,fill=dark)
    draw.arc((-130,-80,1200,330),8,172,fill=_hex("#57D9FF"),width=12)
    for cx,cy,r,c in [(76,142,9,pink),(144,102,7,yellow),(226,150,5,blue),(845,135,7,pink),(968,98,7,yellow),(1025,157,6,blue),(520,105,5,pink),(575,132,4,yellow)]:
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=c)

    logo=_load_logo(logo_path,(390,285))
    if logo:
        canvas.alpha_composite(logo,((1080-logo.width)//2,-18))

    # Selo superior.
    sx,sy,sr=935,145,79
    draw.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=seal_color,outline=white,width=6)
    draw.ellipse((sx-sr+10,sy-sr+10,sx+sr-10,sy+sr-10),outline=(255,255,255,150),width=2)
    badge_lines=profile["badge"].split("\n")
    sf=_fit_font(draw,max(badge_lines,key=len),116,24,17,bold=True)
    yy=sy-(25*len(badge_lines))//2
    for line in badge_lines:
        bb=draw.textbbox((0,0),line,font=sf); draw.text((sx-(bb[2]-bb[0])//2,yy),line,font=sf,fill=white); yy+=25

    # Título gigante, principal característica do modelo Anna.
    t1,t2=profile["title1"],profile["title2"]
    f1=_fit_font(draw,t1,520,132,72,bold=True,serif=True,italic=True)
    draw.text((35,155),t1,font=f1,fill=title_color,stroke_width=2,stroke_fill=white)
    if t2:
        f2=_fit_font(draw,t2,520,84,48,bold=True,serif=True,italic=True)
        lines=_wrap(draw,t2,f2,520,2)
        for i,line in enumerate(lines):
            draw.text((58,292+i*62),line,font=f2,fill=title2_color,stroke_width=1,stroke_fill=white)

    # Faixa azul grande.
    banner_y=405
    banner_lines=_wrap(draw,profile["subtitle"],_font(28,bold=True),510,2)
    bh=58 if len(banner_lines)==1 else 82
    draw.polygon([(42,banner_y+10),(12,banner_y+bh//2),(42,banner_y+bh-10)],fill=banner_color)
    draw.polygon([(570,banner_y+10),(604,banner_y+bh//2),(570,banner_y+bh-10)],fill=banner_color)
    draw.rounded_rectangle((42,banner_y,570,banner_y+bh),radius=14,fill=banner_color)
    bf=_fit_font(draw,max(banner_lines,key=len),490,30,21,bold=True)
    yy=banner_y+(bh-30*len(banner_lines))//2
    for line in banner_lines:
        bb=draw.textbbox((0,0),line,font=bf); draw.text((306-(bb[2]-bb[0])//2,yy),line,font=bf,fill=white); yy+=30

    source=Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    # Foto protagonista maior, mantendo proporção.
    _paste_photo(canvas,source,(590,205,1070,735),28,mode=photo_mode,product_title=title)

    # Benefícios em coluna, com mais respiro.
    benefits=profile["benefits"][:5]
    by=505; item_h=66
    for i,(head,desc,icon) in enumerate(benefits):
        cy=by+i*item_h
        _draw_check(draw,68,cy+20,23,benefits_color,icon=icon)
        hf=_fit_font(draw,head,325,24,18,bold=True)
        draw.text((105,cy-4),head,font=hf,fill=benefits_color)
        df=_fit_font(draw,desc,338,16,13,bold=False)
        for j,line in enumerate(_wrap(draw,desc,df,338,2)):
            draw.text((105,cy+24+j*17),line,font=df,fill=textc)
        draw.line((105,cy+item_h-5,438,cy+item_h-5),fill=_hex(_shade(p["azul"],1.12)),width=2)

    # Selo central.
    cx,cy,cr=505,675,77
    draw.ellipse((cx-cr,cy-cr,cx+cr,cy+cr),fill=white,outline=seal_color,width=4)
    center_lines=profile["center"].split("\n")
    cf=_fit_font(draw,max(center_lines,key=len),128,18,13,bold=True)
    yy=cy-(21*len(center_lines))//2
    for line in center_lines:
        bb=draw.textbbox((0,0),line,font=cf); draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=cf,fill=title_color); yy+=21
    draw.ellipse((486,760,502,776),fill=blue); draw.ellipse((512,752,530,780),fill=pink); draw.ellipse((540,760,556,776),fill=blue)

    # Aplicações sempre presentes no Splash Premium.
    apps=_default_applications(profile,title)
    _draw_application_strip(canvas,source,apps,y=835,blue=blue,dark=title_color,white=white)

    # CTA grande à direita.
    cta_text=(cta or "FAÇA SEU PEDIDO!").upper()
    ctaf=_fit_font(draw,cta_text,455,43,29,bold=True)
    bb=draw.textbbox((0,0),cta_text,font=ctaf); draw.text((820-(bb[2]-bb[0])//2,728),cta_text,font=ctaf,fill=title_color)
    phone_box=(590,775,1048,868)
    draw.rounded_rectangle(phone_box,radius=34,fill=cta_color)
    _draw_whatsapp(draw,645,821,32,green)
    phone_text=phone or "11 97294-9533"
    phf=_fit_font(draw,phone_text,335,47,32,bold=True)
    pbb=draw.textbbox((0,0),phone_text,font=phf)
    tx=700+(1035-700-(pbb[2]-pbb[0]))//2; ty=821-(pbb[3]-pbb[1])//2-pbb[1]
    draw.text((tx,ty),phone_text,font=phf,fill=cta_text_color)

    # Preço opcional em selo pequeno, sem substituir a faixa de aplicações.
    if str(price or "").strip():
        pcx,pcy,pr=590,910,52
        draw.ellipse((pcx-pr,pcy-pr,pcx+pr,pcy+pr),fill=dark,outline=yellow,width=5)
        pf=_fit_font(draw,str(price),88,25,17,bold=True)
        pbb=draw.textbbox((0,0),str(price),font=pf); draw.text((pcx-(pbb[2]-pbb[0])//2,pcy-(pbb[3]-pbb[1])//2-pbb[1]),str(price),font=pf,fill=yellow)

    pink_box=(620,890,1045,968)
    draw.rounded_rectangle(pink_box,radius=15,fill=pink)
    pf=_fit_font(draw,profile["pink"],385,23,16,bold=True,serif=True,italic=True)
    plines=_wrap(draw,profile["pink"],pf,385,2); yy=903
    for line in plines:
        bb=draw.textbbox((0,0),line,font=pf); draw.text((832-(bb[2]-bb[0])//2,yy),line,font=pf,fill=white); yy+=25

    footer_y=990
    draw.rectangle((0,footer_y,1080,1080),fill=footer_color)
    labels=profile["footer"][:4]; cell_w=270
    for i,label in enumerate(labels):
        left=i*cell_w
        _draw_check(draw,left+28,1035,14,white)
        ff=_fit_font(draw,label,205,17,11,bold=True)
        lines=_wrap(draw,label,ff,205,2); yy=1025 if len(lines)==2 else 1032
        for line in lines:
            draw.text((left+52,yy),line,font=ff,fill=footer_text_color); yy+=16
        if i: draw.line((left,1008,left,1063),fill=(255,255,255,80),width=1)
    return canvas

def _render_square(image_bytes: bytes, *, title: str, subtitle: str, description: str, price: str, cta: str, phone: str, logo_path: Path, cfg: dict[str,Any], palette_override: dict[str,str] | None = None, photo_mode: str = "auto") -> Image.Image:
    if str(cfg.get("id")) == "splash_premium_anna":
        return _render_splash_premium_square(image_bytes, title=title, subtitle=subtitle, description=description, price=price, cta=cta, phone=phone, logo_path=logo_path, cfg=cfg, palette_override=palette_override, photo_mode=photo_mode)
    p = _template_palette_from_override(cfg, palette_override)
    blue,dark,pale,pink,yellow,textc,green = (_hex(p[k]) for k in ("azul","azul_escuro","azul_claro","rosa","amarelo","texto","verde"))
    title_color=_hex(p.get("cor_titulo", p["azul_escuro"]))
    title2_color=_hex(p.get("cor_titulo_secundario", p["azul"]))
    banner_color=_hex(p.get("cor_banner", p["azul_escuro"]))
    benefits_color=_hex(p.get("cor_beneficios", p["azul_escuro"]))
    seal_color=_hex(p.get("cor_selo", p["azul"]))
    price_color=_hex(p.get("cor_preco", p["amarelo"]))
    price_bg=_hex(p.get("cor_preco_fundo", p["azul_escuro"]))
    cta_color=_hex(p.get("cor_cta", p["azul_escuro"]))
    cta_text_color=_hex(p.get("cor_cta_texto", "#FFFFFF"))
    footer_color=_hex(p.get("cor_rodape", p["azul_escuro"]))
    footer_text_color=_hex(p.get("cor_rodape_texto", "#FFFFFF"))
    white=(255,255,255,255)
    profile = _product_profile(title,description,subtitle)
    is_splash = str(cfg.get("id")) == "splash_premium_anna"
    canvas=Image.new("RGBA",(1080,1080),_hex(p["fundo"]))
    draw=ImageDraw.Draw(canvas,"RGBA")
    _draw_liquid_corners(draw,blue,dark,pink,yellow)

    logo=_load_logo(logo_path,(360,270))
    if logo:
        canvas.alpha_composite(logo,((1080-logo.width)//2,-8))

    # Selo superior, com texto sempre completo.
    sx,sy,sr=930,155,78
    draw.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=seal_color,outline=white,width=6)
    badge_lines=profile["badge"].split("\n")
    sf=_fit_font(draw,max(badge_lines,key=len),118,23,17,bold=True)
    line_h=max(22,draw.textbbox((0,0),"Ag",font=sf)[3]+5)
    yy=sy-(line_h*len(badge_lines))//2
    for line in badge_lines:
        bb=draw.textbbox((0,0),line,font=sf)
        draw.text((sx-(bb[2]-bb[0])//2,yy),line,font=sf,fill=white)
        yy+=line_h

    # Título: usa toda a área esquerda sem cortar.
    t1,t2=profile["title1"],profile["title2"]
    f1=_fit_font(draw,t1,600,140,76,bold=True,serif=True,italic=True)
    draw.text((32,165),t1,font=f1,fill=title_color,stroke_width=2,stroke_fill=white)
    if t2:
        f2=_fit_font(draw,t2,590,92,52,bold=True,serif=True,italic=True)
        for idx,line in enumerate(_wrap(draw,t2,f2,590,2)):
            draw.text((54,286+idx*62),line,font=f2,fill=title2_color,stroke_width=1,stroke_fill=white)

    # Banner com altura variável para 1 ou 2 linhas.
    rf=_fit_font(draw,profile["subtitle"],510,31,21,bold=True)
    banner_lines=_wrap(draw,profile["subtitle"],rf,500,2)
    ribbon_h=58 if len(banner_lines)==1 else 84
    ribbon_y=400
    draw.polygon([(40,ribbon_y+12),(12,ribbon_y+ribbon_h//2),(40,ribbon_y+ribbon_h-10)],fill=banner_color)
    draw.polygon([(580,ribbon_y+12),(608,ribbon_y+ribbon_h//2),(580,ribbon_y+ribbon_h-10)],fill=banner_color)
    draw.rounded_rectangle((40,ribbon_y,580,ribbon_y+ribbon_h),radius=14,fill=banner_color)
    line_h=29
    yy=ribbon_y+(ribbon_h-line_h*len(banner_lines))//2-2
    for line in banner_lines:
        bb=draw.textbbox((0,0),line,font=rf)
        draw.text((310-(bb[2]-bb[0])//2,yy),line,font=rf,fill=white)
        yy+=line_h

    # Foto: preserva proporção; balões e cenários mantêm a foto inteira.
    source=Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    _paste_photo(canvas,source,(575,195,1070,735),32,mode=photo_mode,product_title=title)

    # Benefícios com altura calculada e texto completo em até 3 linhas.
    benefits=profile["benefits"][:5]
    by=500
    available=420
    item_h=max(76,available//max(1,len(benefits)))
    for i,(head,desc,icon) in enumerate(benefits):
        cy=by+i*item_h
        _draw_check(draw,70,cy+22,24,benefits_color,icon=icon)
        hf=_fit_font(draw,head,330,26,19,bold=True)
        draw.text((108,cy-3),head,font=hf,fill=benefits_color)
        df=_fit_font(draw,desc,340,18,15,bold=False)
        desc_lines=_wrap(draw,desc,df,340,3)
        dy=cy+26
        for line in desc_lines:
            draw.text((108,dy),line,font=df,fill=textc)
            dy+=18
        draw.line((108,cy+item_h-7,435,cy+item_h-7),fill=_hex(_shade(p["azul"],1.15)),width=2)

    # Selo central mais discreto e proporcional.
    cx,cy,cr=520,700,76
    draw.ellipse((cx-cr,cy-cr,cx+cr,cy+cr),fill=white,outline=seal_color,width=4)
    center_lines=profile["center"].split("\n")
    cf=_fit_font(draw,max(center_lines,key=len),128,18,14,bold=True)
    line_h=22
    yy=cy-(line_h*len(center_lines))//2
    for line in center_lines:
        bb=draw.textbbox((0,0),line,font=cf)
        draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=cf,fill=title_color)
        yy+=line_h

    # CTA, preço e WhatsApp em blocos separados e equilibrados.
    cta_text=(cta or "FAÇA SEU PEDIDO!").upper()
    ctaf=_fit_font(draw,cta_text,430,44,30,bold=True)
    bb=draw.textbbox((0,0),cta_text,font=ctaf)
    draw.text((830-(bb[2]-bb[0])//2,722),cta_text,font=ctaf,fill=title_color)

    phone_box=(610,775,1045,875)
    draw.rounded_rectangle(phone_box,radius=34,fill=cta_color)
    _draw_whatsapp(draw,662,825,34,green)
    phone_text=phone or "11 97294-9533"
    phf=_fit_font(draw,phone_text,315,48,34,bold=True)
    pbb=draw.textbbox((0,0),phone_text,font=phf)
    text_left,text_right=706,1030
    text_x=text_left+(text_right-text_left-(pbb[2]-pbb[0]))//2
    text_y=825-(pbb[3]-pbb[1])//2-pbb[1]
    draw.text((text_x,text_y),phone_text,font=phf,fill=cta_text_color)

    applications = profile.get("applications") or []
    if applications and is_splash:
        _draw_application_strip(canvas, source, applications, y=842, blue=blue, dark=title_color, white=white)
        pink_box=(620,895,1040,970)
    else:
        # Preço: maior e mais visível, mas sem cobrir o conteúdo.
        if price.strip():
            pcx,pcy,pr=515,888,76
            draw.ellipse((pcx-pr,pcy-pr,pcx+pr,pcy+pr),fill=price_bg,outline=price_color,width=7)
            small=_font(16,bold=True)
            label="APENAS"
            lbb=draw.textbbox((0,0),label,font=small)
            draw.text((pcx-(lbb[2]-lbb[0])//2,pcy-53),label,font=small,fill=white)
            prf=_fit_font(draw,price,130,38,23,bold=True)
            bb=draw.textbbox((0,0),price,font=prf)
            draw.text((pcx-(bb[2]-bb[0])//2,pcy-20),price,font=prf,fill=price_color)
            vista="à vista"
            vbb=draw.textbbox((0,0),vista,font=small)
            draw.text((pcx-(vbb[2]-vbb[0])//2,pcy+31),vista,font=small,fill=white)
        pink_box=(625,895,1030,960)

    # Faixa de mensagem sem cortar texto.
    draw.rounded_rectangle(pink_box,radius=16,fill=pink)
    pf=_fit_font(draw,profile["pink"],pink_box[2]-pink_box[0]-36,22,16,bold=True,serif=True,italic=True)
    pink_lines=_wrap(draw,profile["pink"],pf,pink_box[2]-pink_box[0]-36,2)
    yy=pink_box[1]+10 if len(pink_lines)==2 else pink_box[1]+22
    center_x=(pink_box[0]+pink_box[2])//2
    for line in pink_lines:
        bb=draw.textbbox((0,0),line,font=pf)
        draw.text((center_x-(bb[2]-bb[0])//2,yy),line,font=pf,fill=white)
        yy+=24

    # Rodapé em quatro células iguais, sem sobreposição e sem cortar palavras.
    footer_y=995
    draw.rectangle((0,footer_y,1080,1080),fill=footer_color)
    labels=profile["footer"][:4]
    cell_w=1080//max(1,len(labels))
    for i,label in enumerate(labels):
        left=i*cell_w; right=(i+1)*cell_w
        _draw_check(draw,left+26,1037,14,white)
        ff=_fit_font(draw,label,cell_w-64,17,12,bold=True)
        lines=_wrap(draw,label,ff,cell_w-64,2)
        total_h=17*len(lines)
        yy=1037-total_h//2-2
        for line in lines:
            draw.text((left+50,yy),line,font=ff,fill=footer_text_color)
            yy+=17
        if i:
            draw.line((left,1011,left,1065),fill=(255,255,255,70),width=1)

    return canvas

def _adapt_channel(square: Image.Image, size: tuple[int,int], cfg: dict[str,Any], palette_override: dict[str,str] | None = None) -> Image.Image:
    W,H=size
    if (W,H)==(1080,1080):
        return square
    p=_template_palette_from_override(cfg, palette_override)
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
    palette_override: dict[str,str] | None=None,
    photo_mode: str="auto",
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
        palette_override=palette_override,
        photo_mode=photo_mode,
    )
    final=_adapt_channel(square,size,cfg,palette_override)
    output=io.BytesIO()
    final.convert("RGB").save(output,"PNG",optimize=True)
    return output.getvalue()
