"""HF81: imagens responsivas reais para mobile sem afetar desktop.

Na geracao de producao, cria uma variante WebP dedicada ao celular e a
entrega via <picture><source media>. O <img src> original permanece intacto
para desktop e como fallback. Somente URLs publicas Supabase/catalogo ou
assets gerados no pacote; nenhuma alteracao no banco de dados.
"""
from __future__ import annotations

import hashlib
import html as html_lib
import io
import re
from typing import Any
from urllib.parse import urlsplit

from site_imagens_remotas_hf79 import _baixar, _permitida

IMG = re.compile(r"<img\b[^>]*>", re.I | re.S)
SRC = re.compile(r"""\bsrc\s*=\s*(["'])(.*?)\1""", re.I | re.S)
CLASS = re.compile(r"""\bclass\s*=\s*(["'])(.*?)\1""", re.I | re.S)
ALT = re.compile(r"""\balt\s*=\s*(["'])(.*?)\1""", re.I | re.S)
LOCAL = re.compile(r"^/assets/img/([0-9a-f]{24})\.(?:png|jpg|jpeg|webp)$", re.I)


def _mobile_webp(dados: bytes, *, largura: int, qualidade: int) -> tuple[bytes, int, int] | None:
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        return None
    if not dados or len(dados) > 8 * 1024 * 1024:
        return None
    try:
        with Image.open(io.BytesIO(dados)) as original:
            if original.format not in {"PNG", "JPEG", "WEBP"}:
                return None
            if getattr(original, "is_animated", False):
                return None
            if not 0 < original.width * original.height <= 16_000_000:
                return None
            img = ImageOps.exif_transpose(original)
            width, height = img.size
            # Nunca ampliar nem cortar os materiais originais.
            target = min(width, largura)
            if target < width:
                img = img.resize(
                    (target, max(1, round(height * target / width))),
                    Image.Resampling.LANCZOS,
                )
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.getbands() or "transparency" in img.info else "RGB")
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=qualidade, method=5)
            novo = buf.getvalue()
            # Evitar perda de qualidade quando nao existe reducao significativa.
            if len(novo) >= len(dados) * 0.80:
                return None
            return novo, width, height
    except (UnidentifiedImageError, OSError, ValueError, MemoryError, Image.DecompressionBombError):
        return None


def otimizar_imagens_mobile_hf81(
    pagina: str,
    arquivos: dict[str, bytes],
    *,
    baixar=_baixar,
) -> tuple[str, dict[str, bytes], dict[str, Any]]:
    """Otimizacao de ate 3 banners e um pop-up, sem mudar a versao desktop."""
    assets = dict(arquivos)
    relatorio: dict[str, Any] = {
        "banners_mobile": 0,
        "popup_mobile": 0,
        "economia_estimada_bytes_por_imagem": 0,
        "original_desktop_preservado": True,
        "falhas_ou_sem_economia": 0,
    }
    limites = {"banner": 3, "popup": 1}
    tentativas = {"banner": 0, "popup": 0}
    memo: dict[str, tuple[str, int, int] | None] = {}

    def processar(match: re.Match) -> str:
        tag = match.group(0)
        if "data-hf81-mobile" in tag:
            return tag
        classe = CLASS.search(tag)
        alt = ALT.search(tag)
        classe_txt = classe.group(2).lower() if classe else ""
        alt_txt = alt.group(2).lower() if alt else ""
        categoria = ""
        if ("hf65-art" in classe_txt or "afc65-art" in classe_txt) and "campanha especial alphafest" in alt_txt:
            categoria = "popup"
        elif "banner informativo alphafest" in alt_txt or "hf81-banner-principal" in classe_txt:
            categoria = "banner"
        if not categoria or relatorio[{"banner":"banners_mobile","popup":"popup_mobile"}[categoria]] >= limites[categoria]:
            return tag
        src_match = SRC.search(tag)
        if not src_match:
            return tag
        original_src = html_lib.unescape(src_match.group(2))
        if original_src in memo:
            item = memo[original_src]
        else:
            if tentativas[categoria] >= 6:
                return tag
            local = LOCAL.fullmatch(original_src)
            if local:
                blob = assets.get(original_src.lstrip("/"))
            elif _permitida(original_src):
                blob = baixar(original_src)
            else:
                return tag
            tentativas[categoria] += 1
            item = None
            if blob:
                mobile = _mobile_webp(
                    blob,
                    largura=(900 if categoria == "banner" else 720),
                    qualidade=(85 if categoria == "banner" else 88),
                )
                if mobile:
                    webp, orig_w, orig_h = mobile
                    key = "assets/img/" + hashlib.sha256(webp).hexdigest()[:24] + ".webp"
                    assets[key] = webp
                    relatorio["economia_estimada_bytes_por_imagem"] += len(blob) - len(webp)
                    item = ("/" + key, orig_w, orig_h)
            if not item:
                relatorio["falhas_ou_sem_economia"] += 1
            memo[original_src] = item
        if not item:
            return tag
        src_mobile, largura_original, altura_original = item
        # A marca evita que a HF79 reescreva o <img> original de desktop.
        novo = tag[:-1] + ' data-hf81-mobile="1">'
        if not re.search(r'\bwidth\s*=', novo, re.I):
            novo = novo[:-1] + f' width="{largura_original}">'
        if not re.search(r'\bheight\s*=', novo, re.I):
            novo = novo[:-1] + f' height="{altura_original}">'
        if not re.search(r'\bdecoding\s*=', novo, re.I):
            novo = novo[:-1] + ' decoding="async">'
        if categoria == "banner" and relatorio["banners_mobile"] == 0:
            if not re.search(r'\bfetchpriority\s*=', novo, re.I):
                novo = novo[:-1] + ' fetchpriority="high">'
        estilo = "display:block;width:100%;height:100%" if categoria == "banner" else "display:block;width:100%"
        classe_picture = "hf81-banner-media" if categoria == "banner" else "hf81-popup-media"
        source = (
            f'<source media="(max-width: 700px)" srcset="{src_mobile}" '
            'type="image/webp">'
        )
        relatorio["banners_mobile" if categoria == "banner" else "popup_mobile"] += 1
        return f'<picture class="{classe_picture}" style="{estilo}">{source}{novo}</picture>'

    pagina_resultado = IMG.sub(processar, str(pagina or ""))
    return pagina_resultado, assets, relatorio
