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


def _fit_font(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], *, bold: bool = True, max_size: int = 72, min_size: int = 14):
    # Usa DejaVu, presente via Pillow/matplotlib na base atual.
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    x1, y1, x2, y2 = box
    maxw, maxh = x2-x1, y2-y1
    for size in range(max_size, min_size-1, -2):
        font = None
        for path in candidates:
            try:
                font = ImageFont.truetype(path, size)
                break
            except Exception:
                pass
        if font is None:
            font = ImageFont.load_default()
        bb = draw.multiline_textbbox((0, 0), text, font=font, spacing=max(2, size//7), align="center")
        if bb[2]-bb[0] <= maxw and bb[3]-bb[1] <= maxh:
            return font
    return font


def _draw_centered_text(draw: ImageDraw.ImageDraw, box, text: str, color: str, *, max_size=64, min_size=14, bold=True, align="center"):
    if not str(text or "").strip():
        return
    x1, y1, x2, y2 = box
    font = _fit_font(draw, str(text), box, bold=bold, max_size=max_size, min_size=min_size)
    bb = draw.multiline_textbbox((0, 0), str(text), font=font, spacing=max(2, getattr(font, "size", 18)//7), align=align)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    x = x1 + (x2-x1-tw)//2
    y = y1 + (y2-y1-th)//2 - bb[1]
    draw.multiline_text((x, y), str(text), font=font, fill=color, spacing=max(2, getattr(font, "size", 18)//7), align=align)


def render_library_square(
    template_cfg: dict[str, Any], *, image_bytes: bytes, title: str, subtitle: str,
    description: str, price: str, cta: str, phone: str, profile: dict[str, Any],
    photo_mode: str = "auto", palette: dict[str, str] | None = None,
) -> Image.Image:
    """Renderizador genérico de zonas para templates importáveis."""
    bg_path: Path = template_cfg["background_path"]
    canvas = Image.open(bg_path).convert("RGBA").resize((1080, 1080), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas, "RGBA")
    layout = template_cfg.get("layout") or {}
    colors = dict(template_cfg.get("colors") or {})
    p = palette or {}
    primary = p.get("primary") or colors.get("primary") or "#07349B"
    secondary = p.get("secondary") or colors.get("secondary") or "#087CE8"
    accent = p.get("accent") or colors.get("accent") or "#EF2A92"
    text_color = p.get("text") or colors.get("text") or "#07349B"

    # Título/subtítulo/faixas e selos.
    if "title" in layout:
        title_text = "\n".join(x for x in [profile.get("title1"), profile.get("title2")] if x)
        _draw_centered_text(draw, _zone_box(layout["title"],1080,1080), title_text, text_color, max_size=92, min_size=30, bold=True)
    if "subtitle" in layout:
        _draw_centered_text(draw, _zone_box(layout["subtitle"],1080,1080), profile.get("subtitle") or subtitle, "#FFFFFF", max_size=35, min_size=17, bold=True)
    if "badge" in layout:
        _draw_centered_text(draw, _zone_box(layout["badge"],1080,1080), profile.get("badge") or "DESTAQUE", "#FFFFFF", max_size=26, min_size=13, bold=True)
    if "center" in layout:
        _draw_centered_text(draw, _zone_box(layout["center"],1080,1080), profile.get("center") or "", text_color, max_size=30, min_size=14, bold=True)

    # Produto sem deformação.
    if "photo" in layout and image_bytes:
        x1,y1,x2,y2 = _zone_box(layout["photo"],1080,1080)
        source = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGBA")
        fitted = ImageOps.contain(source, (x2-x1, y2-y1), Image.Resampling.LANCZOS)
        px = x1 + (x2-x1-fitted.width)//2
        py = y1 + (y2-y1-fitted.height)//2
        canvas.alpha_composite(fitted, (px, py))

    # Benefícios em cinco linhas; cada item respeita sua zona.
    benefits = list(profile.get("benefits") or [])[:5]
    zones = layout.get("benefits") or []
    if isinstance(zones, dict):
        zones = zones.get("items") or []
    for i, benefit in enumerate(benefits):
        if i >= len(zones):
            break
        box = _zone_box(zones[i],1080,1080)
        head, desc = benefit[0], benefit[1]
        x1,y1,x2,y2 = box
        hf = _fit_font(draw, head, (x1,y1,x2,y1+(y2-y1)//2), max_size=25, min_size=13)
        draw.text((x1,y1), head, font=hf, fill=primary)
        df = _fit_font(draw, desc, (x1,y1+(y2-y1)//2,x2,y2), bold=False, max_size=16, min_size=10)
        # quebra simples por largura
        words = str(desc).split(); lines=[]; cur=""
        for word in words:
            cand=(cur+" "+word).strip()
            if draw.textbbox((0,0),cand,font=df)[2] <= x2-x1 or not cur:
                cur=cand
            else:
                lines.append(cur); cur=word
        if cur: lines.append(cur)
        draw.multiline_text((x1,y1+(y2-y1)//2-2),"\n".join(lines[:2]),font=df,fill=text_color,spacing=1)

    # Aplicações: usa a mesma foto como miniatura nas quatro zonas.
    app_zones = layout.get("applications") or []
    apps = list(profile.get("applications") or [])
    if not apps:
        apps = ["Festas", "Presentes", "Decoração", "Momentos"]
    if image_bytes:
        src = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGBA")
        for i, zone in enumerate(app_zones[:4]):
            x1,y1,x2,y2 = _zone_box(zone,1080,1080)
            thumb = ImageOps.fit(src, (x2-x1, y2-y1), method=Image.Resampling.LANCZOS)
            mask=Image.new("L",thumb.size,0); ImageDraw.Draw(mask).ellipse((0,0,thumb.width-1,thumb.height-1),fill=255)
            canvas.paste(thumb,(x1,y1),mask)

    if "phone" in layout:
        _draw_centered_text(draw,_zone_box(layout["phone"],1080,1080),phone or "11 97294-9533","#FFFFFF",max_size=40,min_size=20,bold=True)
    if "cta" in layout:
        _draw_centered_text(draw,_zone_box(layout["cta"],1080,1080),cta or profile.get("pink") or "FAÇA SEU PEDIDO!","#FFFFFF",max_size=28,min_size=15,bold=True)
    if "price" in layout and str(price or "").strip():
        _draw_centered_text(draw,_zone_box(layout["price"],1080,1080),price,accent,max_size=34,min_size=18,bold=True)

    footer_zones = layout.get("footer") or []
    footer = list(profile.get("footer") or [])[:4]
    for i, zone in enumerate(footer_zones[:4]):
        if i < len(footer):
            _draw_centered_text(draw,_zone_box(zone,1080,1080),footer[i],"#FFFFFF",max_size=18,min_size=10,bold=True)
    return canvas
