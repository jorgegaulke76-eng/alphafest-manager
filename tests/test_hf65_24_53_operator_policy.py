"""HF65.24.53 — permissão de operador em identidade já verificada."""
import pytest

from commercial_operator_policy import (
    OperatorPolicy, VerifiedOperator, READ, WRITE, verified_operator_from_backend,
)


@pytest.fixture
def policy():
    return OperatorPolicy(
        issuer="https://issuer.example",
        audience="alphafest-manager-test",
        grants={"opaque-jorge-test": {READ, WRITE},
                "opaque-anna-test": {READ}},
    )


def identity(subject, *, issuer="https://issuer.example",
             audience="alphafest-manager-test", verified=True):
    return verified_operator_from_backend(
        subject=subject, issuer=issuer, audience=audience, verified=verified,
    )


def test_least_privilege_read_only_and_admin(policy):
    assert policy.permitted(identity("opaque-jorge-test"), READ)
    assert policy.permitted(identity("opaque-jorge-test"), WRITE)
    assert policy.permitted(identity("opaque-anna-test"), READ)
    assert not policy.permitted(identity("opaque-anna-test"), WRITE)


def test_unknown_subject_and_issuer_and_audience_fail_closed(policy):
    assert not policy.permitted(identity("other"), READ)
    assert not policy.permitted(identity("opaque-jorge-test", issuer="https://evil.example"), READ)
    assert not policy.permitted(identity("opaque-jorge-test", audience="another-app"), READ)
    assert not policy.permitted(identity("opaque-jorge-test"), "delete_everything")


def test_untrusted_metadata_or_email_does_not_authorize(policy):
    assert not policy.permitted({
        "email": "someone@example.test",
        "role": "admin",
        "user_metadata": {"subject": "opaque-jorge-test"},
    }, WRITE)
    assert not policy.permitted("opaque-jorge-test", READ)


def test_forged_unverified_principal_rejected_before_policy():
    with pytest.raises(ValueError):
        identity("opaque-jorge-test", verified=False)


@pytest.mark.parametrize("grants", [
    {},
    {"somebody": {"superuser"}},
    {"somebody": set()},
    {"": {READ}},
])
def test_invalid_policy_is_rejected(grants):
    with pytest.raises(ValueError):
        OperatorPolicy(issuer="issuer", audience="manager", grants=grants)


def test_verified_principal_is_frozen():
    principal = identity("opaque-jorge-test")
    with pytest.raises(Exception):
        principal.subject = "something-else"
