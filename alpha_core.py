"""Alpha Core — núcleo único de leitura e inteligência operacional.

Este módulo não altera a Central da Anna nem grava dados. Ele consolida os
indicadores que alimentam o ambiente executivo do Jorge e o THU.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Callable

from proposal_status import (
    proposta_concluida as _status_concluida,
    proposta_encerrada as _status_encerrada,
    proposta_faturamento_mensal as _status_mensal,
    proposta_pronta as _status_pronta,
    status_bool as _status_bool,
)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().casefold() in {
        "1", "true", "sim", "yes", "ok", "pago", "aprovado", "pronto", "entregue"
    }


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for candidate in (text, text[:19], text[:10]):
        for fmt in (
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(candidate, fmt).date()
            except (TypeError, ValueError):
                pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def _encerrada(record: dict[str, Any]) -> bool:
    return _status_encerrada(record)


def _concluida(record: dict[str, Any]) -> bool:
    return _status_concluida(record)


def listar_atrasados_operacionais(
    historico: list[dict[str, Any]] | None,
    hoje: date,
) -> list[dict[str, Any]]:
    """Lista oficial de pedidos atrasados do Alpha Core.

    Esta função é a fonte única para THU, Alpha Core, Central e painel de
    indicadores. Um pedido só está atrasado quando a proposta é válida, ainda
    está operacionalmente ativa, foi aprovada, não foi entregue e sua data de
    entrega já venceu. Propostas encerradas/canceladas e mensalistas concluídos
    operacionalmente não entram na lista.
    """
    propostas = [p for p in list(historico or []) if isinstance(p, dict)]
    validas = [p for p in propostas if not _encerrada(p)]
    ativas = [p for p in validas if not _concluida(p)]
    return [
        p for p in ativas
        if _status_bool(p, "aprovado")
        and not _status_pronta(p)
        and not _status_bool(p, "entregue")
        and (_date(p.get("data_entrega")) or date.max) < hoje
    ]


def _total(record: dict[str, Any], calculator: Callable[[dict[str, Any]], tuple[Any, Any, Any]] | None) -> float:
    if calculator:
        try:
            return float(calculator(record)[2] or 0)
        except Exception:
            pass
    for field in ("valor_total", "total", "valor", "total_geral"):
        raw = record.get(field)
        if raw is None:
            continue
        try:
            text = str(raw).replace("R$", "").strip()
            if "," in text:
                text = text.replace(".", "").replace(",", ".")
            return float(text or 0)
        except (TypeError, ValueError):
            continue
    return 0.0


@dataclass(frozen=True)
class AlphaCoreSnapshot:
    data_referencia: date
    propostas_total: int
    pedidos_ativos: int
    aguardando_aprovacao: int
    aprovados_em_andamento: int
    prontos_aguardando_entrega: int
    pagamentos_pendentes: int
    previstas_hoje: int
    pendentes_entrega_hoje: int
    entregues_hoje: int
    atrasados: int
    recebido_hoje: float
    carteira_aberta: float
    valor_previsto_hoje: float
    atendimentos_abertos: int
    qualidade: str
    alertas: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calcular_alpha_core(
    historico: list[dict[str, Any]] | None,
    atendimentos: list[dict[str, Any]] | None,
    hoje: date,
    calcular_valores: Callable[[dict[str, Any]], tuple[Any, Any, Any]] | None = None,
) -> AlphaCoreSnapshot:
    propostas = [p for p in list(historico or []) if isinstance(p, dict)]
    contatos = [a for a in list(atendimentos or []) if isinstance(a, dict)]
    validas = [p for p in propostas if not _encerrada(p)]
    ativas = [p for p in validas if not _concluida(p)]
    aguardando = [p for p in ativas if not _status_bool(p, "aprovado")]
    aprovadas_abertas = [p for p in ativas if _status_bool(p, "aprovado")]
    prontos_aguardando_entrega = [p for p in aprovadas_abertas if _status_pronta(p) and not _status_bool(p, "entregue")]
    pagamentos_pendentes = [p for p in aprovadas_abertas if not _status_mensal(p) and not _status_bool(p, "pago")]

    previstas_hoje_lista = [p for p in ativas if _date(p.get("data_entrega")) == hoje]
    pendentes_hoje_lista = [p for p in aprovadas_abertas if not _status_bool(p, "entregue") and _date(p.get("data_entrega")) == hoje]
    entregues_hoje_lista = [
        p for p in validas
        if _status_bool(p, "entregue")
        and _date(p.get("entregue_em") or p.get("data_entrega_real")) == hoje
    ]
    atrasadas_lista = listar_atrasados_operacionais(propostas, hoje)
    pagos_hoje = [
        p for p in validas
        if _status_bool(p, "pago")
        and _date(p.get("pago_em") or p.get("data_pagamento")) == hoje
    ]

    atendimentos_abertos = [
        a for a in contatos
        if str(a.get("status") or "").strip().casefold() not in {"entregue", "pós-venda", "pos-venda", "arquivado"}
    ]

    alertas: list[str] = []
    if atrasadas_lista:
        alertas.append(f"{len(atrasadas_lista)} pedido(s) atrasado(s)")
    if aguardando:
        alertas.append(f"{len(aguardando)} orçamento(s) aguardando aprovação")
    if pagamentos_pendentes:
        alertas.append(f"{len(pagamentos_pendentes)} pagamento(s) pendente(s)")
    if pendentes_hoje_lista:
        alertas.append(f"{len(pendentes_hoje_lista)} entrega(s) pendente(s) para hoje")
    if not alertas:
        alertas.append("Operação sem alertas críticos")

    qualidade = "Crítico" if atrasadas_lista else ("Atenção" if aguardando or pagamentos_pendentes else "Saudável")

    return AlphaCoreSnapshot(
        data_referencia=hoje,
        propostas_total=len(propostas),
        pedidos_ativos=len(ativas),
        aguardando_aprovacao=len(aguardando),
        aprovados_em_andamento=len(aprovadas_abertas),
        prontos_aguardando_entrega=len(prontos_aguardando_entrega),
        pagamentos_pendentes=len(pagamentos_pendentes),
        previstas_hoje=len(previstas_hoje_lista),
        pendentes_entrega_hoje=len(pendentes_hoje_lista),
        entregues_hoje=len(entregues_hoje_lista),
        atrasados=len(atrasadas_lista),
        recebido_hoje=sum(_total(p, calcular_valores) for p in pagos_hoje),
        carteira_aberta=sum(_total(p, calcular_valores) for p in aprovadas_abertas),
        valor_previsto_hoje=sum(_total(p, calcular_valores) for p in pendentes_hoje_lista),
        atendimentos_abertos=len(atendimentos_abertos),
        qualidade=qualidade,
        alertas=tuple(alertas),
    )
