"""Renderer independente do Template Anna — Prompt Premium.

HF53.3-HF8-HF2: este módulo não reutiliza a composição visual do Template Mestre
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
            bbox = logo.getbbox()
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


def _product_layer(image_bytes: bytes, box: tuple[int, int, int, int], photo_mode: str = "auto") -> tuple[Image.Image, tuple[int, int]]:
    source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mode = str(photo_mode or "auto").casefold()
    prepared = source
    if mode in {"recortar", "remove", "remover fundo"}:
        prepared = _remove_simple_background(source)
    elif mode == "auto":
        bg, spread = _corner_uniform(source)
        if spread < 34 and max(bg) > 145:
            prepared = _remove_simple_background(source)

    x1, y1, x2, y2 = box
    maxw, maxh = x2-x1, y2-y1
    if prepared.getextrema()[3] != (255, 255):
        prepared.thumbnail((maxw, maxh), Image.Resampling.LANCZOS)
        return prepared, (x1 + (maxw-prepared.width)//2, y1 + (maxh-prepared.height)//2)

    # Foto preservada: usa cartão fotográfico grande, com cantos suaves, integrado ao layout.
    fitted = ImageOps.fit(prepared, (maxw, maxh), method=Image.Resampling.LANCZOS, centering=(.5, .48))
    mask = Image.new("L", (maxw, maxh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, maxw-1, maxh-1), radius=max(22, min(maxw, maxh)//18), fill=255)
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
    # grandes formas líquidas nos cantos
    draw.pieslice((-int(W*.22),-int(H*.12),int(W*.43),int(H*.20)),0,180,fill=dark)
    draw.pieslice((-int(W*.18),-int(H*.095),int(W*.39),int(H*.17)),0,180,fill=blue)
    draw.pieslice((int(W*.74),-int(H*.10),int(W*1.18),int(H*.18)),0,180,fill=dark)
    draw.pieslice((int(W*.78),-int(H*.075),int(W*1.14),int(H*.15)),0,180,fill=blue)
    # gotas coloridas
    dots=[(.03,.18,blue,.010),(.09,.12,pink,.008),(.15,.16,yellow,.006),(.22,.10,blue,.006),(.79,.14,pink,.009),(.86,.10,yellow,.007),(.96,.18,blue,.009),(.91,.24,pink,.006),(.47,.70,blue,.008),(.52,.73,pink,.011),(.58,.70,yellow,.007),(.63,.75,blue,.006)]
    for x,y,c,rv in dots:
        r=max(4,int(min(W,H)*rv)); cx=int(W*x); cy=int(H*y)
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=c)


def _draw_square(
    image_bytes: bytes, *, title: str, subtitle: str, description: str, phone: str,
    profile: dict[str, Any], palette: dict[str, str], base_dir: Path, photo_mode: str,
    application_images: list[bytes] | None,
) -> Image.Image:
    W=H=1080
    white=(255,255,255,255)
    blue=_hex(palette.get("azul") or palette.get("secondary") or "#087CE8")
    dark=_hex(palette.get("azul_escuro") or palette.get("primary") or "#07349B")
    pink=_hex(palette.get("rosa") or palette.get("accent") or "#EF2A92")
    yellow=_hex(palette.get("amarelo") or palette.get("metallic") or "#FFD12B")
    green=_hex(palette.get("verde") or "#20B956")
    text=_hex(palette.get("texto") or palette.get("text") or "#102D50")
    canvas=Image.new("RGBA",(W,H),white); draw=ImageDraw.Draw(canvas,"RGBA")
    _draw_splash(draw,W,H,blue,dark,pink,yellow)

    logo=_load_logo(base_dir,(300,285))
    if logo:
        x=(W-logo.width)//2; y=5
        sh=_soft_shadow(logo,12,55); canvas.alpha_composite(sh,(x+5,y+8)); canvas.alpha_composite(logo,(x,y))

    # selo superior
    sx,sy,sr=932,115,77
    draw.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=dark,outline=white,width=5)
    seal="TESTADO E\nAPROVADO!"
    sf=_font(22,bold=True); yy=sy-29
    for line in seal.split("\n"):
        bb=draw.textbbox((0,0),line,font=sf); draw.text((sx-(bb[2]-bb[0])//2,yy),line,font=sf,fill=white); yy+=29

    # título protagonista – 2 linhas no máximo, à esquerda
    title_clean=re.sub(r"\s+"," ",str(title or "Produto AlphaFest")).strip()
    words = title_clean.split()
    if 2 <= len(words) <= 4:
        if "para" in [w.casefold() for w in words]:
            cut = [w.casefold() for w in words].index("para")
            tlines = [" ".join(words[:cut]), " ".join(words[cut:])] if cut > 0 else [title_clean]
        elif len(words) == 2:
            tlines = [words[0], words[1]]
        else:
            cut = max(1, len(words)//2)
            tlines = [" ".join(words[:cut]), " ".join(words[cut:])]
        tf = _fit(draw, max(tlines, key=len), 570, 104, 64, bold=True, serif=True, italic=True)
    else:
        tf=_fit(draw,title_clean,570,104,58,bold=True,serif=True,italic=True)
        tlines=_wrap(draw,title_clean,tf,570,2)
    ty=190; tstep=max(78,draw.textbbox((0,0),"Ag",font=tf)[3]+5)
    for line in tlines:
        draw.text((42,ty),line,font=tf,fill=dark,stroke_width=2,stroke_fill=white); ty+=tstep

    # faixa imediatamente abaixo do título
    banner_text=str(subtitle or profile.get("subtitle") or "Transforme sua ideia em uma peça especial!")
    banner_y=min(430,ty+6)
    banner=(45,banner_y,585,banner_y+66)
    draw.polygon([(25,banner_y+16),(45,banner_y+33),(25,banner_y+51)],fill=dark)
    draw.rounded_rectangle(banner,radius=14,fill=dark)
    bf=_fit(draw,banner_text,500,26,17,bold=True); bl=_wrap(draw,banner_text,bf,500,2); lh=25; yy=banner_y+(66-lh*len(bl))//2
    for line in bl:
        bb=draw.textbbox((0,0),line,font=bf); draw.text((315-(bb[2]-bb[0])//2,yy),line,font=bf,fill=white); yy+=lh

    # produto domina a direita
    draw.ellipse((545,250,1085,760),fill=(*_hex("#E9F8FF")[:3],230))
    draw.arc((515,225,1080,785),205,330,fill=blue,width=14)
    layer,pos=_product_layer(image_bytes,(575,235,1050,720),photo_mode)
    shadow=_soft_shadow(layer,20,85); canvas.alpha_composite(shadow,(pos[0]+10,pos[1]+16)); canvas.alpha_composite(layer,pos)

    # benefícios à esquerda: grandes e legíveis
    benefits=list(profile.get("benefits") or [])[:5]
    fallback=[("DESIGN EXCLUSIVO","Criado para encantar e valorizar."),("FÁCIL DE USAR","Prático, rápido e pronto para aproveitar."),("MATERIAL DE QUALIDADE","Resistente, durável e bem-acabado."),("PERSONALIZADO","Produzido conforme a sua necessidade."),("MÚLTIPLOS USOS","Ideal para presentes, brindes e lembranças.")]
    while len(benefits)<5: benefits.append((*fallback[len(benefits)],"check"))
    by=max(480,banner_y+82); item_h=60; symbols=["★","✓","◆","✓","♥"]
    for i,item in enumerate(benefits[:5]):
        head=str(item[0]); desc=str(item[1]) if len(item)>1 else ""
        cy=by+i*item_h
        _icon_circle(draw,65,cy+22,22,dark,symbols[i])
        hf=_fit(draw,head,390,25,19,bold=True); draw.text((103,cy-3),head,font=hf,fill=dark)
        df=_fit(draw,desc,400,17,14,bold=False); dl=_wrap(draw,desc,df,400,2); dy=cy+28
        for line in dl:
            draw.text((103,dy),line,font=df,fill=text); dy+=18
        draw.line((103,cy+68,487,cy+68),fill=(*blue[:3],120),width=2)

    # selo emocional central
    cx,cy,cr=555,660,78
    draw.ellipse((cx-cr,cy-cr,cx+cr,cy+cr),fill=white,outline=blue,width=4)
    center=re.sub(r"\s+"," ",str(profile.get("center") or "Cada detalhe faz a diferença!").replace("\n"," ")).strip()
    cf=_fit(draw,center,125,18,14,bold=True); cl=_wrap(draw,center,cf,125,4); yy=cy-(20*len(cl))//2
    for line in cl:
        bb=draw.textbbox((0,0),line,font=cf); draw.text((cx-(bb[2]-bb[0])//2,yy),line,font=cf,fill=dark); yy+=20

    # Ideal para: cards de vitrine, com foto quando houver
    apps=list(profile.get("applications") or ["Presentes","Lembranças","Brindes","Temáticos"])[:4]
    while len(apps)<4: apps.append(["Presentes","Lembranças","Brindes","Temáticos"][len(apps)])
    strip_y=822
    draw.rounded_rectangle((28,strip_y,548,1000),radius=22,fill=(250,252,255,245),outline=(*blue[:3],130),width=2)
    draw.rounded_rectangle((35,strip_y-18,165,strip_y+20),radius=16,fill=dark)
    labf=_font(18,bold=True); draw.text((52,strip_y-13),"Ideal para:",font=labf,fill=white)
    unique=[]
    for raw in application_images or []:
        try:
            im=Image.open(io.BytesIO(raw)).convert("RGBA")
            sig=(im.width,im.height,im.resize((8,8)).convert("RGB").tobytes())
            if sig not in [u[0] for u in unique]: unique.append((sig,im))
        except Exception: pass
    card_w=118; gap=8
    for i,label in enumerate(apps):
        x=38+i*(card_w+gap); y=842
        draw.rounded_rectangle((x,y,x+card_w,y+130),radius=18,fill=white,outline=(*blue[:3],150),width=2)
        if i < len(unique):
            thumb=ImageOps.fit(unique[i][1],(104,88),Image.Resampling.LANCZOS,centering=(.5,.5)); mask=Image.new("L",thumb.size,0); ImageDraw.Draw(mask).rounded_rectangle((0,0,103,87),radius=12,fill=255); thumb.putalpha(mask); canvas.alpha_composite(thumb,(x+7,y+7))
        else:
            draw.ellipse((x+30,y+15,x+88,y+73),fill=(232,247,255,255)); _icon_circle(draw,x+59,y+44,24,blue,["★","♥","◆","✓"][i])
        draw.rounded_rectangle((x+5,y+100,x+card_w-5,y+124),radius=10,fill=dark)
        lf=_fit(draw,label,card_w-16,14,10,bold=True); bb=draw.textbbox((0,0),label,font=lf); draw.text((x+(card_w-(bb[2]-bb[0]))//2,y+104),label,font=lf,fill=white)

    # CTA enorme à direita
    cta=(575,790,1050,920); draw.rounded_rectangle(cta,radius=38,fill=dark)
    _wa_icon(draw,640,855,43,green)
    ctaf=_font(25,bold=True); draw.text((700,805),"FAÇA SEU PEDIDO!",font=ctaf,fill=white)
    phone_text=str(phone or "(11) 97294-9533")
    pf=_fit(draw,phone_text,330,42,29,bold=True); draw.text((700,847),phone_text,font=pf,fill=white)

    # faixa rosa emocional
    pts=[(590,940),(635,925),(1020,928),(1055,962),(1015,1000),(625,997),(575,970)]
    draw.polygon(pts,fill=pink)
    slogan="Pequenos detalhes que fazem toda a diferença!"
    slf=_fit(draw,slogan,405,25,18,bold=True,serif=True,italic=True); sl=_wrap(draw,slogan,slf,405,2); yy=947
    for line in sl:
        bb=draw.textbbox((0,0),line,font=slf); draw.text((815-(bb[2]-bb[0])//2,yy),line,font=slf,fill=white); yy+=27

    # barra final
    footer=["PRÁTICO","CRIATIVO","VALORIZA SEU PRODUTO","AUMENTA SUAS VENDAS"]
    draw.rectangle((0,1020,W,1080),fill=dark); cell=W//4
    for i,label in enumerate(footer):
        _icon_circle(draw,i*cell+32,1050,13,white,"✓")
        ff=_fit(draw,label,cell-62,17,12,bold=True); lines=_wrap(draw,label,ff,cell-62,2); yy=1035 if len(lines)>1 else 1043
        for line in lines: draw.text((i*cell+55,yy),line,font=ff,fill=white); yy+=17
        if i: draw.line((i*cell,1032,i*cell,1068),fill=(255,255,255,100),width=1)
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
