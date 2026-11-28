"""HF79: cria variantes leves de imagens publicas ja cadastradas.

Somente leitura de arquivos publicos do bucket catalogo em *.supabase.co.
Nao altera imagens no Supabase, banco, produtos, pedidos ou precos.
Falhas de rede/biblioteca preservam as URLs originais no site.
"""
from __future__ import annotations

import hashlib
import html as html_lib
import io
import re
from urllib.parse import urlsplit
from typing import Any

IMG = re.compile(r"<img\b[^>]*>", re.I | re.S)
SRC = re.compile(r"""\bsrc\s*=\s*(["'])(.*?)\1""", re.I | re.S)
CLASS = re.compile(r"""\bclass\s*=\s*(["'])(.*?)\1""", re.I | re.S)
ALT = re.compile(r"""\balt\s*=\s*(["'])(.*?)\1""", re.I | re.S)

MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


def _permitida(url: str) -> bool:
    try:
        p = urlsplit(html_lib.unescape(url))
    except ValueError:
        return False
    host = (p.hostname or "").lower()
    return (p.scheme == "https" and p.port in (None, 443)
            and re.fullmatch(r"[a-z0-9-]+\.supabase\.co", host) is not None
            and p.path.startswith("/storage/v1/object/public/catalogo/")
            and bool(p.path.rsplit("/", 1)[-1])
            and not p.username and not p.password and not p.query and not p.fragment)


def _baixar(url: str) -> bytes | None:
    import requests
    try:
        with requests.get(url, stream=True, timeout=(3, 6), allow_redirects=False) as resposta:
            if resposta.status_code != 200:
                return None
            tipo = resposta.headers.get("content-type", "").lower()
            if not tipo.startswith("image/") or "svg" in tipo:
                return None
            length = resposta.headers.get("content-length", "0")
            if length.isdigit() and int(length) > MAX_DOWNLOAD_BYTES:
                return None
            blocos = []
            total = 0
            for bloco in resposta.iter_content(chunk_size=65536):
                total += len(bloco)
                if total > MAX_DOWNLOAD_BYTES:
                    return None
                blocos.append(bloco)
            return b"".join(blocos)
    except (requests.RequestException, OSError, ValueError):
        return None


def _variantes(dados: bytes, limite_desktop: int, limite_mobile: int) -> dict[int, bytes]:
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        return {}
    saida: dict[int, bytes] = {}
    try:
        with Image.open(io.BytesIO(dados)) as img:
            if img.width * img.height > MAX_IMAGE_PIXELS or img.width <= 0 or img.height <= 0:
                return {}
            if img.format not in ("PNG", "JPEG", "WEBP"):
                return {}
            # Sem corte, sem alterar textos ou proporcoes das artes.
            img = ImageOps.exif_transpose(img)
            img.load()
            for largura in sorted(set((limite_mobile, limite_desktop))):
                if img.width <= largura:
                    continue
                altura = max(1, round(img.height * largura / img.width))
                reducao = img.resize((largura, altura), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                reducao.save(buffer, format="WEBP", lossless=True, exact=True, method=4)
                bytes_webp = buffer.getvalue()
                if len(bytes_webp) < len(dados) * .80:
                    saida[largura] = bytes_webp
    except (UnidentifiedImageError, OSError, ValueError, MemoryError, Image.DecompressionBombError):
        return {}
    return saida


def otimizar_imagens_remotas_hf79(
    pagina: str,
    arquivos: dict[str, bytes],
    *,
    baixar=_baixar,
) -> tuple[str, dict[str, bytes], dict[str, Any]]:
    """Otimiza ate tres banners, uma campanha e um destaque; falha preserva original."""
    assets = dict(arquivos)
    relatorio: dict[str, Any] = {"imagens_tentadas": 0, "imagens_otimizadas": 0,
                                "bytes_originais": 0, "bytes_principais": 0,
                                "elegiveis_sem_variante": 0, "falhas_download": 0,
                                "origens_ignoradas": 0, "fallback_original_preservado": True}
    limites_categoria = {"banner": 3, "campanha": 1, "produto": 1}
    atendidos = {"banner": 0, "campanha": 0, "produto": 0}
    # Limitar a quantidade de tentativas para nao prolongar a geracao do ZIP.
    tentativas = {"banner": 0, "campanha": 0, "produto": 0}
    urls_ja_vistas = set()

    def trocar(match: re.Match) -> str:
        tag = match.group(0)
        classes = CLASS.search(tag)
        classe = classes.group(2).lower() if classes else ""
        alt = ALT.search(tag)
        texto_alt = alt.group(2).lower() if alt else ""
        categoria = ""
        if "hf6514-banner-slide" in classe or "banner informativo alphafest" in texto_alt:
            categoria = "banner"
        elif "hf65-art" in classe and "campanha especial alphafest" in texto_alt:
            categoria = "campanha"
        elif "hf50-carousel-product-img" in classe:
            categoria = "produto"
        if not categoria or atendidos[categoria] >= limites_categoria[categoria]:
            return tag
        src = SRC.search(tag)
        if src is None:
            return tag
        url = html_lib.unescape(src.group(2))
        if not _permitida(url):
            relatorio["origens_ignoradas"] += 1
            return tag
        if url in urls_ja_vistas or tentativas[categoria] >= 6:
            return tag
        urls_ja_vistas.add(url)
        tentativas[categoria] += 1
        relatorio["imagens_tentadas"] += 1
        bruto = baixar(url)
        if not bruto:
            relatorio["falhas_download"] += 1
            return tag
        limites = (1280, 900) if categoria == "banner" else ((760, 480) if categoria == "produto" else (840, 520))
        variantes = _variantes(bruto, *limites)
        if not variantes:
            relatorio["elegiveis_sem_variante"] += 1
            return tag
        # Marcar como atendida somente depois de gerar uma variante real.
        # Caso contrário o primeiro card bloqueia os seguintes.
        atendidos[categoria] += 1
        arquivos_gerados = {}
        for largura, blob in variantes.items():
            caminho = "assets/img/" + hashlib.sha256(blob).hexdigest()[:24] + ".webp"
            arquivos_gerados[largura] = ("/" + caminho, caminho, blob)
        maior = max(arquivos_gerados)
        menor = min(arquivos_gerados)
        assets.update({v[1]: v[2] for v in arquivos_gerados.values()})
        relatorio["imagens_otimizadas"] += 1
        relatorio["bytes_originais"] += len(bruto)
        relatorio["bytes_principais"] += len(arquivos_gerados[maior][2])
        novo = tag[:src.start(2)] + html_lib.escape(arquivos_gerados[maior][0], quote=True) + tag[src.end(2):]
        if menor != maior and not re.search(r"\bsrcset\s*=", novo, re.I):
            tamanhos = "(max-width: 700px) 100vw, 90vw" if categoria == "banner" else "(max-width: 700px) 90vw, 340px"
            adicional = (f' srcset="{arquivos_gerados[menor][0]} {menor}w, '
                         f'{arquivos_gerados[maior][0]} {maior}w" sizes="{tamanhos}"')
            novo = novo[:-1] + adicional + ">"
        if categoria == "banner" and atendidos[categoria] == 1:
            novo = re.sub(r"""\bloading\s*=\s*(["'])lazy\1""", 'loading="eager"', novo, flags=re.I)
            if not re.search(r"\bfetchpriority\s*=", novo, re.I):
                novo = novo[:-1] + ' fetchpriority="high">'
        return novo

    return IMG.sub(trocar, str(pagina or "")), assets, relatorio
