"""Motor puro da I8.13 — Central de Entregas & Retiradas.

A proposta oficial continua sendo a única fonte de Pronto/Entregue. Este motor
somente organiza a fila de saída e calcula indicadores; não persiste dados.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable


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


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for fmt, sample in (("%d/%m/%Y %H:%M", 16), ("%d/%m/%Y", 10), ("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:sample], fmt).date()
        except ValueError:
            pass
    return None


def dias_aguardando(record: dict, hoje: date) -> int | None:
    pronto_em = _date(record.get("pronto_em"))
    if pronto_em is None:
        return None
    return max(0, (hoje - pronto_em).days)


def montar_fila(propostas: Iterable[dict], hoje: date, resumo_produtos=None) -> list[dict]:
    linhas = []
    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        status = _status(proposta)
        if not status["pronto"] or status["entregue"]:
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
        "aguardando_3_dias": sum(1 for x in itens if (x.get("dias_aguardando") or 0) >= 3),
        "nao_pagos": sum(1 for x in itens if not x.get("pago")),
    }
