"""HF65.24.53 — política de permissões para identidades já verificadas.

Não é autenticador, não verifica tokens, não liga login e não fornece acesso
ao aplicativo. Deve receber a identidade APÓS verificação criptográfica feita
por provedor confiável no servidor, com issuer/audience checados.
Nunca autorizar por nome, e-mail exibido ou user_metadata editável.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from typing import Any


READ = "read_attribution"
WRITE = "write_attribution"
PERMISSIONS = frozenset({READ, WRITE})


@dataclass(frozen=True)
class VerifiedOperator:
    """Representação interna gerada somente após autenticação do servidor."""
    subject: str
    issuer: str
    audience: str


class OperatorPolicy:
    """ACL explícita com sujeitos opacos verificados e privilégios mínimos."""

    def __init__(
        self, *, issuer: str, audience: str,
        grants: Mapping[str, Iterable[str]],
    ) -> None:
        if not issuer or not audience or not grants:
            raise ValueError("Política privada incompleta.")
        if not isinstance(grants, Mapping):
            raise ValueError("Permissões inválidas.")
        self.issuer = issuer
        self.audience = audience
        normalized: dict[str, frozenset[str]] = {}
        for subject, actions in grants.items():
            if not isinstance(subject, str) or not subject.strip():
                raise ValueError("Identificador do operador inválido.")
            action_set = frozenset(actions)
            if not action_set or not action_set <= PERMISSIONS:
                raise ValueError("Privilégio desconhecido ou vazio.")
            normalized[subject] = action_set
        self.grants = normalized

    def permitted(self, principal: Any, action: str) -> bool:
        if not isinstance(principal, VerifiedOperator):
            return False
        if action not in PERMISSIONS:
            return False
        if principal.issuer != self.issuer or principal.audience != self.audience:
            return False
        return action in self.grants.get(principal.subject, frozenset())


def verified_operator_from_backend(
    *, subject: str, issuer: str, audience: str, verified: bool,
) -> VerifiedOperator:
    """Apenas adapta prova VALIDADA no backend; não valida tokens por si só.

    O parâmetro verified nunca pode ser extraído de dados do navegador.
    O chamador deve obtê-lo exclusivamente como resultado de validação
    assinada do provedor, incluindo validade temporal e revogação aplicável.
    """
    if verified is not True or not isinstance(subject, str) or not subject.strip():
        raise ValueError("Identidade não verificada.")
    if not isinstance(issuer, str) or not issuer.strip():
        raise ValueError("Emissor não verificado.")
    if not isinstance(audience, str) or not audience.strip():
        raise ValueError("Público não verificado.")
    return VerifiedOperator(subject=subject, issuer=issuer, audience=audience)
