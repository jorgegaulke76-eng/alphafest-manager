"""Automação segura da fotografia diária da Agenda da Anna.

HF51: prepara a fotografia do início do dia na primeira abertura da Central,
sem alterar propostas, status ou regras operacionais. A persistência continua
sob responsabilidade do app, que só considera o snapshot válido após o banco
confirmar a gravação.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable


def prepare_daily_snapshot(
    snapshots: dict[str, Any] | None,
    day_key: str,
    agenda: Iterable[dict[str, Any]] | None,
    registered_at: datetime,
    *,
    create_snapshot: Callable[[Iterable[dict[str, Any]] | None, datetime], dict[str, Any] | None],
    validate_snapshot: Callable[[Any], bool],
    retention_days: int = 60,
) -> tuple[dict[str, Any] | None, dict[str, Any], bool]:
    """Prepara um snapshot diário sem sobrescrever fotografia já válida.

    Retorna ``(snapshot_do_dia, mapa_atualizado, criado_agora)``. A função é
    pura: não grava banco, não toca em session_state e não altera a agenda.
    """
    base = dict(snapshots or {}) if isinstance(snapshots, dict) else {}
    key = str(day_key or "").strip()
    if not key:
        return None, base, False

    existing = base.get(key)
    if validate_snapshot(existing):
        return existing, base, False

    created = create_snapshot(agenda, registered_at)
    if not validate_snapshot(created):
        return None, base, False

    updated = dict(base)
    updated[key] = created

    keep = max(1, int(retention_days or 60))
    date_keys = sorted(k for k in updated if len(str(k)) == 10 and str(k)[4:5] == "-" and str(k)[7:8] == "-")
    for old_key in date_keys[:-keep]:
        updated.pop(old_key, None)

    return created, updated, True
