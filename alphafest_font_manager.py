"""Gerenciador portátil de fontes do AlphaFest Manager.

As fontes são resolvidas preferencialmente pelo pacote matplotlib, que inclui
DejaVu e é instalado pelo requirements.txt. Assim o renderizador não depende
das fontes disponíveis no sistema operacional do Streamlit Cloud.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final

from PIL import ImageFont


class FontUnavailableError(RuntimeError):
    """Erro claro quando nenhuma fonte vetorial portátil pode ser carregada."""


@lru_cache(maxsize=16)
def resolve_font_path(*, bold: bool = False, serif: bool = False, italic: bool = False) -> str:
    """Retorna o caminho de uma fonte escalável incluída pelo matplotlib.

    O pacote matplotlib distribui a família DejaVu em todas as plataformas
    suportadas. Isso evita depender de /usr/share/fonts ou fontconfig.
    """
    try:
        from matplotlib import font_manager
    except Exception as exc:  # pragma: no cover - mensagem exibida no app
        raise FontUnavailableError(
            "O pacote matplotlib não está disponível para carregar as fontes portáteis. "
            "Confirme 'matplotlib>=3.8' no requirements.txt e reinicie o aplicativo."
        ) from exc

    family: Final[str] = "DejaVu Serif" if serif else "DejaVu Sans"
    weight: Final[str] = "bold" if bold else "normal"
    style: Final[str] = "italic" if italic else "normal"

    try:
        props = font_manager.FontProperties(family=family, weight=weight, style=style)
        candidate = font_manager.findfont(props, fallback_to_default=True)
    except Exception as exc:
        raise FontUnavailableError(f"Falha ao localizar a fonte portátil {family}: {exc}") from exc

    path = Path(candidate)
    if not path.is_file() or path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
        raise FontUnavailableError(
            f"A fonte portátil {family} não foi encontrada. Reinstale as dependências do aplicativo."
        )
    return str(path)


@lru_cache(maxsize=256)
def get_font(size: int, *, bold: bool = False, serif: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Carrega uma fonte FreeType escalável e nunca usa a bitmap padrão."""
    path = resolve_font_path(bold=bool(bold), serif=bool(serif), italic=bool(italic))
    try:
        font = ImageFont.truetype(path, max(8, int(size)))
    except Exception as exc:
        raise FontUnavailableError(f"Falha ao abrir a fonte portátil {path}: {exc}") from exc
    if not isinstance(font, ImageFont.FreeTypeFont):
        raise FontUnavailableError(f"A fonte carregada não é escalável: {path}")
    return font


def clear_font_cache() -> None:
    """Limpa os caches; útil em diagnóstico e testes."""
    resolve_font_path.cache_clear()
    get_font.cache_clear()
