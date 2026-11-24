"""HF65.24.53 — contrato dos snapshots oficiais, SANITIZADO e fail-closed.

Origem documentada no app.py legado:
  historico_orcamentos  -> lista de propostas
  atendimentos_db       -> dict com chave 'itens' (lista de atendimentos)

Este módulo NÃO carrega arquivos, não conecta ao Supabase e não afirma que um
snapshot foi realmente obtido. O chamador autenticado deve fornecer dados
exclusivamente do backend de homologação, sem fallback local. Só os campos
necessários aos cálculos são mantidos; os campos pessoais são descartados.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from commercial_private_document_adapter import PrivateStoreDenied

MAX_ROWS = 10000
CONTACT_KEYS = frozenset({"id", "etapa_captacao"})
PROPOSAL_KEYS = frozenset({
    "numero_proposta", "atendimento_id", "pago", "valor_total", "total",
    "total_geral", "modalidade_cobranca", "cancelado_cliente", "cancelado",
    "status", "status_proposta", "pagamento_parcial", "pago_parcial",
    "parcialmente_pago", "estornado", "pagamento_estornado", "reembolsado",
    "reembolso_pendente", "chargeback", "contestacao_pagamento",
    "status_pagamento", "situacao_pagamento", "status_financeiro",
    "valor_pago", "valor_recebido", "total_recebido", "valor_estornado",
    "valor_reembolsado", "saldo_pendente", "saldo_devedor",
})


def _rows(value: Any, *, kind: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        raise PrivateStoreDenied(f"Snapshot oficial de {kind} inválido.")
    result = []
    keys = CONTACT_KEYS if kind == "atendimentos" else PROPOSAL_KEYS
    for row in value:
        if not isinstance(row, Mapping):
            raise PrivateStoreDenied(f"Registro oficial de {kind} inválido.")
        obj = {k: row[k] for k in keys if k in row}
        identifier = "id" if kind == "atendimentos" else "numero_proposta"
        val = obj.get(identifier)
        if (not isinstance(val, str) or not val.strip()
            or len(val) > 256 or val != val.strip()):
            raise PrivateStoreDenied(f"Identificador de {kind} ausente ou ambíguo.")
        if kind == "propostas":
            aid = obj.get("atendimento_id")
            if not isinstance(aid, str) or len(aid) > 256:
                raise PrivateStoreDenied("Vínculo da proposta inválido.")
        result.append(obj)
    return result


def sanitize_official_manager_snapshots(
    *, historico_orcamentos: Any, atendimentos_db: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retorna (propostas, contatos), somente com campos essenciais."""
    if (not isinstance(atendimentos_db, Mapping)
        or not isinstance(atendimentos_db.get("itens"), list)):
        raise PrivateStoreDenied("Atendimentos oficiais indisponíveis.")
    propostas = _rows(historico_orcamentos, kind="propostas")
    contatos = _rows(atendimentos_db["itens"], kind="atendimentos")
    return propostas, contatos


def make_sanitized_official_snapshot_loader(*, read_proposals: Any, read_contacts: Any):
    """Injetar EXCLUSIVAMENTE funções servidoras já autenticadas/autorizadas.

    Não há fallback: uma falha em qualquer leitura interrompe o relatório.
    """
    if not callable(read_proposals) or not callable(read_contacts):
        raise PrivateStoreDenied("Leitores oficiais do backend não configurados.")

    def load():
        try:
            proposals = read_proposals()
            contacts = read_contacts()
            return sanitize_official_manager_snapshots(
                historico_orcamentos=proposals,
                atendimentos_db=contacts,
            )
        except PrivateStoreDenied:
            raise
        except Exception:
            raise PrivateStoreDenied("Snapshots oficiais indisponíveis.") from None

    return load
