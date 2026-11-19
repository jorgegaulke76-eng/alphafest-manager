"""Snapshot operacional compartilhado da Central AlphaFest.

HF36 — consolida, em uma única fotografia somente leitura, os cálculos que
antes eram repetidos no mesmo rerun da Central: previsão de produção, fila de
saída, central de produção e prioridades operacionais.

Nenhum status é persistido por este módulo. As fontes oficiais continuam sendo
Histórico, consumo/reservas, estoque, planejamento de compras e Fluxo.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable

from risco_producao_engine import montar_previsao_producao
from central_producao_engine import montar_central_producao, resumo_central
from central_entregas_engine import montar_fila, resumo_fila
from proposal_status import resumo_status
from prioridade_operacional_engine import (
    montar_prioridades_operacionais,
    resumo_prioridades,
    indexar_prioridades,
)


def montar_snapshot_operacional(
    propostas: Iterable[dict] | None,
    tarefas_ativas: Iterable[dict] | None,
    consumos: Iterable[dict] | None,
    estoque: dict[str, Any] | None,
    planejamentos: Iterable[dict] | None,
    hoje: date,
    *,
    resumo_produtos: Callable[[dict], str] | None = None,
    sob_encomenda: bool = False,
) -> dict[str, Any]:
    """Monta uma fotografia coerente e reaproveitável da operação.

    A função mantém as mesmas engines já homologadas. O ganho vem apenas de
    executar cada derivação uma vez e compartilhar o resultado entre os blocos
    da Central no mesmo rerun.
    """
    propostas_l = list(propostas or [])
    tarefas_l = list(tarefas_ativas or [])
    consumos_l = list(consumos or [])
    planejamentos_l = list(planejamentos or [])
    estoque_d = estoque if isinstance(estoque, dict) else {}
    movimentos = list(estoque_d.get("movimentacoes") or [])

    # HF38 — a Central inteira compartilha a mesma leitura oficial de status.
    # Isso evita recalcular Aprovado/Pago/Pronto/Entregue em Entregas,
    # Prioridades e novamente na própria tela. Regra e fonte continuam sendo
    # proposal_status.resumo_status.
    status_por_numero: dict[str, dict] = {}
    propostas_por_numero: dict[str, dict] = {}
    propostas_operacionais: list[dict] = []
    propostas_aprovadas_abertas: list[dict] = []
    propostas_aguardando_aprovacao: list[dict] = []
    propostas_pagamento_pendente: list[dict] = []
    for proposta in propostas_l:
        if not isinstance(proposta, dict):
            continue
        status = resumo_status(proposta)
        numero = str(proposta.get("numero_proposta") or "").strip()
        if numero:
            status_por_numero[numero] = status
            propostas_por_numero[numero] = proposta
        if not status.get("encerrada"):
            propostas_operacionais.append(proposta)
            if status.get("aprovado") and not status.get("entregue"):
                propostas_aprovadas_abertas.append(proposta)
            if not status.get("aprovado") and not status.get("entregue"):
                propostas_aguardando_aprovacao.append(proposta)
        if status.get("pagamento_individual_pendente"):
            propostas_pagamento_pendente.append(proposta)

    consumos_ativos_por_proposta: dict[str, dict] = {}
    for consumo in consumos_l:
        if not isinstance(consumo, dict) or consumo.get("estornado"):
            continue
        numero = str(consumo.get("numero_proposta") or "").strip()
        if numero:
            # Preserva a semântica anterior da compreensão em dict: a última
            # ocorrência ativa do mesmo número vence.
            consumos_ativos_por_proposta[numero] = consumo

    fila_entregas = montar_fila(
        propostas_l,
        hoje,
        resumo_produtos=resumo_produtos,
        status_por_numero=status_por_numero,
    )
    if sob_encomenda:
        from datetime import datetime
        previsao = []
        for proposta in propostas_aprovadas_abertas:
            status = status_por_numero.get(str(proposta.get("numero_proposta") or ""), {})
            numero = str(proposta.get("numero_proposta") or "").strip()
            if not numero:
                continue
            raw = proposta.get("data_entrega")
            data_entrega = None
            if hasattr(raw, "year") and hasattr(raw, "month"):
                data_entrega = raw.date() if isinstance(raw, datetime) else raw
            elif raw:
                for formato in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        data_entrega = datetime.strptime(str(raw)[:10], formato).date()
                        break
                    except ValueError:
                        pass
            dias = (data_entrega - hoje).days if data_entrega else None
            pronto = bool(status.get("pronto"))
            risco = bool(dias is not None and dias < 0 and not pronto)
            base = "pronto_aguardando_entrega" if pronto else "liberado"
            legenda = "📦 Pronto — aguardando entrega" if pronto else "🟢 Pedido aprovado — sob encomenda"
            previsao.append({
                "numero_proposta": numero,
                "cliente_nome": str(proposta.get("cliente_nome") or "Cliente"),
                "resumo_produtos": resumo_produtos(proposta) if resumo_produtos else "",
                "pronto_oficial": pronto,
                "data_entrega": data_entrega,
                "data_entrega_original": raw,
                "dias_ate_entrega": dias,
                "consumo": None, "resumo_consumo": None, "pendencias": [], "materiais": [],
                "chave_base": base, "chave": "risco_atraso" if risco else base,
                "status_base": legenda,
                "status": "🔴 Entrega atrasada" if risco else legenda,
                "risco_atraso": risco,
                "motivos": ["prazo de entrega vencido"] if risco else [],
                "severidade": 0 if risco else (4 if pronto else 5),
                "quantidade_materiais_pendentes": 0,
                "quantidade_materiais_sem_cobertura": 0,
            })
        previsao.sort(key=lambda p: (p["severidade"], p["data_entrega"] or date.max, p["numero_proposta"]))
    else:
        previsao = montar_previsao_producao(
            propostas_l,
            consumos_l,
            movimentos,
            planejamentos_l,
            hoje=hoje,
        )
    central_producao = montar_central_producao(
        previsao,
        tarefas_l,
        hoje=hoje,
        sob_encomenda=sob_encomenda,
    )
    prioridades = montar_prioridades_operacionais(
        propostas_l,
        hoje,
        central_producao=central_producao,
        fila_entregas=fila_entregas,
        resumo_produtos=resumo_produtos,
        status_por_numero=status_por_numero,
    )

    return {
        "status_por_numero": status_por_numero,
        "propostas_por_numero": propostas_por_numero,
        "propostas_operacionais": propostas_operacionais,
        "propostas_aprovadas_abertas": propostas_aprovadas_abertas,
        "propostas_aguardando_aprovacao": propostas_aguardando_aprovacao,
        "propostas_pagamento_pendente": propostas_pagamento_pendente,
        "consumos_ativos_por_proposta": consumos_ativos_por_proposta,
        "previsao": previsao,
        "central_producao": central_producao,
        "resumo_central_producao": resumo_central(central_producao),
        "fila_entregas": fila_entregas,
        "resumo_fila_entregas": resumo_fila(fila_entregas),
        "prioridades": prioridades,
        "resumo_prioridades": resumo_prioridades(prioridades),
        "mapa_prioridades": indexar_prioridades(prioridades),
    }
