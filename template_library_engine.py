"""AlphaFest Template Library Engine — Sprint 20.0.

Templates instaláveis sem alteração de código. Cada template vive em:
  templates/<id>/fundo.png
  templates/<id>/layout.json
  templates/<id>/config.json
  templates/<id>/preview.png   (opcional)

O layout usa coordenadas normalizadas em uma grade de 1000 x 1000 para que o
mesmo mapa seja escalado para Feed/Story/formatos futuros.
"""
from __future__ import annotations

import base64
import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
RUNTIME_TEMPLATES_DIR = Path(tempfile.gettempdir()) / "alphafest_template_library"

REQUIRED_FILES = ("fundo.png", "layout.json", "config.json")


def _safe_id(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_")
    return value[:80]


def ensure_library() -> Path:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return TEMPLATES_DIR


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def list_library_templates() -> list[dict[str, Any]]:
    ensure_library()
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in (RUNTIME_TEMPLATES_DIR, TEMPLATES_DIR):
        if not root.exists():
            continue
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or not all((folder / name).exists() for name in REQUIRED_FILES):
                continue
            cfg = _read_json(folder / "config.json")
            tid = _safe_id(cfg.get("id") or folder.name)
            if not tid or tid in seen:
                continue
            seen.add(tid)
            found.append({
                "id": tid,
                "nome": str(cfg.get("nome") or folder.name),
                "descricao": str(cfg.get("descricao") or "Template instalado na biblioteca AlphaFest."),
                "source": "library",
                "folder": str(folder),
                "preview": str(folder / (cfg.get("preview") or "preview.png")),
            })
    return found


def load_library_template(template_id: str) -> dict[str, Any] | None:
    safe = _safe_id(template_id)
    for item in list_library_templates():
        if item["id"] != safe:
            continue
        folder = Path(item["folder"])
        cfg = _read_json(folder / "config.json")
        layout = _read_json(folder / "layout.json")
        cfg.update({
            "id": safe,
            "source": "library",
            "folder": folder,
            "background_path": folder / str(cfg.get("background") or "fundo.png"),
            "preview_path": folder / str(cfg.get("preview") or "preview.png"),
            "layout": layout,
        })
        return cfg
    return None


def install_template_zip(zip_bytes: bytes, *, replace: bool = False, persistent_source: bool = False) -> dict[str, Any]:
    """Instala um pacote de template e retorna os metadados instalados.

    O ZIP deve conter config.json/layout.json/fundo.png na raiz ou dentro de uma
    única pasta. Caminhos inseguros e arquivos executáveis são rejeitados.
    """
    ensure_library()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if n and not n.endswith("/")]
        if not names:
            raise ValueError("O ZIP do template está vazio.")
        for name in names:
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError("ZIP de template contém caminho inválido.")
            if p.suffix.lower() in {".py", ".exe", ".bat", ".cmd", ".ps1", ".sh", ".dll"}:
                raise ValueError("Pacotes de template não podem conter código executável.")
        roots = {Path(n).parts[0] for n in names if len(Path(n).parts) > 1}
        prefix = next(iter(roots)) if len(roots) == 1 and not any(len(Path(n).parts) == 1 for n in names) else ""
        def member(base: str) -> str:
            return f"{prefix}/{base}" if prefix else base
        missing = [f for f in REQUIRED_FILES if member(f) not in names]
        if missing:
            raise ValueError("Template incompleto. Faltam: " + ", ".join(missing))
        cfg = json.loads(zf.read(member("config.json")).decode("utf-8"))
        tid = _safe_id(cfg.get("id") or cfg.get("nome"))
        if not tid:
            raise ValueError("config.json precisa definir id ou nome do template.")
        target = (TEMPLATES_DIR if persistent_source else RUNTIME_TEMPLATES_DIR) / tid
        if target.exists():
            if not replace:
                raise FileExistsError(f"O template '{tid}' já existe.")
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".json", ".txt", ".md"}
        for name in names:
            rel = Path(name)
            if prefix:
                try:
                    rel = rel.relative_to(prefix)
                except ValueError:
                    continue
            if not rel.parts or rel.suffix.lower() not in allowed_ext:
                continue
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(name))
    loaded = load_library_template(tid)
    if not loaded:
        raise ValueError("Template foi copiado, mas não pôde ser validado.")
    return {"id": loaded["id"], "nome": loaded.get("nome", tid)}


