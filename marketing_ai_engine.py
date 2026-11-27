"""Geração IA Premium e pós-processamento oficial AlphaFest."""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


def _client(api_key: str | None = None):
    key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("Configure OPENAI_API_KEY nos Secrets para usar a Campanha IA Premium.")
    if OpenAI is None:
        raise RuntimeError("A biblioteca OpenAI não está instalada.")
    return OpenAI(api_key=key)


def _decode_image_response(response: Any) -> bytes:
    data = getattr(response, "data", None) or []
    if not data:
        raise RuntimeError("O gerador de imagens não retornou uma arte.")
    item = data[0]
    b64 = getattr(item, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    raise RuntimeError("Resposta de imagem sem conteúdo em base64.")


def generate_premium_square(*, prompt: str, product_png: bytes, api_key: str | None = None) -> bytes:
    """Gera a composição completa usando a foto enviada como referência."""
    client = _client(api_key)
    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    image_file = io.BytesIO(product_png)
    image_file.name = "produto.png"
    try:
        response = client.images.edit(
            model=model,
            image=image_file,
            prompt=prompt,
            size="1024x1024",
            quality=os.getenv("OPENAI_IMAGE_QUALITY", "high"),
        )
    except TypeError:
        image_file.seek(0)
        response = client.images.edit(model=model, image=image_file, prompt=prompt, size="1024x1024")
    return _decode_image_response(response)


def _prepare_logo(logo_path: Path, max_size: tuple[int, int]) -> Image.Image | None:
    if not logo_path.exists():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    if logo.getextrema()[3] == (255, 255):
        pixels = logo.load()
        for y in range(logo.height):
            for x in range(logo.width):
                r, g, b, a = pixels[x, y]
                if max(r, g, b) < 24:
                    pixels[x, y] = (r, g, b, 0)
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    logo.thumbnail(max_size, Image.Resampling.LANCZOS)
    return logo


def apply_official_logo(image_bytes: bytes, logo_path: Path) -> bytes:
    """Aplica o logo oficial na zona superior reservada pelo Prompt Mestre."""
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    logo = _prepare_logo(logo_path, (int(base.width * .28), int(base.height * .20)))
    if logo:
        shadow_alpha = logo.getchannel("A").filter(ImageFilter.GaussianBlur(max(4, base.width // 180)))
        shadow = Image.new("RGBA", logo.size, (0, 30, 90, 0))
        shadow.putalpha(shadow_alpha.point(lambda value: int(value * .28)))
        x = (base.width - logo.width) // 2
        y = max(8, int(base.height * .015))
        base.alpha_composite(shadow, (x + 5, y + 8))
        base.alpha_composite(logo, (x, y))
    output = io.BytesIO()
    base.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def adapt_square_to_channel(square_bytes: bytes, size: tuple[int, int]) -> bytes:
    """Adapta a arte premium sem distorcer nem cortar textos importantes."""
    source = Image.open(io.BytesIO(square_bytes)).convert("RGB")
    width, height = size
    if width == height:
        result = ImageOps.fit(source, size, Image.Resampling.LANCZOS)
    else:
        background = ImageOps.fit(source, size, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(34))
        # Escala a arte inteira para caber e preserva todos os textos.
        foreground = source.copy()
        foreground.thumbnail((int(width * .96), int(height * .90)), Image.Resampling.LANCZOS)
        x = (width - foreground.width) // 2
        y = (height - foreground.height) // 2
        background.paste(foreground, (x, y))
        result = background
    output = io.BytesIO()
    result.save(output, format="PNG", optimize=True)
    return output.getvalue()
