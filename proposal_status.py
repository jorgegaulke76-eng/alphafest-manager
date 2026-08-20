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


def valor_campo(record: dict[str, Any] | None, campo: str, default: Any = None) -> Any:
    """Lê um campo oficial aceitando apenas aliases legados conhecidos.

    A fonte continua sendo a própria proposta; esta função evita que telas novas
    criem regras próprias para ``Aprovado/aprovado``, ``Pago/pago`` e
    ``Entregue/entregue``. O primeiro valor realmente presente vence.
    """
    record = record or {}
    aliases = {
        "aprovado": ("aprovado", "Aprovado"),
        "pago": ("pago", "Pago"),
        "entregue": ("entregue", "Entregue"),
        "encerrado": ("encerrado", "Encerrado"),
        "faturamento_mensal": ("faturamento_mensal", "FaturamentoMensal"),
        "modalidade_cobranca": ("modalidade_cobranca", "ModalidadeCobranca"),
    }.get(campo, (campo,))
    for alias in aliases:
        if alias in record and record.get(alias) is not None:
            return record.get(alias)
    return default


def status_bool(record: dict[str, Any] | None, campo: str) -> bool:
    return valor_bool(valor_campo(record, campo, False))


def proposta_faturamento_mensal(record: dict[str, Any] | None) -> bool:
    record = record or {}
    if status_bool(record, "faturamento_mensal"):
        return True
    modalidade = str(valor_campo(record, "modalidade_cobranca", "") or "").strip().casefold()
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
    return motivo_nao_fechado or status_bool(record, "encerrado") or status in {
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
    aprovado = status_bool(record, "aprovado")
    entregue = status_bool(record, "entregue")
    if proposta_faturamento_mensal(record):
        return aprovado and entregue
    return aprovado and status_bool(record, "pago") and entregue


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
        and status_bool(record, "aprovado")
        and not proposta_faturamento_mensal(record)
        and not status_bool(record, "pago")
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
        "aprovado": status_bool(record, "aprovado"),
        "pago": status_bool(record, "pago"),
        "entregue": status_bool(record, "entregue"),
    }
