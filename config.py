"""Configurações centrais do AlphaFest Manager.

A versão exibida pelo aplicativo é lida de ``VERSAO.txt`` para impedir que o
pacote, o GitHub e o Streamlit mostrem números diferentes.
"""
from pathlib import Path
import json

_BASE_DIR = Path(__file__).resolve().parent
_VERSION_FILE = _BASE_DIR / "VERSAO.txt"
_FALLBACK_VERSION = "19.0.2"


def _read_app_version() -> str:
    try:
        value = _VERSION_FILE.read_text(encoding="utf-8").strip()
        return value or _FALLBACK_VERSION
    except OSError:
        return _FALLBACK_VERSION


def _read_release_display() -> str:
    """Lê a data/hora gravada no pacote; não confunde com o horário de abertura."""
    try:
        payload = json.loads((_BASE_DIR / "RELEASE_INFO.json").read_text(encoding="utf-8"))
        if payload.get("version") != _read_app_version():
            return "Data da versão indisponível (metadados divergentes)"
        from datetime import datetime
        from zoneinfo import ZoneInfo
        date = datetime.fromisoformat(payload["created_at"])
        if date.tzinfo is None:
            return "Data da versão indisponível"
        return date.astimezone(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%d/%m/%Y às %H:%M")
    except (OSError, ValueError, TypeError, KeyError):
        return "Data da versão indisponível"


APP_VERSION = _read_app_version()
DATA_VERSION = 5
DEFAULT_TIMEZONE = "America/Sao_Paulo"
APP_RELEASE_DISPLAY = _read_release_display()

DOCUMENT_CACHE_TTL_SECONDS = 30
CONNECTION_CACHE_TTL_SECONDS = 120
