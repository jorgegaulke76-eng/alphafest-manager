"""Motor puro da I8.12.4 — consumo de estoque por pedido.

Sem dependência de Streamlit ou banco. O app.py cuida de persistência/UI; este módulo
concentra os cálculos que precisam ser únicos entre Estoque, Pedidos e Central.
"""
from __future__ import annotations

from typing import Any, Iterable


def _num(valor: Any) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def movimento_estornado(movimentos: Iterable[dict], movimento_id: str) -> bool:
    alvo = str(movimento_id or "")
    return any(str((m or {}).get("estorno_de") or "") == alvo for m in (movimentos or []))


def total_baixado(consumo_id: str, material_id: str, movimentos: Iterable[dict]) -> float:
    """Soma baixas ativas do pedido/material. Estornos deixam de contar."""
    total = 0.0
    consumo_id = str(consumo_id or "")
    material_id = str(material_id or "")
    movimentos = list(movimentos or [])
    for mov in movimentos:
        if str((mov or {}).get("origem_tipo") or "") != "Pedido":
            continue
        if str((mov or {}).get("origem_id") or "") != consumo_id:
            continue
        if str((mov or {}).get("material_id") or "") != material_id:
            continue
        if _num((mov or {}).get("delta")) >= 0:
            continue
        if movimento_estornado(movimentos, (mov or {}).get("id")):
            continue
        total += abs(_num((mov or {}).get("delta")))
    return round(total, 6)


def resumo_consumo(consumo: dict, movimentos: Iterable[dict]) -> dict:
    """Deriva o estado do consumo a partir da necessidade confirmada + movimentos."""
    if not isinstance(consumo, dict):
        return {"status": "Sem consumo", "chave": "sem_consumo", "necessidades": [], "pendente": False}
    if consumo.get("estornado"):
        return {"status": "⚪ Estornado", "chave": "estornado", "necessidades": [], "pendente": False}

    linhas = []
    total_necessidades = 0.0
    total_baixas = 0.0
    tem_pendente = False
    tem_baixa = False
    for nec in consumo.get("necessidades") or []:
        material_id = str((nec or {}).get("material_id") or "")
        necessario = max(0.0, _num((nec or {}).get("necessario")))
        baixado = min(necessario, total_baixado(consumo.get("id"), material_id, movimentos))
        pendente = max(0.0, necessario - baixado)
        total_necessidades += necessario
        total_baixas += baixado
        tem_baixa = tem_baixa or baixado > 1e-7
        tem_pendente = tem_pendente or pendente > 1e-7
        linhas.append({**dict(nec or {}), "necessario": necessario, "baixado": baixado, "pendente": pendente})

    if not linhas:
        status, chave = "⚪ Sem materiais", "sem_materiais"
    elif not tem_pendente:
        status, chave = "🟢 Materiais atendidos", "atendido"
    elif tem_baixa:
        status, chave = "🟡 Parcialmente atendido", "parcial"
    else:
        status, chave = "🟠 Material pendente", "pendente"

    return {
        "status": status,
        "chave": chave,
        "necessidades": linhas,
        "pendente": tem_pendente,
        "total_necessidades": round(total_necessidades, 6),
        "total_baixas": round(total_baixas, 6),
    }


def pendencia_material(consumos: Iterable[dict], movimentos: Iterable[dict], material_id: str) -> float:
    total = 0.0
    material_id = str(material_id or "")
    for consumo in consumos or []:
        if (consumo or {}).get("estornado"):
            continue
        resumo = resumo_consumo(consumo, movimentos)
        for nec in resumo.get("necessidades") or []:
            if str((nec or {}).get("material_id") or "") == material_id:
                total += _num((nec or {}).get("pendente"))
    return round(total, 6)


def planejar_regularizacao(consumos: Iterable[dict], movimentos: Iterable[dict], saldos: dict[str, float]) -> list[dict]:
    """Planeja FIFO das pendências usando apenas saldo físico disponível.

    Não altera as entradas recebidas. O app aplica cada alocação como movimento
    negativo e, depois, recalcula os saldos. Nunca propõe quantidade maior que o saldo.
    """
    saldos_trabalho = {str(k): max(0.0, _num(v)) for k, v in (saldos or {}).items()}
    ativos = [c for c in (consumos or []) if isinstance(c, dict) and not c.get("estornado")]
    ativos.sort(key=lambda c: (str(c.get("confirmado_em") or ""), str(c.get("id") or "")))
    plano = []
    for consumo in ativos:
        resumo = resumo_consumo(consumo, movimentos)
        for nec in resumo.get("necessidades") or []:
            material_id = str(nec.get("material_id") or "")
            pendente = max(0.0, _num(nec.get("pendente")))
            disponivel = max(0.0, saldos_trabalho.get(material_id, 0.0))
            alocar = min(disponivel, pendente)
            if alocar <= 1e-7:
                continue
            plano.append({
                "consumo_id": str(consumo.get("id") or ""),
                "numero_proposta": str(consumo.get("numero_proposta") or ""),
                "material_id": material_id,
                "material_nome": str(nec.get("material_nome") or ""),
                "unidade": str(nec.get("unidade") or ""),
                "quantidade": round(alocar, 6),
            })
            saldos_trabalho[material_id] = round(disponivel - alocar, 6)
    return plano
