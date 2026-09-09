"""Renderer independente do Template Anna — Prompt Premium.

HF53.3-HF8-HF3: este módulo não reutiliza a composição visual do Template Mestre
nem o compositor legado. Ele recebe somente dados já preparados pelo motor e
constrói nativamente cada proporção do Template Anna.
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps
from alphafest_font_manager import get_font


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
            cut = _remove_grabcut_background(source)
            if cut is not None:
                prepared = cut

    x1, y1, x2, y2 = box
    maxw, maxh = x2-x1, y2-y1
    alpha = prepared.getchannel("A")
    has_transparency = alpha.getextrema() != (255, 255)
    if has_transparency:
        prepared.thumbnail((maxw, maxh), Image.Resampling.LANCZOS)
        return prepared, (x1 + (maxw-prepared.width)//2, y1 + (maxh-prepared.height)//2)

    # Fallback fotográfico premium: cartão grande, sem moldura pesada.
    fitted = ImageOps.fit(prepared, (maxw, maxh), method=Image.Resampling.LANCZOS, centering=(.5, .46))
    mask = Image.new("L", (maxw, maxh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, maxw-1, maxh-1), radius=max(24, min(maxw, maxh)//14), fill=255)
    fitted.putalpha(mask)
    return fitted, (x1, y1)

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


def _draw_splash(draw: ImageDraw.ImageDraw, W: int, H: int, blue, dark, pink, yellow):
    # Moldura líquida AlphaFest com mais presença, sem invadir a área de leitura.
    draw.pieslice((-int(W*.22),-int(H*.15),int(W*.43),int(H*.20)),0,180,fill=dark)
    draw.pieslice((-int(W*.17),-int(H*.11),int(W*.39),int(H*.16)),0,180,fill=blue)
    draw.pieslice((int(W*.72),-int(H*.13),int(W*1.18),int(H*.19)),0,180,fill=dark)
    draw.pieslice((int(W*.77),-int(H*.09),int(W*1.13),int(H*.15)),0,180,fill=blue)
    # pequenas gotas 3D simuladas: círculo + brilho
    dots=[(.025,.20,blue,.011),(.08,.11,pink,.008),(.145,.16,yellow,.007),(.22,.095,blue,.006),
          (.80,.16,pink,.010),(.87,.10,yellow,.007),(.965,.19,blue,.010),(.91,.25,pink,.006),
          (.47,.72,blue,.008),(.52,.75,pink,.011),(.58,.72,yellow,.007),(.64,.76,blue,.006)]
    for x,y,c,rv in dots:
        r=max(4,int(min(W,H)*rv)); cx=int(W*x); cy=int(H*y)
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=c)
        if r>=7:
            draw.ellipse((cx-r//3,cy-r//2,cx+r//5,cy-r//6),fill=(255,255,255,150))

def _draw_square(
    image_bytes: bytes, *, title: str, subtitle: str, description: str, phone: str,
    profile: dict[str, Any], palette: dict[str, str], base_dir: Path, photo_mode: str,
    application_images: list[bytes] | None,
) -> Image.Image:
    """HF53.3-HF8-HF3 — refino comercial do renderer Anna.

    Hierarquia fixa: marca forte -> manchete -> promessa -> produto -> benefícios ->
    vitrine -> CTA. O objetivo é leitura em miniatura de feed, não densidade de sistema.
    """
    W=H=1080
    white=(255,255,255,255)
    blue=_hex(palette.get("azul") or palette.get("secondary") or "#087CE8")
    dark=_hex(palette.get("azul_escuro") or palette.get("primary") or "#07349B")
    pink=_hex(palette.get("rosa") or palette.get("accent") or "#EF2A92")
    yellow=_hex(palette.get("amarelo") or palette.get("metallic") or "#FFD12B")
    green=_hex(palette.get("verde") or "#20B956")
    text=_hex(palette.get("texto") or palette.get("text") or "#102D50")
    canvas=Image.new("RGBA",(W,H),(252,253,255,255)); draw=ImageDraw.Draw(canvas,"RGBA")

    # manchas suaves que integram produto e texto
    draw.ellipse((515,175,1160,790),fill=(*_hex("#E9F8FF")[:3],235))
    draw.ellipse((690,280,1115,705),fill=(*blue[:3],38))
    draw.ellipse((-140,520,260,920),fill=(*_hex("#F3FAFF")[:3],220))
    _draw_splash(draw,W,H,blue,dark,pink,yellow)

    # Logo splash correto, maior de verdade: o crop por alpha remove a margem invisível.
    logo=_load_logo(base_dir,(255,205))
    if logo:
        x=(W-logo.width)//2; y=2
        sh=_soft_shadow(logo,11,70); canvas.alpha_composite(sh,(x+5,y+7)); canvas.alpha_composite(logo,(x,y))

    # selo superior direito
    sx,sy,sr=934,102,70
    draw.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=dark,outline=white,width=5)
    draw.ellipse((sx-sr+8,sy-sr+8,sx+sr-8,sy+sr-8),outline=(*blue[:3],210),width=3)
    draw.ellipse((sx-15,sy-45,sx+15,sy-15), fill=white)
    ck=_font(18,bold=True); bb=draw.textbbox((0,0),"✓",font=ck); draw.text((sx-(bb[2]-bb[0])//2,sy-42),"✓",font=ck,fill=dark)
    sf=_font(18,bold=True); yy=sy-3
    for line in ("TESTADO E","APROVADO!"):
        bb=draw.textbbox((0,0),line,font=sf); draw.text((sx-(bb[2]-bb[0])//2,yy),line,font=sf,fill=white); yy+=22

    # Manchete: grande, mas sem esmagar o corpo. 1ª linha mais forte, 2ª linha de apoio.
    title_clean=re.sub(r"\s+"," ",str(title or "Produto AlphaFest")).strip()
    words=title_clean.split()
    if len(words)>=2:
        if len(words)==2:
            tlines=[words[0],words[1]]
        else:
            cut=max(1,(len(words)+1)//2); tlines=[" ".join(words[:cut])," ".join(words[cut:])]
    else:
        tlines=[title_clean]
    title_area_w=540
    y=178
    for i,line in enumerate(tlines[:2]):
        start_size=86 if i==0 else 72
        f=_fit(draw,line,title_area_w,start_size,56,bold=True,serif=False,italic=False)
        draw.text((48,y),line,font=f,fill=dark,stroke_width=1,stroke_fill=white)
        y += max(70,draw.textbbox((0,0),"Ag",font=f)[3]-draw.textbbox((0,0),"Ag",font=f)[1]+6)

    # Faixa-promessa curta e forte, imediatamente abaixo da manchete.
    promise=str(subtitle or profile.get("subtitle") or "Transforme sua ideia em uma peça especial!")
    banner_y=min(385,y+6); banner_h=58
    draw.polygon([(26,banner_y+10),(48,banner_y+29),(26,banner_y+48)],fill=dark)
    draw.rounded_rectangle((48,banner_y,565,banner_y+banner_h),radius=15,fill=dark)
    bf=_fit(draw,promise,470,22,16,bold=True); bl=_wrap(draw,promise,bf,470,2); yy=banner_y+8
    for line in bl:
        bb=draw.textbbox((0,0),line,font=bf); draw.text((306-(bb[2]-bb[0])//2,yy),line,font=bf,fill=white); yy+=23

    # Produto protagonista à direita, preferencialmente recortado do fundo real.
    stage_box=(560,205,1055,735)
    draw.arc((520,185,1080,770),195,336,fill=blue,width=15)
    draw.arc((545,210,1060,748),203,328,fill=(*pink[:3],135),width=5)
    layer,pos=_product_layer(image_bytes,stage_box,photo_mode)
    sh=_soft_shadow(layer,22,95); canvas.alpha_composite(sh,(pos[0]+12,pos[1]+18)); canvas.alpha_composite(layer,pos)

    # Benefícios grandes: headline + uma frase curta, sem aparência de tabela.
    benefits=list(profile.get("benefits") or [])[:5]
    fallback=[("DESIGN EXCLUSIVO","Criado para encantar e valorizar."),("FÁCIL DE USAR","Prático e pronto para aproveitar."),("MATERIAL DE QUALIDADE","Resistente, durável e bem-acabado."),("PERSONALIZADO","Produzido do seu jeito."),("MÚLTIPLOS USOS","Presentes, brindes e lembranças.")]
    while len(benefits)<5: benefits.append((*fallback[len(benefits)],"check"))
    by=max(455,banner_y+76); item_h=62; symbols=["★","✓","◆","✦","♥"]
    for i,item in enumerate(benefits[:5]):
        head=str(item[0]); desc=str(item[1]) if len(item)>1 else ""
        cy=by+i*item_h
        _icon_circle(draw,66,cy+24,23,dark,symbols[i])
        hf=_fit(draw,head,385,25,19,bold=True); draw.text((105,cy-1),head,font=hf,fill=dark)
        # uma linha útil vale mais do que duas linhas minúsculas no feed
        df=_fit(draw,desc,385,18,15,bold=False)
        if draw.textbbox((0,0),desc,font=df)[2] > 385:
            dl=_wrap(draw,desc,df,385,2)
        else:
            dl=[desc]
        dy=cy+29
        for line in dl[:2]:
            draw.text((105,dy),line,font=df,fill=text); dy+=18
        draw.line((105,cy+57,478,cy+57),fill=(*blue[:3],120),width=2)

    # selo emocional – deslocado para a borda da área de produto, como adesivo editorial.
    cx,cy,cr=535,650,73
    draw.ellipse((cx-cr+5,cy-cr+8,cx+cr+5,cy+cr+8),fill=(0,35,90,35))
    draw.ellipse((cx-cr,cy-cr,cx+cr,cy+cr),fill=white,outline=blue,width=4)
    center=re.sub(r"\s+"," ",str(profile.get("center") or "Cada detalhe faz a diferença!").replace("\n"," ")).strip()
    cf=_fit(draw,center,118,18,14,bold=True); cl=_wrap(draw,center,cf,118,4); yy=cy-(20*len(cl))//2
    for line in cl:
        bb=draw.textbbox((0,0),line,font=cf); draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=cf,fill=dark); yy+=20
    draw.text((cx-8,cy+cr-28),"♥",font=_font(20,bold=True),fill=pink)

    # Vitrine "Ideal para": imagens ocupam o card, legenda vira tarja publicitária.
    apps=list(profile.get("applications") or ["Presentes","Lembranças","Brindes","Temáticos"])[:4]
    while len(apps)<4: apps.append(["Presentes","Lembranças","Brindes","Temáticos"][len(apps)])
    strip_y=808
    draw.rounded_rectangle((30,strip_y,610,1002),radius=24,fill=(251,253,255,248),outline=(*blue[:3],125),width=2)
    draw.rounded_rectangle((38,strip_y-18,170,strip_y+22),radius=16,fill=dark)
    draw.text((54,strip_y-12),"Ideal para:",font=_font(19,bold=True),fill=white)
    unique=[]
    for raw in application_images or []:
        try:
            im=Image.open(io.BytesIO(raw)).convert("RGBA")
            sig=(im.width,im.height,im.resize((8,8)).convert("RGB").tobytes())
            if sig not in [u[0] for u in unique]: unique.append((sig,im))
        except Exception:
            pass
    card_w=132; gap=8
    for i,label in enumerate(apps):
        x=39+i*(card_w+gap); y=834
        draw.rounded_rectangle((x,y,x+card_w,y+145),radius=18,fill=white,outline=(*blue[:3],145),width=2)
        if i < len(unique):
            thumb=ImageOps.fit(unique[i][1],(118,105),Image.Resampling.LANCZOS,centering=(.5,.48))
            mask=Image.new("L",thumb.size,0); ImageDraw.Draw(mask).rounded_rectangle((0,0,117,104),radius=13,fill=255); thumb.putalpha(mask); canvas.alpha_composite(thumb,(x+7,y+7))
        else:
            draw.rounded_rectangle((x+7,y+7,x+card_w-7,y+112),radius=13,fill=(232,247,255,255))
            _icon_circle(draw,x+card_w//2,y+58,29,blue,["★","♥","◆","✓"][i])
        draw.rounded_rectangle((x+6,y+113,x+card_w-6,y+139),radius=10,fill=dark)
        lf=_fit(draw,label,card_w-18,14,10,bold=True); bb=draw.textbbox((0,0),label,font=lf); draw.text((x+(card_w-(bb[2]-bb[0]))//2,y+118),label,font=lf,fill=white)

    # CTA: um dos três maiores pesos da peça.
    cta=(625,785,1048,925)
    draw.rounded_rectangle(cta,radius=42,fill=dark)
    _wa_icon(draw,686,855,45,green)
    ctaf=_font(25,bold=True); draw.text((750,800),"FAÇA SEU PEDIDO!",font=ctaf,fill=white)
    phone_text=str(phone or "(11) 97294-9533")
    pf=_fit(draw,phone_text,282,38,29,bold=True); draw.text((750,844),phone_text,font=pf,fill=white)

    # Fechamento emocional em rosa – vira elemento gráfico, não rodapé tímido.
    pts=[(630,944),(675,928),(1018,931),(1055,963),(1015,1005),(662,1000),(612,972)]
    draw.polygon(pts,fill=pink)
    slogan="Pequenos detalhes que fazem toda a diferença!"
    slf=_fit(draw,slogan,370,23,17,bold=True,serif=True,italic=True); sl=_wrap(draw,slogan,slf,370,2); yy=949
    for line in sl:
        bb=draw.textbbox((0,0),line,font=slf); draw.text((832-(bb[2]-bb[0])//2,yy),line,font=slf,fill=white); yy+=25

    # Barra final legível e padronizada.
    footer=["PRÁTICO","CRIATIVO","VALORIZA SEU PRODUTO","AUMENTA SUAS VENDAS"]
    draw.rectangle((0,1020,W,1080),fill=dark); cell=W//4
    for i,label in enumerate(footer):
        draw.ellipse((i*cell+20,1036,i*cell+48,1064),fill=white)
        ck=_font(17,bold=True); draw.text((i*cell+27,1038),"✓",font=ck,fill=dark)
        ff=_fit(draw,label,cell-65,17,12,bold=True); lines=_wrap(draw,label,ff,cell-65,2); yy=1036 if len(lines)>1 else 1043
        for line in lines:
            draw.text((i*cell+58,yy),line,font=ff,fill=white); yy+=17
        if i: draw.line((i*cell,1032,i*cell,1068),fill=(255,255,255,110),width=1)
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
