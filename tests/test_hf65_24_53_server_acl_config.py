"""ACL comercial nao pode herdar o email da allowlist de diagnostico."""
from types import SimpleNamespace
import pytest
from commercial_server_acl_config import commercial_read_policy_from_server_secrets
from commercial_private_document_adapter import PrivateStoreDenied
from commercial_operator_policy import VerifiedOperator, READ, WRITE


def test_only_explicit_opaque_subjects_are_granted_read():
    subject = "a" * 64
    st = SimpleNamespace(secrets={
        "HF53_COMMERCIAL_ACL_ENABLED": True,
        "HF53_COMMERCIAL_READ_SUBJECTS": [subject],
        "HF53_HTTP_DIAG_ALLOWED_EMAIL": "user@example.invalid",
        "auth": {"client_id": "web-client-test"},
    })
    policy = commercial_read_policy_from_server_secrets(st)
    principal = VerifiedOperator(subject, "https://accounts.google.com", "web-client-test")
    assert policy.permitted(principal, READ)
    assert not policy.permitted(principal, WRITE)
    assert not policy.permitted(VerifiedOperator("user@example.invalid",
        "https://accounts.google.com", "web-client-test"), READ)
    assert not policy.permitted(VerifiedOperator(subject,
        "https://accounts.google.com", "another-client"), READ)


@pytest.mark.parametrize("grants", [[], ["user@example.invalid"], ["Jorge"],
    ["x" * 64], ["a" * 64, "a" * 64], "a" * 64, [123]])
def test_invalid_acl_never_implicitly_grants(grants):
    st = SimpleNamespace(secrets={
        "HF53_COMMERCIAL_ACL_ENABLED": True,
        "HF53_COMMERCIAL_READ_SUBJECTS": grants,
        "auth": {"client_id": "web-client-test"},
    })
    with pytest.raises(PrivateStoreDenied):
        commercial_read_policy_from_server_secrets(st)


def test_missing_opt_in_blocks_commercial_policy():
    st = SimpleNamespace(secrets={
        "HF53_COMMERCIAL_READ_SUBJECTS": ["a" * 64],
        "auth": {"client_id": "web-client-test"},
    })
    with pytest.raises(PrivateStoreDenied):
        commercial_read_policy_from_server_secrets(st)
