"""AlphaFest Marketing Template Engine.

HF53.3 — Biblioteca de Templates do Alpha Marketing.
O Template Mestre Comercial HF53.2-HF5-HF7 permanece congelado e homologado.
Esta etapa adiciona metadados de catálogo, proteção do template oficial e seleção
segura pelo Piloto Automático sem alterar seu render, layout ou identidade visual.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from alphafest_font_manager import get_font, resolve_font_path
from template_library_engine import list_library_templates, load_library_template, render_library_square
from marketing_anna_renderer_hf11 import render_anna_prompt, ANNA_RENDERER_VERSION

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = "anna_base_dinamica"
EMBEDDED_DEFAULT_TEMPLATE = "splash_premium_anna"

ANNA_PROMPT_SPEC: dict[str, Any] = {
    "versao": ANNA_RENDERER_VERSION,
    "nome": "Anna Prompt Premium",
    "layout_fixo": [
        "logo", "titulo", "faixa", "beneficios", "produto", "selo_central",
        "ideal_para", "cta_whatsapp", "faixa_emocional", "rodape",
    ],
    "cta": "FAÇA SEU PEDIDO!",
    "selo_superior": "TESTADO E\nAPROVADO!",
    "faixa_emocional": "Pequenos detalhes que fazem toda a diferença!",
    "rodape": ["PRÁTICO", "CRIATIVO", "VALORIZA SEU PRODUTO", "AUMENTA SUAS VENDAS"],
    "formatos": {
        "Instagram Feed": (1080, 1080),
        "Facebook": (1080, 1080),
        "Instagram Story": (1080, 1920),
        "Status WhatsApp": (1080, 1920),
        "Horizontal": (1920, 1080),
    },
}

EMBEDDED_TEMPLATES: dict[str, dict[str, Any]] = {
    "splash_premium_anna": {
        "id": "splash_premium_anna",
        "nome": "Template Mestre Comercial AlphaFest ⭐",
        "descricao": "Modelo oficial HF53.2-HF5-HF7 em 1080×1350: acabamento final preservado e ícone clássico do WhatsApp em alta legibilidade no CTA.",
        "categoria_template": "Comercial",
        "status_template": "Homologado",
        "versao_template": "HF53.2-HF5-HF7",
        "oficial": True,
        "protegido": True,
        "autopilot_aprovado": True,
        "preview": "assets/marketing/template_mestre_hf7_preview.png",
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
    "anna_social_redes": {
        "id": "anna_social_redes",
        "nome": "Template Anna — Redes Sociais",
        "descricao": "Template Anna — Modelo 1 HF8-HF15: correção de composição mantendo o renderer aprovado HF11. Gravação Laser preserva a manchete visual homologada e o tipo de letra aprovado; remove a sobreposição indevida do produto herdada da referência-base; mantém palco oval limpo, produto nítido, selo único e cards temáticos; Mestre HF7 permanece congelado.",
        "categoria_template": "Redes Sociais",
        "status_template": "Homologado",
        "versao_template": ANNA_RENDERER_VERSION,
        "oficial": False,
        "protegido": True,
        "autopilot_aprovado": True,
        "preview": "assets/marketing/template_anna_redes_preview.png",
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
        "nome": "AlphaFest Agência — Legado",
        "descricao": "Compatibilidade com campanhas antigas. O Piloto Automático não usa este registro como template de produção.",
        "categoria_template": "Legado",
        "status_template": "Compatibilidade",
        "versao_template": "Legado",
        "oficial": False,
        "protegido": True,
        "autopilot_aprovado": False,
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


def anna_runtime_version() -> str:
    """Versão efetivamente carregada pelo renderer dedicado do Template Anna."""
    return str(ANNA_RENDERER_VERSION)


def listar_templates() -> list[dict[str, Any]]:
    """Catálogo único de templates do Alpha Marketing.

    O mestre oficial é sempre o primeiro item e permanece protegido. Templates
    importados continuam disponíveis no Studio, mas só entram no Piloto Automático
    depois de uma homologação explícita futura.
    """
    embedded: list[dict[str, Any]] = []
    for key, value in EMBEDDED_TEMPLATES.items():
        item = {
            "id": key,
            "nome": str(value.get("nome") or key),
            "descricao": str(value.get("descricao") or ""),
            "source": "embedded",
            "categoria_template": str(value.get("categoria_template") or "Geral"),
            "status_template": str(value.get("status_template") or "Disponível"),
            "versao_template": str(value.get("versao_template") or ""),
            "oficial": bool(value.get("oficial")),
            "protegido": bool(value.get("protegido")),
            "autopilot_aprovado": bool(value.get("autopilot_aprovado")),
        }
        preview = str(value.get("preview") or "").strip()
        if preview:
            item["preview"] = str(BASE_DIR / preview)
        embedded.append(item)

    installed: list[dict[str, Any]] = []
    for raw in list_library_templates():
        item = dict(raw)
        item.setdefault("categoria_template", "Biblioteca")
        item.setdefault("status_template", "Em teste")
        item.setdefault("versao_template", "Importado")
        # HF53.3: metadados de confiança nunca vêm de um ZIP importado.
        item["oficial"] = False
        item["protegido"] = False
        item["autopilot_aprovado"] = False
        installed.append(item)

    official = [x for x in embedded if x.get("oficial")]
    others = [x for x in embedded if not x.get("oficial")]
    return official + installed + others


def listar_templates_autopilot() -> list[dict[str, Any]]:
    """Retorna apenas templates liberados para produção automática."""
    return [item for item in listar_templates() if bool(item.get("autopilot_aprovado"))]


def carregar_template(template_id: str = DEFAULT_TEMPLATE) -> dict[str, Any]:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", template_id or DEFAULT_TEMPLATE)
    external = load_library_template(safe)
    if external:
        # Mantém uma paleta base para compatibilidade com adaptação de canais.
        external.setdefault("paleta", {
            "fundo": "#FFFFFF", "azul": "#087CE8", "azul_escuro": "#07349B",
            "azul_claro": "#DDF5FF", "rosa": "#EF2A92", "amarelo": "#FFD12B",
            "texto": "#102D50", "verde": "#20B956",
        })
        return external
    # Compatibilidade com campanhas salvas antes da versão 19.0.1.
    if safe in {"alphafest_agencia", "alphafest_agencia_anna"}:
        safe = "splash_premium_anna"
    cfg = EMBEDDED_TEMPLATES.get(safe) or EMBEDDED_TEMPLATES[EMBEDDED_DEFAULT_TEMPLATE]
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


def _draw_check(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill, *, icon: str = "check", icon_color=None):
    white = (255, 255, 255, 255)
    ink = icon_color or white
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fill)
    if icon == "star":
        # estrela simples e legível
        pts = [(cx, cy-radius+6), (cx+8, cy-7), (cx+radius-5, cy-7), (cx+12, cy+5),
               (cx+18, cy+radius-5), (cx, cy+13), (cx-18, cy+radius-5), (cx-12, cy+5),
               (cx-radius+5, cy-7), (cx-8, cy-7)]
        draw.polygon(pts, outline=ink)
    elif icon == "diamond":
        draw.polygon([(cx,cy-radius+7),(cx+radius-7,cy-3),(cx,cy+radius-7),(cx-radius+7,cy-3)], outline=ink)
    elif icon == "heart":
        draw.ellipse((cx-radius//2,cy-radius//3,cx,cy+radius//3), fill=ink)
        draw.ellipse((cx,cy-radius//3,cx+radius//2,cy+radius//3), fill=ink)
        draw.polygon([(cx-radius//2,cy),(cx+radius//2,cy),(cx,cy+radius//2)], fill=ink)
    else:
        draw.line((cx-radius//2, cy, cx-radius//8, cy+radius//3), fill=ink, width=5)
        draw.line((cx-radius//8, cy+radius//3, cx+radius//2, cy-radius//3), fill=ink, width=5)


WHATSAPP_ICON_PATH = BASE_DIR / "assets" / "marketing" / "whatsapp_classic.png"


@lru_cache(maxsize=8)
def _whatsapp_icon(size: int) -> Image.Image | None:
    """Carrega o ícone clássico fornecido pela AlphaFest e preserva sua leitura."""
    try:
        if not WHATSAPP_ICON_PATH.exists():
            return None
        icon = Image.open(WHATSAPP_ICON_PATH).convert("RGBA")
        icon = ImageOps.fit(icon, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        return icon
    except Exception:
        return None


def _draw_whatsapp(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill):
    """HF53.2-HF5-HF7: usa o símbolo clássico real do WhatsApp no CTA.

    O hotfix remove o glifo genérico que podia parecer um telefone incompleto e
    aplica o ícone fornecido pela AlphaFest, com balão + handset reconhecíveis
    mesmo na miniatura do Feed. Mantém fallback vetorial somente se o asset faltar.
    """
    size = max(36, radius * 2)
    icon = _whatsapp_icon(size)
    surface = getattr(draw, "_image", None)
    if icon is not None and isinstance(surface, Image.Image):
        surface.alpha_composite(icon, (cx - icon.width // 2, cy - icon.height // 2))
        return

    # Fallback: símbolo simples, apenas para instalações onde o asset foi removido.
    white=(255,255,255,255)
    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=fill,outline=white,width=max(4,radius//9))
    draw.arc((cx-radius//2,cy-radius//2,cx+radius//2,cy+radius//2),35,315,fill=white,width=max(5,radius//6))
    draw.line((cx-radius//5,cy+radius//5,cx-radius//2,cy+radius//2),fill=white,width=max(5,radius//7))


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


def _paste_photo(canvas: Image.Image, source: Image.Image, box: tuple[int,int,int,int], radius: int = 28, *, mode: str = "auto", product_title: str = "", upscale: bool = False):
    """Posiciona a foto sem deformar e escolhe o tratamento adequado.

    HF53.2-HF5-HF3: a foto é renderizada primeiro em uma camada do tamanho
    exato da área protegida. Assim, produto e sombra jamais podem invadir título,
    benefícios, miniaturas ou CTA, mesmo quando a imagem original é muito maior
    que a caixa. ``upscale`` permite ampliar imagens pequenas, mas nunca impede
    o downscale obrigatório de imagens grandes.

    ``auto`` preserva fotos de balões e produtos com cenário; nos demais casos,
    tenta remover o fundo. ``preservar`` mantém a foto inteira e ``recortar``
    força o recorte do produto.
    """
    x1, y1, x2, y2 = box
    w, h = max(1, x2 - x1), max(1, y2 - y1)
    original = ImageOps.exif_transpose(source).convert("RGBA")
    title_low = str(product_title or "").casefold()
    preserve_auto = any(k in title_low for k in ("balão", "balao", "painel", "cenário", "cenario", "decoração completa"))
    preserve = mode == "preservar" or (mode == "auto" and preserve_auto)

    # Toda a composição da foto nasce nesta camada. Qualquer pixel fora dela é
    # fisicamente descartado antes de chegar ao canvas mestre.
    zone = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if preserve:
        # Foto inteira, sem esticar. Fundo suavemente arredondado para fotos de ambiente.
        photo = ImageOps.contain(original, (w, h), Image.Resampling.LANCZOS)
        px = (w - photo.width) // 2
        py = (h - photo.height) // 2
        mask = Image.new("L", photo.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, photo.width, photo.height), radius=min(radius, max(8, min(photo.size)//8)), fill=255)
        shadow_mask = mask.filter(ImageFilter.GaussianBlur(16))
        shadow = Image.new("RGBA", photo.size, (0, 35, 80, 0)); shadow.putalpha(shadow_mask.point(lambda v: int(v*.32)))
        zone.alpha_composite(shadow, (px+10, py+14))
        zone.paste(photo, (px, py), mask)
        canvas.alpha_composite(zone, (x1, y1))
        return

    product = _trim_transparent(_remove_background(original) if mode in {"auto", "recortar"} else original)
    if not product.getbbox():
        product = original

    if product.width > 0 and product.height > 0:
        fit_scale = min(w / product.width, h / product.height)
        if upscale:
            # Imagem pequena pode crescer até 3x; imagem grande SEMPRE diminui
            # até caber integralmente na área segura.
            scale = min(fit_scale, 3.0)
        else:
            scale = min(1.0, fit_scale)
        if abs(scale - 1.0) > 0.001:
            product = product.resize(
                (max(1, int(product.width * scale)), max(1, int(product.height * scale))),
                Image.Resampling.LANCZOS,
            )

    px = (w - product.width) // 2
    py = (h - product.height) // 2
    alpha = product.getchannel("A")
    shadow = _soft_shadow(alpha, blur=max(12, int(min(product.size) * 0.045)), opacity=95)
    zone.alpha_composite(shadow, (px + 16, py + 20))
    zone.alpha_composite(product, (px, py))
    canvas.alpha_composite(zone, (x1, y1))

def _commercial_subtitle(subtitle: str, fallback: str) -> str:
    """Evita usar apenas o nome da campanha como promessa comercial do template Anna."""
    txt = re.sub(r"\s+", " ", str(subtitle or "")).strip()
    short_campaigns = {
        "permanente", "natal", "outubro rosa", "dia das crianças", "dia das criancas",
        "dia das mães", "dia das maes", "dia dos pais", "páscoa", "pascoa",
        "corporativo", "black friday", "ano novo", "festa junina", "carnaval",
    }
    if not txt or txt.casefold() in short_campaigns:
        return fallback
    return txt


def _product_profile(title: str, description: str, subtitle: str) -> dict[str, Any]:
    raw = re.sub(r"\([^)]*\)", " ", str(title or "Produto AlphaFest"))
    raw = re.sub(r"^[^\wÀ-ÿ]+", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    low = raw.casefold()
    if "leopardo" in low or "voronoi" in low:
        return {
            "title1": "Leopardo",
            "title2": "Voronoi",
            "subtitle": _commercial_subtitle(subtitle, "Design moderno que transforma qualquer ambiente!"),
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

    if any(k in low for k in ("gravação", "gravacao", "laser")):
        return {
            "title1": "Gravação",
            "title2": "Laser",
            "subtitle": _commercial_subtitle(subtitle, "Personalização durável para presentes, brindes e empresas"),
            "benefits": [
                ("DESIGN EXCLUSIVO", "Criado para encantar e valorizar", "diamond"),
                ("FÁCIL DE USAR", "Prático, rápido e pronto para o dia a dia", "check"),
                ("MATERIAL DE QUALIDADE", "Resistente, durável e bem-acabado", "diamond"),
                ("PERSONALIZADO", "Produzido conforme o seu pedido", "check"),
                ("MÚLTIPLOS USOS", "Ideal para presentes, brindes e empresa", "heart"),
            ],
            "center": "Detalhes que\nencantam e fazem\na diferença!",
            "badge": "ARTE\nAPROVADA",
            "pink": "Pequenas personalizações, grandes histórias!",
            "footer": ["PRÁTICO", "CRIATIVO", "VALORIZE SEU PRODUTO", "AUMENTA SUAS VENDAS"],
            "applications": ["Presentes", "Empresas", "Eventos", "Brindes"],
        }

    if any(k in low for k in ("carimbo", "carimbos", "doces", "brigadeiro")):
        return {
            "title1": "Carimbos",
            "title2": "para Doces",
            "subtitle": _commercial_subtitle(subtitle, "Transforme seus doces em pequenas obras de arte!"),
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
            "subtitle": _commercial_subtitle(subtitle, "Um detalhe especial para deixar sua festa inesquecível!"),
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
        "subtitle": _commercial_subtitle(subtitle, "Personalizado do seu jeito!"),
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
    """Faixa de aplicações com largura fixa e espaço reservado para o preço."""
    draw = ImageDraw.Draw(canvas, "RGBA")
    left, right, bottom = 24, 520, y + 136
    draw.rounded_rectangle((left, y, right, bottom), radius=20, fill=(255,255,255,245), outline=blue, width=2)
    draw.polygon([(left,y+18),(8,y+36),(left,y+54)], fill=dark)
    draw.rounded_rectangle((left,y-15,186,y+24), radius=10, fill=blue)
    font = _font(19, bold=True)
    draw.text((48,y-10), "Ideal para:", font=font, fill=white)
    thumb = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), (78,78), method=Image.Resampling.LANCZOS)
    for i, label in enumerate(labels[:4]):
        cx = 76 + i*112
        mask = Image.new("L", (78,78), 0)
        ImageDraw.Draw(mask).ellipse((0,0,77,77), fill=255)
        canvas.paste(thumb.convert("RGBA"), (cx-39,y+29), mask)
        draw.ellipse((cx-41,y+27,cx+41,y+109), outline=blue, width=3)
        lf = _fit_font(draw, label, 96, 14, 10, bold=True)
        lines = _wrap(draw, label, lf, 96, 2)
        yy = y+108
        for line in lines:
            bb=draw.textbbox((0,0),line,font=lf)
            draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=lf,fill=dark)
            yy += 13



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


def _wrap_complete(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Quebra todas as palavras sem truncar nem acrescentar reticências."""
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
    if current:
        lines.append(current)
    return lines