def hydrate_template_packages(packages: dict[str, str] | None) -> None:
    """Restaura templates persistidos no banco para a biblioteca temporária."""
    if not isinstance(packages, dict):
        return
    ensure_library()
    for tid, encoded in packages.items():
        safe = _safe_id(tid)
        if not safe or not isinstance(encoded, str) or not encoded:
            continue
        target = RUNTIME_TEMPLATES_DIR / safe
        if target.exists() and all((target / f).exists() for f in REQUIRED_FILES):
            continue
        try:
            install_template_zip(base64.b64decode(encoded), replace=True, persistent_source=False)
        except Exception:
            continue


def export_template_zip(template_id: str) -> bytes:
    cfg = load_library_template(template_id)
    if not cfg:
        raise KeyError(template_id)
    folder: Path = cfg["folder"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in folder.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(folder).as_posix())
    return buf.getvalue()


def _zone_box(zone: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    # layout normalizado: x/y/w/h em 0..1000
    x = int(float(zone.get("x", 0)) * width / 1000)
    y = int(float(zone.get("y", 0)) * height / 1000)
    w = int(float(zone.get("w", 100)) * width / 1000)
    h = int(float(zone.get("h", 100)) * height / 1000)
    return x, y, x + max(1, w), y + max(1, h)


def _font_for_size(size: int, *, bold: bool = True) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, max(6, int(size)))
        except Exception:
            pass
    return ImageFont.load_default()


def _measure_multiline(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, *, spacing: int = 2, align: str = "left") -> tuple[int, int, tuple[int,int,int,int]]:
    bb = draw.multiline_textbbox((0, 0), str(text or ""), font=font, spacing=spacing, align=align)
    return bb[2]-bb[0], bb[3]-bb[1], bb


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, *, max_lines: int | None = None) -> list[str]:
    """Quebra texto por largura sem cortar palavras desnecessariamente."""
    raw = str(text or "").replace("\r", "").strip()
    if not raw:
        return []
    out: list[str] = []
    for paragraph in raw.split("\n"):
        words = paragraph.split()
        if not words:
            out.append("")
            continue
        cur = words[0]
        for word in words[1:]:
            cand = f"{cur} {word}".strip()
            if draw.textbbox((0, 0), cand, font=font)[2] <= max_width:
                cur = cand
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    if max_lines and len(out) > max_lines:
        out = out[:max_lines]
        # Só usa reticências no último recurso; antes disso o auto-fit tenta uma fonte menor.
        last = out[-1]
        ell = "…"
        while last and draw.textbbox((0,0), last + ell, font=font)[2] > max_width:
            last = last[:-1].rstrip()
        out[-1] = (last + ell) if last else ell
    return out


def _fit_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int,int,int,int],
    *, bold: bool = True,
    max_size: int = 72,
    min_size: int = 12,
    max_lines: int | None = None,
    padding: int = 0,
    align: str = "left",
) -> tuple[ImageFont.ImageFont, str, int]:
    x1,y1,x2,y2 = box
    avail_w = max(1, x2-x1-(padding*2))
    avail_h = max(1, y2-y1-(padding*2))
    last_font = _font_for_size(min_size, bold=bold)
    last_text = str(text or "")
    last_spacing = 2
    for size in range(int(max_size), int(min_size)-1, -1):
        font = _font_for_size(size, bold=bold)
        spacing = max(1, int(size * 0.12))
        lines = _wrap_lines(draw, text, font, avail_w, max_lines=None)
        if max_lines and len(lines) > max_lines:
            continue
        wrapped = "\n".join(lines)
        tw, th, _ = _measure_multiline(draw, wrapped, font, spacing=spacing, align=align)
        last_font, last_text, last_spacing = font, wrapped, spacing
        if tw <= avail_w and th <= avail_h:
            return font, wrapped, spacing
    # Se nem no mínimo couber, limita linhas e garante clipping posterior.
    lines = _wrap_lines(draw, text, last_font, avail_w, max_lines=max_lines)
    return last_font, "\n".join(lines), last_spacing


