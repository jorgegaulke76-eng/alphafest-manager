"""Configurações centrais do AlphaFest Manager.

A versão exibida pelo aplicativo é lida de ``VERSAO.txt`` para impedir que o
pacote, o GitHub e o Streamlit mostrem números diferentes.
"""
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent
_VERSION_FILE = _BASE_DIR / "VERSAO.txt"
_FALLBACK_VERSION = "19.0.2"


def _read_app_version() -> str:
    try:
        value = _VERSION_FILE.read_text(encoding="utf-8").strip()
        return value or _FALLBACK_VERSION
    except OSError:
        return _FALLBACK_VERSION


APP_VERSION = _read_app_version()
DATA_VERSION = 5
DEFAULT_TIMEZONE = "America/Sao_Paulo"

DOCUMENT_CACHE_TTL_SECONDS = 30
CONNECTION_CACHE_TTL_SECONDS = 120
