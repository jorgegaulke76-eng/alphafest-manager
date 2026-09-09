"""20.4.9-I8.13.5 — diagnósticos puros de status oficiais.

Não grava dados e não depende do Streamlit. Mantém o diagnóstico executivo
alinhado à mesma Fonte Única usada pelas telas operacionais.
"""
from __future__ import annotations

from typing import Any, Iterable

from proposal_status import (
    proposta_concluida,
    proposta_faturamento_mensal,
    resumo_status,
)


def diagnosticar_sincronizacao_status(historico: Iterable[dict[str, Any]] | None) -> dict[str, Any]:
    divergencias: list[dict[str, str]] = []
    contradicoes: list[dict[str, str]] = []
    avaliadas = 0

    for prop in (historico or []):
        if not isinstance(prop, dict):
            continue
        avaliadas += 1
        numero = str(prop.get("numero_proposta") or "SEM-NÚMERO")
        cliente = str(prop.get("cliente_nome") or prop.get("cliente") or "Cliente")
        estado = resumo_status(prop)
        aprovado = bool(estado.get("aprovado"))
        pago = bool(estado.get("pago"))
        pronto = bool(estado.get("pronto"))
        entregue = bool(estado.get("entregue"))
        legado_concluido = aprovado and pago and entregue
        oficial_concluido = proposta_concluida(prop)

        if legado_concluido != oficial_concluido:
            divergencias.append({
                "Proposta": numero,
                "Cliente": cliente,
                "Cobrança": "Mensal" if proposta_faturamento_mensal(prop) else "Por proposta",
                "Aprovado": "Sim" if aprovado else "Não",
                "Pago": "Sim" if pago else "Não",
                "Pronto": "Sim" if pronto else "Não",
                "Entregue": "Sim" if entregue else "Não",
                "Regra oficial": "Concluída" if oficial_concluido else "Ativa",
            })
        if entregue and not pronto:
            contradicoes.append({
                "Proposta": numero,
                "Cliente": cliente,
                "Problema": "Entregue sem Pronto (registro legado; leitura oficial corrige em memória)",
            })
        if entregue and not aprovado:
            contradicoes.append({"Proposta": numero, "Cliente": cliente, "Problema": "Entregue sem aprovação"})
        if pago and not aprovado:
            contradicoes.append({"Proposta": numero, "Cliente": cliente, "Problema": "Pago sem aprovação"})

    return {
        "avaliadas": avaliadas,
        "divergencias_legadas": divergencias,
        "contradicoes": contradicoes,
    }
