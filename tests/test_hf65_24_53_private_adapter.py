"""Testes do adaptador sem internet, Supabase ou dados reais."""
import copy
from uuid import uuid4

import pytest

from commercial_private_document_adapter import (
    DOCUMENT_KEY, PrivateStoreDenied, PrivateStoreConflict,
    append_private_event, read_private_events,
)

ORDERS = [{"numero_proposta": "P1", "atendimento_id": "A1", "pago": True}]
CONTACTS = [{"id": "A1"}]


class MemoryDocument:
    def __init__(self):
        self.value = {"events": []}
        self.cas_calls = 0

    def load(self, key):
        assert key == DOCUMENT_KEY
        return copy.deepcopy(self.value)

    def save(self, key, expected, value):
        assert key == DOCUMENT_KEY
        self.cas_calls += 1
        if self.value != expected:
            return False, "conflito"
        self.value = copy.deepcopy(value)
        return True, "online"


def allow(principal, action):
    return principal == ("verified", "admin") and action in {
        "read_attribution", "write_attribution"
    }


def deny(principal, action):
    return False


def service():
    return "service"


def anon():
    return "anon"


def args(db, **overrides):
    data = {
        "principal": ("verified", "admin"),
        "authorize": allow,
        "credential_mode": service,
        "load": db.load,
        "save_cas": db.save,
        "event_id": str(uuid4()),
        "numero_proposta": "P1",
        "atendimento_id": "A1",
        "campaign": "natal_2026",
        "decisao": "confirmar",
        "evidencia": "mensagem_whatsapp",
        "ocorrido_em": "2026-11-23T16:00:00-03:00",
        "usuario_verificado": "operador_autenticado",
        "propostas": ORDERS,
        "atendimentos": CONTACTS,
    }
    data.update(overrides)
    return data


def test_requires_real_auth_callback_and_service_mode():
    db = MemoryDocument()
    for changed in (
        {"authorize": None},
        {"authorize": deny},
        {"credential_mode": anon},
        {"principal": "operador_autodeclarado"},
    ):
        with pytest.raises(PrivateStoreDenied):
            append_private_event(**args(db, **changed))
    assert db.cas_calls == 0


def test_private_read_denied_before_loading():
    db = MemoryDocument()
    with pytest.raises(PrivateStoreDenied):
        read_private_events(
            principal="intruso", authorize=allow,
            credential_mode=service, load=db.load
        )


def test_create_and_retry_are_idempotent():
    db = MemoryDocument()
    params = args(db)
    append_private_event(**params)
    append_private_event(**params)
    assert db.cas_calls == 1
    assert len(read_private_events(
        principal=("verified", "admin"), authorize=allow,
        credential_mode=service, load=db.load,
    )) == 1


def test_duplicate_event_id_with_other_campaign_denied():
    db = MemoryDocument()
    params = args(db)
    append_private_event(**params)
    with pytest.raises(PrivateStoreConflict):
        append_private_event(**dict(params, campaign="professores"))
    assert db.cas_calls == 1


def test_concurrent_change_rejected_not_counted_as_save():
    db = MemoryDocument()
    def conflicting_save(key, expected, value):
        db.value = {"events": [{"unexpected": "external"}]}
        return False, "conflito"
    with pytest.raises(PrivateStoreConflict):
        append_private_event(**args(db, save_cas=conflicting_save))


def test_invalid_existing_event_refuses_append():
    db = MemoryDocument()
    db.value = {"events": [{"unknown": "field"}]}
    with pytest.raises(ValueError):
        append_private_event(**args(db))
    assert db.cas_calls == 0


def test_no_local_fallback_confirmation():
    db = MemoryDocument()
    def local_save(key, expected, value):
        return False, "contingência local sem confirmação online"
    with pytest.raises(PrivateStoreConflict):
        append_private_event(**args(db, save_cas=local_save))


def test_cannot_migrate_event_to_unrelated_contact():
    db = MemoryDocument()
    append_private_event(**args(db))
    with pytest.raises(PrivateStoreConflict):
        append_private_event(**args(
            db, atendimento_id="A2", propostas=[{"numero_proposta": "P1", "atendimento_id": "A2"}],
            atendimentos=[{"id": "A2"}]
        ))


def test_missing_remote_document_blocks_writes_and_reads():
    db = MemoryDocument()
    db.value = None
    with pytest.raises(PrivateStoreConflict):
        append_private_event(**args(db))
    with pytest.raises(PrivateStoreConflict):
        read_private_events(
            principal=("verified", "admin"), authorize=allow,
            credential_mode=service, load=db.load,
        )
    assert db.cas_calls == 0
