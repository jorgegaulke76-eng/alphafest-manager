"""HF53 bootstrap em SQLite temporário. Sem conexões externas."""
import json
import sqlite3

import pytest

from commercial_private_bootstrap import (
    BootstrapUnavailable, initialize_private_history_if_absent as bootstrap,
)
from commercial_private_document_adapter import (
    DOCUMENT_KEY, PrivateStoreDenied, PrivateStoreConflict,
)
from commercial_operator_policy import VerifiedOperator

USER = VerifiedOperator("operator-test", "issuer-test", "audience-test")


class SQLiteDocument:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE app_data (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.calls = 0

    def read(self, key):
        row = self.db.execute("SELECT value FROM app_data WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def insert(self, key, value):
        self.calls += 1
        cur = self.db.execute(
            "INSERT INTO app_data (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
            (key, json.dumps(value)),
        )
        self.db.commit()
        return cur.rowcount == 1

    def close(self):
        self.db.close()


def invoke(store, **changes):
    settings = dict(
        principal=USER,
        approve_initialization=lambda user: user == USER,
        credential_mode=lambda: "service",
        read_online=store.read,
        insert_if_absent=store.insert,
    )
    settings.update(changes)
    return bootstrap(**settings)


def test_first_bootstrap_and_retry_never_overwrite():
    store = SQLiteDocument()
    try:
        assert invoke(store) == "created"
        assert invoke(store) == "existing"
        assert store.calls == 1
        assert store.read(DOCUMENT_KEY) == {"events": []}
    finally:
        store.close()


def test_existing_nonempty_history_is_preserved():
    store = SQLiteDocument()
    try:
        original = {"events": [{
            "event_id": "b0b20f6d-866f-4f15-8dad-4b62a90d5ce7",
            "numero_proposta": "P1", "atendimento_id": "A1",
            "campaign": "natal", "decisao": "confirmar",
            "evidencia": "referencia_cliente", "usuario": "operator-test",
            "ocorrido_em": "2026-11-23T16:00:00-03:00",
        }]}
        assert store.insert(DOCUMENT_KEY, original) is True
        assert invoke(store) == "existing"
        assert store.calls == 1
        assert store.read(DOCUMENT_KEY) == original
    finally:
        store.close()


def test_competing_initializer_wins_atomically_without_overwrite():
    store = SQLiteDocument()
    try:
        original_insert = store.insert

        def concurrently_created(key, value):
            original_insert(key, {"events": []})
            return original_insert(key, value)

        assert invoke(store, insert_if_absent=concurrently_created) == "existing"
        assert store.read(DOCUMENT_KEY) == {"events": []}
    finally:
        store.close()


def test_corrupt_existing_document_is_not_repaired():
    store = SQLiteDocument()
    try:
        store.insert(DOCUMENT_KEY, {"unknown": []})
        with pytest.raises(ValueError):
            invoke(store)
        assert store.calls == 1
    finally:
        store.close()


@pytest.mark.parametrize("change", [
    {"principal": "operator-test"},
    {"approve_initialization": lambda user: False},
    {"credential_mode": lambda: "anon"},
    {"approve_initialization": lambda user: (_ for _ in ()).throw(RuntimeError())},
])
def test_authorization_failed_before_database_write(change):
    store = SQLiteDocument()
    try:
        with pytest.raises(PrivateStoreDenied):
            invoke(store, **change)
        assert store.calls == 0
    finally:
        store.close()


def test_remote_unavailable_no_fallback_or_write():
    store = SQLiteDocument()
    try:
        with pytest.raises(BootstrapUnavailable):
            invoke(store, read_online=lambda key: (_ for _ in ()).throw(OSError()))
        assert store.calls == 0
    finally:
        store.close()


def test_unconfirmed_insert_never_reports_success():
    store = SQLiteDocument()
    try:
        with pytest.raises(BootstrapUnavailable):
            invoke(store, insert_if_absent=lambda key, value: None)
    finally:
        store.close()


def test_insert_success_but_concurrent_change_does_not_claim_empty():
    store = SQLiteDocument()
    try:
        def inserted_then_changed(key, value):
            assert store.insert(key, value)
            store.db.execute("UPDATE app_data SET value = ? WHERE key = ?",
                             (json.dumps({"unknown": []}), key))
            store.db.commit()
            return True

        with pytest.raises(ValueError):
            invoke(store, insert_if_absent=inserted_then_changed)
    finally:
        store.close()


def test_permission_revoked_between_read_and_insert_prevents_write():
    store = SQLiteDocument()
    try:
        checks = []

        def approve(_user):
            checks.append(True)
            return len(checks) == 1

        with pytest.raises(PrivateStoreDenied):
            invoke(store, approve_initialization=approve)
        assert len(checks) == 2
        assert store.calls == 0
        assert store.read(DOCUMENT_KEY) is None
    finally:
        store.close()


def test_credentials_downgraded_between_read_and_insert_prevents_write():
    store = SQLiteDocument()
    try:
        modes = iter(["service", "anon"])
        with pytest.raises(PrivateStoreDenied):
            invoke(store, credential_mode=lambda: next(modes))
        assert store.calls == 0
    finally:
        store.close()


def test_preexisting_history_does_not_need_second_permission_check():
    store = SQLiteDocument()
    try:
        assert store.insert(DOCUMENT_KEY, {"events": []}) is True
        checks = []
        def approve(_user):
            checks.append(True)
            return True
        assert invoke(store, approve_initialization=approve) == "existing"
        assert len(checks) == 1
        assert store.calls == 1
    finally:
        store.close()
