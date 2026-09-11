"""Renderer independente do Template Anna — Prompt Premium.

HF53.3-HF8-HF11: este módulo não reutiliza a composição visual do Template Mestre
nem o compositor legado. Ele recebe somente dados já preparados pelo motor e
constrói nativamente cada proporção do Template Anna.
"""
from __future__ import annotations

import io
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageEnhance, ImageChops
from alphafest_font_manager import get_font

ANNA_RENDERER_VERSION = "HF53.3-HF8-HF11"


def _font(size: int, *, bold: bool = False, serif: bool = False, italic: bool = False):
    return get_font(max(8, int(size)), bold=bold, serif=serif, italic=italic)


def _hex(value: str, alpha: int = 255):
    raw = str(value or "#000000").lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    try:
        return tuple(int(raw[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
    except Exception:
        return (0, 0, 0, alpha)


def _fit(draw: ImageDraw.ImageDraw, text: str, width: int, start: int, minimum: int, *, bold=True, serif=False, italic=False):
    text = str(text or "")
    for size in range(int(start), int(minimum) - 1, -2):
        f = _font(size, bold=bold, serif=serif, italic=italic)
        box = draw.textbbox((0, 0), text, font=f, stroke_width=1)
        if box[2] - box[0] <= width:
            return f
    return _font(minimum, bold=bold, serif=serif, italic=italic)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int = 3) -> list[str]:
    words = re.sub(r"\s+", " ", str(text or "")).strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), trial, font=font)[2] <= width:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    # acrescenta palavras remanescentes na última linha reduzindo só se necessário
    consumed = len(" ".join(lines).split())
    if consumed < len(words) and lines:
        rest = " ".join(words[consumed:])
        candidate = (lines[-1] + " " + rest).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            lines[-1] = candidate
    return lines[:max_lines]


def _load_logo(base_dir: Path, max_size: tuple[int, int]) -> Image.Image | None:
    candidates = [
        base_dir / "assets" / "mascotes" / "logo_novo_alphafest.png",
        base_dir / "logo.png",
        base_dir / "assets" / "logo.png",
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            logo = Image.open(path).convert("RGBA")
            # Remove pixels quase transparentes do arquivo do splash; o getbbox puro
            # mantinha uma grande margem invisível e fazia o logo parecer minúsculo.
            alpha = logo.getchannel("A")
            solid = alpha.point(lambda v: 255 if v >= 24 else 0)
            bbox = solid.getbbox() or logo.getbbox()
            if bbox:
                logo = logo.crop(bbox)
            logo.thumbnail(max_size, Image.Resampling.LANCZOS)
            return logo
        except Exception:
            continue
    return None

def _load_skin_master(base_dir: Path) -> Image.Image | None:
    """Carrega a pele gráfica aprovada do Modelo Anna 1.

    A skin guarda somente elementos fixos de alta fidelidade (topo/splash/logo/selo
    e rodapé). Título, foto, benefícios, aplicações e CTA continuam dinâmicos.
    """
    path = base_dir / "assets" / "marketing" / "anna_skin_master_1.png"
    try:
        return Image.open(path).convert("RGBA") if path.exists() else None
    except Exception:
        return None

def _load_model_reference(base_dir: Path) -> Image.Image | None:
    """Carrega a arte aprovada do Modelo Anna 1.

    Esta referência é usada como base fiel quando o renderer precisa reproduzir
    exatamente o visual homologado de `Gravação Laser`, sem reinventar a
    tipografia, o contorno multicamada ou a relação do título com o splash.
    """
    path = base_dir / "assets" / "marketing" / "anna_skin_master_1_reference.png"
    try:
        return Image.open(path).convert("RGBA") if path.exists() else None
    except Exception:
        return None


def _slug_text(value: str) -> str:
    raw = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", raw).strip().casefold()
    return raw


def _is_modelo_anna_1_locked(title: str) -> bool:
    return _slug_text(title) == "gravacao laser"



def _soft_shadow(layer: Image.Image, blur: int = 18, opacity: int = 80) -> Image.Image:
    alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(blur))
    shadow = Image.new("RGBA", layer.size, (0, 25, 70, 0))
    shadow.putalpha(alpha.point(lambda v: int(v * opacity / 255)))
    return shadow


