"""Motor puro da I8.12.6 — Planejamento de compras por necessidade.

O planejamento é um estado operacional distinto da necessidade real e da compra
realizada. Ele referencia materiais oficiais e registra apenas o que foi
solicitado ao fornecedor / recebido. Não movimenta estoque e não substitui a
Central de Necessidades da I8.12.5.
"""
from __future__ import annotations

from typing import Any, Iterable


def _num(valor: Any) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def quantidade_aberta(plano: dict) -> float:
    if not isinstance(plano, dict) or plano.get("cancelado"):
        return 0.0
    solicitado = max(0.0, _num(plano.get("quantidade_solicitada")))
    recebido = max(0.0, _num(plano.get("quantidade_recebida")))
    return round(max(0.0, solicitado - recebido), 6)


def status_plano(plano: dict) -> str:
    if not isinstance(plano, dict):
        return "Inválido"
    solicitado = max(0.0, _num(plano.get("quantidade_solicitada")))
    recebido = max(0.0, _num(plano.get("quantidade_recebida")))
    if plano.get("cancelado"):
        return "Parcialmente recebido · restante cancelado" if recebido > 1e-7 else "Cancelado"
    if solicitado <= 1e-7:
        return "Sem quantidade"
    if recebido <= 1e-7:
        return "Solicitado"
    if recebido + 1e-7 < solicitado:
        return "Parcialmente recebido"
    if recebido <= solicitado + 1e-7:
        return "Recebido"
    return "Recebido com excedente"


def agregar_aberto_por_material(planos: Iterable[dict]) -> dict[str, dict]:
    """Soma somente quantidades ainda abertas, preservando os planos envolvidos."""
    mapa: dict[str, dict] = {}
    for plano in (planos or []):
        if not isinstance(plano, dict):
            continue
        aberto = quantidade_aberta(plano)
        if aberto <= 1e-7:
            continue
        material_id = str(plano.get("material_id") or "").strip()
        if not material_id:
            continue
        linha = mapa.setdefault(material_id, {
            "material_id": material_id,
            "quantidade_em_compra": 0.0,
            "planos": [],
        })
        linha["quantidade_em_compra"] = round(_num(linha.get("quantidade_em_compra")) + aberto, 6)
        linha["planos"].append(plano)
    return mapa


def aplicar_planejamento_necessidades(necessidades: Iterable[dict], planos: Iterable[dict]) -> list[dict]:
    """Enriquece faltas reais com o que já foi solicitado, sem alterar a fonte da falta."""
    abertos = agregar_aberto_por_material(planos)
    resultado: list[dict] = []
    for necessidade in (necessidades or []):
        if not isinstance(necessidade, dict):
            continue
        linha = dict(necessidade)
        material_id = str(linha.get("material_id") or "").strip()
        falta = max(0.0, _num(linha.get("quantidade_pendente")))
        planejamento = abertos.get(material_id, {})
        em_compra = max(0.0, _num(planejamento.get("quantidade_em_compra")))
        linha.update({
            "quantidade_em_compra": round(em_compra, 6),
            "quantidade_a_solicitar": round(max(0.0, falta - em_compra), 6),
            "excesso_planejado": round(max(0.0, em_compra - falta), 6),
            "planos_abertos": list(planejamento.get("planos") or []),
        })
        resultado.append(linha)
    return resultado
