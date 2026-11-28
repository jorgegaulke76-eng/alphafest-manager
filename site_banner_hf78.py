"""HF78: otimiza apenas o primeiro banner PNG, sem perda visual.

A variante WebP e lossless, sem redimensionamento, e so e escolhida quando
reduz >= 12% do tamanho. A imagem original permanece no ZIP.
Sem alteracao de cadastro, preco, pedido ou publicacao automatica.
"""
from __future__ import annotations

import hashlib
import io
import re
from typing import Any

PRIMEIRO_BANNER = re.compile(
    r'(<section\b[^>]*class=["\'][^"\']*\bhf6514-banner\b[^"\']*["\'][^>]*>)(.*?)(</section>)',
    re.IGNORECASE | re.DOTALL,
)
IMAGEM = re.compile(r'<img\b[^>]*>', re.IGNORECASE | re.DOTALL)
SRC = re.compile(r'\bsrc=["\'](/assets/img/([0-9a-f]{24})\.(png|jpg|webp))["\']', re.IGNORECASE)


def otimizar_banner_inicial_hf78(html: str, arquivos: dict[str, bytes]) -> tuple[str, dict[str, bytes], dict[str, Any]]:
    """Retorna nova Home, mapa de assets e diagnostico privado."""
    assets = dict(arquivos)
    relatorio: dict[str, Any] = {
        "banner_identificado": False,
        "variante_lossless": False,
        "economia_bytes": 0,
        "imagem_original_preservada": True,
    }
    m = PRIMEIRO_BANNER.search(html)
    if not m:
        return html, assets, relatorio
    img = IMAGEM.search(m.group(2))
    if not img:
        return html, assets, relatorio
    tag = img.group(0)
    src = SRC.search(tag)
    if not src:
        return html, assets, relatorio
    caminho = src.group(1).lstrip("/")
    bruto = assets.get(caminho)
    if not bruto:
        return html, assets, relatorio
    relatorio["banner_identificado"] = True
    novo_caminho = caminho
    dimensoes = None
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        # Ambientes de verificacao sem Pillow continuam gerando o mesmo site.
        return html, assets, relatorio
    try:
        with Image.open(io.BytesIO(bruto)) as original:
            # Respeitar limites de memoria do gerador. Preservar transparencias.
            if original.width * original.height <= 16_000_000:
                dimensoes = (original.width, original.height)
                if src.group(3).lower() == "png" and original.format == "PNG" and len(bruto) >= 70_000:
                    buffer = io.BytesIO()
                    original.save(buffer, format="WEBP", lossless=True, exact=True, method=4)
                    variante = buffer.getvalue()
                    if len(variante) <= len(bruto) * .88:
                        digest = hashlib.sha256(variante).hexdigest()[:24]
                        novo_caminho = f"assets/img/{digest}.webp"
                        assets[novo_caminho] = variante
                        relatorio["variante_lossless"] = True
                        relatorio["economia_bytes"] = len(bruto) - len(variante)
    except (UnidentifiedImageError, OSError, ValueError, MemoryError, Image.DecompressionBombError):
        pass
    novo_tag = tag
    if novo_caminho != caminho:
        novo_tag = novo_tag[:src.start(1)] + "/" + novo_caminho + novo_tag[src.end(1):]
    if not re.search(r'\bfetchpriority\s*=', novo_tag, re.I):
        novo_tag = novo_tag[:-1] + ' fetchpriority="high">'
    if not re.search(r'\bdecoding\s*=', novo_tag, re.I):
        novo_tag = novo_tag[:-1] + ' decoding="async">'
    if dimensoes:
        if not re.search(r'\bwidth\s*=', novo_tag, re.I):
            novo_tag = novo_tag[:-1] + f' width="{dimensoes[0]}">'
        if not re.search(r'\bheight\s*=', novo_tag, re.I):
            novo_tag = novo_tag[:-1] + f' height="{dimensoes[1]}">'
    return html[:m.start(2)+img.start()] + novo_tag + html[m.start(2)+img.end():], assets, relatorio
