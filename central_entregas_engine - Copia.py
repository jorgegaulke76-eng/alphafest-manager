"""Motor puro da I8.13 — Central de Entregas & Retiradas.

A proposta oficial continua sendo a única fonte de Pronto/Entregue. Este motor
somente organiza a fila de saída e calcula indicadores; não persiste dados.

HF2 reforça a proveniência da data de Pronto:
- a espera só é calculada quando ``pronto_em`` foi capturado por uma transição nova e
  traz o marcador ``pronto_em_confiavel``;
- carimbos legados ou criados por versões anteriores sem esse marcador não são
  tratados como 'Pronto hoje';
- histórico de entregas continua usando apenas data real de entrega, nunca a prevista.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from proposal_status import resumo_status


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().casefold() in {"1", "true", "sim", "yes", "ok", "pago", "aprovado", "pronto", "entregue"}


def _status(record: dict) -> dict:
    entregue = _bool(record.get("entregue") if "entregue" in record else record.get("Entregue"))
    pronto = _bool(record.get("pronto") if "pronto" in record else record.get("Pronto")) or entregue
    aprovado = _bool(record.get("aprovado") if "aprovado" in record else record.get("Aprovado"))
    pago = _bool(record.get("pago") if "pago" in record else record.get("Pago"))
    return {"aprovado": aprovado, "pago": pago, "pronto": pronto, "entregue": entregue}


def _datetime(value: Any) -> datetime | None:
    """Converte formatos antigos/atuais sem inventar data quando o campo está vazio."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    text = str(value or "").strip()
    if not text:
        return None

    # Primeiro tenta ISO, inclusive registros com timezone/Z.
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed
    except ValueError:
        pass

    for fmt in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _date(value: Any) -> date | None:
    parsed = _datetime(value)
    return parsed.date() if parsed is not None else None


def pronto_em_confiavel(record: dict) -> datetime | None:
    """Retorna o carimbo de Pronto somente quando sua origem é comprovada.

    A HF2 introduz ``pronto_em_confiavel``. Isso é propositalmente conservador:
    registros legados podem até conter ``pronto_em`` preenchido por versões
    anteriores, mas sem o marcador não há como provar que aquele horário é o
    momento real em que a produção terminou. Nesse caso, devolvemos ``None``.
    """
    if not _bool(record.get("pronto_em_confiavel")):
        return None
    return _datetime(record.get("pronto_em"))


def dias_aguardando(record: dict, hoje: date) -> int | None:
    """Dias desde uma conclusão de produção com data comprovadamente capturada."""
    pronto_dt = pronto_em_confiavel(record)
    if pronto_dt is None:
        return None
    return max(0, (hoje - pronto_dt.date()).days)


def data_real_entrega(record: dict) -> datetime | None:
    """Data efetiva da entrega, sem recorrer a ``data_entrega`` (prevista)."""
    return _datetime(record.get("entregue_em")) or _datetime(record.get("data_entrega_real"))


def ordenar_historico_entregues(propostas: Iterable[dict]) -> list[dict]:
    """Mais recentes primeiro; registros legados sem data real ficam no final."""
    itens = [p for p in (propostas or []) if isinstance(p, dict)]

    def chave(proposta: dict):
        real = data_real_entrega(proposta)
        return (
            1 if real is not None else 0,
            real or datetime.min,
            str(proposta.get("numero_proposta") or ""),
        )

    return sorted(itens, key=chave, reverse=True)


def montar_fila(propostas: Iterable[dict], hoje: date, resumo_produtos=None) -> list[dict]:
    linhas = []
    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        # HF6: Entregas usa a mesma Fonte Única do Histórico/Central.
        # Propostas encerradas/não fechadas não podem reaparecer na fila de saída
        # apenas por possuírem um marcador legado de Pronto.
        status = resumo_status(proposta)
        if not status.get("ativa") or not status.get("pronto") or status.get("entregue"):
            continue
        entrega = _date(proposta.get("data_entrega"))
        dias = dias_aguardando(proposta, hoje)
        tipo = str(proposta.get("logistica_tipo") or "").strip()
        avisado_em = str(proposta.get("cliente_avisado_em") or "").strip()
        numero = str(proposta.get("numero_proposta") or "").strip()
        cliente = str(proposta.get("cliente_nome") or proposta.get("cliente") or "Cliente").strip()
        resumo = resumo_produtos(proposta) if callable(resumo_produtos) else ""
        linhas.append({
            "numero_proposta": numero,
            "cliente_nome": cliente,
            "whatsapp": str(proposta.get("whatsapp") or proposta.get("cliente_wa") or "").strip(),
            "data_entrega": entrega,
            "resumo_produtos": resumo,
            "pago": status["pago"],
            "tipo_entrega": tipo,
            "observacao": str(proposta.get("logistica_observacao") or "").strip(),
            "cliente_avisado": bool(avisado_em),
            "cliente_avisado_em": avisado_em,
            "cliente_avisado_por": str(proposta.get("cliente_avisado_por") or "").strip(),
            "pronto_em": str(proposta.get("pronto_em") or "").strip(),
            "pronto_por": str(proposta.get("pronto_por") or "").strip(),
            "pronto_em_confiavel": _bool(proposta.get("pronto_em_confiavel")),
            "dias_aguardando": dias,
            "entrega_hoje": entrega == hoje,
            "proposta": proposta,
        })
    linhas.sort(key=lambda x: (
        0 if x["entrega_hoje"] else 1,
        0 if not x["cliente_avisado"] else 1,
        -(x["dias_aguardando"] if x["dias_aguardando"] is not None else -1),
        x["data_entrega"] or date.max,
        x["cliente_nome"].casefold(),
    ))
    return linhas


def resumo_fila(linhas: Iterable[dict]) -> dict:
    itens = list(linhas or [])
    return {
        "prontos": len(itens),
        "hoje": sum(1 for x in itens if x.get("entrega_hoje")),
        "nao_avisados": sum(1 for x in itens if not x.get("cliente_avisado")),
        "aguardando_3_dias": sum(
            1 for x in itens
            if isinstance(x.get("dias_aguardando"), int) and x.get("dias_aguardando") >= 3
        ),
        "nao_pagos": sum(1 for x in itens if not x.get("pago")),
    }
