"""HF65.24.53 — laboratório de sessões próprias revogáveis, backend-only.

NÃO substitui validação do OIDC ou do cookie Streamlit. Este módulo só
modela armazenamento persistente/revogação, com conexão sqlite injetada e
isolada de teste. Não é importado pelo aplicativo publicado nem pelo gateway.
Não aceitar handle de URL, formulário, claims do usuário ou frontend.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from sqlite3 import Connection, IntegrityError
from typing import Any

from commercial_operator_policy import VerifiedOperator

MAX_SESSION_SECONDS = 3600


class SessionStoreRejected(PermissionError):
    """A sessão não está autorizada, ativa ou íntegra."""


@dataclass(frozen=True)
class IssuedSession:
    """Handle secreto transitório; jamais persistir ou registrar o valor bruto."""
    handle: str
    expires_at: int


def install_session_lab_schema(conn: Connection) -> None:
    """Criar esquema descartável e restrito, sem conexão ao Supabase."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS hf53_session_lab ("
        "hash TEXT PRIMARY KEY, subject TEXT NOT NULL, issuer TEXT NOT NULL, "
        "audience TEXT NOT NULL, expires_at INTEGER NOT NULL, "
        "revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0,1)))"
    )


def _timestamp(now: datetime) -> int:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise SessionStoreRejected("Relógio de servidor inválido.")
    return int(now.astimezone(timezone.utc).timestamp())


def _identity(identity: Any) -> VerifiedOperator:
    if not isinstance(identity, VerifiedOperator) or any(
        not isinstance(x, str) or not x or x != x.strip() or len(x) > 256
        for x in (identity.subject, identity.issuer, identity.audience)
    ):
        raise SessionStoreRejected("Identidade do servidor inválida.")
    return identity


def issue_session_lab(
    conn: Connection, *, identity: VerifiedOperator,
    now: datetime, ttl_seconds: int = 900,
) -> IssuedSession:
    """Emitir novo handle APENAS após identidade OIDC autenticada fora daqui."""
    identity = _identity(identity)
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_SESSION_SECONDS:
        raise SessionStoreRejected("Prazo de sessão inválido.")
    issued_at = _timestamp(now)
    handle = token_urlsafe(32)
    digest = sha256(handle.encode("ascii")).hexdigest()
    expires_at = issued_at + ttl_seconds
    try:
        with conn:
            conn.execute(
                "INSERT INTO hf53_session_lab"
                "(hash,subject,issuer,audience,expires_at,revoked) "
                "VALUES (?,?,?,?,?,0)",
                (digest, identity.subject, identity.issuer, identity.audience, expires_at),
            )
    except Exception:
        raise SessionStoreRejected("Registro privado de sessão indisponível.") from None
    return IssuedSession(handle=handle, expires_at=expires_at)


def session_active_lab(
    conn: Connection, *, identity: VerifiedOperator,
    handle: str, now: datetime,
) -> bool:
    """Verificar estado em cada acesso, vinculando handle + identidade + prazo."""
    try:
        identity = _identity(identity)
        current = _timestamp(now)
        if not isinstance(handle, str) or len(handle) < 40 or len(handle) > 128:
            return False
        digest = sha256(handle.encode("ascii")).hexdigest()
        row = conn.execute(
            "SELECT hash,subject,issuer,audience,expires_at,revoked "
            "FROM hf53_session_lab WHERE hash=?",
            (digest,),
        ).fetchone()
        return bool(
            row and compare_digest(row[0], digest)
            and compare_digest(row[1], identity.subject)
            and compare_digest(row[2], identity.issuer)
            and compare_digest(row[3], identity.audience)
            and row[4] > current and row[5] == 0
        )
    except Exception:
        return False


def revoke_session_lab(conn: Connection, *, handle: str) -> bool:
    """Revogar server-side de forma idempotente; sem depender de apagar cookie."""
    if not isinstance(handle, str) or len(handle) < 40 or len(handle) > 128:
        return False
    try:
        digest = sha256(handle.encode("ascii")).hexdigest()
        with conn:
            cursor = conn.execute(
                "UPDATE hf53_session_lab SET revoked=1 WHERE hash=? AND revoked=0",
                (digest,),
            )
        return cursor.rowcount == 1
    except Exception:
        return False
