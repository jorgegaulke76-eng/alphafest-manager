"""Cache leve de documentos gerados no AlphaFest Manager.

HF42: evita reconstruir o mesmo PDF/arquivo em todo rerun do Streamlit. O cache
recebe uma assinatura do conteúdo que alimenta o documento; qualquer mudança
real nos dados gera uma nova entrada automaticamente.

O módulo é independente de Streamlit para poder ser testado isoladamente.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, MutableMapping
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


def _normalise(value: Any) -> Any:
    """Converte estruturas comuns em uma representação JSON determinística."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, bytes):
        return {"__bytes_sha256__": hashlib.sha256(value).hexdigest(), "size": len(value)}
    if isinstance(value, Path):
        return {"__path__": str(value)}
    if isinstance(value, dict):
        return {str(k): _normalise(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if isinstance(value, set):
        normalised = [_normalise(v) for v in value]
        return sorted(normalised, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))
    return {"__repr__": repr(value)}


def stable_signature(value: Any) -> str:
    payload = json.dumps(
        _normalise(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cache_get_or_build(
    cache: MutableMapping[str, Any],
    namespace: str,
    payload: Any,
    builder: Callable[[], T],
    *,
    ttl_seconds: int | float = 600,
    max_entries: int = 16,
    now: float | None = None,
) -> tuple[T, bool]:
    """Retorna documento já pronto ou chama ``builder`` uma única vez.

    Retorno: ``(valor, cache_hit)``. Entradas são limitadas por quantidade e TTL
    para não deixar PDFs antigos ocupando memória indefinidamente.
    """
    if not isinstance(cache, MutableMapping):
        raise TypeError("cache precisa ser um mapeamento mutável")
    current = float(time.time() if now is None else now)
    ttl = max(0.0, float(ttl_seconds))
    limit = max(1, int(max_entries))
    key = f"{str(namespace)}:{stable_signature(payload)}"

    # Limpa entradas expiradas antes da consulta. Ignora chaves externas caso o
    # chamador use o mesmo dicionário para metadados auxiliares.
    expired: list[str] = []
    for item_key, entry in list(cache.items()):
        if not isinstance(entry, dict) or "created_at" not in entry or "value" not in entry:
            continue
        try:
            created = float(entry.get("created_at") or 0.0)
        except Exception:
            created = 0.0
        if ttl and current - created > ttl:
            expired.append(item_key)
    for item_key in expired:
        cache.pop(item_key, None)

    entry = cache.get(key)
    if isinstance(entry, dict) and "value" in entry:
        entry["last_access"] = current
        return entry["value"], True

    value = builder()
    cache[key] = {"value": value, "created_at": current, "last_access": current}

    managed = [
        (item_key, entry)
        for item_key, entry in cache.items()
        if isinstance(entry, dict) and "created_at" in entry and "value" in entry
    ]
    if len(managed) > limit:
        managed.sort(key=lambda item: float(item[1].get("last_access") or item[1].get("created_at") or 0.0))
        for item_key, _ in managed[: len(managed) - limit]:
            cache.pop(item_key, None)

    return value, False


def clear_namespace(cache: MutableMapping[str, Any], namespace: str) -> int:
    prefix = f"{str(namespace)}:"
    keys = [key for key in list(cache.keys()) if str(key).startswith(prefix)]
    for key in keys:
        cache.pop(key, None)
    return len(keys)
