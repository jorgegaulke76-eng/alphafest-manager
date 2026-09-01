"""20.4.9-I8.13.4-HF7 — auditoria e saneamento seguro de sincronização operacional.

Motor puro/somente leitura. Compara a Fonte Única de Status do Histórico com
projeções operacionais (Fluxo/Produção, risco de prazo e fila de saída) para
identificar divergências sem inventar novos status.
"""
from __future__ import annotations

from typing import Any, Iterable

from proposal_status import resumo_status, status_bool


def _numero(reg: dict[str, Any] | None) -> str:
    return str((reg or {}).get("numero_proposta") or "").strip()


def _indexar(itens: Iterable[dict] | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in itens or []:
        if not isinstance(item, dict):
            continue
        numero = _numero(item)
        if numero:
            out[numero] = item
    return out



def correcoes_seguras_status(record: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Lista apenas correções históricas que completam pré-requisitos obrigatórios.

    Regras conservadoras da HF7:
    - Entregue implica Pronto;
    - Pronto implica Aprovado;
    - Pago implica Aprovado.

    Nunca infere ``Pago``, nunca desfaz um status e não cria datas históricas.
    """
    record = record or {}
    aprovado = status_bool(record, "aprovado")
    pago = status_bool(record, "pago")
    pronto = status_bool(record, "pronto")
    entregue = status_bool(record, "entregue")
    correcoes: list[dict[str, Any]] = []

    if entregue and not pronto:
        correcoes.append({
            "campo": "pronto",
            "valor_anterior": False,
            "valor_novo": True,
            "motivo": "Entregue exige Pronto",
        })

    if not aprovado and (pago or pronto or entregue):
        motivos = []
        if pago:
            motivos.append("Pago")
        if pronto:
            motivos.append("Pronto")
        elif entregue:
            motivos.append("Entregue")
        correcoes.append({
            "campo": "aprovado",
            "valor_anterior": False,
            "valor_novo": True,
            "motivo": f"{'/'.join(motivos)} exige Aprovado",
        })
    return correcoes


def aplicar_correcoes_seguras_status(record: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Aplica no registro somente as correções retornadas acima e devolve o que mudou."""
    if not isinstance(record, dict):
        return []
    correcoes = correcoes_seguras_status(record)
    for correcao in correcoes:
        record[str(correcao["campo"])] = True
    return correcoes


def planejar_saneamento_status_historicos(
    propostas: Iterable[dict] | None,
) -> dict[str, Any]:
    """Cria uma prévia sem mutar as propostas."""
    planos: list[dict[str, Any]] = []
    total_alteracoes = 0
    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        numero = _numero(proposta)
        if not numero:
            continue
        correcoes = correcoes_seguras_status(proposta)
        if not correcoes:
            continue
        planos.append({
            "pedido": numero,
            "cliente": str(proposta.get("cliente_nome") or proposta.get("cliente") or "").strip(),
            "correcoes": correcoes,
        })
        total_alteracoes += len(correcoes)
    return {
        "propostas": len(planos),
        "alteracoes": total_alteracoes,
        "planos": planos,
    }

def auditar_consistencia_operacional(
    propostas: Iterable[dict] | None,
    tarefas_fluxo: Iterable[dict] | None,
    previsao_risco: Iterable[dict] | None,
    fila_entregas: Iterable[dict] | None = None,
) -> dict[str, Any]:
    """Compara as projeções com a Fonte Única Oficial.

    Retorna conjuntos/listas úteis para diagnóstico. Não grava nada.
    """
    propostas_validas = [p for p in (propostas or []) if isinstance(p, dict) and _numero(p)]
    por_numero = {_numero(p): p for p in propostas_validas}
    estados = {numero: resumo_status(p) for numero, p in por_numero.items()}

    oficiais_operacionais = {
        numero for numero, estado in estados.items()
        if estado.get("ativa") and not estado.get("entregue")
    }
    oficiais_aprovados_abertos = {
        numero for numero, estado in estados.items()
        if estado.get("ativa") and estado.get("aprovado") and not estado.get("entregue")
    }
    oficiais_prontos_saida = {
        numero for numero, estado in estados.items()
        if estado.get("ativa") and estado.get("aprovado") and estado.get("pronto") and not estado.get("entregue")
    }

    tarefas = [t for t in (tarefas_fluxo or []) if isinstance(t, dict) and _numero(t)]
    fluxo_ativos = {_numero(t) for t in tarefas if t.get("ativa", True)}
    fluxo_inativos = {_numero(t) for t in tarefas if not t.get("ativa", True)}

    previsoes = [p for p in (previsao_risco or []) if isinstance(p, dict) and _numero(p)]
    previsao_numeros = {_numero(p) for p in previsoes}
    risco_numeros = {_numero(p) for p in previsoes if str(p.get("chave") or "") == "risco_atraso"}

    saidas = [p for p in (fila_entregas or []) if isinstance(p, dict) and _numero(p)]
    saida_numeros = {_numero(p) for p in saidas}

    fluxo_faltantes = sorted(oficiais_operacionais - fluxo_ativos)
    fluxo_fechados_ativos = sorted(
        numero for numero in fluxo_ativos
        if numero in estados and numero not in oficiais_operacionais
    )
    fluxo_orfaos = sorted(numero for numero in fluxo_ativos if numero not in estados)

    previsao_faltantes = sorted(oficiais_aprovados_abertos - previsao_numeros)
    previsao_indevida = sorted(
        numero for numero in previsao_numeros
        if numero not in oficiais_aprovados_abertos
    )
    risco_indevido = sorted(
        numero for numero in risco_numeros
        if numero not in oficiais_aprovados_abertos
        or estados.get(numero, {}).get("pronto")
        or estados.get(numero, {}).get("entregue")
        or estados.get(numero, {}).get("encerrada")
    )

    saida_faltantes = sorted(oficiais_prontos_saida - saida_numeros) if fila_entregas is not None else []
    saida_indevida = sorted(
        numero for numero in saida_numeros
        if numero not in oficiais_prontos_saida
    ) if fila_entregas is not None else []

    contradicoes: list[dict[str, str]] = []
    for numero, estado in estados.items():
        if estado.get("pago") and not estado.get("aprovado"):
            contradicoes.append({"pedido": numero, "problema": "Pago sem Aprovado"})
        # A leitura oficial faz Entregue implicar Pronto; ainda assim vale apontar
        # combinações brutas suspeitas para o saneamento histórico seguro da HF7.
        proposta = por_numero[numero]
        bruto_entregue = status_bool(proposta, "entregue")
        bruto_pronto = status_bool(proposta, "pronto")
        bruto_aprovado = status_bool(proposta, "aprovado")
        if bruto_pronto and not bruto_aprovado:
            contradicoes.append({"pedido": numero, "problema": "Pronto sem Aprovado"})
        if bruto_entregue and not bruto_pronto:
            contradicoes.append({"pedido": numero, "problema": "Registro bruto Entregue sem Pronto"})

    problemas = (
        len(fluxo_faltantes) + len(fluxo_fechados_ativos) + len(fluxo_orfaos)
        + len(previsao_faltantes) + len(previsao_indevida) + len(risco_indevido)
        + len(saida_faltantes) + len(saida_indevida) + len(contradicoes)
    )

    return {
        "ok": problemas == 0,
        "problemas": problemas,
        "contagens": {
            "propostas": len(propostas_validas),
            "operacionais_oficiais": len(oficiais_operacionais),
            "aprovados_abertos": len(oficiais_aprovados_abertos),
            "prontos_saida": len(oficiais_prontos_saida),
            "fluxo_ativos": len(fluxo_ativos),
            "previsao": len(previsao_numeros),
            "risco": len(risco_numeros),
            "fila_saida": len(saida_numeros),
        },
        "fluxo_faltantes": fluxo_faltantes,
        "fluxo_fechados_ativos": fluxo_fechados_ativos,
        "fluxo_orfaos": fluxo_orfaos,
        "fluxo_inativos": sorted(fluxo_inativos),
        "previsao_faltantes": previsao_faltantes,
        "previsao_indevida": previsao_indevida,
        "risco_indevido": risco_indevido,
        "saida_faltantes": saida_faltantes,
        "saida_indevida": saida_indevida,
        "contradicoes": contradicoes,
    }