def _draw_text_box(
    canvas: Image.Image,
    box: tuple[int,int,int,int],
    text: str,
    color: str,
    *,
    max_size: int = 64,
    min_size: int = 12,
    bold: bool = True,
    align: str = "center",
    valign: str = "center",
    max_lines: int | None = None,
    padding: int = 4,
) -> None:
    """Renderiza em uma camada limitada à zona: nada pode vazar para outra área."""
    if not str(text or "").strip():
        return
    x1,y1,x2,y2 = box
    w,h = max(1,x2-x1), max(1,y2-y1)
    layer = Image.new("RGBA", (w,h), (0,0,0,0))
    ldraw = ImageDraw.Draw(layer, "RGBA")
    local_box=(0,0,w,h)
    font, wrapped, spacing = _fit_wrapped_text(
        ldraw, str(text), local_box, bold=bold, max_size=max_size, min_size=min_size,
        max_lines=max_lines, padding=padding, align=align,
    )
    tw, th, bb = _measure_multiline(ldraw, wrapped, font, spacing=spacing, align=align)
    if align == "left":
        tx = padding - bb[0]
    elif align == "right":
        tx = w - padding - tw - bb[0]
    else:
        tx = (w-tw)//2 - bb[0]
    if valign == "top":
        ty = padding - bb[1]
    elif valign == "bottom":
        ty = h - padding - th - bb[1]
    else:
        ty = (h-th)//2 - bb[1]
    ldraw.multiline_text((tx,ty), wrapped, font=font, fill=color, spacing=spacing, align=align)
    canvas.alpha_composite(layer, (x1,y1))


def _draw_centered_text(draw: ImageDraw.ImageDraw, box, text: str, color: str, *, max_size=64, min_size=14, bold=True, align="center"):
    # Compatibilidade para chamadas antigas do módulo; o renderizador 20.4 usa _draw_text_box.
    if not str(text or "").strip():
        return
    font, wrapped, spacing = _fit_wrapped_text(draw, str(text), box, bold=bold, max_size=max_size, min_size=min_size, max_lines=None, padding=0, align=align)
    x1,y1,x2,y2=box
    bb=draw.multiline_textbbox((0,0),wrapped,font=font,spacing=spacing,align=align)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    x=x1+(x2-x1-tw)//2-bb[0]
    y=y1+(y2-y1-th)//2-bb[1]
    draw.multiline_text((x,y),wrapped,font=font,fill=color,spacing=spacing,align=align)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], *, bold: bool = True, max_size: int = 72, min_size: int = 14):
    font, _, _ = _fit_wrapped_text(draw, text, box, bold=bold, max_size=max_size, min_size=min_size)
    return font


