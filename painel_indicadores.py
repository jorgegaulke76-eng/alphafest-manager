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


def _status_text(record: dict[str, Any]) -> str:
    return str(record.get("status_comercial") or record.get("situacao_comercial") or record.get("status") or "").strip().casefold()


def _encerrada(record: dict[str, Any]) -> bool:
    status = _status_text(record)
    return _bool(record.get("encerrado")) or status in {
        "encerrado", "encerrada", "encerrado sem retorno", "encerrado por preço",
        "encerrado por preco", "encerrado pelo cliente", "encerrado por prazo",
        "cancelado", "cancelada", "recusado", "recusada", "arquivado", "arquivada",
        "excluído", "excluida", "excluído", "excluída",
    }


def _numero(record: dict[str, Any]) -> str:
    return str(record.get("numero_proposta") or record.get("proposta") or record.get("id") or "").strip()


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
    propostas_validas = [p for p in propostas if not _encerrada(p)]
    aprovadas_total = [p for p in propostas_validas if _bool(p.get("aprovado"))]
    aprovadas_hoje = [
        p for p in aprovadas_total
        if _is_today(p, ("aprovado_em", "atualizado_em", "updated_at", "data_geracao", "data"), hoje)
    ]
    entregues_total = [p for p in propostas_validas if _bool(p.get("entregue"))]
    entregues_hoje = [
        p for p in entregues_total
        if _is_today(p, ("entregue_em", "atualizado_em", "updated_at"), hoje)
    ]
    pagas_total = [p for p in propostas_validas if _bool(p.get("pago"))]

    propostas_abertas = [p for p in propostas_validas if not _bool(p.get("entregue"))]
    aguardando_aprovacao = [p for p in propostas_abertas if not _bool(p.get("aprovado"))]
    aprovadas_em_andamento = [p for p in propostas_abertas if _bool(p.get("aprovado"))]
    pagamentos_pendentes = [p for p in aprovadas_em_andamento if not _bool(p.get("pago"))]

    entregas_hoje_abertas = [
        p for p in aprovadas_em_andamento
        if _parse_date(p.get("data_entrega")) == hoje
    ]
    atrasadas = [
        p for p in aprovadas_em_andamento
        if (_parse_date(p.get("data_entrega")) or date.max) < hoje
    ]

    tarefas_ativas = [t for t in tarefas_lista if _bool(t.get("ativa", True))]
    aprovadas_abertas_ids = {_numero(p) for p in aprovadas_em_andamento if _numero(p)}
    status_por_proposta: dict[str, set[str]] = {}
    for tarefa in tarefas_ativas:
        numero = _numero(tarefa)
        if numero not in aprovadas_abertas_ids:
            continue
        status = str(tarefa.get("status") or "Pedido recebido").strip()
        status_por_proposta.setdefault(numero, set()).add(status)

    prontos_ids = {n for n, statuses in status_por_proposta.items() if statuses and statuses <= {"Pronto", "Entregue"} and "Pronto" in statuses}
    em_producao_ids = {
        n for n, statuses in status_por_proposta.items()
        if n not in prontos_ids and any(s in {"Pedido recebido", "Arte pendente", "Aguardando aprovação", "Pronto para produzir", "Em produção"} for s in statuses)
    }
    # Propostas aprovadas ainda sem tarefa sincronizada também precisam aparecer como operação pendente.
    em_producao_ids.update(aprovadas_abertas_ids - set(status_por_proposta))

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
        "atrasados_operacionais": len(atrasadas),
        "entregas_hoje_abertas": len(entregas_hoje_abertas),
        "em_producao_operacional": len(em_producao_ids),
        "prontos_operacionais": len(prontos_ids),
        "numeros_em_producao": sorted(em_producao_ids),
        "numeros_prontos": sorted(prontos_ids),
        "funil": {
            "Novos leads": novos_leads,
            "Em atendimento": em_atendimento,
            "Orçamento": len(aguardando_aprovacao),
            "Aguardando resposta": aguardando_resposta,
            "Fechados": len(aprovadas_total),
            "Perdidos / arquivados": max(0, len(propostas) - len(propostas_abertas) - len(entregues_total)),
        },
    }
