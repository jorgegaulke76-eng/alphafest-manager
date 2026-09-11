"""Regras puras do agendamento de backup do AlphaFest Manager."""
from __future__ import annotations

from datetime import datetime, timedelta


def parse_schedule(value: str, default: tuple[int, int] = (22, 0)) -> tuple[int, int]:
    try:
        hour_s, minute_s = str(value or "").strip().split(":", 1)
        hour, minute = int(hour_s), int(minute_s)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except Exception:
        pass
    return default


def parse_datetime(value: str, tzinfo) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or "").strip())
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzinfo)
    return dt.astimezone(tzinfo)


def latest_due_slot(now: datetime, schedule: str) -> datetime:
    """Última ocorrência do horário diário que já deveria ter acontecido."""
    hour, minute = parse_schedule(schedule)
    today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return today if now >= today else today - timedelta(days=1)


def backup_due(now: datetime, schedule: str, last_backup_em: str) -> tuple[bool, datetime]:
    slot = latest_due_slot(now, schedule)
    last = parse_datetime(last_backup_em, now.tzinfo)
    return (last is None or last < slot), slot


def slot_id(slot: datetime) -> str:
    return slot.isoformat(timespec="minutes")


def reservation_is_active(claimed_at: str, now: datetime, minutes: int = 30) -> bool:
    claimed = parse_datetime(claimed_at, now.tzinfo)
    if claimed is None:
        return False
    return now - claimed < timedelta(minutes=max(1, int(minutes or 30)))
