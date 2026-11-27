"""Runtime leve para Relacionamentos / histórico de propostas.

HF52: evita recalcular total, status, modalidade e ordenação da mesma proposta
várias vezes dentro do mesmo rerun da tela Relacionamentos. Somente leitura.
"""
from __future__ import annotations

from typing import Any, Callable


def build_relationship_proposal_facts(
    historico: list[dict[str, Any]] | None,
    *,
    value_calculator: Callable[[dict[str, Any]], tuple[Any, Any, Any]],
    status_resolver: Callable[[dict[str, Any]], dict[str, Any]],
    date_resolver: Callable[[Any], Any],
    monthly_resolver: Callable[[dict[str, Any]], bool],
) -> dict[int, dict[str, Any]]:
    """Pré-calcula fatos usados repetidamente pelos cartões de Relacionamentos.

    A chave é ``id(proposta)`` porque o índice é estritamente de runtime e vale
    apenas para os mesmos objetos carregados no rerun atual.
    """
    facts: dict[int, dict[str, Any]] = {}
    for prop in historico or []:
        if not isinstance(prop, dict):
            continue
        try:
            total = value_calculator(prop)[2]
        except Exception:
            total = 0.0
        try:
            status = status_resolver(prop) or {}
        except Exception:
            status = {}
        try:
            date_sort = date_resolver(prop.get("data_geracao"))
        except Exception:
            date_sort = None
        try:
            monthly = bool(monthly_resolver(prop))
        except Exception:
            monthly = False
        facts[id(prop)] = {
            "total": total,
            "status": status,
            "date_sort": date_sort,
            "monthly": monthly,
            # Mantém a regra histórica de recebido usada no cartão: campo bruto.
            "paid_raw": bool(prop.get("pago", False)),
        }
    return facts


def facts_for_proposal(
    proposal: dict[str, Any],
    facts: dict[int, dict[str, Any]] | None,
) -> dict[str, Any]:
    return (facts or {}).get(id(proposal), {})
