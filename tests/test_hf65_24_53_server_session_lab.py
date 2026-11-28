"""HF53: contrato da sessão revogável somente backend (SQLite descartável)."""
from datetime import datetime, timedelta, timezone
import sqlite3

from commercial_operator_policy import VerifiedOperator
from commercial_server_session_lab import (
    install_session_lab_schema, issue_session_lab, session_active_lab,
    revoke_session_lab, SessionStoreRejected,
)

NOW = datetime(2026, 11, 24, 13, 0, tzinfo=timezone.utc)
USER = VerifiedOperator("operator-opaque", "issuer-test", "audience-test")
OTHER = VerifiedOperator("other-operator", "issuer-test", "audience-test")


def test_issued_session_is_bound_to_identity_and_revocable():
    with sqlite3.connect(":memory:") as conn:
        install_session_lab_schema(conn)
        issued = issue_session_lab(conn, identity=USER, now=NOW, ttl_seconds=60)
        assert session_active_lab(conn, identity=USER, handle=issued.handle, now=NOW)
        assert not session_active_lab(conn, identity=OTHER, handle=issued.handle, now=NOW)
        assert revoke_session_lab(conn, handle=issued.handle) is True
        assert not session_active_lab(conn, identity=USER, handle=issued.handle, now=NOW)
        assert revoke_session_lab(conn, handle=issued.handle) is False


def test_session_expires_and_random_handle_never_authorizes():
    with sqlite3.connect(":memory:") as conn:
        install_session_lab_schema(conn)
        issued = issue_session_lab(conn, identity=USER, now=NOW, ttl_seconds=1)
        assert not session_active_lab(
            conn, identity=USER, handle=issued.handle, now=NOW+timedelta(seconds=1)
        )
        assert not session_active_lab(conn, identity=USER, handle="x"*43, now=NOW)


def test_only_digest_is_persisted_not_raw_session_handle():
    with sqlite3.connect(":memory:") as conn:
        install_session_lab_schema(conn)
        issued = issue_session_lab(conn, identity=USER, now=NOW)
        raw = str(conn.execute("SELECT * FROM hf53_session_lab").fetchall())
        assert issued.handle not in raw
        assert "operator-opaque" in raw


def test_invalid_ttl_identity_or_no_table_fail_closed():
    import pytest
    with sqlite3.connect(":memory:") as conn:
        install_session_lab_schema(conn)
        for ttl in (0, -1, 3601, 1.2, True):
            with pytest.raises(SessionStoreRejected):
                issue_session_lab(conn, identity=USER, now=NOW, ttl_seconds=ttl)
        with pytest.raises(SessionStoreRejected):
            issue_session_lab(conn, identity=OTHER, now=NOW.replace(tzinfo=None))
    with sqlite3.connect(":memory:") as conn:
        assert not session_active_lab(conn, identity=USER, handle="x"*43, now=NOW)
        with pytest.raises(SessionStoreRejected):
            issue_session_lab(conn, identity=USER, now=NOW)