def _fit_wrapped_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_height: int, start: int, minimum: int, max_lines: int, *, bold: bool = True, serif: bool = False, italic: bool = False):
    """HF53.2-HF5-HF4: reduz a fonte até TODO o título caber, sem ``...``."""
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    for size in range(int(start), int(minimum) - 1, -2):
        font = _font(size, bold=bold, serif=serif, italic=italic)
        lines = _wrap_complete(draw, clean, font, max_width)
        if len(lines) > max_lines:
            continue
        line_h = max(1, draw.textbbox((0, 0), "Ag", font=font)[3] - draw.textbbox((0, 0), "Ag", font=font)[1])
        total_h = line_h * len(lines) + max(0, len(lines)-1) * max(2, int(size*.05))
        widest = max((draw.textbbox((0,0), line, font=font)[2] for line in lines), default=0)
        if widest <= max_width and total_h <= max_height:
            return font, lines, line_h
    # Salvaguarda extrema: continua reduzindo abaixo do mínimo nominal em vez
    # de cortar o nome. Produtos cadastrados normalmente não chegam aqui.
    for size in range(int(minimum) - 2, 31, -2):
        font = _font(size, bold=bold, serif=serif, italic=italic)
        lines = _wrap_complete(draw, clean, font, max_width)
        if len(lines) <= max_lines:
            line_h = max(1, draw.textbbox((0, 0), "Ag", font=font)[3] - draw.textbbox((0, 0), "Ag", font=font)[1])
            total_h = line_h * len(lines) + max(0, len(lines)-1) * max(2, int(size*.05))
            if total_h <= max_height:
                return font, lines, line_h
    font = _font(32, bold=bold, serif=serif, italic=italic)
    lines = _wrap_complete(draw, clean, font, max_width)
    return font, lines[:max_lines], max(1, draw.textbbox((0, 0), "Ag", font=font)[3] - draw.textbbox((0, 0), "Ag", font=font)[1])


