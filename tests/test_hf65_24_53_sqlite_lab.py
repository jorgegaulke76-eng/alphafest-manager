"""Laboratório de armazenamento append-only; sem bancos externos."""
import sqlite3
import uuid

import pytest

from commercial_attribution_sqlite_lab import (
    AttributionConflict, append_validated_event_lab, current_revision,
    install_test_schema, read_events, read_effective_lab,
)


ORDERS = [{"numero_proposta": "P1", "atendimento_id": "A1", "pago": True, "valor_total": "99,90"}]
CONTACTS = [{"id": "A1"}]


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    install_test_schema(conn)
    yield conn
    conn.close()


def append(db, *, event_id=None, expected_revision=0, decision="confirmar",
           campaign="natal_2026", time="2026-11-23T15:00:00-03:00"):
    return append_validated_event_lab(
        db, event_id=event_id or str(uuid.uuid4()),
        expected_revision=expected_revision, numero_proposta="P1",
        atendimento_id="A1", campaign=campaign, decisao=decision,
        evidencia="mensagem_whatsapp", usuario="operador_teste",
        ocorrido_em=time, propostas=ORDERS, atendimentos=CONTACTS,
    )


def test_confirm_revoke_append_only(db):
    append(db)
    rev = current_revision(db, "P1")
    assert rev == 1
    assert read_effective_lab(db) == [{"numero_proposta": "P1", "campaign": "natal_2026"}]
    append(db, expected_revision=rev, decision="revogar",
           time="2026-11-23T15:01:00-03:00")
    assert current_revision(db, "P1") == 2
    assert len(read_events(db, "P1")) == 2
    assert read_effective_lab(db) == []
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM hf53_attribution_events_lab WHERE seq = 1")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE hf53_attribution_events_lab SET campaign='outra' WHERE seq=1")


def test_repeat_same_idempotency_id_no_duplicate(db):
    identity = str(uuid.uuid4())
    append(db, event_id=identity)
    append(db, event_id=identity)
    assert current_revision(db, "P1") == 1
    assert len(read_events(db)) == 1


def test_reuse_event_id_different_content_fails(db):
    identity = str(uuid.uuid4())
    append(db, event_id=identity)
    with pytest.raises(AttributionConflict):
        append(db, event_id=identity, campaign="outra")
    assert len(read_events(db)) == 1


def test_stale_revision_prevents_lost_update(db):
    append(db)
    with pytest.raises(AttributionConflict):
        append(db, expected_revision=0, campaign="instagram")
    assert read_effective_lab(db) == [{"numero_proposta": "P1", "campaign": "natal_2026"}]


def test_bad_event_does_not_open_transaction(db):
    with pytest.raises(ValueError):
        append(db, campaign="cliente@example.com")
    append(db)
    assert len(read_events(db)) == 1


def test_requires_valid_uuid_and_revision(db):
    with pytest.raises(ValueError):
        append(db, event_id="not-a-uuid")
    with pytest.raises(ValueError):
        append(db, expected_revision=-1)


def test_reopen_file_laboratory(tmp_path):
    path = tmp_path / "lab.sqlite"
    with sqlite3.connect(path, isolation_level=None) as conn:
        install_test_schema(conn)
        append(conn)
    with sqlite3.connect(path, isolation_level=None) as conn:
        assert len(read_events(conn)) == 1
        assert current_revision(conn, "P1") == 1
