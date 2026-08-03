from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().casefold() in {"1", "true", "sim", "yes", "ok", "pago", "aprovado", "entregue"}


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    # Datas reais encontradas no FestManager e formatos ISO do Supabase.
    candidates = [text, text[:19], text[:10]]
    formats = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    )
    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt).date()
            except (TypeError, ValueError):
                pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def _is_today(record: dict[str, Any], fields: Iterable[str], today: date) -> bool:
    return any(_parse_date(record.get(field)) == today for field in fields)


def calcular_indicadores_unificados(
    historico: list[dict[str, Any]] | None,
    atendimentos: list[dict[str, Any]] | None,
    tarefas: list[dict[str, Any]] | None = None,
    hoje: date | None = None,
) -> dict[str, Any]:
    """Fonte única dos indicadores usados na Central, CRM e futuramente pelo THU.

    A função não altera registros e aceita tanto os JSON locais quanto os documentos
    trazidos do Supabase.
    """
    hoje = hoje or date.today()
    propostas = list(historico or [])
    contatos = list(atendimentos or [])
    tarefas_lista = list(tarefas or [])

    status_finais_atendimento = {"entregue", "pós-venda", "pos-venda", "arquivado", "descartado", "recusado"}
    atendimentos_abertos = [
        a for a in contatos
        if str(a.get("status") or "").strip().casefold() not in status_finais_atendimento
    ]

    propostas_hoje = [
        p for p in propostas
        if _is_today(p, ("data_geracao", "data", "criado_em", "created_at"), hoje)
    ]
    aprovadas_total = [p for p in propostas if _bool(p.get("aprovado"))]
    aprovadas_hoje = [
        p for p in aprovadas_total
        if _is_today(p, ("aprovado_em", "atualizado_em", "updated_at", "data_geracao", "data"), hoje)
    ]
    entregues_total = [p for p in propostas if _bool(p.get("entregue"))]
    entregues_hoje = [
        p for p in entregues_total
        if _is_today(p, ("entregue_em", "atualizado_em", "updated_at"), hoje)
    ]
    pagas_total = [p for p in propostas if _bool(p.get("pago"))]

    propostas_abertas = [
        p for p in propostas
        if not _bool(p.get("entregue"))
        and str(p.get("status") or "").strip().casefold() not in {"excluída", "excluida", "cancelada", "recusada", "arquivada"}
    ]
    aguardando_aprovacao = [p for p in propostas_abertas if not _bool(p.get("aprovado"))]
    aprovadas_em_andamento = [p for p in propostas_abertas if _bool(p.get("aprovado"))]
    pagamentos_pendentes = [p for p in propostas_abertas if not _bool(p.get("pago"))]

    tarefas_ativas = [t for t in tarefas_lista if t.get("ativa", True)]

    # Funil unificado: atendimentos representam captação; propostas representam o
    # avanço comercial. Dessa forma, CRM e Central deixam de contar bases isoladas.
    novos_leads = sum(
        1 for a in atendimentos_abertos
        if str(a.get("status") or "").strip().casefold() in {"", "novo contato", "novo lead", "recebido"}
    )
    em_atendimento = sum(
        1 for a in atendimentos_abertos
        if str(a.get("status") or "").strip().casefold() in {"em atendimento", "respondido", "qualificação", "qualificacao"}
    )
    aguardando_resposta = sum(
        1 for a in atendimentos_abertos
        if str(a.get("status") or "").strip().casefold() in {"aguardando cliente", "aguardando resposta"}
    )

    return {
        "data_referencia": hoje,
        "propostas_total": len(propostas),
        "propostas_hoje": len(propostas_hoje),
        "propostas_abertas": len(propostas_abertas),
        "aguardando_aprovacao": len(aguardando_aprovacao),
        "aprovadas_total": len(aprovadas_total),
        "aprovadas_hoje": len(aprovadas_hoje),
        "aprovadas_em_andamento": len(aprovadas_em_andamento),
        "pagas_total": len(pagas_total),
        "pagamentos_pendentes": len(pagamentos_pendentes),
        "entregues_total": len(entregues_total),
        "entregues_hoje": len(entregues_hoje),
        "atendimentos_total": len(contatos),
        "atendimentos_abertos": len(atendimentos_abertos),
        "tarefas_ativas": len(tarefas_ativas),
        "funil": {
            "Novos leads": novos_leads,
            "Em atendimento": em_atendimento,
            "Orçamento": len(aguardando_aprovacao),
            "Aguardando resposta": aguardando_resposta,
            "Fechados": len(aprovadas_total),
            "Perdidos / arquivados": max(0, len(propostas) - len(propostas_abertas) - len(entregues_total)),
        },
    }