def _draw_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill, outline=None, width: int = 2):
    r=max(2,int(size*.28))
    draw.ellipse((cx-size//2,cy-size//3,cx-size//2+r*2,cy-size//3+r*2),fill=fill,outline=outline,width=width)
    draw.ellipse((cx+size//2-r*2,cy-size//3,cx+size//2,cy-size//3+r*2),fill=fill,outline=outline,width=width)
    draw.polygon([(cx-size//2,cy),(cx+size//2,cy),(cx,cy+size//2)],fill=fill)


def _draw_campaign_ribbon(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color):
    """Laço de conscientização vetorial, usado por campanhas como Outubro Rosa."""
    w=max(12,int(24*scale))
    pts1=[(x,y),(x+int(72*scale),y+int(74*scale)),(x+int(28*scale),y+int(150*scale))]
    pts2=[(x+int(72*scale),y),(x,y+int(74*scale)),(x+int(116*scale),y+int(150*scale))]
    draw.line(pts1,fill=color,width=w,joint="curve")
    draw.line(pts2,fill=color,width=w,joint="curve")
    hi=(255,255,255,90)
    draw.line([(x+int(4*scale),y+int(3*scale)),(x+int(70*scale),y+int(70*scale))],fill=hi,width=max(2,w//5))


def _draw_flower(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, petal, center):
    pr=max(4,int(r*.55))
    for dx,dy in ((0,-r),(r,0),(0,r),(-r,0),(int(r*.7),int(r*.7)),(-int(r*.7),int(r*.7))):
        draw.ellipse((cx+dx-pr,cy+dy-pr,cx+dx+pr,cy+dy+pr),fill=petal)
    draw.ellipse((cx-pr//2,cy-pr//2,cx+pr//2,cy+pr//2),fill=center)


def _split_campaign_subtitle(subtitle: str) -> tuple[str, str]:
    clean=re.sub(r"\s+"," ",str(subtitle or "")).strip()
    if ":" in clean:
        left,right=clean.split(":",1)
        if 1 <= len(left.strip()) <= 34:
            return left.strip(), right.strip()
    return "", clean


def _brand_wordmark(max_size=(600,160), fallback: Path | None = None) -> Image.Image | None:
    candidates=[BASE_DIR/"assets"/"mascotes"/"logo_wordmark_transparent.png"]
    if fallback:
        candidates.append(fallback)
    for path in candidates:
        logo=_load_logo(path,max_size)
        if logo is not None:
            return logo
    return None


def _unique_application_sources(primary: Image.Image, application_images: list[bytes] | None) -> list[Image.Image]:
    """Retorna até 4 imagens visualmente distintas; nunca repete a mesma foto."""
    candidates=[primary]
    for raw in list(application_images or []):
        if not raw:
            continue
        try:
            candidates.append(ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGBA"))
        except Exception:
            continue
    unique=[]; seen=set()
    for img in candidates:
        # fingerprint visual simples, independente do nome/URL do arquivo
        fp=img.convert("RGB").resize((16,16),Image.Resampling.BILINEAR).tobytes()
        if fp in seen:
            continue
        seen.add(fp); unique.append(img)
        if len(unique)>=4:
            break
    return unique


def _format_phone_br(value: str) -> str:
    digits=re.sub(r"\D", "", str(value or ""))
    if digits.startswith("55") and len(digits) in {12,13}:
        digits=digits[2:]
    if len(digits)==11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits)==10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return str(value or "(11) 97294-9533").strip() or "(11) 97294-9533"


def _render_splash_premium_portrait(image_bytes: bytes, *, title: str, subtitle: str, description: str, price: str, cta: str, phone: str, logo_path: Path, cfg: dict[str,Any], palette_override: dict[str,str] | None = None, photo_mode: str = "auto", application_images: list[bytes] | None = None) -> Image.Image:
    """HF53.2-HF5 — Template Mestre Comercial profissional (1080x1350 nativo).

    A hierarquia segue a referência aprovada pela AlphaFest: marca no topo,
    título de alto impacto, campanha em faixa própria, cinco benefícios à
    esquerda, produto protagonista à direita, quatro aplicações, CTA WhatsApp
    dominante e quatro diferenciais no rodapé. A estrutura é fixa; campanha,
    paleta, produto e textos continuam dinâmicos.
    """
    p=_template_palette_from_override(cfg,palette_override)
    primary=_hex(p["azul_escuro"]); secondary=_hex(p["azul"]); accent=_hex(p["rosa"])
    metallic=_hex(p["amarelo"]); textc=_hex(p["texto"]); green=_hex(p["verde"]); bg=_hex(p["fundo"])
    white=(255,255,255,255)
    dark_accent=_hex(_shade(p["rosa"],.72))
    pale_accent=_hex(_shade(p["rosa"],1.38),95)
    profile=_product_profile(title,description,subtitle)
    source=ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGBA")
    W,H=1080,1350
    canvas=Image.new("RGBA",(W,H),bg)
    draw=ImageDraw.Draw(canvas,"RGBA")

    # Fundo claro com ondas largas, brilho e acabamento de campanha.
    for y in range(H):
        t=y/(H-1)
        base=_hex(p["fundo"])
        rr=int(base[0]*(1-t*.05)+255*(t*.05)); gg=int(base[1]*(1-t*.05)+255*(t*.05)); bb=int(base[2]*(1-t*.05)+255*(t*.05))
        draw.line((0,y,W,y),fill=(rr,gg,bb,255))
    draw.ellipse((-260,-240,490,220),fill=_hex(_shade(p["azul_escuro"],1.18),115))
    draw.ellipse((720,-250,1320,230),fill=_hex(_shade(p["azul"],1.12),95))
    draw.ellipse((-250,1180,650,1530),fill=_hex(_shade(p["azul"],1.20),125))
    draw.ellipse((620,1160,1350,1530),fill=_hex(_shade(p["azul_escuro"],1.08),120))
    draw.arc((-120,80,1180,540),200,350,fill=_hex(_shade(p["rosa"],1.25),120),width=16)
    draw.arc((-160,1040,1240,1470),12,166,fill=_hex(_shade(p["rosa"],1.18),135),width=15)

    campaign_label,campaign_body=_split_campaign_subtitle(subtitle)
    campaign_key=(campaign_label+" "+campaign_body).casefold()
    awareness=any(k in campaign_key for k in ("outubro rosa","novembro azul","câncer","cancer","conscientiza"))

    # Pequenos detalhes decorativos nunca invadem as áreas de texto.
    for cx,cy,sz in [(45,240,22),(670,285,18),(760,345,20),(1010,355,18),(525,660,20)]:
        _draw_heart(draw,cx,cy,sz,fill=_hex(p["rosa"],185))
    if awareness:
        _draw_campaign_ribbon(draw,802,48,.82,_hex(p["rosa"],165))
        _draw_campaign_ribbon(draw,35,410,.55,accent)
        _draw_flower(draw,555,850,16,_hex(_shade(p["rosa"],1.35),155),metallic)
        _draw_flower(draw,1005,835,15,_hex(_shade(p["rosa"],1.35),150),metallic)

    # Frases de apoio no topo, como na referência, mas mantidas fora do título.
    # QA final: frases do topo legíveis, mas confinadas aos cantos para não tocar a marca.
    script=_font(25,bold=True,serif=True,italic=True)
    left_phrase="Pequenos detalhes,\ngrandes\nhistórias!"
    right_phrase="Juntos por mais\nsorrisos!" if awareness else "Feito para marcar\nmomentos\nespeciais!"
    draw.multiline_text((24,50),left_phrase,font=script,fill=white,spacing=0,align="left",stroke_width=2,stroke_fill=dark_accent)
    rbb=draw.multiline_textbbox((0,0),right_phrase,font=script,spacing=0,align="right",stroke_width=2)
    draw.multiline_text((1052-(rbb[2]-rbb[0]),50),right_phrase,font=script,fill=white,spacing=0,align="right",stroke_width=2,stroke_fill=dark_accent)

    # Marca oficial em wordmark horizontal.
    logo=_brand_wordmark((640,168),logo_path)
    if logo:
        canvas.alpha_composite(logo,((W-logo.width)//2,16))

    # Título inteligente: preserva o nome integral e usa até três linhas sem reticências.
    raw_title=re.sub(r"\s+"," ",str(title or profile.get("title1") or "PRODUTO ALPHAFEST")).strip().upper()
    tf,title_lines,line_h=_fit_wrapped_font(draw,raw_title,690,218,124,44,3,bold=True)
    ty=180
    spacing=max(2,int(tf.size*.02)) if hasattr(tf,"size") else 3
    for line in title_lines:
        draw.text((49,ty+8),line,font=tf,fill=dark_accent,stroke_width=4,stroke_fill=white)
        draw.text((40,ty),line,font=tf,fill=primary,stroke_width=3,stroke_fill=white)
        ty += line_h + spacing

    # Selo de aprovação no alto direito.
    sx,sy,sr=934,280,92
    draw.ellipse((sx-sr-5,sy-sr-5,sx+sr+5,sy+sr+5),fill=_hex(_shade(p["rosa"],1.30),155))
    draw.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=dark_accent,outline=white,width=5)
    # Ícone de aprovação maior que no HF4 para equilibrar texto x símbolo.
    ir=31; icy=sy-35
    draw.ellipse((sx-ir,icy-ir,sx+ir,icy+ir),fill=white)
    draw.line((sx-13,icy,sx-4,icy+9),fill=dark_accent,width=7)
    draw.line((sx-4,icy+9,sx+15,icy-13),fill=dark_accent,width=7)
    for j,line in enumerate(["ARTE","APROVADA"]):
        badgef=_fit_font(draw,line,132,17,15,bold=True)
        bb=draw.textbbox((0,0),line,font=badgef); draw.text((sx-(bb[2]-bb[0])//2,sy+17+j*22),line,font=badgef,fill=white)

    # Faixa de campanha em duas hierarquias.
    banner_y=408
    draw.rounded_rectangle((30,banner_y,635,banner_y+108),radius=30,fill=_hex(_shade(p["rosa"],.92)),outline=_hex(_shade(p["rosa"],1.22)),width=3)
    if awareness:
        _draw_campaign_ribbon(draw,43,banner_y+11,.27,white)
    label=(campaign_label or "ALPHAFEST").upper()
    if "outubro rosa" in campaign_key:
        band_title="OUTUBRO ROSA • Personalização"
        band_sub="com propósito para presentes, brindes e empresa"
    else:
        # HF6: a linha principal deve ser uma frase completa. Nunca corta o corpo
        # no meio nem repete o mesmo texto na linha de baixo.
        title_key=raw_title.casefold()
        if any(k in title_key for k in ("copo", "caneca", "squeeze", "garrafa")):
            band_theme="PRESENTE PERSONALIZADO"
        elif any(k in title_key for k in ("gravação", "gravacao", "laser")):
            band_theme="PERSONALIZAÇÃO COM PROPÓSITO"
        elif any(k in title_key for k in ("balão", "balao", "decoração", "decoracao")):
            band_theme="DECORAÇÃO PERSONALIZADA"
        else:
            band_theme="PERSONALIZAÇÃO ALPHAFEST"
        band_title=f"{label} • {band_theme}" if campaign_label else band_theme
        band_sub=campaign_body or (profile.get("subtitle") or "Personalização sob medida para você")
    btf=_fit_font(draw,band_title,500,27,19,bold=True)
    draw.text((82,banner_y+16),band_title,font=btf,fill=white)
    bsf=_fit_font(draw,band_sub,510,18,14,bold=False)
    b_lines=_wrap(draw,band_sub,bsf,510,2)
    for j,line in enumerate(b_lines): draw.text((82,banner_y+55+j*19),line,font=bsf,fill=white)

    # Produto protagonista com pedestal e halo, sem moldura pesada.
    photo_box=(510,448,1045,965)
    draw.ellipse((540,852,1028,990),fill=_hex(_shade(p["rosa"],1.12),235),outline=_hex(_shade(p["rosa"],.88)),width=4)
    draw.ellipse((565,458,1035,946),fill=(255,255,255,125))
    _paste_photo(canvas,source,photo_box,28,mode=photo_mode,product_title=title,upscale=True)

    # Benefícios: exatamente cinco posições fixas, sem deixar o conteúdo “andar”.
    benefits=list(profile.get("benefits") or [])[:5]
    if len(benefits)<5:
        defaults=[
            ("DESIGN EXCLUSIVO","Criado para encantar e valorizar","diamond"),
            ("FÁCIL DE USAR","Prático, rápido e pronto para o dia a dia","check"),
            ("MATERIAL DE QUALIDADE","Resistente, durável e bem-acabado","diamond"),
            ("PERSONALIZADO","Produzido conforme o seu pedido","check"),
            ("MÚLTIPLOS USOS","Ideal para presentes, brindes e empresa","heart"),
        ]
        benefits=(benefits+defaults)[:5]
    by=535; item_h=82
    for i,(head,desc,icon) in enumerate(benefits):
        cy=by+i*item_h
        _draw_check(draw,67,cy+27,25,accent,icon=icon if icon in {"star","diamond","heart","check"} else "check")
        hf=_fit_font(draw,str(head).upper(),355,25,18,bold=True)
        draw.text((110,cy+1),str(head).upper(),font=hf,fill=dark_accent)
        df=_fit_font(draw,str(desc),365,17,13,bold=False)
        dlines=_wrap(draw,str(desc),df,365,2)
        for j,line in enumerate(dlines): draw.text((110,cy+31+j*18),line,font=df,fill=textc)
        draw.line((110,cy+76,470,cy+76),fill=pale_accent,width=2)

    # Destaque de mensagem circular próximo ao produto.
    center_text="Detalhes\nque fazem\na diferença!"
    cx,cy,cr=945,905,82
    draw.ellipse((cx-cr,cy-cr,cx+cr,cy+cr),fill=accent,outline=white,width=5)
    cf=_font(20,bold=True,serif=True,italic=True)
    cbb=draw.multiline_textbbox((0,0),center_text,font=cf,spacing=0,align="center")
    draw.multiline_text((cx-(cbb[2]-cbb[0])//2,cy-(cbb[3]-cbb[1])//2-3),center_text,font=cf,fill=white,spacing=0,align="center")

    # Quatro aplicações visuais. Fotos reais são deduplicadas; quando o produto
    # só possui uma foto, os demais espaços viram cards de aplicação — nunca clones.
    apps=_default_applications(profile,title)[:4]
    thumb_sources=_unique_application_sources(source, application_images)
    thumb_y=972
    fallback_icons=("star","heart","diamond","check")
    for i,label in enumerate(apps):
        cx=70+i*126
        if i < len(thumb_sources):
            thumb=ImageOps.fit(thumb_sources[i],(94,94),method=Image.Resampling.LANCZOS,centering=(.5,.5))
            mask=Image.new("L",(94,94),0); ImageDraw.Draw(mask).ellipse((0,0,93,93),fill=255)
            layer=thumb.copy(); layer.putalpha(mask); canvas.alpha_composite(layer,(cx-47,thumb_y))
        else:
            draw.ellipse((cx-47,thumb_y,cx+47,thumb_y+94),fill=_hex(_shade(p["rosa"],1.32),235))
            _draw_check(draw,cx,thumb_y+47,28,accent,icon=fallback_icons[i],icon_color=white)
        draw.ellipse((cx-50,thumb_y-3,cx+50,thumb_y+97),outline=accent,width=3)
        lf=_fit_font(draw,label,105,14,11,bold=True); lns=_wrap(draw,label,lf,105,1)
        if lns:
            bb=draw.textbbox((0,0),lns[0],font=lf); draw.text((cx-(bb[2]-bb[0])//2,thumb_y+102),lns[0],font=lf,fill=dark_accent)

    # CTA WhatsApp: rótulo + telefone grande em um único bloco de alta conversão.
    cta_label=(cta or "CONHEÇA ESTE PRODUTO").upper()
    cta_box=(555,988,1048,1120)
    draw.rounded_rectangle(cta_box,radius=48,fill=dark_accent,outline=_hex(_shade(p["rosa"],1.26)),width=4)
    _draw_whatsapp(draw,618,1054,48,green)
    ctf=_fit_font(draw,cta_label,340,25,18,bold=True)
    bb=draw.textbbox((0,0),cta_label,font=ctf); draw.text((855-(bb[2]-bb[0])//2,1001),cta_label,font=ctf,fill=white)
    phone_text=_format_phone_br(phone or "(11) 97294-9533")
    phf=_fit_font(draw,phone_text,350,43,30,bold=True)
    pbb=draw.textbbox((0,0),phone_text,font=phf); draw.text((855-(pbb[2]-pbb[0])//2,1042),phone_text,font=phf,fill=white)

    # Faixa inferior com quatro diferenciais fixos.
    footer_labels=(profile.get("footer") or ["PRÁTICO","CRIATIVO","VALORIZE SEU PRODUTO","AUMENTA SUAS VENDAS"])[:4]
    while len(footer_labels)<4: footer_labels.append(["PRÁTICO","CRIATIVO","VALORIZE SEU PRODUTO","AUMENTA SUAS VENDAS"][len(footer_labels)])
    strip_y=1142
    draw.rounded_rectangle((-20,strip_y,1100,1258),radius=44,fill=dark_accent)
    cell=270
    footer_icons=("check","star","diamond","check")
    for i,label in enumerate(footer_labels):
        left=i*cell
        _draw_check(draw,left+47,1200,26,white,icon=footer_icons[i],icon_color=dark_accent)
        # HF6: todos os quatro diferenciais usam exatamente o mesmo tamanho
        # tipográfico; muda apenas a quebra de linha quando necessário.
        ff=_font(20,bold=True)
        lines=_wrap(draw,str(label).upper(),ff,180,2)
        yy=1184 if len(lines)>1 else 1194
        step=23
        for line in lines:
            draw.text((left+82,yy),line,font=ff,fill=white); yy+=step
        if i: draw.line((left,1164,left,1238),fill=(255,255,255,105),width=2)

    # Rodapé em ondas, com assinatura emocional curta.
    draw.polygon([(0,1250),(180,1270),(380,1255),(600,1280),(820,1258),(1080,1278),(1080,1350),(0,1350)],fill=_hex(_shade(p["rosa"],1.28),205))
    phrase="Pequenas personalizações, grandes histórias!"
    pf=_fit_font(draw,phrase,930,32,27,bold=True,serif=True,italic=True)
    pbb=draw.textbbox((0,0),phrase,font=pf)
    px=(W-(pbb[2]-pbb[0]))//2
    draw.text((px,1281),phrase,font=pf,fill=dark_accent)
    if awareness:
        _draw_campaign_ribbon(draw,902,1253,.55,accent)
    return canvas


def _adapt_master_portrait_to_channel(portrait: Image.Image, size: tuple[int,int], cfg: dict[str,Any], palette_override: dict[str,str] | None = None) -> Image.Image:
    """Adapta o mestre 4:5 sem recortar conteúdo comercial."""
    W,H=size
    if (W,H)==(1080,1350):
        return portrait
    p=_template_palette_from_override(cfg,palette_override)
    bg=_hex(p["fundo"]); primary=_hex(p["azul_escuro"]); accent=_hex(p["rosa"]); metallic=_hex(p["amarelo"])
    canvas=Image.new("RGBA",(W,H),bg)
    d=ImageDraw.Draw(canvas,"RGBA")
    if H>=W:
        fitted=ImageOps.contain(portrait,(W,min(H,int(W*1.25))),Image.Resampling.LANCZOS)
        x=(W-fitted.width)//2; y=(H-fitted.height)//2
        d.rectangle((0,0,W,max(0,y+20)),fill=primary)
        d.rectangle((0,max(0,y+fitted.height-20),W,H),fill=primary)
        for cx,cy,r,c in ((70,70,9,accent),(180,105,6,metallic),(W-85,85,8,accent),(W-185,120,6,metallic)):
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=c)
        canvas.alpha_composite(fitted,(x,y))
        return canvas
    fitted=ImageOps.contain(portrait,(W,H),Image.Resampling.LANCZOS)
    x=(W-fitted.width)//2; y=(H-fitted.height)//2
    d.rectangle((0,0,W,H),fill=primary)
    canvas.alpha_composite(fitted,(x,y))
    return canvas



def _render_anna_social_native(
    image_bytes: bytes,
    size: tuple[int, int],
    *,
    title: str,
    subtitle: str,
    description: str,
    price: str,
    cta: str,
    phone: str,
    logo_path: Path,
    cfg: dict[str, Any],
    palette_override: dict[str, str] | None = None,
    photo_mode: str = "auto",
    application_images: list[bytes] | None = None,
) -> Image.Image:
    """HF53.3-HF8-HF5 — Template Anna Prompt Premium, com grade comercial fixa baseada na grade editorial aprovada.

    O wordmark horizontal fica proibido neste template; somente o logo splash aprovado pela Anna é usado no cabeçalho.
    A referência deixa de ser apenas inspiração: a composição passa a obedecer à
    mesma hierarquia comercial (marca forte -> título gigante -> faixa -> conteúdo
    + produto protagonista -> benefícios -> aplicações -> CTA -> rodapé). Cada
    proporção é desenhada nativamente. O Template Mestre HF7 continua congelado.
    """
    W, H = int(size[0]), int(size[1])
    p = _template_palette_from_override(cfg, palette_override)
    white = (255, 255, 255, 255)
    blue = _hex(p["azul"]); dark = _hex(p["azul_escuro"]); pink = _hex(p["rosa"])
    yellow = _hex(p["amarelo"]); green = _hex(p["verde"])
    pale = _hex(p.get("azul_claro", "#DDF5FF"))
    canvas = Image.new("RGBA", (W, H), white)
    draw = ImageDraw.Draw(canvas, "RGBA")
    source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    profile = _product_profile(title, description, subtitle)
    apps = _default_applications(profile, title)[:4]
    benefits = list(profile.get("benefits") or [])[:5]
    footer = list(ANNA_PROMPT_SPEC["rodape"])[:4]
    t1 = str(profile.get("title1") or title or "AlphaFest").strip()
    t2 = str(profile.get("title2") or "").strip()
    low_title = str(title or "").casefold()
    badge = str(ANNA_PROMPT_SPEC["selo_superior"])
    center_text = re.sub(r"\s+", " ", str(profile.get("center") or "Cada detalhe, cada sorriso!").replace("\n", " ")).strip()
    slogan = str(ANNA_PROMPT_SPEC["faixa_emocional"])
    phone_text = _format_phone_br(phone or "(11) 97294-9533")
    cta_label = str(ANNA_PROMPT_SPEC["cta"])
    ratio = W / max(1, H)
    is_story = ratio < .72
    is_landscape = ratio > 1.32
    is_square = .90 <= ratio <= 1.10

    def sc(v: float) -> int:
        return max(1, int(min(W, H) * v))

    def commercial_copy() -> tuple[str, str]:
        clean_desc = re.sub(r"\s+", " ", str(description or "")).strip()
        if any(k in low_title for k in ("gravação", "gravacao", "laser")):
            return (
                "PERSONALIZAÇÃO QUE VALORIZA CADA DETALHE!",
                "Transforme copos, brindes e presentes em peças únicas, com gravação durável e acabamento profissional.",
            )
        if any(k in low_title for k in ("carimbo", "doces", "brigadeiro")):
            return (
                "MAIS CHARME, MAIS SABOR E MUITO MAIS VENDAS!",
                "Os Carimbos para Doces AlphaFest deixam brigadeiros, doces finos e confeitos ainda mais irresistíveis!",
            )
        if any(k in low_title for k in ("vela", "velas")):
            return (
                "PERSONALIZADO DO SEU JEITO!",
                "Escolha personagem, nome, idade e tema para criar uma lembrança única e cheia de presença.",
            )
        return (
            "UM DETALHE PERSONALIZADO MUDA TUDO!",
            clean_desc[:220] or "Criado para valorizar seu produto, sua festa e cada momento especial.",
        )

    emotional_head, emotional_body = commercial_copy()

    promise = re.sub(r"\s+", " ", str(profile.get("subtitle") or subtitle or "Personalizado do seu jeito!")).strip()
    if any(k in low_title for k in ("gravação", "gravacao", "laser")):
        promise_display = "Personalização durável para presentes, brindes e empresas"
    elif len(promise) > 62:
        promise_display = "Personalização feita para valorizar cada detalhe"
    else:
        promise_display = promise

    def decorate():
        # HF53.3-HF8-HF5: linguagem visual fixa do prompt premium. O fundo deixa de parecer uma
        # tela vazia do sistema e ganha continuidade visual com a marca AlphaFest.
        draw.pieslice((-int(W*.25), -int(H*.10), int(W*.42), int(H*.15)), 0, 180, fill=dark)
        draw.pieslice((-int(W*.22), -int(H*.07), int(W*.38), int(H*.125)), 0, 180, fill=blue)
        draw.pieslice((int(W*.70), -int(H*.09), int(W*1.20), int(H*.14)), 0, 180, fill=dark)
        draw.pieslice((int(W*.75), -int(H*.055), int(W*1.18), int(H*.115)), 0, 180, fill=blue)
        # ondas/halos suaves que conectam produto, benefícios e CTA.
        draw.ellipse((int(W*.44),int(H*.19),int(W*1.08),int(H*.70)),fill=(*pale[:3],105))
        draw.arc((int(W*.42),int(H*.20),int(W*1.05),int(H*.72)),205,335,fill=(*blue[:3],165),width=max(5,sc(.004)))
        draw.arc((int(W*.45),int(H*.23),int(W*1.02),int(H*.69)),210,330,fill=(*pink[:3],130),width=max(3,sc(.0025)))
        dots = [
            (.025,.18,blue,.010),(.07,.125,pink,.007),(.12,.17,yellow,.006),(.20,.11,blue,.006),
            (.76,.14,pink,.009),(.84,.105,yellow,.007),(.95,.17,blue,.009),(.91,.23,pink,.006),
            (.45,.66,blue,.009),(.50,.70,pink,.011),(.56,.68,yellow,.007),(.62,.73,blue,.006),
            (.30,.76,pink,.005),(.70,.76,yellow,.005),(.94,.62,blue,.006),
        ]
        for x,y,c,r in dots:
            rr=sc(r); cx=int(W*x); cy=int(H*y)
            draw.ellipse((cx-rr,cy-rr,cx+rr,cy+rr), fill=c)
            if rr>5:
                draw.ellipse((cx-rr//3,cy-rr//2,cx+rr//5,cy-rr//6),fill=(255,255,255,145))
        for x,y,c in ((.02,.32,blue),(.98,.30,pink),(.60,.73,blue),(.67,.70,pink),(.39,.81,blue)):
            cx=int(W*x); cy=int(H*y); rr=sc(.008)
            draw.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=c)
            draw.ellipse((cx-rr//2,cy-rr*2,cx+rr//2,cy),fill=c)

    def logo(max_w: int, max_h: int, y: int):
        # Regra fixa da Anna: apenas o splash compacto aprovado no cabeçalho.
        splash = BASE_DIR / "assets" / "mascotes" / "logo_novo_alphafest.png"
        candidate = splash if splash.exists() else logo_path
        try:
            im = _trim_transparent(Image.open(candidate).convert("RGBA"))
            im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        except Exception:
            im = _load_logo(candidate, (max_w, max_h))
        if im:
            canvas.alpha_composite(im, ((W-im.width)//2, y))

    def approval_seal(cx: int, cy: int, r: int):
        draw.ellipse((cx-r-5,cy-r-5,cx+r+5,cy+r+5),fill=white,outline=blue,width=max(3,r//16))
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=dark,outline=white,width=max(3,r//15))
        _draw_check(draw,cx,cy-int(r*.45),max(12,int(r*.18)),white,icon="heart",icon_color=dark)
        lines=[x.strip() for x in badge.split("\n") if x.strip()] or ["APROVADO"]
        f=_fit_font(draw,max(lines,key=len),int(r*1.55),max(23,int(r*.31)),max(15,int(r*.20)),bold=True)
        lh=max(18,draw.textbbox((0,0),"Ag",font=f)[3]+1)
        yy=cy-int(lh*len(lines)*.20)
        for line in lines:
            bb=draw.textbbox((0,0),line,font=f)
            draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=f,fill=white)
            yy+=lh

    def big_title(x: int, y: int, max_w: int, max_h: int) -> int:
        # Manchete comercial: ocupa o espaço como na referência da Anna.
        # Sombra curta + contorno dão leitura forte mesmo no preview do Manager.
        f1=_fit_font(draw,t1,max_w,max(122,int(max_h*.72)),max(68,int(max_h*.44)),bold=True,serif=True,italic=True)
        lines1=_wrap_complete(draw,t1,f1,max_w)[:2]
        yy=y; lh1=max(72,draw.textbbox((0,0),"Ag",font=f1)[3]+1)
        for line in lines1:
            draw.text((x+7,yy+8),line,font=f1,fill=(*blue[:3],120),stroke_width=max(2,sc(.002)),stroke_fill=(255,255,255,80))
            draw.text((x,yy),line,font=f1,fill=dark,stroke_width=max(2,sc(.0018)),stroke_fill=white)
            yy+=lh1
        if t2:
            f2=_fit_font(draw,t2,max_w,max(92,int(max_h*.54)),max(54,int(max_h*.35)),bold=True,serif=True,italic=True)
            for line in _wrap_complete(draw,t2,f2,max_w)[:2]:
                draw.text((x+4,yy+4),line,font=f2,fill=(*dark[:3],95))
                draw.text((x,yy),line,font=f2,fill=blue,stroke_width=max(2,sc(.0014)),stroke_fill=white)
                yy+=max(60,draw.textbbox((0,0),"Ag",font=f2)[3]+1)
        return yy

    def promise_ribbon(x1: int, y1: int, x2: int, y2: int):
        h=y2-y1
        draw.polygon([(x1,y1+int(h*.16)),(x1-int(h*.36),y1+int(h*.50)),(x1,y2-int(h*.16))],fill=blue)
        draw.polygon([(x2,y1+int(h*.16)),(x2+int(h*.36),y1+int(h*.50)),(x2,y2-int(h*.16))],fill=blue)
        draw.rounded_rectangle((x1,y1,x2,y2),radius=max(10,h//5),fill=dark)
        f=_fit_font(draw,promise_display,int((x2-x1)*.88),max(28,int(h*.44)),max(15,int(h*.23)),bold=True)
        lines=_wrap_complete(draw,promise_display,f,int((x2-x1)*.88))[:2]
        lh=max(20,draw.textbbox((0,0),"Ag",font=f)[3]+1)
        yy=(y1+y2)//2-(lh*len(lines))//2
        for line in lines:
            bb=draw.textbbox((0,0),line,font=f)
            draw.text(((x1+x2-(bb[2]-bb[0]))//2,yy),line,font=f,fill=white)
            yy+=lh

    def emotional_box(x: int, y: int, width: int, height: int):
        # Sem borda dura: cartão branco suave como na referência dos carimbos.
        shadow=Image.new("RGBA",(width+18,height+18),(0,0,0,0))
        sd=ImageDraw.Draw(shadow,"RGBA")
        sd.rounded_rectangle((8,8,width+8,height+8),radius=max(24,int(height*.12)),fill=(18,48,100,35))
        shadow=shadow.filter(ImageFilter.GaussianBlur(8)); canvas.alpha_composite(shadow,(x-8,y-8))
        draw.rounded_rectangle((x,y,x+width,y+height),radius=max(22,int(height*.11)),fill=(255,255,255,247),outline=(*pale[:3],170),width=max(2,sc(.0014)))
        heart_r=max(9,int(height*.045)); _draw_check(draw,x+28,y+30,heart_r,pink,icon="heart",icon_color=white)
        hf=_fit_font(draw,emotional_head,width-78,max(30,int(height*.18)),max(20,int(height*.13)),bold=True)
        hlines=_wrap_complete(draw,emotional_head,hf,width-78)[:3]
        yy=y+14
        for line in hlines:
            draw.text((x+54,yy),line,font=hf,fill=pink); yy+=max(25,draw.textbbox((0,0),"Ag",font=hf)[3]+2)
        bf=_fit_font(draw,emotional_body,width-48,max(24,int(height*.12)),max(17,int(height*.09)),bold=False)
        blines=_wrap_complete(draw,emotional_body,bf,width-48)[:5]
        yy=max(yy+8,y+int(height*.48))
        for line in blines:
            draw.text((x+24,yy),line,font=bf,fill=(24,34,54,255)); yy+=max(20,draw.textbbox((0,0),"Ag",font=bf)[3]+2)

    def benefits_block(x: int, y: int, width: int, item_h: int):
        icons=["star","heart","diamond","check","heart"]
        for i,(head,desc,icon) in enumerate(benefits[:5]):
            top=y+i*item_h
            rr=max(29,int(item_h*.31)); use_icon=icon if icon in {"star","heart","diamond","check"} else icons[i%5]
            _draw_check(draw,x+rr,top+rr+2,rr,dark,icon=use_icon,icon_color=white)
            tx=x+rr*2+20; maxw=width-(tx-x)
            hf=_fit_font(draw,str(head).upper(),maxw,max(40,int(item_h*.36)),max(27,int(item_h*.27)),bold=True)
            draw.text((tx,top-1),str(head).upper(),font=hf,fill=dark)
            df=_fit_font(draw,str(desc),maxw,max(30,int(item_h*.27)),max(20,int(item_h*.20)),bold=False)
            lines=_wrap_complete(draw,str(desc),df,maxw)[:3]
            dy=top+max(35,draw.textbbox((0,0),"Ag",font=hf)[3]+2)
            for line in lines:
                draw.text((tx,dy),line,font=df,fill=(20,31,51,255)); dy+=max(23,draw.textbbox((0,0),"Ag",font=df)[3]+1)
            draw.line((tx,top+item_h+1,x+width,top+item_h+1),fill=(*dark[:3],135),width=max(2,sc(.0014)))

    def product_stage(box: tuple[int,int,int,int]):
        x1,y1,x2,y2=box; bw=x2-x1; bh=y2-y1
        # Palco grande: produto deixa de parecer uma miniatura solta e passa a
        # dominar a metade direita, como nos exemplos aprovados pela Anna.
        draw.ellipse((x1-int(bw*.05),y1+int(bh*.04),x2+int(bw*.03),y2-int(bh*.01)),fill=(*pale[:3],150))
        draw.arc((x1-int(bw*.03),y1+int(bh*.05),x2+int(bw*.02),y2-int(bh*.01)),215,335,fill=(*blue[:3],150),width=max(5,sc(.004)))
        draw.ellipse((x1-int(bw*.02),y2-int(bh*.16),x2+int(bw*.01),y2+int(bh*.02)),fill=(*yellow[:3],235))
        _paste_photo(canvas,source,box,max(18,sc(.024)),mode=photo_mode,product_title=title,upscale=True)

    def message_badge(cx: int, cy: int, r: int):
        draw.ellipse((cx-r-5,cy-r-5,cx+r+5,cy+r+5),fill=white,outline=blue,width=max(3,sc(.0025)))
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(255,255,255,252),outline=(*blue[:3],130),width=max(2,sc(.0015)))
        _draw_check(draw,cx,cy-int(r*.58),max(9,int(r*.12)),blue,icon="heart",icon_color=white)
        f=_fit_font(draw,center_text,int(r*1.50),max(22,int(r*.22)),max(14,int(r*.15)),bold=True)
        lines=_wrap_complete(draw,center_text,f,int(r*1.50))[:5]; lh=max(17,draw.textbbox((0,0),"Ag",font=f)[3]+1); yy=cy-(lh*len(lines))//2+int(r*.04)
        for line in lines:
            bb=draw.textbbox((0,0),line,font=f); draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=f,fill=dark); yy+=lh

    def applications(y: int, h: int, left: int, right: int):
        """Cards visuais reais. Vitrine de aplicações com círculos fotográficos + legendas, nunca botões de sistema."""
        width=right-left
        tag="Ideal para:"; tagw=int(width*.23); tagh=max(38,int(h*.20)); tx=left+4
        # faixa azul curta, no estilo de etiqueta publicitária.
        draw.polygon([(tx,y+tagh//2),(tx+18,y-5),(tx+tagw-8,y-5),(tx+tagw+18,y+tagh//2),(tx+tagw-8,y+tagh),(tx+18,y+tagh)],fill=dark)
        tf=_fit_font(draw,tag,int(tagw*.78),max(25,int(tagh*.56)),max(15,int(tagh*.38)),bold=True)
        bb=draw.textbbox((0,0),tag,font=tf); draw.text((tx+(tagw-(bb[2]-bb[0]))//2,y+(tagh-(bb[3]-bb[1]))//2-bb[1]),tag,font=tf,fill=white)
        imgs=[]; seen=set()
        for raw in (application_images or []):
            try:
                im=Image.open(io.BytesIO(raw)).convert("RGBA"); sig=(im.width,im.height,hash(raw[:256]))
                if sig not in seen: seen.add(sig); imgs.append(im)
            except Exception: pass
        count=4; gap=max(10,int(width*.018)); cellw=(width-gap*(count-1))//count
        top=y+tagh+max(6,int(h*.03)); circle_d=min(int(cellw*.78),int(h*.58)); label_h=max(28,int(h*.18))
        for i,label in enumerate(apps[:4]):
            cx=left+i*(cellw+gap)+cellw//2; cy=top+circle_d//2
            # sombra e aro branco/azul, como mini-vitrine da referência.
            draw.ellipse((cx-circle_d//2+5,cy-circle_d//2+7,cx+circle_d//2+5,cy+circle_d//2+7),fill=(5,40,100,40))
            draw.ellipse((cx-circle_d//2-4,cy-circle_d//2-4,cx+circle_d//2+4,cy+circle_d//2+4),fill=white,outline=blue,width=max(2,sc(.0016)))
            if i<len(imgs):
                im=ImageOps.fit(imgs[i],(circle_d,circle_d),method=Image.Resampling.LANCZOS)
                mask=Image.new("L",(circle_d,circle_d),0); ImageDraw.Draw(mask).ellipse((0,0,circle_d-1,circle_d-1),fill=255)
                canvas.paste(im,(cx-circle_d//2,cy-circle_d//2),mask)
            elif i==0:
                # primeira aplicação usa a própria foto do produto, sem repetir em todos os cards.
                im=ImageOps.fit(source,(circle_d,circle_d),method=Image.Resampling.LANCZOS)
                mask=Image.new("L",(circle_d,circle_d),0); ImageDraw.Draw(mask).ellipse((0,0,circle_d-1,circle_d-1),fill=255)
                canvas.paste(im,(cx-circle_d//2,cy-circle_d//2),mask)
            else:
                icon_c=[pink,yellow,blue][(i-1)%3]; rr=max(18,int(circle_d*.26))
                draw.ellipse((cx-circle_d//2,cy-circle_d//2,cx+circle_d//2,cy+circle_d//2),fill=(*pale[:3],220))
                _draw_check(draw,cx,cy,rr,icon_c,icon=["heart","diamond","star"][i-1],icon_color=white if i!=2 else dark)
            pill_y=cy+circle_d//2+max(4,int(h*.018)); pill_w=int(cellw*.92)
            draw.rounded_rectangle((cx-pill_w//2,pill_y,cx+pill_w//2,pill_y+label_h),radius=label_h//2,fill=dark)
            lf=_fit_font(draw,label,int(pill_w*.86),max(23,int(label_h*.60)),max(14,int(label_h*.42)),bold=True)
            lines=_wrap_complete(draw,label,lf,int(pill_w*.83))[:2]; lh=max(14,draw.textbbox((0,0),"Ag",font=lf)[3]+1); yy=pill_y+(label_h-lh*len(lines))//2
            for line in lines:
                bb=draw.textbbox((0,0),line,font=lf); draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=lf,fill=white); yy+=lh

    def cta_box(box: tuple[int,int,int,int]):
        x1,y1,x2,y2=box; h=y2-y1
        draw.rounded_rectangle(box,radius=max(28,int(h*.30)),fill=dark,outline=blue,width=max(3,sc(.0025)))
        r=int(h*.34); _draw_whatsapp(draw,x1+int(h*.48),(y1+y2)//2,r,green)
        tx=x1+int(h*1.00); avail=x2-tx-int(h*.10)
        compact = avail < 330
        lf=_fit_font(draw,cta_label,avail,24 if compact else max(31,int(h*.24)),14 if compact else max(17,int(h*.15)),bold=True)
        lbb=draw.textbbox((0,0),cta_label,font=lf)
        draw.text((tx,y1+max(5,int(h*.07))-lbb[1]),cta_label,font=lf,fill=white)
        pf=_fit_font(draw,phone_text,avail,36 if compact else max(49,int(h*.40)),20 if compact else max(23,int(h*.20)),bold=True)
        pbb=draw.textbbox((0,0),phone_text,font=pf)
        py=y2-int(h*.08)-(pbb[3]-pbb[1])-pbb[1]
        draw.text((tx,py),phone_text,font=pf,fill=white)

    def slogan_box(box: tuple[int,int,int,int]):
        x1,y1,x2,y2=box; h=y2-y1; mid=(y1+y2)//2
        # faixa rosa tipo pincel, visível e emocional.
        pts=[(x1+10,y1+int(h*.16)),(x1+int((x2-x1)*.10),y1),(x2-int((x2-x1)*.08),y1+int(h*.08)),(x2-4,mid),(x2-int((x2-x1)*.08),y2-int(h*.08)),(x1+int((x2-x1)*.08),y2),(x1+4,mid)]
        draw.polygon(pts,fill=(*pink[:3],248))
        f=_fit_font(draw,slogan,int((x2-x1)*.86),max(34,int(h*.36)),max(20,int(h*.24)),bold=True,serif=True,italic=True)
        lines=_wrap_complete(draw,slogan,f,int((x2-x1)*.86))[:2]; lh=max(24,draw.textbbox((0,0),"Ag",font=f)[3]+2); yy=mid-(lh*len(lines))//2
        for line in lines:
            bb=draw.textbbox((0,0),line,font=f); draw.text(((x1+x2-(bb[2]-bb[0]))//2,yy),line,font=f,fill=white); yy+=lh

    def footer_band(y1: int, y2: int):
        draw.rectangle((0,y1,W,y2),fill=dark); cw=W//4
        for i,label in enumerate(footer[:4]):
            r=max(12,int((y2-y1)*.24)); _draw_check(draw,i*cw+int(cw*.14),(y1+y2)//2,r,white,icon="check",icon_color=dark)
            maxw=int(cw*.69); ff=_fit_font(draw,label,maxw,max(22,int((y2-y1)*.30)),max(14,int((y2-y1)*.19)),bold=True)
            lines=_wrap_complete(draw,label,ff,maxw)[:2]; lh=max(15,draw.textbbox((0,0),"Ag",font=ff)[3]+1); yy=(y1+y2)//2-(lh*len(lines))//2
            for line in lines:
                draw.text((i*cw+int(cw*.27),yy),line,font=ff,fill=white); yy+=lh
            if i<3: draw.line(((i+1)*cw,y1+int((y2-y1)*.16),(i+1)*cw,y2-int((y2-y1)*.16)),fill=(255,255,255,110),width=2)

    decorate()

    if is_square:
        # Facebook / post quadrado — composição baseada diretamente no prompt aprovado.
        logo(int(W*.50),int(H*.25),-10)
        approval_seal(int(W*.90),int(H*.115),int(W*.083))
        title_end=big_title(int(W*.035),int(H*.155),int(W*.58),int(H*.245))
        rib_y=max(int(H*.385),title_end+2)
        promise_ribbon(int(W*.045),rib_y,int(W*.57),rib_y+int(H*.075))
        product_stage((int(W*.53),int(H*.20),int(W*.995),int(H*.68)))
        benefit_y=max(int(H*.46),rib_y+int(H*.09))
        benefits_block(int(W*.035),benefit_y,int(W*.45),int(H*.065))
        message_badge(int(W*.78),int(H*.68),int(W*.082))
        applications(int(H*.755),int(H*.145),int(W*.025),int(W*.56))
        cta_box((int(W*.59),int(H*.765),int(W*.985),int(H*.875)))
        slogan_box((int(W*.58),int(H*.885),int(W*.985),int(H*.945)))
        footer_band(int(H*.955),H)
        return canvas

    if is_story:
        # Story/Status: reduz texto, mantém produto e CTA gigantes.
        logo(int(W*.52),int(H*.18),-2)
        approval_seal(int(W*.88),int(H*.075),int(W*.085))
        title_end=big_title(int(W*.045),int(H*.13),int(W*.72),int(H*.15))
        rib_y=max(int(H*.265),title_end+4)
        promise_ribbon(int(W*.055),rib_y,int(W*.94),rib_y+int(H*.055))
        product_stage((int(W*.45),int(H*.315),int(W*.995),int(H*.625)))
        benefits_block(int(W*.04),int(H*.42),int(W*.42),int(H*.052))
        message_badge(int(W*.78),int(H*.64),int(W*.092))
        applications(int(H*.735),int(H*.125),int(W*.04),int(W*.96))
        cta_box((int(W*.045),int(H*.865),int(W*.955),int(H*.93)))
        slogan_box((int(W*.14),int(H*.936),int(W*.86),int(H*.968)))
        footer_band(int(H*.976),H)
        return canvas

    if is_landscape:
        logo(int(W*.27),int(H*.27),-8)
        approval_seal(int(W*.94),int(H*.14),int(H*.082))
        title_end=big_title(int(W*.025),int(H*.12),int(W*.42),int(H*.25))
        rib_y=max(int(H*.395),title_end+2)
        promise_ribbon(int(W*.035),rib_y,int(W*.43),rib_y+int(H*.09))
        benefits_block(int(W*.025),max(int(H*.50),rib_y+int(H*.105)),int(W*.42),int(H*.072))
        product_stage((int(W*.46),int(H*.08),int(W*.995),int(H*.70)))
        message_badge(int(W*.77),int(H*.67),int(H*.090))
        applications(int(H*.735),int(H*.17),int(W*.45),int(W*.70))
        cta_box((int(W*.70),int(H*.745),int(W*.99),int(H*.87)))
        slogan_box((int(W*.70),int(H*.88),int(W*.99),int(H*.93)))
        footer_band(int(H*.945),H)
        return canvas

    # Instagram Feed 4:5 — grade final da versão completa, com a mesma linguagem do prompt quadrado.
    logo(int(W*.52),int(H*.22),-8)
    approval_seal(int(W*.90),int(H*.085),int(W*.082))
    title_end=big_title(int(W*.035),int(H*.145),int(W*.57),int(H*.18))
    rib_y=max(int(H*.315),title_end+2)
    promise_ribbon(int(W*.045),rib_y,int(W*.58),rib_y+int(H*.06))
    product_stage((int(W*.50),int(H*.205),int(W*.995),int(H*.655)))
    benefits_block(int(W*.035),max(int(H*.405),rib_y+int(H*.075)),int(W*.44),int(H*.062))
    message_badge(int(W*.80),int(H*.665),int(W*.078))
    applications(int(H*.735),int(H*.125),int(W*.025),int(W*.975))
    cta_box((int(W*.025),int(H*.865),int(W*.975),int(H*.925)))
    slogan_box((int(W*.16),int(H*.932),int(W*.84),int(H*.958)))
    footer_band(int(H*.966),H)
    return canvas


def _render_splash_premium_square(image_bytes: bytes, *, title: str, subtitle: str, description: str, price: str, cta: str, phone: str, logo_path: Path, cfg: dict[str,Any], palette_override: dict[str,str] | None = None, photo_mode: str = "auto", application_images: list[bytes] | None = None) -> Image.Image:
    """Compatibilidade: deriva o quadrado a partir do novo mestre 4:5 HF53.2-HF5."""
    portrait=_render_splash_premium_portrait(image_bytes,title=title,subtitle=subtitle,description=description,price=price,cta=cta,phone=phone,logo_path=logo_path,cfg=cfg,palette_override=palette_override,photo_mode=photo_mode,application_images=application_images)
    return _adapt_master_portrait_to_channel(portrait,(1080,1080),cfg,palette_override)

def _render_square(image_bytes: bytes, *, title: str, subtitle: str, description: str, price: str, cta: str, phone: str, logo_path: Path, cfg: dict[str,Any], palette_override: dict[str,str] | None = None, photo_mode: str = "auto") -> Image.Image:
    if str(cfg.get("source")) == "library":
        profile = _product_profile(title, description, subtitle)
        profile["applications"] = _default_applications(profile, title)
        return render_library_square(
            cfg, image_bytes=image_bytes, title=title, subtitle=subtitle, description=description,
            price=price, cta=cta, phone=phone, profile=profile, photo_mode=photo_mode, palette=palette_override,
        )
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
    phone_text=_format_phone_br(phone or "(11) 97294-9533")
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
    phone: str="(11) 97294-9533",
    logo_path: str|Path|None=None,
    palette_override: dict[str,str] | None=None,
    photo_mode: str="auto",
    application_images: list[bytes] | None=None,
) -> bytes:
    cfg=carregar_template(template_id)
    _logo=Path(logo_path or BASE_DIR/"logo.png")
    if str(cfg.get("id")) == "splash_premium_anna" and str(cfg.get("source")) != "library":
        portrait=_render_splash_premium_portrait(
            image_bytes, title=title, subtitle=subtitle, description=description, price=price,
            cta=cta, phone=phone, logo_path=_logo, cfg=cfg,
            palette_override=palette_override, photo_mode=photo_mode, application_images=application_images,
        )
        final=_adapt_master_portrait_to_channel(portrait,size,cfg,palette_override)
    elif str(cfg.get("id")) == "anna_social_redes" and str(cfg.get("source")) != "library":
        # HF53.3-HF8-HF11: renderer Anna independente homologado no Modelo Anna 1. Não reutiliza o compositor
        # visual antigo nem o Template Mestre. O perfil textual continua vindo da mesma fonte
        # de dados, mas toda a composição é construída em marketing_anna_renderer.py.
        _profile = _product_profile(title, description, subtitle)
        _profile["applications"] = _default_applications(_profile, title)
        final = render_anna_prompt(
            image_bytes, size, title=title, subtitle=subtitle, description=description, phone=phone,
            profile=_profile, palette=_template_palette_from_override(cfg, palette_override),
            base_dir=BASE_DIR, photo_mode=photo_mode, application_images=application_images,
        )
    else:
        square=_render_square(
            image_bytes,
            title=title,
            subtitle=subtitle,
            description=description,
            price=price,
            cta=cta,
            phone=phone,
            logo_path=_logo,
            cfg=cfg,
            palette_override=palette_override,
            photo_mode=photo_mode,
        )
        final=_adapt_channel(square,size,cfg,palette_override)
    output=io.BytesIO()
    final.convert("RGB").save(output,"PNG",optimize=True)
    return output.getvalue()