def _render_photo_in_zone(canvas: Image.Image, source: Image.Image, zone: dict[str,Any], box: tuple[int,int,int,int], *, photo_mode: str = "auto", padding: int = 8) -> None:
    x1,y1,x2,y2 = box
    bw,bh=max(1,x2-x1),max(1,y2-y1)
    pad=max(0,int(zone.get("padding", padding)))
    target=(max(1,bw-pad*2), max(1,bh-pad*2))
    mode=str(photo_mode or "auto").lower().strip()
    if mode == "auto":
        mode=str(zone.get("fit") or "contain").lower().strip()
    if mode in {"cover","crop","fill"}:
        fitted=ImageOps.fit(source,target,method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
    else:
        fitted=ImageOps.contain(source,target,Image.Resampling.LANCZOS)
    px=x1+pad+(target[0]-fitted.width)//2
    py=y1+pad+(target[1]-fitted.height)//2
    # Limita fisicamente a composição à caixa definida no layout.
    zone_layer=Image.new("RGBA",(bw,bh),(0,0,0,0))
    zone_layer.alpha_composite(fitted,(px-x1,py-y1))
    canvas.alpha_composite(zone_layer,(x1,y1))

def render_library_square(
    template_cfg: dict[str, Any], *, image_bytes: bytes, title: str, subtitle: str,
    description: str, price: str, cta: str, phone: str, profile: dict[str, Any],
    photo_mode: str = "auto", palette: dict[str, str] | None = None,
    canvas_size: tuple[int, int] = (1080, 1080),
) -> Image.Image:
    """Renderizador genérico de precisão para templates importáveis.

    Sprint 20.4: cada elemento é composto dentro da própria zona, com auto-fit,
    quebra de linha e clipping. O fundo do template nunca é alterado.
    """
    bg_path: Path = template_cfg["background_path"]
    CW, CH = (int(canvas_size[0]), int(canvas_size[1]))
    canvas = Image.open(bg_path).convert("RGBA").resize((CW, CH), Image.Resampling.LANCZOS)
    layout = template_cfg.get("layout") or {}
    type_scale = min(1.30, max(1.0, (CH / 1080.0) ** 0.34))
    def sz(value, floor=8):
        return max(floor, int(round(float(value) * type_scale)))
    def box(zone):
        return _zone_box(zone, CW, CH)
    colors = dict(template_cfg.get("colors") or {})
    p = palette or {}
    primary = p.get("primary") or colors.get("primary") or "#07349B"
    accent = p.get("accent") or colors.get("accent") or "#EF2A92"
    text_color = p.get("text") or colors.get("text") or "#07349B"

    # Título: máximo de 2 linhas para preservar a área nobre da composição.
    if "title" in layout:
        title_text = "\n".join(x for x in [profile.get("title1"), profile.get("title2")] if x) or title
        z=layout["title"]
        _draw_text_box(canvas, box(z), title_text, text_color,
                       max_size=sz(z.get("max_size",82)), min_size=max(sz(z.get("min_size",25)), sz(34)),
                       bold=True, align=str(z.get("align","center")), max_lines=int(z.get("max_lines",2)), padding=int(z.get("padding",6)))

    if "subtitle" in layout:
        z=layout["subtitle"]
        _draw_text_box(canvas,box(z),profile.get("subtitle") or subtitle,"#FFFFFF",
                       max_size=sz(z.get("max_size",34)),min_size=max(sz(z.get("min_size",15)),sz(18)),bold=True,
                       align=str(z.get("align","center")),max_lines=int(z.get("max_lines",2)),padding=int(z.get("padding",10)))

    if "badge" in layout:
        z=layout["badge"]
        _draw_text_box(canvas,box(z),profile.get("badge") or "DESTAQUE","#FFFFFF",
                       max_size=sz(z.get("max_size",23)),min_size=max(sz(z.get("min_size",11)),sz(13)),bold=True,
                       align="center",max_lines=int(z.get("max_lines",3)),padding=int(z.get("padding",12)))

    if "center" in layout:
        z=layout["center"]
        _draw_text_box(canvas,box(z),profile.get("center") or "",text_color,
                       max_size=sz(z.get("max_size",25)),min_size=max(sz(z.get("min_size",11)),sz(13)),bold=True,
                       align="center",max_lines=int(z.get("max_lines",6)),padding=int(z.get("padding",18)))

    source = None
    if image_bytes:
        try:
            source=ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGBA")
        except Exception:
            source=None

    if "photo" in layout and source is not None:
        z=layout["photo"]
        _render_photo_in_zone(canvas, source, z, box(z), photo_mode=photo_mode, padding=int(z.get("padding",8)))

    # Benefícios: título e descrição medidos como um único bloco vertical para
    # impedir colisão entre um item e outro.
    benefits=list(profile.get("benefits") or [])[:5]
    zones=layout.get("benefits") or []
    if isinstance(zones,dict):
        zones=zones.get("items") or []
    for i,benefit in enumerate(benefits):
        if i>=len(zones):
            break
        z=zones[i]
        box=box(z)
        x1,y1,x2,y2=box
        bh=y2-y1
        head=str(benefit[0] if len(benefit)>0 else "")
        desc=str(benefit[1] if len(benefit)>1 else "")
        if len(desc) > 74:
            desc = desc[:74].rsplit(" ", 1)[0].rstrip(" ,.;:-") + "…"
        # Cabeçalho ocupa ~42% da zona; descrição o restante.
        split=y1+max(20,int(bh*0.42))
        _draw_text_box(canvas,(x1,y1,x2,split),head,primary,max_size=sz(z.get("head_max",22)),min_size=max(sz(z.get("head_min",11)),sz(14)),
                       bold=True,align="left",valign="center",max_lines=1,padding=int(z.get("padding",2)))
        _draw_text_box(canvas,(x1,split,x2,y2),desc,text_color,max_size=sz(z.get("desc_max",13)),min_size=max(sz(z.get("desc_min",8)),sz(10)),
                       bold=False,align="left",valign="top",max_lines=int(z.get("desc_lines",2)),padding=int(z.get("padding",2)))

    # Aplicações: imagem limitada ao interior dos círculos, com pequeno recuo
    # para não cobrir o contorno desenhado no fundo.
    app_zones=layout.get("applications") or []
    if source is not None:
        for zone in app_zones[:4]:
            x1,y1,x2,y2=box(zone)
            inset=int(zone.get("padding",5))
            w=max(1,x2-x1-inset*2); h=max(1,y2-y1-inset*2)
            thumb=ImageOps.fit(source,(w,h),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
            mask=Image.new("L",(w,h),0)
            ImageDraw.Draw(mask).ellipse((0,0,w-1,h-1),fill=255)
            layer=Image.new("RGBA",(w,h),(0,0,0,0)); layer.paste(thumb,(0,0),mask)
            canvas.alpha_composite(layer,(x1+inset,y1+inset))

    if "price" in layout and str(price or "").strip():
        z=layout["price"]
        _draw_text_box(canvas,box(z),price,accent,max_size=sz(z.get("max_size",27)),min_size=max(sz(z.get("min_size",13)),sz(18)),
                       bold=True,align="center",max_lines=int(z.get("max_lines",2)),padding=int(z.get("padding",4)))

    if "phone" in layout:
        z=layout["phone"]
        _draw_text_box(canvas,box(z),phone or "11 97294-9533","#FFFFFF",
                       max_size=sz(z.get("max_size",31)),min_size=max(sz(z.get("min_size",16)),sz(21)),bold=True,
                       align="center",max_lines=1,padding=int(z.get("padding",3)))

    if "cta" in layout:
        z=layout["cta"]
        _draw_text_box(canvas,box(z),cta or profile.get("pink") or "FAÇA SEU PEDIDO!","#FFFFFF",
                       max_size=sz(z.get("max_size",25)),min_size=max(sz(z.get("min_size",12)),sz(16)),bold=True,
                       align="center",max_lines=int(z.get("max_lines",2)),padding=int(z.get("padding",8)))

    footer_zones=layout.get("footer") or []
    footer=list(profile.get("footer") or [])[:4]
    for i,zone in enumerate(footer_zones[:4]):
        if i<len(footer):
            _draw_text_box(canvas,box(zone),footer[i],"#FFFFFF",
                           max_size=sz(zone.get("max_size",14)),min_size=max(sz(zone.get("min_size",8)),sz(10)),bold=True,
                           align="center",max_lines=int(zone.get("max_lines",2)),padding=int(zone.get("padding",2)))
    return canvas

