"""20.4.9-I8.11.1-HF3 — fonte única de status de propostas.

Este módulo não grava dados e não depende do Streamlit. Ele concentra as regras
usadas por Anna, Jorge, THU, Alpha Core e painéis executivos para que a mesma
proposta nunca seja considerada concluída em uma tela e pendente em outra.
"""
from __future__ import annotations

from typing import Any


def valor_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().casefold() in {
        "1", "true", "sim", "yes", "ok", "pago", "aprovado", "entregue"
    }


def proposta_faturamento_mensal(record: dict[str, Any] | None) -> bool:
    record = record or {}
    if valor_bool(record.get("faturamento_mensal")):
        return True
    modalidade = str(record.get("modalidade_cobranca") or "").strip().casefold()
    return modalidade in {"faturamento mensal", "mensal", "mensalista"}


def proposta_encerrada(record: dict[str, Any] | None) -> bool:
    record = record or {}
    status = str(
        record.get("status_comercial")
        or record.get("situacao_comercial")
        or record.get("status")
        or ""
    ).strip().casefold()
    motivo_nao_fechado = valor_bool(record.get("nao_fechado_pagamento")) or valor_bool(record.get("nao_fechado_sem_retorno"))
    return motivo_nao_fechado or valor_bool(record.get("encerrado")) or status in {
        "encerrado", "encerrada", "encerrado sem retorno", "encerrado por preço", "encerrado por preco",
        "encerrado pelo cliente", "encerrado por prazo", "cancelado", "cancelada", "recusado", "recusada",
        "nao_fechado_pagamento", "não fechado — falta de pagamento", "nao_fechado_sem_retorno",
        "não fechado — sem retorno do cliente", "arquivado", "arquivada", "excluído", "excluida", "excluída",
    }


def proposta_concluida(record: dict[str, Any] | None) -> bool:
    """Regra oficial de conclusão operacional.

    - cobrança por proposta: Aprovado + Pago + Entregue;
    - faturamento mensal: Aprovado + Entregue. O pagamento pertence à Central
      de Faturamento Mensal e não mantém o pedido operacionalmente pendente.
    """
    record = record or {}
    aprovado = valor_bool(record.get("aprovado"))
    entregue = valor_bool(record.get("entregue"))
    if proposta_faturamento_mensal(record):
        return aprovado and entregue
    return aprovado and valor_bool(record.get("pago")) and entregue


def proposta_ativa_operacional(record: dict[str, Any] | None) -> bool:
    return not proposta_encerrada(record) and not proposta_concluida(record)


def pagamento_individual_pendente(record: dict[str, Any] | None) -> bool:
    """Indica pendência de pagamento que deve aparecer nos painéis operacionais.

    Mensalistas nunca entram como pagamento individual pendente: o financeiro é
    acompanhado no fechamento mensal.
    """
    record = record or {}
    return (
        not proposta_encerrada(record)
        and valor_bool(record.get("aprovado"))
        and not proposta_faturamento_mensal(record)
        and not valor_bool(record.get("pago"))
    )


def resumo_status(record: dict[str, Any] | None) -> dict[str, Any]:
    record = record or {}
    mensal = proposta_faturamento_mensal(record)
    concluida = proposta_concluida(record)
    encerrada = proposta_encerrada(record)
    return {
        "mensalista": mensal,
        "encerrada": encerrada,
        "concluida": concluida,
        "ativa": not encerrada and not concluida,
        "pagamento_individual_pendente": pagamento_individual_pendente(record),
        "aprovado": valor_bool(record.get("aprovado")),
        "pago": valor_bool(record.get("pago")),
        "entregue": valor_bool(record.get("entregue")),
    }