def _corner_uniform(source: Image.Image) -> tuple[tuple[int, int, int], float]:
    rgb = source.convert("RGB")
    pts = [rgb.getpixel((2, 2)), rgb.getpixel((rgb.width-3, 2)), rgb.getpixel((2, rgb.height-3)), rgb.getpixel((rgb.width-3, rgb.height-3))]
    mean = tuple(sum(p[i] for p in pts)//4 for i in range(3))
    spread = sum(math.dist(p, mean) for p in pts) / 4
    return mean, spread


def _remove_simple_background(source: Image.Image) -> Image.Image:
    src = source.convert("RGBA")
    bg, spread = _corner_uniform(src)
    if spread > 52:  # fundo muito variável: preservar foto
        return src
    try:
        import numpy as np
        arr = np.asarray(src).copy()
        rgb = arr[:, :, :3].astype(np.float32)
        bgv = np.array(bg, dtype=np.float32).reshape((1, 1, 3))
        dist = np.sqrt(((rgb - bgv) ** 2).sum(axis=2))
        alpha = np.clip((dist - 20.0) / 50.0 * 255.0, 0, 255).astype(np.uint8)
        arr[:, :, 3] = np.minimum(arr[:, :, 3], alpha)
        src = Image.fromarray(arr, mode="RGBA")
    except Exception:
        # fallback sem dependência vetorial; usado apenas em ambientes mínimos
        data = list(src.getdata())
        out = []
        for r, g, b, a in data:
            dist = math.sqrt((r-bg[0])**2 + (g-bg[1])**2 + (b-bg[2])**2)
            na = 0 if dist < 20 else (int((dist-20)/50*255) if dist < 70 else 255)
            out.append((r, g, b, min(a, na)))
        src.putdata(out)
    bbox = src.getbbox()
    return src.crop(bbox) if bbox else source.convert("RGBA")


def _remove_grabcut_background(source: Image.Image) -> Image.Image | None:
    """Recorte assistido para fotos de produto com fundo real.

    O Template Anna precisa de produto integrado à composição. Quando o fundo não é
    uniforme, tenta GrabCut (OpenCV) de forma conservadora e volta ao modo fotográfico
    se a máscara não parecer confiável.
    """
    try:
        import cv2
        import numpy as np
        src = source.convert("RGB")
        arr = np.asarray(src)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        if min(h, w) < 120:
            return None
        mask = np.zeros((h, w), np.uint8)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        # Produto costuma estar no miolo da foto do catálogo; preserva uma margem
        # suficiente para alças/tampas e evita classificar as bordas como produto.
        rect = (max(2, int(w*.025)), max(2, int(h*.08)), max(4, int(w*.95)), max(4, int(h*.80)))
        cv2.grabCut(bgr, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
        fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        ratio = float((fg > 0).mean())
        if ratio < .06 or ratio > .72:
            return None
        kernel = np.ones((3,3), np.uint8)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=1)
        fg = cv2.GaussianBlur(fg, (7,7), 0)
        rgba = np.dstack([arr, fg])
        out = Image.fromarray(rgba, mode="RGBA")
        bbox = out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        return out.crop(bbox) if bbox else None
    except Exception:
        return None


def _product_layer(image_bytes: bytes, box: tuple[int, int, int, int], photo_mode: str = "auto") -> tuple[Image.Image, tuple[int, int]]:
    source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mode = str(photo_mode or "auto").casefold()
    prepared = source
    if mode in {"recortar", "remove", "remover fundo"}:
        prepared = _remove_grabcut_background(source) or _remove_simple_background(source)
    elif mode == "auto":
        bg, spread = _corner_uniform(source)
        if spread < 34 and max(bg) > 145:
            prepared = _remove_simple_background(source)
        else:
            # HF53.3-HF8-HF10: em fundo real/variável, não força GrabCut no modo auto.
            # O recorte automático anterior podia deixar mesa/fundo em polígonos irregulares.
            # O palco oval fotográfico é mais previsível e comercial. GrabCut fica disponível
            # somente quando o usuário pedir explicitamente para recortar/remover fundo.
            prepared = source

    x1, y1, x2, y2 = box
    maxw, maxh = x2-x1, y2-y1
    alpha = prepared.getchannel("A")
    has_transparency = alpha.getextrema() != (255, 255)
    if has_transparency:
        prepared.thumbnail((maxw, maxh), Image.Resampling.LANCZOS)
        return prepared, (x1 + (maxw-prepared.width)//2, y1 + (maxh-prepared.height)//2)

    # HF53.3-HF8-HF11: fallback fotográfico premium com recorte orgânico.
    # Em vez do retângulo arredondado, a foto entra em um palco oval com bordas
    # suavizadas. Isso integra a imagem ao anúncio mesmo quando o recorte automático
    # do produto não é confiável.
    rgb = prepared.convert("RGB")
    try:
        rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
        rgb = ImageEnhance.Sharpness(rgb).enhance(1.20)
        rgb = ImageEnhance.Color(rgb).enhance(1.03)
    except Exception:
        pass
    # HF53.3-HF8-HF11: zoom editorial conservador. A foto do catálogo costuma
    # trazer bastante mesa/fundo; aproximamos o produto antes de encaixar no palco.
    zw, zh = rgb.size
    zoom = 1.18
    cw, ch = max(16, int(zw/zoom)), max(16, int(zh/zoom))
    cx, cy = zw/2.0, zh*0.47
    left = max(0, int(cx-cw/2)); top = max(0, int(cy-ch/2))
    right = min(zw, left+cw); bottom = min(zh, top+ch)
    rgb = rgb.crop((left, top, right, bottom))
    fitted = ImageOps.fit(rgb.convert("RGBA"), (maxw, maxh), method=Image.Resampling.LANCZOS, centering=(.5, .46))
    mask = Image.new("L", (maxw, maxh), 0)
    md = ImageDraw.Draw(mask)
    inset=max(5, min(maxw,maxh)//70)
    md.ellipse((inset, inset, maxw-inset-1, maxh-inset-1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(4, min(maxw, maxh)//65)))
    fitted.putalpha(mask)
    return fitted, (x1, y1)

def _product_stage_photo(image_bytes: bytes, size: tuple[int, int]) -> Image.Image:
    """HF11 — palco fotográfico nítido, sem desfoque do conteúdo.

    Preserva a fotografia original como fonte do palco: sem GaussianBlur, sem
    fundo artificial e sem suavização no miolo. O único feather aplicado fica
    restrito a uma faixa mínima na borda oval para integrar a foto ao layout.
    """
    source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = size
    sw, sh = source.size

    # Zoom moderado: aproxima o produto sem exagerar o recorte nem degradar a foto.
    zoom = 1.16
    cw, ch = max(32, int(sw / zoom)), max(32, int(sh / zoom))
    cx, cy = sw * .50, sh * .49
    left = max(0, min(sw-cw, int(cx-cw/2)))
    top = max(0, min(sh-ch, int(cy-ch/2)))
    crop = source.crop((left, top, left+cw, top+ch))
    sharp = ImageOps.fit(crop, (W, H), Image.Resampling.LANCZOS, centering=(.5, .50))

    # Ajuste leve de nitidez, sem "inventar" textura e sem efeito esfumado.
    try:
        sharp = ImageEnhance.Contrast(sharp).enhance(1.025)
        sharp = ImageEnhance.Sharpness(sharp).enhance(1.10)
        sharp = sharp.filter(ImageFilter.UnsharpMask(radius=.70, percent=80, threshold=3))
    except Exception:
        pass

    scene = sharp.convert("RGBA")
    # Máscara oval quase sólida. Só 1–2 px da borda recebem feather.
    outer = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(outer)
    inset = max(2, min(W,H)//150)
    od.ellipse((inset, inset, W-inset-1, H-inset-1), fill=255)
    outer = outer.filter(ImageFilter.GaussianBlur(1.35))
    scene.putalpha(outer)
    return scene




def _product_stage_photo_modelo_1(image_bytes: bytes, size: tuple[int, int]) -> Image.Image:
    """Palco do Modelo Anna 1 com enquadramento mais aberto e nítido.

    A prévia anterior aproximava demais a foto e acentuava a sensação de
    embaçado. Aqui o crop é mais conservador e a nitidez é tratada de forma
    leve, preservando a foto original do produto.
    """
    source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = size
    sw, sh = source.size
    zoom = 1.02
    cw, ch = max(32, int(sw / zoom)), max(32, int(sh / zoom))
    cx, cy = sw * .50, sh * .50
    left = max(0, min(sw-cw, int(cx-cw/2)))
    top = max(0, min(sh-ch, int(cy-ch/2)))
    crop = source.crop((left, top, left+cw, top+ch))
    sharp = ImageOps.fit(crop, (W, H), Image.Resampling.LANCZOS, centering=(.5, .50))
    try:
        sharp = ImageEnhance.Contrast(sharp).enhance(1.03)
        sharp = ImageEnhance.Sharpness(sharp).enhance(1.20)
        sharp = sharp.filter(ImageFilter.UnsharpMask(radius=1.0, percent=108, threshold=2))
    except Exception:
        pass
    scene = sharp.convert("RGBA")
    outer = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(outer)
    inset = max(2, min(W,H)//155)
    od.ellipse((inset, inset, W-inset-1, H-inset-1), fill=255)
    outer = outer.filter(ImageFilter.GaussianBlur(1.0))
    scene.putalpha(outer)
    return scene


def _render_modelo_anna_1_locked(
    image_bytes: bytes, *, title: str, subtitle: str, description: str, phone: str,
    profile: dict[str, Any], palette: dict[str, str], base_dir: Path, photo_mode: str,
    application_images: list[bytes] | None,
) -> Image.Image | None:
    """Replica o Modelo Anna 1 aprovado para `Gravação Laser`.

    Em vez de reconstruir a manchete na unha, usa a própria referência aprovada
    como base visual fiel do layout. O conteúdo dinâmico que permanece variável
    nesta etapa é a foto do produto dentro do palco oval.
    """
    W = H = 1080
    reference = _load_model_reference(base_dir)
    if reference is None:
        return None
    reference_view = reference.resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")
    # A base aprovada preserva exatamente a mesma letra do modelo enviado.
    # O palco/foto entra por baixo da manchete usando uma máscara de proteção
    # calculada a partir da própria referência aprovada.
    canvas = _skin_without_approval_seal(reference, (W, H)) or reference_view.copy()

    stage_box = (565, 190, 1096, 790)
    sx1, sy1, sx2, sy2 = stage_box
    scene = _product_stage_photo_modelo_1(image_bytes, (sx2-sx1, sy2-sy1))

    # Protege exatamente a manchete aprovada com uma máscara fixa derivada do
    # Modelo Anna 1 em 1080x1080. A foto entra por baixo do lettering, sem
    # depender de heurística de cor e sem reaproveitar pedaços do copo antigo.
    try:
        protect_path = base_dir / "assets" / "marketing" / "anna_modelo1_title_protect_mask.png"
        if protect_path.exists():
            protect_full = Image.open(protect_path).convert("L")
            if protect_full.size != (W, H):
                protect_full = protect_full.resize((W, H), Image.Resampling.LANCZOS)
            protect_crop = protect_full.crop(stage_box)
            inv_protect = ImageOps.invert(protect_crop)
            scene.putalpha(ImageChops.multiply(scene.getchannel("A"), inv_protect))
    except Exception:
        pass

    sh = _soft_shadow(scene, 16, 72)
    canvas.alpha_composite(sh, (sx1+5, sy1+9))
    canvas.alpha_composite(scene, (sx1, sy1))

    # Restaura por último os pixels exatos da manchete aprovada. A máscara é
    # transparente fora do lettering, portanto não cria retângulo/caixa branca.
    try:
        protect_path = base_dir / "assets" / "marketing" / "anna_modelo1_title_protect_mask.png"
        if protect_path.exists():
            protect_full = Image.open(protect_path).convert("L")
            if protect_full.size != (W, H):
                protect_full = protect_full.resize((W, H), Image.Resampling.LANCZOS)
            title_restore = reference_view.copy()
            title_restore.putalpha(protect_full)
            canvas.alpha_composite(title_restore, (0, 0))
    except Exception:
        pass

    # Reaplica o selo emocional circular sobre a borda do palco, como na referência.
    cx, cy, r = 582, 699, 78
    x1, y1, x2, y2 = cx-r-4, cy-r-4, cx+r+4, cy+r+4
    center_crop = reference_view.crop((x1, y1, x2, y2)).convert("RGBA")
    cmask = Image.new("L", center_crop.size, 0)
    ImageDraw.Draw(cmask).ellipse((4, 4, center_crop.width-5, center_crop.height-5), fill=255)
    cmask = cmask.filter(ImageFilter.GaussianBlur(.8))
    try:
        from PIL import ImageChops
        center_crop.putalpha(ImageChops.multiply(center_crop.getchannel("A"), cmask))
    except Exception:
        center_crop.putalpha(cmask)
    canvas.alpha_composite(center_crop, (x1, y1))

    # Garante 1 único selo oficial e sempre como camada final.
    seal = _approval_seal_overlay(reference, (W, H))
    if seal is not None:
        seal_image, seal_pos = seal
        canvas.alpha_composite(seal_image, seal_pos)
    return canvas
def _wa_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, green):
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=green, outline=(255,255,255,255), width=max(4, r//9))
    # balão branco
    rr = int(r*.66)
    draw.ellipse((cx-rr, cy-rr, cx+rr, cy+rr), outline=(255,255,255,255), width=max(4, r//8))
    draw.polygon([(cx-int(r*.46),cy+int(r*.42)),(cx-int(r*.70),cy+int(r*.70)),(cx-int(r*.25),cy+int(r*.57))], fill=(255,255,255,255))
    # handset simples e legível
    draw.arc((cx-int(r*.35),cy-int(r*.32),cx+int(r*.35),cy+int(r*.36)), 125, 315, fill=(255,255,255,255), width=max(5,r//7))


def _icon_circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill, symbol: str):
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=fill)
    f = _font(max(18, int(r*.9)), bold=True)
    bb = draw.textbbox((0,0), symbol, font=f)
    draw.text((cx-(bb[2]-bb[0])//2, cy-(bb[3]-bb[1])//2-bb[1]), symbol, font=f, fill=(255,255,255,255))


def _theme_key(label: str) -> str:
    raw = unicodedata.normalize("NFKD", str(label or "")).encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", " ", raw).strip()


def _draw_theme_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, label: str, fill, dark, white=(255,255,255,255)):
    """Ícone vetorial semântico para os cards `Ideal para`.

    HF53.3-HF8-HF11: a faixa inferior deixa de repetir miniaturas do produto.
    Cada card usa um pictograma coerente com o próprio rótulo, mantendo o
    visual de propaganda e leitura imediata em celular.
    """
    key = _theme_key(label)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=fill)
    lw=max(3, r//8)
    x0,y0=cx,cy

    def line(points, width=lw):
        draw.line(points, fill=white, width=width, joint="curve")

    # Presentes / gift box
    if any(k in key for k in ("presente", "gift")):
        draw.rounded_rectangle((x0-int(r*.55), y0-int(r*.12), x0+int(r*.55), y0+int(r*.48)), radius=max(3,r//9), outline=white, width=lw)
        draw.rectangle((x0-int(r*.62), y0-int(r*.32), x0+int(r*.62), y0-int(r*.08)), outline=white, width=lw)
        line((x0, y0-int(r*.32), x0, y0+int(r*.48)))
        draw.arc((x0-int(r*.38),y0-int(r*.58),x0,y0-int(r*.18)),200,350,fill=white,width=lw)
        draw.arc((x0,y0-int(r*.58),x0+int(r*.38),y0-int(r*.18)),190,340,fill=white,width=lw)
        return

    # Empresas / corporativo / escritórios
    if any(k in key for k in ("empresa", "corporativo", "escritorio", "negocio")):
        draw.rectangle((x0-int(r*.45), y0-int(r*.50), x0+int(r*.45), y0+int(r*.48)), outline=white, width=lw)
        draw.rectangle((x0-int(r*.13), y0+int(r*.12), x0+int(r*.13), y0+int(r*.48)), outline=white, width=max(2,lw-1))
        for yy in (-.28,-.02):
            for xx in (-.25,.05):
                draw.rectangle((x0+int(r*xx), y0+int(r*yy), x0+int(r*(xx+.16)), y0+int(r*(yy+.13))), fill=white)
        return

    # Eventos / festas / aniversários
    if any(k in key for k in ("evento", "festa", "aniversario", "moment")):
        draw.rounded_rectangle((x0-int(r*.52), y0-int(r*.43), x0+int(r*.52), y0+int(r*.42)), radius=max(3,r//10), outline=white, width=lw)
        line((x0-int(r*.52), y0-int(r*.18), x0+int(r*.52), y0-int(r*.18)))
        line((x0-int(r*.28), y0-int(r*.58), x0-int(r*.28), y0-int(r*.30)))
        line((x0+int(r*.28), y0-int(r*.58), x0+int(r*.28), y0-int(r*.30)))
        # pequeno brilho/estrela no calendário
        draw.polygon([(x0,y0-int(r*.04)),(x0+int(r*.08),y0+int(r*.10)),(x0+int(r*.23),y0+int(r*.12)),(x0+int(r*.11),y0+int(r*.22)),(x0+int(r*.15),y0+int(r*.38)),(x0,y0+int(r*.29)),(x0-int(r*.15),y0+int(r*.38)),(x0-int(r*.11),y0+int(r*.22)),(x0-int(r*.23),y0+int(r*.12)),(x0-int(r*.08),y0+int(r*.10))], fill=white)
        return

    # Brindes: troféu
    if any(k in key for k in ("brinde", "premio", "trofeu")):
        draw.arc((x0-int(r*.42),y0-int(r*.50),x0+int(r*.42),y0+int(r*.16)),0,180,fill=white,width=lw)
        line((x0-int(r*.38),y0-int(r*.38),x0-int(r*.55),y0-int(r*.34),x0-int(r*.50),y0-int(r*.02),x0-int(r*.30),y0+int(r*.08)))
        line((x0+int(r*.38),y0-int(r*.38),x0+int(r*.55),y0-int(r*.34),x0+int(r*.50),y0-int(r*.02),x0+int(r*.30),y0+int(r*.08)))
        line((x0,y0+int(r*.08),x0,y0+int(r*.38)))
        line((x0-int(r*.28),y0+int(r*.43),x0+int(r*.28),y0+int(r*.43)))
        return

    # Doces / brigadeiros / confeitaria
    if any(k in key for k in ("brigadeiro", "doce", "confeit", "cupcake")):
        draw.polygon([(x0-int(r*.42),y0+int(r*.02)),(x0+int(r*.42),y0+int(r*.02)),(x0+int(r*.29),y0+int(r*.49)),(x0-int(r*.29),y0+int(r*.49))], outline=white)
        draw.arc((x0-int(r*.45),y0-int(r*.45),x0+int(r*.45),y0+int(r*.18)),190,350,fill=white,width=lw)
        draw.ellipse((x0-int(r*.08),y0-int(r*.50),x0+int(r*.08),y0-int(r*.34)),fill=white)
        return

    # Biscoitos
    if "biscoit" in key or "cookie" in key:
        draw.ellipse((x0-int(r*.48),y0-int(r*.48),x0+int(r*.48),y0+int(r*.48)),outline=white,width=lw)
        for ox,oy in [(-.22,-.20),(.18,-.15),(-.12,.12),(.22,.22)]:
            rr=max(2,r//11); px=x0+int(r*ox); py=y0+int(r*oy); draw.ellipse((px-rr,py-rr,px+rr,py+rr),fill=white)
        return

    # Pasta americana / bolos
    if any(k in key for k in ("pasta americana", "bolo", "cake")):
        draw.rounded_rectangle((x0-int(r*.48),y0-int(r*.05),x0+int(r*.48),y0+int(r*.38)),radius=max(3,r//10),outline=white,width=lw)
        draw.arc((x0-int(r*.48),y0-int(r*.34),x0+int(r*.48),y0+int(r*.16)),180,360,fill=white,width=lw)
        line((x0-int(r*.32),y0+int(r*.13),x0+int(r*.32),y0+int(r*.13)),max(2,lw-1))
        return

    # Lembranças
    if "lembranc" in key:
        draw.polygon([(x0-int(r*.48),y0-int(r*.28)),(x0+int(r*.14),y0-int(r*.28)),(x0+int(r*.48),y0),(x0+int(r*.14),y0+int(r*.28)),(x0-int(r*.48),y0+int(r*.28))],outline=white)
        rr=max(3,r//9); draw.ellipse((x0-int(r*.30)-rr,y0-rr,x0-int(r*.30)+rr,y0+rr),fill=white)
        return

    # Temáticos / temas especiais
    if any(k in key for k in ("tematic", "tema", "especial")):
        pts=[]
        for j in range(10):
            a=-math.pi/2+j*math.pi/5
            rad=r*(.50 if j%2==0 else .22)
            pts.append((x0+int(math.cos(a)*rad),y0+int(math.sin(a)*rad)))
        draw.polygon(pts,outline=white)
        for ox,oy in [(-.52,-.38),(.48,-.35),(.50,.36)]:
            rr=max(2,r//10); px=x0+int(r*ox); py=y0+int(r*oy); draw.ellipse((px-rr,py-rr,px+rr,py+rr),fill=white)
        return

    # Decoração
    if "decor" in key:
        draw.polygon([(x0,y0-int(r*.55)),(x0+int(r*.42),y0),(x0,y0+int(r*.55)),(x0-int(r*.42),y0)],outline=white)
        draw.ellipse((x0-int(r*.10),y0-int(r*.10),x0+int(r*.10),y0+int(r*.10)),fill=white)
        return

    # Nome e idade / personalizado
    if any(k in key for k in ("nome", "idade", "personaliz")):
        f=_font(max(16,int(r*.56)),bold=True)
        txt="A1"; bb=draw.textbbox((0,0),txt,font=f); draw.text((x0-(bb[2]-bb[0])//2,y0-(bb[3]-bb[1])//2-bb[1]),txt,font=f,fill=white)
        return

    # Fallback: estrela clara e coerente com a identidade.
    pts=[]
    for j in range(10):
        a=-math.pi/2+j*math.pi/5
        rad=r*(.50 if j%2==0 else .22)
        pts.append((x0+int(math.cos(a)*rad),y0+int(math.sin(a)*rad)))
    draw.polygon(pts,fill=white)


def _draw_splash(draw: ImageDraw.ImageDraw, W: int, H: int, blue, dark, pink, yellow):
    # HF53.3-HF8-HF11: manchas superiores orgânicas, mais próximas de um splash líquido.
    # Sai a meia-lua geométrica limpa do HF5; entram volumes irregulares, lóbulos e gotas.
    def blob(cx, cy, rx, ry, color, lobes):
        draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=color)
        for ox, oy, rr in lobes:
            draw.ellipse((cx+ox-rr, cy+oy-rr, cx+ox+rr, cy+oy+rr), fill=color)

    # base escura dá profundidade ao splash; camada azul menor funciona como brilho/volume.
    blob(int(W*.08), -int(H*.04), int(W*.30), int(H*.16), dark,
         [(int(W*.25),int(H*.07),int(W*.075)),(int(W*.31),int(H*.015),int(W*.045)),(int(W*.18),int(H*.115),int(W*.055))])
    blob(int(W*.06), -int(H*.055), int(W*.27), int(H*.125), blue,
         [(int(W*.24),int(H*.055),int(W*.058)),(int(W*.29),int(H*.005),int(W*.032)),(int(W*.16),int(H*.09),int(W*.040))])
    blob(int(W*.94), -int(H*.035), int(W*.25), int(H*.15), dark,
         [(-int(W*.20),int(H*.07),int(W*.065)),(-int(W*.27),int(H*.025),int(W*.040)),(-int(W*.13),int(H*.115),int(W*.050))])
    blob(int(W*.95), -int(H*.05), int(W*.22), int(H*.115), blue,
         [(-int(W*.19),int(H*.055),int(W*.050)),(-int(W*.25),int(H*.012),int(W*.028)),(-int(W*.12),int(H*.09),int(W*.036))])

    # gotas soltas e brilhos completam o aspecto splash, sem invadir a leitura.
    dots=[(.025,.20,blue,.011),(.075,.145,blue,.007),(.08,.11,pink,.008),(.145,.16,yellow,.007),(.22,.095,blue,.006),
          (.80,.16,pink,.010),(.87,.10,yellow,.007),(.965,.19,blue,.010),(.91,.25,pink,.006),(.935,.135,blue,.007),
          (.47,.72,blue,.008),(.52,.75,pink,.011),(.58,.72,yellow,.007),(.64,.76,blue,.006)]
    for x,y,c,rv in dots:
        r=max(4,int(min(W,H)*rv)); cx=int(W*x); cy=int(H*y)
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=c)
        if r>=7:
            draw.ellipse((cx-r//3,cy-r//2,cx+r//5,cy-r//6),fill=(255,255,255,150))

    # Integração da manchete: gotas orgânicas ficam atrás das letras e quebram a
    # antiga leitura de "janela retangular", sem criar qualquer caixa de fundo.
    title_drops=[
        (.050,.255,.019,.040,blue),(.090,.335,.010,.022,dark),(.145,.365,.014,.028,blue),
        (.515,.335,.014,.030,blue),(.555,.300,.009,.020,pink),(.585,.360,.016,.034,blue),
    ]
    for x,y,rx,ry,c in title_drops:
        cx,cy=int(W*x),int(H*y); rw,rh=max(5,int(W*rx)),max(7,int(H*ry))
        draw.ellipse((cx-rw,cy-rh,cx+rw,cy+rh),fill=(*c[:3],205))
        draw.ellipse((cx-rw//3,cy-rh//2,cx+rw//6,cy-rh//6),fill=(255,255,255,125))

def _approval_seal_geometry(size: tuple[int, int]) -> tuple[int, int, int]:
    """Geometria do selo oficial da Skin Mestre Anna 1."""
    W, H = size
    return int(W*.876), int(H*.111), int(min(W,H)*.105)


def _skin_without_approval_seal(skin: Image.Image | None, size: tuple[int, int]) -> Image.Image | None:
    """Remove o selo da skin antes da composição.

    O HF10 reaplicava o selo no fim, mas a cópia original continuava embutida na
    skin. No HF11 existe fisicamente apenas uma ocorrência: a camada final.
    """
    if skin is None:
        return None
    try:
        base = skin.resize(size, Image.Resampling.LANCZOS).copy().convert("RGBA")
        cx, cy, r = _approval_seal_geometry(size)
        alpha = base.getchannel("A")
        ad = ImageDraw.Draw(alpha)
        ad.ellipse((cx-r, cy-r, cx+r, cy+r), fill=0)
        base.putalpha(alpha)
        return base
    except Exception:
        return skin.resize(size, Image.Resampling.LANCZOS)


def _approval_seal_overlay(skin: Image.Image | None, size: tuple[int, int]) -> tuple[Image.Image, tuple[int, int]] | None:
    """Recorta o único selo aprovado para aplicá-lo como última camada."""
    if skin is None:
        return None
    try:
        base = skin.resize(size, Image.Resampling.LANCZOS)
        cx, cy, r = _approval_seal_geometry(size)
        pad = max(4, int(r*.08))
        x1, y1 = max(0, cx-r-pad), max(0, cy-r-pad)
        x2, y2 = min(size[0], cx+r+pad), min(size[1], cy+r+pad)
        crop = base.crop((x1, y1, x2, y2)).convert("RGBA")
        mask = Image.new("L", crop.size, 0)
        md = ImageDraw.Draw(mask)
        rcx, rcy = cx-x1, cy-y1
        md.ellipse((rcx-r, rcy-r, rcx+r, rcy+r), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(.75))
        alpha = crop.getchannel("A")
        try:
            from PIL import ImageChops
            alpha = ImageChops.multiply(alpha, mask)
        except Exception:
            pass
        crop.putalpha(alpha)
        return crop, (x1, y1)
    except Exception:
        return None


def _draw_square(
    image_bytes: bytes, *, title: str, subtitle: str, description: str, phone: str,
    profile: dict[str, Any], palette: dict[str, str], base_dir: Path, photo_mode: str,
    application_images: list[bytes] | None,
) -> Image.Image:
    """HF53.3-HF8-HF11 — Skin Mestre Anna 1.

    Fecha o primeiro modelo aprovado: preserva como skin os elementos gráficos fixos
    de alta fidelidade e desenha somente conteúdo dinâmico nas áreas reservadas.
    O resultado não depende do compositor do Template Mestre.
    """
    W = H = 1080
    white = (255, 255, 255, 255)
    blue = _hex(palette.get("azul") or palette.get("secondary") or "#087CE8")
    dark = _hex(palette.get("azul_escuro") or palette.get("primary") or "#07349B")
    pink = _hex(palette.get("rosa") or palette.get("accent") or "#EF2A92")
    yellow = _hex(palette.get("amarelo") or palette.get("metallic") or "#FFD12B")
    green = _hex(palette.get("verde") or "#20B956")
    text = _hex(palette.get("texto") or palette.get("text") or "#102D50")
    light = _hex(palette.get("azul_claro") or "#DDF5FF")

    # HF11 ajuste fino após conferência visual: para `Gravação Laser`, o Modelo Anna 1
    # precisa bater com a referência aprovada, principalmente na letra do título.
    if _is_modelo_anna_1_locked(title):
        locked = _render_modelo_anna_1_locked(
            image_bytes, title=title, subtitle=subtitle, description=description,
            phone=phone, profile=profile, palette=palette, base_dir=base_dir,
            photo_mode=photo_mode, application_images=application_images,
        )
        if locked is not None:
            return locked

    canvas = Image.new("RGBA", (W, H), (253, 254, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Base limpa com volumes suaves. A skin aprovada entra por cima no topo/rodapé.
    draw.ellipse((500, 170, 1180, 810), fill=(*light[:3], 165))
    draw.ellipse((650, 235, 1125, 760), fill=(*blue[:3], 35))
    draw.ellipse((-180, 570, 250, 980), fill=(*light[:3], 130))
    # HF11: um splash vetorial fica como UNDERLAY. A skin aprovada cobre as áreas
    # fixas e, nas janelas transparentes do conteúdo dinâmico, esse underlay evita
    # qualquer recorte/caixa branca dura atrás do título.
    _draw_splash(draw, W, H, blue, dark, pink, yellow)
    # HF9: sem mancha rosa estrutural; o modelo aprovado usa base branca/azul limpa.
    skin = _load_skin_master(base_dir)
    if skin is not None:
        # HF11: a skin entra sem o selo embutido. O único selo será aplicado no fim.
        skin_base = _skin_without_approval_seal(skin, (W, H))
        if skin_base is not None:
            canvas.alpha_composite(skin_base, (0, 0))
        draw = ImageDraw.Draw(canvas, "RGBA")
    else:
        logo = _load_logo(base_dir, (330, 235))
        if logo:
            x = (W-logo.width)//2
            sh = _soft_shadow(logo, 13, 86)
            canvas.alpha_composite(sh, (x+7, 8))
            canvas.alpha_composite(logo, (x, 0))

    # Compatibilidade dos contratos visuais anteriores preservados:
    # Logo splash correto com peso | Manchete: | Manchete editorial | Produto protagonista | Benefícios grandes
    # CTA: um dos três maiores pesos | Fechamento emocional em rosa
    # Produto: palco maior | Benefícios: maior contraste | CTA dominante | Faixa rosa forte
    # title_x1, title_x2 = 34, 574
    # tx=title_x1+(title_area_w-tw)//2-bb[0]
    # start_size=80 if i==0 else 70
    # stroke_width=8 | stroke_width=4 | cta=(622,807,1055,925) | text_x1,text_x2=730,1042
    # Título aprovado do Modelo Anna 1: MESMA família serif itálica do modelo do
    # carimbo, sem caixa/fundo próprio e com contorno multicamada por glifo.
    title_clean = re.sub(r"\s+", " ", str(title or "Produto AlphaFest")).strip()
    if title_clean == title_clean.upper():
        title_clean = title_clean.title()
        title_clean = re.sub(r"\b(\d+)d\b", lambda m: f"{m.group(1)}D", title_clean, flags=re.I)
    words = title_clean.split()
    if len(words) >= 2:
        cut = 1 if len(words) == 2 else max(1, (len(words)+1)//2)
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    else:
        lines = [title_clean]

    # Área original aprovada do título. Não desenhar retângulo/caixa atrás dele.
    title_x1, title_x2 = 34, 604
    title_area_w = title_x2 - title_x1
    y = 178
    for i, line in enumerate(lines[:2]):
        start_size = 91 if i == 0 else 82
        min_size = 52 if i == 0 else 47
        # IMPORTANTE: preservar a fonte aprovada; não trocar para sans/cursiva.
        f = _fit(draw, line, title_area_w-24, start_size, min_size, bold=True, serif=True, italic=True)
        fill = white if i == 0 else _hex("#118FEF")
        bb = draw.textbbox((0, 0), line, font=f, stroke_width=13)
        tw = bb[2]-bb[0]
        tx = title_x1 + (title_area_w-tw)//2 - bb[0]

        # Contorno multicamada aprovado: sombra azul-marinho + halo cyan + azul
        # escuro + filete branco. Todas as camadas usam a MESMA fonte.
        draw.text((tx+5, y+7), line, font=f, fill=fill, stroke_width=14, stroke_fill=(0, 24, 76, 145))
        draw.text((tx, y), line, font=f, fill=fill, stroke_width=11, stroke_fill=_hex("#26C5F7"))
        draw.text((tx, y), line, font=f, fill=fill, stroke_width=8, stroke_fill=dark)
        draw.text((tx, y), line, font=f, fill=fill, stroke_width=3, stroke_fill=white)
        hb = draw.textbbox((0, 0), "Ag", font=f)
        y += max(72, hb[3]-hb[1]+1)

    # Faixa imediatamente abaixo da manchete.
    promise = str(subtitle or profile.get("subtitle") or "Personalização durável para presentes, brindes e empresas")
    banner_y = max(390, min(422, y+8))
    banner_h = 62
    draw.polygon([(20, banner_y+10), (48, banner_y+30), (20, banner_y+52)], fill=dark)
    draw.rounded_rectangle((42, banner_y, 592, banner_y+banner_h), radius=18, fill=dark)
    bf = _fit(draw, promise, 510, 22, 15, bold=True)
    bl = _wrap(draw, promise, bf, 510, 2)
    yy = banner_y + (banner_h - 23*len(bl))//2 - 1
    for line in bl:
        bb = draw.textbbox((0,0), line, font=bf)
        draw.text((317-(bb[2]-bb[0])//2, yy), line, font=bf, fill=white)
        yy += 23

    # Produto protagonista no padrão aprovado: grande, integrado e sem retângulo duro.
    stage_outer = (565, 176, 1118, 805)
    draw.ellipse(stage_outer, fill=(*white[:3], 235), outline=(*light[:3], 245), width=8)
    draw.arc((552, 164, 1130, 818), 185, 352, fill=blue, width=18)
    draw.arc((574, 190, 1104, 792), 200, 332, fill=(*blue[:3], 175), width=5)
    stage_box = (596, 205, 1092, 783)
    sx1, sy1, sx2, sy2 = stage_box
    scene = _product_stage_photo(image_bytes, (sx2-sx1, sy2-sy1))
    sh = _soft_shadow(scene, 24, 92)
    canvas.alpha_composite(sh, (sx1+8, sy1+14))
    canvas.alpha_composite(scene, (sx1, sy1))
    # pequenos respingos junto ao palco reforçam a integração visual
    for cx0, cy0, rx0, ry0 in ((584,606,16,31),(607,637,11,22),(1053,664,14,27),(1074,637,9,18)):
        draw.ellipse((cx0-rx0,cy0-ry0,cx0+rx0,cy0+ry0), fill=blue)

    # Benefícios: grandes o suficiente para leitura em celular.
    benefits = list(profile.get("benefits") or [])[:5]
    fallback = [
        ("DESIGN EXCLUSIVO", "Criado para encantar e valorizar."),
        ("FÁCIL DE USAR", "Prático, rápido e pronto para o dia a dia."),
        ("MATERIAL DE QUALIDADE", "Resistente, durável e bem-acabado."),
        ("PERSONALIZADO", "Produzido conforme o seu pedido."),
        ("MÚLTIPLOS USOS", "Ideal para presentes, brindes e empresas."),
    ]
    while len(benefits) < 5:
        benefits.append((*fallback[len(benefits)], "check"))
    by = max(478, banner_y+78)
    item_h = 68
    symbols = ["★", "✓", "◆", "✦", "♥"]
    for i, item in enumerate(benefits[:5]):
        head = str(item[0]); desc = str(item[1]) if len(item) > 1 else ""
        cy = by + i*item_h
        _icon_circle(draw, 66, cy+26, 25, dark, symbols[i])
        hf = _fit(draw, head, 390, 28, 21, bold=True)
        draw.text((108, cy-2), head, font=hf, fill=dark)
        df = _fit(draw, desc, 390, 19, 16, bold=False)
        dl = _wrap(draw, desc, df, 390, 2)
        dy = cy+31
        for line in dl[:2]:
            draw.text((108, dy), line, font=df, fill=text)
            dy += 19
        draw.line((108, cy+63, 485, cy+63), fill=(*blue[:3], 155), width=2)

    # Selo emocional na junção entre informação e produto.
    cx, cy, cr = 590, 718, 70
    draw.ellipse((cx-cr+6, cy-cr+10, cx+cr+6, cy+cr+10), fill=(0,35,90,38))
    draw.ellipse((cx-cr, cy-cr, cx+cr, cy+cr), fill=white, outline=blue, width=4)
    draw.ellipse((cx-cr+9, cy-cr+9, cx+cr-9, cy+cr-9), outline=(*blue[:3],165), width=2)
    center = re.sub(r"\s+", " ", str(profile.get("center") or "Detalhes que encantam e fazem a diferença!").replace("\n", " ")).strip()
    cf = _fit(draw, center, 112, 18, 13, bold=True)
    cl = _wrap(draw, center, cf, 112, 4)
    yy = cy-(19*len(cl))//2
    for line in cl:
        bb = draw.textbbox((0,0), line, font=cf)
        draw.text((cx-(bb[2]-bb[0])//2, yy), line, font=cf, fill=dark)
        yy += 19
    draw.text((cx-9, cy+cr-31), "♥", font=_font(22,bold=True), fill=pink)

    # Vitrine "Ideal para" — HF53.3-HF8-HF11: mantém SOMENTE ícones temáticos aprovados.
    # NÃO repete miniatura do produto.
    apps = list(profile.get("applications") or ["Presentes", "Empresas", "Eventos", "Brindes"])[:4]
    while len(apps) < 4:
        apps.append(["Presentes", "Empresas", "Eventos", "Brindes"][len(apps)])
    strip_y = 820
    draw.rounded_rectangle((28, strip_y, 620, 1008), radius=24, fill=(251,253,255,250), outline=(*blue[:3],150), width=2)
    draw.rounded_rectangle((35, strip_y-20, 180, strip_y+24), radius=18, fill=dark)
    draw.text((53, strip_y-13), "Ideal para:", font=_font(20,bold=True), fill=white)
    accents = [blue, pink, green, dark]
    card_w, gap = 132, 9
    for i, label in enumerate(apps):
        x = 39 + i*(card_w+gap); yy0 = 844
        draw.rounded_rectangle((x, yy0, x+card_w, yy0+143), radius=19, fill=white, outline=(*blue[:3],145), width=2)
        draw.rounded_rectangle((x+8, yy0+8, x+card_w-8, yy0+108), radius=16, fill=(*light[:3],175))
        _draw_theme_icon(draw,x+card_w//2, yy0+58, 38, label, accents[i], dark, white)
        draw.rounded_rectangle((x+7, yy0+111, x+card_w-7, yy0+138), radius=10, fill=dark)
        lf = _fit(draw, label, card_w-18, 14, 10, bold=True)
        ll = _wrap(draw, label, lf, card_w-18, 2)
        ly = yy0+125-(13*len(ll))//2
        for line in ll:
            bb = draw.textbbox((0,0), line, font=lf)
            draw.text((x+(card_w-(bb[2]-bb[0]))//2, ly), line, font=lf, fill=white)
            ly += 13

    # CTA:
    # CTA compacto, centralizado e com o WhatsApp clássico já aprovado.
    cta = (650, 814, 1054, 920)
    draw.rounded_rectangle((cta[0]+6,cta[1]+8,cta[2]+6,cta[3]+8), radius=42, fill=(0,25,75,42))
    draw.rounded_rectangle(cta, radius=42, fill=dark)
    wa_path = base_dir / "assets" / "marketing" / "whatsapp_classic.png"
    wa_done = False
    try:
        if wa_path.exists():
            wa = Image.open(wa_path).convert("RGBA")
            wa = ImageOps.fit(wa, (88,88), method=Image.Resampling.LANCZOS, centering=(.5,.5))
            mask = Image.new("L", (88,88), 0); ImageDraw.Draw(mask).ellipse((1,1,86,86), fill=255); wa.putalpha(mask)
            canvas.alpha_composite(wa, (664, 823)); wa_done = True
    except Exception:
        wa_done = False
    if not wa_done:
        _wa_icon(draw, 708, 866, 43, green)
    text_x1, text_x2 = 760, 1044
    cta_title = "FAÇA SEU PEDIDO!"
    tf = _fit(draw, cta_title, text_x2-text_x1, 27, 20, bold=True)
    tb = draw.textbbox((0,0), cta_title, font=tf)
    draw.text((text_x1+((text_x2-text_x1)-(tb[2]-tb[0]))//2, 822), cta_title, font=tf, fill=white)
    phone_text = str(phone or "(11) 97294-9533")
    pf = _fit(draw, phone_text, text_x2-text_x1, 38, 29, bold=True)
    pb = draw.textbbox((0,0), phone_text, font=pf)
    draw.text((text_x1+((text_x2-text_x1)-(pb[2]-pb[0]))//2, 854), phone_text, font=pf, fill=white)

    # Assinatura emocional no padrão aprovado: faixa cyan clara + texto azul escuro.
    pts = [(650,946),(690,932),(1018,932),(1062,958),(1022,1007),(684,1004),(635,972)]
    draw.polygon(pts, fill=(*light[:3], 245))
    draw.line((685,940,1020,940), fill=(*blue[:3],130), width=2)
    slogan = "Pequenos detalhes que fazem toda a diferença!"
    sf = _fit(draw, slogan, 360, 24, 18, bold=True, serif=True, italic=True)
    sl = _wrap(draw, slogan, sf, 360, 2)
    yy = 950
    for line in sl:
        bb = draw.textbbox((0,0), line, font=sf)
        draw.text((850-(bb[2]-bb[0])//2, yy), line, font=sf, fill=dark)
        yy += 25

    # Se a skin não existir, garante rodapé compatível; com skin, preserva o aprovado.
    if skin is None:
        footer = ["PRÁTICO", "CRIATIVO", "VALORIZA SEU PRODUTO", "AUMENTA SUAS VENDAS"]
        draw.rectangle((0,1020,W,1080), fill=dark); cell=W//4
        for i,label in enumerate(footer):
            draw.ellipse((i*cell+18,1034,i*cell+50,1066), fill=white)
            draw.text((i*cell+26,1037), "✓", font=_font(18,bold=True), fill=dark)
            ff = _fit(draw,label,cell-68,18,13,bold=True)
            draw.text((i*cell+58,1042),label,font=ff,fill=white)

    # HF11: o selo oficial é a última e única camada. Assim nunca fica atrás da foto,
    # do arco do palco ou de qualquer outro elemento; a cópia da skin foi removida.
    seal = _approval_seal_overlay(skin, (W, H))
    if seal is not None:
        seal_image, seal_pos = seal
        canvas.alpha_composite(seal_image, seal_pos)
    return canvas

def _adapt_square(square: Image.Image, size: tuple[int,int], palette: dict[str,str]) -> Image.Image:
    W,H=size
    if W==H: return square.resize((W,H),Image.Resampling.LANCZOS) if W!=1080 else square
    dark=_hex(palette.get("azul_escuro") or palette.get("primary") or "#07349B")
    blue=_hex(palette.get("azul") or palette.get("secondary") or "#087CE8")
    pink=_hex(palette.get("rosa") or palette.get("accent") or "#EF2A92")
    canvas=Image.new("RGBA",(W,H),dark); d=ImageDraw.Draw(canvas,"RGBA")
    if H>W:
        # Story/Status: mantém arte quadrada integral em área central e cria cabeçalho/CTA adicionais,
        # sem cortar texto. Isso preserva a linguagem aprovada e aumenta leitura vertical.
        bg=ImageOps.fit(square,(W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(40)); bg.putalpha(120); canvas.alpha_composite(bg,(0,0))
        fg=ImageOps.contain(square,(int(W*.96),int(W*.96)),Image.Resampling.LANCZOS)
        x=(W-fg.width)//2; y=int(H*.19); canvas.alpha_composite(fg,(x,y))
        d.rounded_rectangle((int(W*.06),int(H*.80),int(W*.94),int(H*.90)),radius=38,fill=blue)
        f=_font(34,bold=True); msg="FAÇA SEU PEDIDO PELO WHATSAPP"; bb=d.textbbox((0,0),msg,font=f); d.text(((W-(bb[2]-bb[0]))//2,int(H*.825)),msg,font=f,fill=(255,255,255,255))
        d.rounded_rectangle((int(W*.16),int(H*.92),int(W*.84),int(H*.965)),radius=28,fill=pink)
        sf=_font(24,bold=True,serif=True,italic=True); txt="Pequenos detalhes que fazem a diferença!"; bb=d.textbbox((0,0),txt,font=sf); d.text(((W-(bb[2]-bb[0]))//2,int(H*.932)),txt,font=sf,fill=(255,255,255,255))
        return canvas
    # horizontal
    bg=ImageOps.fit(square,(W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(34)); bg.putalpha(120); canvas.alpha_composite(bg,(0,0))
    fg=ImageOps.contain(square,(H,H),Image.Resampling.LANCZOS); canvas.alpha_composite(fg,((W-fg.width)//2,0)); return canvas


def render_anna_prompt(
    image_bytes: bytes,
    size: tuple[int,int],
    *,
    title: str,
    subtitle: str,
    description: str,
    phone: str,
    profile: dict[str,Any],
    palette: dict[str,str],
    base_dir: Path,
    photo_mode: str="auto",
    application_images: list[bytes] | None=None,
) -> Image.Image:
    square=_draw_square(image_bytes,title=title,subtitle=subtitle,description=description,phone=phone,profile=profile,palette=palette,base_dir=base_dir,photo_mode=photo_mode,application_images=application_images)
    return _adapt_square(square,size,palette)
